from dataclasses import dataclass
import math
import logging

logger = logging.getLogger(__name__)

INSTANCE_TYPE_CAPTURE_NODE = "m5.xlarge" # Arbitrarily chosen
TRAFFIC_PER_M5_XL = 2 # in Gbps, guestimate, should be updated with experimental data
MAX_TRAFFIC = 100 # Gbps, scaling limit of a single User Subnet VPC Endpoint
MINIMUM_NODES = 1 # We'll always have at least one capture node
MINIMUM_TRAFFIC = MINIMUM_NODES * TRAFFIC_PER_M5_XL
CAPACITY_BUFFER_FACTOR = 1.25 # Arbitrarily chosen

class TooMuchTraffic(Exception):
    def __init__(self, expected_traffic: int):
        super().__init__(f"User's expected traffic ({expected_traffic} Gbps) exceed the limit of a single cluster ({MAX_TRAFFIC})")

@dataclass
class CaptureNodesPlan:
    instance_type: str
    desired_count: int
    max_count: int
    min_count: int

    def __equal__(self, other):
        return (self.instance_type == other.instance_type and self.desired_count == other.desired_count
                and self.max_count == other.max_count and self.min_count == other.min_count)

    def to_dict(self):
        return {
            "instanceType": self.instance_type,
            "desiredCount": self.desired_count,
            "maxCount": self.max_count,
            "minCount": self.min_count,
        }

def get_capture_node_capacity_plan(expected_traffic: int) -> CaptureNodesPlan:
    """
    Creates a capacity plan for the indicated traffic load.
    expected_traffic: The expected traffic volume for the Arkime cluster, in Gigabits Per Second (Gbps)
    """

    if not expected_traffic or expected_traffic < TRAFFIC_PER_M5_XL:
        desired_instances = MINIMUM_NODES
    elif expected_traffic > MAX_TRAFFIC:
        raise TooMuchTraffic(expected_traffic)
    else:
        desired_instances = math.ceil(expected_traffic/TRAFFIC_PER_M5_XL)

    return CaptureNodesPlan(
        INSTANCE_TYPE_CAPTURE_NODE,
        desired_instances,
        math.ceil(desired_instances * CAPACITY_BUFFER_FACTOR),
        MINIMUM_NODES
    )


class UnknownInstanceType(Exception):
    def __init__(self, instance_type: str):
        super().__init__(f"Unknown instance type: {instance_type}")

@dataclass
class EcsSysResourcePlan:
    cpu: int # vCPUs; 1024 per 1 vCPU
    memory: int # in MB

    def __equal__(self, other):
        return self.cpu == other.cpu and self.memory == other.memory

    def to_dict(self):
        return {
            "cpu": self.cpu,
            "memory": self.memory
        }

def get_ecs_sys_resource_plan(instance_type: str) -> EcsSysResourcePlan:
    """
    Creates a capacity plan for the indicated instance type.
    instance_type: The instance type to plan for
    """

    if instance_type == INSTANCE_TYPE_CAPTURE_NODE:
        # We want the full capacity of our m5.xlarge because we're using HOST network type and therefore won't
        # place multiple containers on a single host.  However, we can't ask for ALL of its resources (ostensibly,
        # 4 vCPU and 16 GiB) because then ECS placement will fail.  We therefore ask for a slightly reduced
        # amount.  This is the minimum amount we're requesting ECS to reserve, so it can't reserve more than
        # exist.
        return EcsSysResourcePlan(
            3584, # 3.5 vCPUs
            15360 # 15 GiB
        )
    else:
        raise UnknownInstanceType(instance_type)