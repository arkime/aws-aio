from abc import ABC, abstractmethod
import json
import logging
from typing import Dict, List

import constants as constants
from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.ssm_operations as ssm_ops

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

It tracks two different pieces of state:
* An incrementing integer that allows us to find the next, unused VNI when the user doesn't specify one
* The mapping of all VNIs the user specified to the VPCs they're associated with
"""
class SsmVniProvider(VniProvider):
    def __init__(self, cluster_name: str, aws_provider: AwsClientProvider):
        super().__init__(cluster_name)
        self.aws_provider = aws_provider

    """
    Get the next available VNI that's not already assigned
    """
    def get_next_vni(self) -> int:
        # Get the next unused VNI
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

        # Update our current VNI counter if appropriate
        current_autogen_vni = self._get_current_autogen_vni()
        if vni > current_autogen_vni:
            self._update_current_autogen_vni(vni)

    """
    Mark a user-specified VNI as in-use
    """
    def register_user_vni(self, vni: int, vpc_id: str):
        # Raise if outside acceptable range
        if (vni < constants.VNI_MIN) or (vni > constants.VNI_MAX):
            raise VniOutsideRange(vni)

        # Get existing state
        user_vnis_map = self._get_user_vnis_mapping()

        # Add to the mapping
        if vni in user_vnis_map:
            user_vnis_map[vni].append(vpc_id)
        else:
            user_vnis_map[vni] = [vpc_id]
        self._update_user_vnis_mapping(user_vnis_map)

    def is_vni_available(self, vni: int):
        # Raise if outside acceptable range
        if (vni < constants.VNI_MIN) or (vni > constants.VNI_MAX):
            raise VniOutsideRange(vni)

        return True

    """
    Remove a VNI from use.  Remove from the user-specified list if relevant.
    """
    def relinquish_vni(self, vni: int, vpc_id: str):
        # Raise if outside acceptable range
        if (vni < constants.VNI_MIN) or (vni > constants.VNI_MAX):
            raise VniOutsideRange(vni)

        # Get existing state
        user_vnis_map = self._get_user_vnis_mapping()
        
        # Remove from user-list if in there
        if vni in user_vnis_map:
            vpcs_for_vni = user_vnis_map[vni]
            vpcs_for_vni.remove(vpc_id)

            if not vpcs_for_vni:
                user_vnis_map.pop(vni)
            else:
                user_vnis_map[vni] = vpcs_for_vni
            
            self._update_user_vnis_mapping(user_vnis_map)

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

    def _update_user_vnis_mapping(self, new_value: Dict[int, List[str]]) -> Dict[int, List[str]]:
        ssm_ops.put_ssm_param(
            constants.get_vnis_user_ssm_param_name(self.cluster_name),
            json.dumps(new_value),
            self.aws_provider,
            description=f"User-specified mapping of the VNIs associated with VPCs monitored by cluster {self.cluster_name}",
            overwrite=True
        )
        return new_value

    def _get_user_vnis_mapping(self) -> Dict[int, List[str]]:
        ssm_param_name = constants.get_vnis_user_ssm_param_name(self.cluster_name)
        try:
            raw_value = ssm_ops.get_ssm_param_value(ssm_param_name, self.aws_provider)
            raw_mapping: Dict[str, List[str]] = json.loads(raw_value) # This our VNI ints will be strings; need to convert back
            return {int(k): v for k, v in raw_mapping.items()}
        except ssm_ops.ParamDoesNotExist:
            return self._update_user_vnis_mapping({})

    def _get_user_vnis(self) -> List[int]:
        mapping = self._get_user_vnis_mapping()
        return list(mapping.keys())