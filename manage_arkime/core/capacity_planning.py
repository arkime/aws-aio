from dataclasses import dataclass
from enum import Enum
import math
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

INSTANCE_TYPE_CAPTURE_NODE = "m5.xlarge" # Arbitrarily chosen
TRAFFIC_PER_M5_XL = 2 # in Gbps, guestimate, should be updated with experimental data
MAX_TRAFFIC = 100 # Gbps, scaling limit of a single User Subnet VPC Endpoint
MINIMUM_NODES = 1 # We'll always have at least one capture node
MINIMUM_TRAFFIC = MINIMUM_NODES * TRAFFIC_PER_M5_XL
CAPACITY_BUFFER_FACTOR = 1.25 # Arbitrarily chosen

class TooMuchTraffic(Exception):
    def __init__(self, expected_traffic: int):
        super().__init__(f"User's expected traffic ({expected_traffic} Gbps) exceeds the limit of a single cluster ({MAX_TRAFFIC})")

class NotEnoughStorage(Exception):
    def __init__(self, expected_traffic: int):
        super().__init__(f"User's expected traffic ({expected_traffic} Gbps) exceeds the limit of a OpenSearch Domain to store.")

@dataclass
class CaptureNodesPlan:
    instance_type: str
    desired_count: int
    max_count: int
    min_count: int

    def __equal__(self, other):
        return (self.instance_type == other.instance_type and self.desired_count == other.desired_count
                and self.max_count == other.max_count and self.min_count == other.min_count)

    def to_dict(self) -> Dict[str, str]:
        return {
            "instanceType": self.instance_type,
            "desiredCount": self.desired_count,
            "maxCount": self.max_count,
            "minCount": self.min_count,
        }

def get_capture_node_capacity_plan(expected_traffic: float) -> CaptureNodesPlan:
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

    def to_dict(self) -> Dict[str, str]:
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


"""
This factor is a simplified knockdown that converts the raw packet volume to the amount of OpenSearch Domain storage.
It is based on awick@'s experience, and encompasses the following sub-factors:
* The ratio of raw-packet-data size to metadata-size
* OpenSearch indexing overhead (10%) [1]
* Linux system reserved space (5%) [1]
* OpenSearch Service overhead (20%) [1]

[1] https://docs.aws.amazon.com/opensearch-service/latest/developerguide/sizing-domains.html
"""
MAGIC_FACTOR = 0.03

@dataclass
class DataNode:
    type: str
    vol_size: int # in GiB

T3_SMALL_SEARCH = DataNode("t3.small.search", 100)
R6G_LARGE_SEARCH = DataNode("r6g.large.search", 1024)
R6G_4XLARGE_SEARCH = DataNode("r6g.4xlarge.search", 6*1024)
R6G_12XLARGE_SEARCH = DataNode("r6g.12xlarge.search", 12*1024)

@dataclass
class DataNodesPlan:
    count: int
    type: str
    vol_size: int # in GiB

    def __equal__(self, other):
        return (self.count == other.count and self.type == other.type
                and self.vol_size == other.vol_size)

    def to_dict(self) -> Dict[str, str]:
        return {
            "count": self.count,
            "type": self.type,
            "volSize": self.vol_size
        }
    
@dataclass
class MasterNodesPlan:
    count: int
    type: str

    def __equal__(self, other):
        return (self.count == other.count and self.type == other.type)

    def to_dict(self) -> Dict[str, str]:
        return {
            "count": self.count,
            "type": self.type
        }

@dataclass
class OSDomainPlan:
    data_nodes: DataNodesPlan
    master_nodes: MasterNodesPlan

    def __equal__(self, other):
        return (self.data_nodes == other.dataNodes
                and self.master_nodes == other.masterNodes)

    def to_dict(self) -> Dict[str, str]:
        return {
            "dataNodes": self.data_nodes.to_dict(),
            "masterNodes": self.master_nodes.to_dict()
        }
    
