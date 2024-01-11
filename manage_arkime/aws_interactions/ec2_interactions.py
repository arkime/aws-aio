from dataclasses import dataclass
import logging
from typing import List, Dict

from botocore.exceptions import ClientError

from aws_interactions.aws_client_provider import AwsClientProvider

logger = logging.getLogger(__name__)

class VpcDoesNotExist(Exception):
    def __init__(self, vpc_id: str):
        self.vpc_id = vpc_id
        super().__init__(f"The AWS VPC {vpc_id} does not exist")

def get_subnets_of_vpc(vpc_id: str, aws_provider: AwsClientProvider) -> List[str]:
    ec2_client = aws_provider.get_ec2()
    subnets_response = ec2_client.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )

    # Will be [] if the VPC does not exist; all VPCs have at least one subnet
    if not subnets_response["Subnets"]: 
        raise VpcDoesNotExist(vpc_id=vpc_id)
    subnet_ids = [subnet["SubnetId"] for subnet in subnets_response["Subnets"]]

    next_token = subnets_response.get("NextToken")
    while next_token:
        subnets_response = ec2_client.describe_subnets(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}],
            NextToken=next_token
        )
        next_subnets = [subnet["SubnetId"] for subnet in subnets_response["Subnets"]]
        subnet_ids.extend(next_subnets)
        next_token = subnets_response.get("NextToken")

    return subnet_ids

@dataclass
class NetworkInterface:
    vpc_id: str
    subnet_id: str
    eni_id: str
    eni_type: str

    def to_dict(self):
        return {
            'vpc_id': self.vpc_id,
            'subnet_id': self.subnet_id,
            'eni_id': self.eni_id,
            'eni_type': self.eni_type,
        }

def get_enis_of_instance(instance_id: str, aws_provider: AwsClientProvider) -> List[NetworkInterface]:
    ec2_client = aws_provider.get_ec2()
    describe_instance_response = ec2_client.describe_instances(
        InstanceIds=[instance_id]
    )
    instance_details = describe_instance_response["Reservations"][0]["Instances"][0]

    network_interfaces = []
    for eni in instance_details.get("NetworkInterfaces", []):
        network_interfaces.append(
            NetworkInterface(eni["VpcId"], eni["SubnetId"], eni["NetworkInterfaceId"], eni["InterfaceType"])
        )

    return network_interfaces

def get_enis_of_subnet(subnet_id: str, aws_provider: AwsClientProvider) -> List[NetworkInterface]:
    ec2_client = aws_provider.get_ec2()
    describe_eni_response = ec2_client.describe_network_interfaces(
            Filters=[{"Name": "subnet-id", "Values": [subnet_id]}]
    )
    network_interfaces = []
    for eni in describe_eni_response.get("NetworkInterfaces", []):
        network_interfaces.append(
            NetworkInterface(eni["VpcId"], eni["SubnetId"], eni["NetworkInterfaceId"], eni["InterfaceType"])
        )

    next_token = describe_eni_response.get("NextToken")
    while next_token:
        describe_eni_response = ec2_client.describe_network_interfaces(
            Filters=[{"Name": "subnet-id", "Values": [subnet_id]}],
            NextToken=next_token
        )
        next_interfaces = []
        for eni in describe_eni_response.get("NetworkInterfaces", []):
            next_interfaces.append(
                NetworkInterface(eni["VpcId"], eni["SubnetId"], eni["NetworkInterfaceId"], eni["InterfaceType"])
            )
        network_interfaces.extend(next_interfaces)
        next_token = describe_eni_response.get("NextToken")

    return network_interfaces

NON_MIRRORABLE_ENI_TYPES = ["gateway_load_balancer_endpoint", "nat_gateway"]

class NonMirrorableEniType(Exception):
    def __init__(self, eni: NetworkInterface):
        self.eni = eni
        super().__init__(f"The ENI {eni.eni_id} is of type {eni.eni_type}, which is not mirrorable")

"""
Sets up a VPC Traffic Mirroring Session on a given ENI towards the specified Traffic Target using the specified
Traffic Filter and returns the Traffic Session ID.
"""
def mirror_eni(eni: NetworkInterface, traffic_target: str, traffic_filter: str, vpc_id: str, aws_provider: AwsClientProvider, virtual_network: int = 123) -> str:
    if eni.eni_type in NON_MIRRORABLE_ENI_TYPES:
        raise NonMirrorableEniType(eni)

    ec2_client = aws_provider.get_ec2()
    create_session_response = ec2_client.create_traffic_mirror_session(
        NetworkInterfaceId=eni.eni_id,
        TrafficMirrorTargetId=traffic_target,
        TrafficMirrorFilterId=traffic_filter,
        SessionNumber=1,
        VirtualNetworkId=virtual_network,
        TagSpecifications=[
            {
                "ResourceType": "traffic-mirror-session",
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": f"{vpc_id}-{eni.eni_id}"
                    },
                ]
            },
        ],
    )

    return create_session_response["TrafficMirrorSession"]["TrafficMirrorSessionId"]


class MirrorDoesntExist(Exception):
    def __init__(self, session: str):
        self.session = session
        super().__init__(f"The Traffic Mirror Session {session} does not exist")

def delete_eni_mirroring(traffic_session: str, aws_provider: AwsClientProvider) -> str:
    ec2_client = aws_provider.get_ec2()

    try:
        ec2_client.delete_traffic_mirror_session(
            TrafficMirrorSessionId=traffic_session
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "InvalidTrafficMirrorSessionId.NotFound":
            raise MirrorDoesntExist(traffic_session)
        else:
            raise

@dataclass
class VpcDetails:
    vpc_id: str
    owner_id: str
    cidr_blocks: List[str]
    tenancy: str

    def to_dict(self) -> Dict[str, any]:
        return {
            'vpc_id': self.vpc_id,
            'owner_id': self.owner_id,
            'cidr_blocks': self.cidr_blocks,
            'tenancy': self.tenancy,
        }

def get_vpc_details(vpc_id: str, aws_provider: AwsClientProvider) -> VpcDetails:
    ec2_client = aws_provider.get_ec2()
    describe_vpc_response = ec2_client.describe_vpcs(
        VpcIds=[vpc_id]
    )

    # Will be [] if the VPC does not exist
    if not describe_vpc_response["Vpcs"]: 
        raise VpcDoesNotExist(vpc_id=vpc_id)

    vpc_details = describe_vpc_response["Vpcs"][0]
    cidr_blocks = [item["CidrBlock"] for item in vpc_details["CidrBlockAssociationSet"] if item["CidrBlockState"]["State"] in ["associating", "associated"]]

    return VpcDetails(
        vpc_id=vpc_details["VpcId"],
        owner_id=vpc_details["OwnerId"],
        cidr_blocks=cidr_blocks,
        tenancy=vpc_details["InstanceTenancy"]
    )

def get_azs_in_region(aws_provider: AwsClientProvider) -> List[str]:
    ec2_client = aws_provider.get_ec2()

    response = ec2_client.describe_availability_zones()
    azs = [az["ZoneName"] for az in response["AvailabilityZones"]]

    return azs