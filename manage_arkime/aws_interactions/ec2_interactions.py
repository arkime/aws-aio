from dataclasses import dataclass
import logging
from typing import List

from botocore.exceptions import ClientError

from manage_arkime.aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.ssm_operations as ssm_ops
from manage_arkime.cdk_client import CdkClient
import manage_arkime.constants as constants
import manage_arkime.cdk_context as context

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
    id: str
    type: str

def get_enis_of_subnet(subnet_id: str, aws_provider: AwsClientProvider) -> List[NetworkInterface]:
    ec2_client = aws_provider.get_ec2()
    describe_eni_response = ec2_client.describe_network_interfaces(
            Filters=[{"Name": "subnet-id", "Values": [subnet_id]}]
    )
    network_inferfaces = [NetworkInterface(eni["NetworkInterfaceId"], eni["InterfaceType"]) for eni in describe_eni_response.get("NetworkInterfaces", [])]

    next_token = describe_eni_response.get("NextToken")
    while next_token:
        describe_eni_response = ec2_client.describe_network_interfaces(
            Filters=[{"Name": "subnet-id", "Values": [subnet_id]}],
            NextToken=next_token
        )
        next_interfaces = [NetworkInterface(eni["NetworkInterfaceId"], eni["InterfaceType"]) for eni in describe_eni_response.get("NetworkInterfaces", [])]
        network_inferfaces.extend(next_interfaces)
        next_token = describe_eni_response.get("NextToken")

    return network_inferfaces

NON_MIRRORABLE_ENI_TYPES = ["gateway_load_balancer_endpoint", "nat_gateway"]

class NonMirrorableEniType(Exception):
    def __init__(self, eni: NetworkInterface):
        self.eni = eni
        super().__init__(f"The ENI {eni.id} is of type {eni.type}, which is not mirrorable")

"""
Sets up a VPC Traffic Mirroring Session on a given ENI towards the specified Traffic Target using the specified
Traffic Filter and returns the Traffic Session ID.
"""
def mirror_eni(eni: NetworkInterface, traffic_target: str, traffic_filter: str, aws_provider: AwsClientProvider, virtual_network: int = 123) -> str:
    if eni.type in NON_MIRRORABLE_ENI_TYPES:
        raise NonMirrorableEniType(eni)

    ec2_client = aws_provider.get_ec2()
    create_session_response = ec2_client.create_traffic_mirror_session(
        NetworkInterfaceId=eni.id,
        TrafficMirrorTargetId=traffic_target,
        TrafficMirrorFilterId=traffic_filter,
        SessionNumber=1,
        VirtualNetworkId=virtual_network
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
        if exc.response['Error']['Code'] == 'InvalidTrafficMirrorSessionId.NotFound':
            raise MirrorDoesntExist(traffic_session)
        else:
            raise