def _get_storage_per_replica(expected_traffic: float, spi_days: int) -> float:
    """
    Predict the required OpenSearch domain storage for each replica, in GiB

    expected_traffic: traffic volume to the capture nodes, in Gbps
    spi_days: the number of days to retain the SPI data stored in the OpenSearch Domain
    """
    return (spi_days * 24 * 60 * 60) * expected_traffic/8 * MAGIC_FACTOR

def _get_total_storage(expected_traffic: float, spi_days: int, replicas: int) -> float:
    """
    Predict the total required OpenSearch domain storage, in GiB

    expected_traffic: traffic volume to the capture nodes, in Gbps
    spi_days: the number of days to retain the SPI data stored in the OpenSearch Domain
    replicas: the number of replicas to have of the data
    """
    return _get_storage_per_replica(expected_traffic, spi_days) * replicas

def _get_data_node_plan(total_storage: float) -> DataNodesPlan:
    """
    Per the OpenSearch Service limits doc [1], you can have a maximum of 10 T2/T3 data nodes or 80 of other types by
    default.  You can raise this limit up to 200.  To keep things simple, we will assume if the user needs more storage
    than 80 of the largest instance type can provide, they'll bump the limit out of band and just keep getting more of
    that largest instance type.

    There's also an apparent incentive to have more, smaller nodes than fewer, larger nodes [2]

    [1] https://docs.aws.amazon.com/opensearch-service/latest/developerguide/limits.html
    [2] https://github.com/arkime/aws-aio/issues/56#issuecomment-1563652060

    total_storage: full stage requirement for all data, including replicas, in GiB
    """

    if total_storage <= 10 * T3_SMALL_SEARCH.vol_size:
        node = T3_SMALL_SEARCH
    elif total_storage <= 80 * R6G_LARGE_SEARCH.vol_size:
        node = R6G_LARGE_SEARCH
    elif total_storage <= 80 * R6G_4XLARGE_SEARCH.vol_size:
        node = R6G_4XLARGE_SEARCH
    elif total_storage <= 80 * R6G_12XLARGE_SEARCH.vol_size:
        node = R6G_12XLARGE_SEARCH

    plan = DataNodesPlan(
        count = math.ceil(total_storage / node.vol_size),
        type = node.type,
        vol_size = node.vol_size
    )

    return plan

def _get_master_node_plan(storage_per_replica: float, data_node_count: int) -> MasterNodesPlan:
    """
    We follow the sizing recommendation in the docs [1].

    [1] https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-dedicatedmasternodes.html

    storage_per_replica: storage required for each replica, in GiB
    """

    # Arkime is a write-heavy usecase so recommended data/shard is 30-50 GiB, per the docs.
    # See: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/sizing-domains.html#bp-sharding
    storage_per_shard = 40 # GiB
    num_shards = math.ceil(storage_per_replica / storage_per_shard)

    if num_shards <= 10000 and data_node_count <= 10:
        node_type = "m6g.large.search"
    elif num_shards <= 30000 and data_node_count <= 30:
        node_type = "c6g.2xlarge.search"
    elif num_shards <= 75000 and data_node_count <= 125:
        node_type = "r6g.2xlarge.search"
    else:
        node_type = "r6g.4xlarge.search"

    return MasterNodesPlan(
        count = 3, # Recommended number in docs
        type = node_type
    )
    
def get_os_domain_plan(expected_traffic: float, spi_days: int, replicas: int) -> OSDomainPlan:
    """
    Get the OpenSearch Domain capacity required to satisify the expected traffic
    """

    storage_per_replica = _get_storage_per_replica(expected_traffic, spi_days)
    total_storage = _get_total_storage(expected_traffic, spi_days, replicas)

    data_node_plan = _get_data_node_plan(total_storage)
    master_node_plan = _get_master_node_plan(storage_per_replica, data_node_plan.count)

    return OSDomainPlan(data_node_plan, master_node_plan)