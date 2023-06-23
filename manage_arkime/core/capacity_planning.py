from dataclasses import dataclass
import math
import logging
from typing import Dict, Type, TypeVar


logger = logging.getLogger(__name__)

INSTANCE_TYPE_CAPTURE_NODE = "m5.xlarge" # Arbitrarily chosen
TRAFFIC_PER_M5_XL = 2 # in Gbps, guestimate, should be updated with experimental data
MAX_TRAFFIC = 100 # Gbps, scaling limit of a single User Subnet VPC Endpoint
MINIMUM_NODES = 1 # We'll always have at least one capture node
MINIMUM_TRAFFIC = 0.01 # Gbps; arbitrarily chosen, but will yield a minimal cluster
CAPACITY_BUFFER_FACTOR = 1.25 # Arbitrarily chosen
MASTER_NODE_COUNT = 3 # Recommended number in docs
DEFAULT_SPI_DAYS = 30 # How many days of SPI metadata to keep in the OS Domain
DEFAULT_REPLICAS = 1 # How replicas of metadata to keep in the OS Domain
DEFAULT_HISTORY_DAYS = 365 # How many days of Arkime Viewer user history to keep in the OS Domain
DEFAULT_NUM_AZS = 2 # How many AWS Availability zones to utilize

class TooMuchTraffic(Exception):
    def __init__(self, expected_traffic: int):
        super().__init__(f"User's expected traffic ({expected_traffic} Gbps) exceeds the limit of a single cluster ({MAX_TRAFFIC})")

class NotEnoughStorage(Exception):
    def __init__(self, expected_traffic: int):
        super().__init__(f"User's expected traffic ({expected_traffic} Gbps) exceeds the limit of a OpenSearch Domain to store.")

