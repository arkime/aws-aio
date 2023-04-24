from abc import ABC, abstractmethod
import json
import logging
from typing import List

import manage_arkime.constants as constants
from manage_arkime.aws_interactions.aws_client_provider import AwsClientProvider
import manage_arkime.aws_interactions.ssm_operations as ssm_ops

logger = logging.getLogger(__name__)

class VniAlreadyUsed(Exception):
    def __init__(self, vni: int):
        self.vni = vni
        super().__init__(f"The VNI {vni} has already been assigned to a VPC")

class VniOutsideRange(Exception):
    def __init__(self, vni: int):
        self.vni = vni
        super().__init__(f"The VNI {vni} is outside the acceptable range {constants.VNI_MIN}-{constants.VNI_MAX}")

class VniPoolExhausted(Exception):
    def __init__(self):
        super().__init__(f"There are no available VNIs in the range {constants.VNI_MIN}-{constants.VNI_MAX}")

"""
ABC to present a consistent interface for managing the VNIs associated with User VPCs.  The VNI/VPC mappings are unique
to a given cluster.
"""
class VniProvider(ABC):
    def __init__(self, cluster_name: str):
        self.cluster_name = cluster_name

    @abstractmethod
    def get_next_vni(self) -> int:
        pass

    @abstractmethod
    def use_next_vni(self, vni: int):
        pass

    @abstractmethod
    def register_user_vni(self, vni: int):
        pass

    @abstractmethod
    def is_vni_available(self, vni: int):
        pass

    @abstractmethod
    def relinquish_vni(self, vni: int):
        pass