@dataclass
class CaptureNodesPlan:
    instanceType: str
    desiredCount: int
    maxCount: int
    minCount: int

    def __equal__(self, other) -> bool:
        return (self.instanceType == other.instance_type and self.desiredCount == other.desired_count
                and self.maxCount == other.max_count and self.minCount == other.min_count)

    def to_dict(self) -> Dict[str, any]:
        return {
            "instanceType": self.instanceType,
            "desiredCount": self.desiredCount,
            "maxCount": self.maxCount,
            "minCount": self.minCount,
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

    def __equal__(self, other) -> bool:
        return self.cpu == other.cpu and self.memory == other.memory

    def to_dict(self) -> Dict[str, any]:
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
    instanceType: str
    volumeSize: int # in GiB

    def __equal__(self, other) -> bool:
        return (self.count == other.count and self.instanceType == other.type
                and self.volumeSize == other.vol_size)

    def to_dict(self) -> Dict[str, any]:
        return {
            "count": self.count,
            "instanceType": self.instanceType,
            "volumeSize": self.volumeSize
        }
    
@dataclass
class MasterNodesPlan:
    count: int
    instanceType: str

    def __equal__(self, other) -> bool:
        return (self.count == other.count and self.instanceType == other.type)

    def to_dict(self) -> Dict[str, any]:
        return {
            "count": self.count,
            "instanceType": self.instanceType
        }

T_OSDomainPlan = TypeVar('T_OSDomainPlan', bound='OSDomainPlan')

@dataclass
class OSDomainPlan:
    dataNodes: DataNodesPlan
    masterNodes: MasterNodesPlan

    def __equal__(self, other) -> bool:
        return (self.dataNodes == other.dataNodes
                and self.masterNodes == other.masterNodes)

    def to_dict(self) -> Dict[str, any]:
        return {
            "dataNodes": self.dataNodes.to_dict(),
            "masterNodes": self.masterNodes.to_dict()
        }
    
    @classmethod
    def from_dict(cls: Type[T_OSDomainPlan], input: Dict[str, any]) -> T_OSDomainPlan:
        data_nodes = DataNodesPlan(**input["dataNodes"])
        master_nodes = MasterNodesPlan(**input["masterNodes"])
        return cls(data_nodes, master_nodes)
    
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
    return _get_storage_per_replica(expected_traffic, spi_days) * (1 + replicas)

def _get_data_node_plan(total_storage: float, num_azs: int) -> DataNodesPlan:
    """
    Per the OpenSearch Service limits doc [1], you can have a maximum of 10 T2/T3 data nodes or 80 of other types by
    default.  You can raise this limit up to 200.  To keep things simple, we will assume if the user needs more storage
    than 80 of the largest instance type can provide, they'll bump the limit out of band and just keep getting more of
    that largest instance type. There's also an apparent incentive to have more, smaller nodes than fewer, larger
    nodes [2].
    
    We ensure there are at least two data nodes of whichever type is selected for the
    capacity plan.

    An additional constraint is that you must have an even number of data nodes if you have two AZs.

    [1] https://docs.aws.amazon.com/opensearch-service/latest/developerguide/limits.html
    [2] https://github.com/arkime/aws-aio/issues/56#issuecomment-1563652060

    total_storage: full storage requirement for all data, including replicas, in GiB
    """

    if total_storage <= 10 * T3_SMALL_SEARCH.vol_size:
        node = T3_SMALL_SEARCH
    elif total_storage <= 80 * R6G_LARGE_SEARCH.vol_size:
        node = R6G_LARGE_SEARCH
    elif total_storage <= 80 * R6G_4XLARGE_SEARCH.vol_size:
        node = R6G_4XLARGE_SEARCH
    elif total_storage <= 80 * R6G_12XLARGE_SEARCH.vol_size:
        node = R6G_12XLARGE_SEARCH
    else:
        node = R6G_12XLARGE_SEARCH # overflow with our largest instance type

    num_of_nodes = max(math.ceil(total_storage / node.vol_size), 2)
    if num_azs == 2:
        num_of_nodes = math.ceil(num_of_nodes / 2) * 2 # The next largest even integer

    plan = DataNodesPlan(
        count = num_of_nodes,
        instanceType = node.type,
        volumeSize = node.vol_size
    )

    return plan

def _get_master_node_plan(storage_per_replica: float, data_node_count: int, data_node_type: str) -> MasterNodesPlan:
    """
    We follow the sizing recommendation in the docs [1].  One complicating 

    [1] https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-dedicatedmasternodes.html

    storage_per_replica: storage required for each replica, in GiB
    """

    # Arkime is a write-heavy usecase so recommended data/shard is 30-50 GiB, per the docs.
    # See: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/sizing-domains.html#bp-sharding
    storage_per_shard = 40 # GiB
    num_shards = math.ceil(storage_per_replica / storage_per_shard)

    if data_node_type == T3_SMALL_SEARCH.type:
        # You can't mix graviton and non-graviton instance types across the data/master node roles.  Additionally,
        # there are no "toy"-class graviton data node instance types.  Therefore, we need this (hacky) check to
        # make sure we're using a compatible type.
        node_type = "m5.large.search"
    elif num_shards <= 10000 and data_node_count <= 10:
        node_type = "m6g.large.search"
    elif num_shards <= 30000 and data_node_count <= 30:
        node_type = "c6g.2xlarge.search"
    elif num_shards <= 75000 and data_node_count <= 125:
        node_type = "r6g.2xlarge.search"
    else:
        node_type = "r6g.4xlarge.search"

    return MasterNodesPlan(
        count = MASTER_NODE_COUNT,
        instanceType = node_type
    )
    
def get_os_domain_plan(expected_traffic: float, spi_days: int, replicas: int, num_azs: int) -> OSDomainPlan:
    """
    Get the OpenSearch Domain capacity required to satisify the expected traffic

    expected_traffic: traffic volume to the capture nodes, in Gbps
    spi_days: the number of days to retain the SPI data stored in the OpenSearch Domain
    replicas: the number of replicas to have of the data
    num_azs: the number of AZs in the domain's VPC
    """

    storage_per_replica = _get_storage_per_replica(expected_traffic, spi_days)
    total_storage = _get_total_storage(expected_traffic, spi_days, replicas)

    data_node_plan = _get_data_node_plan(total_storage, num_azs)
    master_node_plan = _get_master_node_plan(storage_per_replica, data_node_plan.count, data_node_plan.instanceType)

    return OSDomainPlan(data_node_plan, master_node_plan)

@dataclass
class CaptureVpcPlan:
    numAzs: int

    def __equal__(self, other) -> bool:
        return self.numAzs == other.numAzs
    
    def to_dict(self) -> Dict[str, any]:
        return {
            "numAzs": self.numAzs
        }
    
DEFAULT_S3_STORAGE_CLASS = "STANDARD"
DEFAULT_S3_STORAGE_DAYS = 30

@dataclass
class S3Plan:
    pcapStorageClass: str
    pcapStorageDays: int

    def __equal__(self, other) -> bool:
        return self.pcapStorageClass == other.pcapStorageClass and self.pcapStorageDays == other.pcapStorageDays
    
    def to_dict(self) -> Dict[str, any]:
        return {
            "pcapStorageClass": self.pcapStorageClass,
            "pcapStorageDays": self.pcapStorageDays
        }
    
T_ClusterPlan = TypeVar('T_ClusterPlan', bound='ClusterPlan')

@dataclass
class ClusterPlan:
    captureNodes: CaptureNodesPlan
    captureVpc: CaptureVpcPlan
    ecsResources: EcsSysResourcePlan
    osDomain: OSDomainPlan
    s3: S3Plan

    def __equal__(self, other) -> bool:
        return (self.captureNodes == other.captureNodes and self.ecsResources == other.ecsResources 
                and self.osDomain == other.osDomain and self.captureVpc == other.vpc and self.s3 == other.s3)

    def to_dict(self) -> Dict[str, any]:
        return {
            "captureNodes": self.captureNodes.to_dict(),
            "captureVpc": self.captureVpc.to_dict(),
            "ecsResources": self.ecsResources.to_dict(),
            "osDomain": self.osDomain.to_dict(),
            "s3": self.s3.to_dict(),
        }
    
    @classmethod
    def from_dict(cls: Type[T_ClusterPlan], input: Dict[str, any]) -> T_ClusterPlan:
        capture_nodes = CaptureNodesPlan(**input["captureNodes"])
        capture_vpc = CaptureVpcPlan(**input["captureVpc"])
        ecs_resources = EcsSysResourcePlan(**input["ecsResources"])
        os_domain = OSDomainPlan.from_dict(input["osDomain"])
        s3 = S3Plan(**input["s3"])

        return cls(capture_nodes, capture_vpc, ecs_resources, os_domain, s3)
    