"""
Uses SSM Parameter Store to manage VNI state.

It tracks three different pieces of state:
* An incrementing integer that allows us to find the next, unused VNI when the user doesn't specify one
* The list of all VNIs the user specified
* A list of any previously-relinquished VNIs that we can recycle
"""
class SsmVniProvider(VniProvider):
    def __init__(self, cluster_name: str, aws_provider: AwsClientProvider):
        super().__init__(cluster_name)
        self.aws_provider = aws_provider

    """
    Get the next available VNI that's not already assigned, preferring a recycled one if possible
    """
    def get_next_vni(self) -> int:
        # Use a recycled VNI if possible
        recycled_vnis = self._get_recycled_vnis()
        if recycled_vnis:
            unique_vni = recycled_vnis.pop()
            return unique_vni

        # Otherwise, get the next unused VNI
        user_vnis = self._get_user_vnis()
        current_autogen_vni = self._get_current_autogen_vni()
        next_vni = current_autogen_vni + 1

        while next_vni in user_vnis:
            next_vni += 1

        # No more VNIs to choose from, according to the standard
        if next_vni > constants.VNI_MAX:
            raise VniPoolExhausted()

        # VNI is valid; return
        return next_vni

    """
    Mark a non-user-specified VNI as in-use.  It is expected, but not enforced, that the VNI supplied to this method
    come from an immediately preceding invocation of get_next_vni()
    """
    def use_next_vni(self, vni: int):
        # Raise if outside acceptable range
        if (vni < constants.VNI_MIN) or (vni > constants.VNI_MAX):
            raise VniOutsideRange(vni)
        
        # Remove from list of recycled VNIs if it's in there
        recycled_vnis = self._get_recycled_vnis()
        if vni in recycled_vnis:
            recycled_vnis.remove(vni)
            self._update_recycled_vnis(recycled_vnis)

        # Update our current VNI counter if appropriate
        current_autogen_vni = self._get_current_autogen_vni()
        if vni > current_autogen_vni:
            self._update_current_autogen_vni(vni)

    """
    Mark a user-specified VNI as in-use, as long as it hasn't already been assigned
    """
    def register_user_vni(self, vni: int):
        # Raise if outside acceptable range
        if (vni < constants.VNI_MIN) or (vni > constants.VNI_MAX):
            raise VniOutsideRange(vni)

        # Get existing state
        recycled_vnis = self._get_recycled_vnis()
        user_vnis = self._get_user_vnis()
        current_autogen_vni = self._get_current_autogen_vni()

        # Raise if we've already used this VNI
        is_recycled = vni in recycled_vnis # Free to re-use
        is_user_assigned = vni in user_vnis # Collision
        is_previous_autogen = vni <= current_autogen_vni # Collision
        if not is_recycled and (is_user_assigned or is_previous_autogen):
            raise VniAlreadyUsed(vni)

        # Update our list of user VNIs
        user_vnis.append(vni)
        self._update_user_vnis(user_vnis)

        # If it was in the recycled list, update that too
        if is_recycled:
            recycled_vnis.remove(vni)
            self._update_recycled_vnis(recycled_vnis)

    def is_vni_available(self, vni: int):
        # Raise if outside acceptable range
        if (vni < constants.VNI_MIN) or (vni > constants.VNI_MAX):
            raise VniOutsideRange(vni)

        recycled_vnis = self._get_recycled_vnis()
        user_vnis = self._get_user_vnis()
        current_autogen_vni = self._get_current_autogen_vni()

        is_in_use = (vni in user_vnis) or ((vni <= current_autogen_vni) and vni not in recycled_vnis)

        return not is_in_use

    """
    Remove a VNI from use.  Remove from the user-specified list if relevant.  Add to list of recycled VNIs if
    appropriate.
    """
    def relinquish_vni(self, vni: int):
        # Raise if outside acceptable range
        if (vni < constants.VNI_MIN) or (vni > constants.VNI_MAX):
            raise VniOutsideRange(vni)

        # Get existing state
        recycled_vnis = self._get_recycled_vnis()
        user_vnis = self._get_user_vnis()
        current_autogen_vni = self._get_current_autogen_vni()
        
        # Remove from user-list if in there
        if vni in user_vnis:
            user_vnis.remove(vni)
            self._update_user_vnis(user_vnis)

        # Add to our list of available VNIs if we'd otherwise miss it with auto assignment
        if (vni >= constants.VNI_MIN) and (vni <= current_autogen_vni):
            recycled_vnis.append(vni)
            self._update_recycled_vnis(recycled_vnis)

    def _update_current_autogen_vni(self, new_value: int) -> int:
        ssm_ops.put_ssm_param(
            constants.get_vni_current_ssm_param_name(self.cluster_name),
            str(new_value),
            self.aws_provider,
            description=f"The most recently auto-assigned VNI for cluster {self.cluster_name}",
            overwrite=True
        )
        return new_value

    def _get_current_autogen_vni(self) -> int:
        ssm_param_name = constants.get_vni_current_ssm_param_name(self.cluster_name)
        try:
            raw_value = ssm_ops.get_ssm_param_value(ssm_param_name, self.aws_provider)
            return int(raw_value)
        except ssm_ops.ParamDoesNotExist:
            # Subtract 1 because we increment before assigning a VNI and want the first value to be VNI_MIN
            return self._update_current_autogen_vni(constants.VNI_MIN - 1)

    def _update_recycled_vnis(self, new_values: List[int]) -> List[int]:
        ssm_ops.put_ssm_param(
            constants.get_vnis_recycled_ssm_param_name(self.cluster_name),
            json.dumps(new_values),
            self.aws_provider,
            description=f"List of recycled VNIs ready for re-use by cluster {self.cluster_name}",
            overwrite=True
        )
        return new_values

    def _get_recycled_vnis(self) -> List[int]:
        ssm_param_name = constants.get_vnis_recycled_ssm_param_name(self.cluster_name)
        try:
            raw_value = ssm_ops.get_ssm_param_value(ssm_param_name, self.aws_provider)
            return json.loads(raw_value)
        except ssm_ops.ParamDoesNotExist:
            return self._update_recycled_vnis([])

    def _update_user_vnis(self, new_value: List[int]) -> List[int]:
        ssm_ops.put_ssm_param(
            constants.get_vnis_user_ssm_param_name(self.cluster_name),
            json.dumps(new_value),
            self.aws_provider,
            description=f"User-specified list of VNIs currently mapped to VPCs monitored by cluster {self.cluster_name}",
            overwrite=True
        )
        return new_value

    def _get_user_vnis(self) -> List[int]:
        ssm_param_name = constants.get_vnis_user_ssm_param_name(self.cluster_name)
        try:
            raw_value = ssm_ops.get_ssm_param_value(ssm_param_name, self.aws_provider)
            return json.loads(raw_value)
        except ssm_ops.ParamDoesNotExist:
            return self._update_user_vnis([])