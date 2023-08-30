from dataclasses import dataclass
import json
import logging
import re
from typing import Dict, List

from aws_interactions.aws_client_provider import AwsClientProvider
from aws_interactions.aws_environment import AwsEnvironment
from aws_interactions.iam_interactions import does_iam_role_exist
import aws_interactions.ssm_operations as ssm_ops
import core.constants as constants


logger = logging.getLogger(__name__)

@dataclass
class CrossAccountAssociation:
    clusterAccount: str
    clusterName: str
    roleName: str
    vpcAccount: str
    vpcId: str
    vpceServiceId: str

    def __eq__(self, other) -> bool:
        return (self.clusterAccount == other.clusterAccount
                and self.clusterName == other.clusterName
                and self.roleName == other.roleName
                and self.vpcAccount == other.vpcAccount
                and self.vpcId == other.vpcId
                and self.vpceServiceId == other.vpceServiceId)

    def to_dict(self) -> Dict[str, str]:
        return {
            'clusterAccount': self.clusterAccount,
            'clusterName': self.clusterName,
            'roleName': self.roleName,
            'vpcAccount': self.vpcAccount,
            'vpcId': self.vpcId,
            'vpceServiceId': self.vpceServiceId
        }

def get_iam_role_name(cluster_name: str, vpc_id: str):
    # There's a maximum length of 64 characters we have to work around.  VPC IDs are quite unique, so we'll lean
    # on that to make our life easier.  We take as many of the characters from the cluster name as we can fit.
    prefix = "arkime_"
    suffix = f"_{vpc_id}"
    max_chars_from_cluster_name = 64 - len(prefix) - len(suffix)
    beginning_of_cluster_name = cluster_name[:max_chars_from_cluster_name]
    return f"{prefix}{beginning_of_cluster_name}{suffix}" # Like: arkime_MyCluster_vpc-0f08710cdbc32d58a

def ensure_cross_account_role_exists(cluster_name: str, other_account_id: str, vpc_id: str,
                                      aws_provider: AwsClientProvider, aws_env: AwsEnvironment):
    logger.info("Ensuring the cross-account IAM role exists, as expected...")

    role_name = get_iam_role_name(cluster_name, vpc_id)
    iam_client = aws_provider.get_iam()

    trust_relationship = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": f"arn:aws:iam::{other_account_id}:root"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    if does_iam_role_exist(role_name, aws_provider):
        # Make sure the trust policy is as we expect
        iam_client.update_assume_role_policy(
            RoleName=role_name,
            PolicyDocument=json.dumps(trust_relationship)
        )
    else:
        iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_relationship),
            Description=f"Arkime cross-account role assumable by {other_account_id}",
        )
    
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ssm:DeleteParameter",
                    "ssm:GetParameter",
                    "ssm:GetParameters",
                    "ssm:PutParameter",
                ],
                "Resource": f"arn:aws:ssm:{aws_env.aws_region}:{aws_env.aws_account}:parameter/arkime/clusters/{cluster_name}*"
            }
        ]
    }

    iam_client.put_role_policy(
        RoleName=role_name,
        PolicyName='CrossAcctSSMAccessPolicy',
        PolicyDocument=json.dumps(policy)
    )

    logger.info(f"Cross account role exists and is configured: {role_name}")
    return role_name

def add_vpce_permissions(vpce_service_id: str, vpc_account_id: str, aws_provider: AwsClientProvider):
    """
    Add the root account principal for the AWS account containing the VPC to our Gateway Load Balancer's
    whitelist of actors that can make GWLB Endpoints directed towards it.  Any IAM user/role in the account will
    be allowed to make the Endpoint.
    """
    logger.info(f"Ensuring actors in AWS Account {vpc_account_id} can add/remove Gateway Loadbalancer Endpoints...")
    ec2_client = aws_provider.get_ec2()
    ec2_client.modify_vpc_endpoint_service_permissions(
        ServiceId=vpce_service_id,
        AddAllowedPrincipals=[
            f"arn:aws:iam::{vpc_account_id}:root"
        ]
    )

def remove_vpce_permissions(cluster_name: str, vpc_id: str, aws_provider: AwsClientProvider):
    """
    Removes the root account principal for the AWS account containing the VPC from our Gateway Load Balancer's
    whitelist of actors that can make GWLB Endpoints directed towards it - if no other VPCs need that permission.
    """
    associations = get_cross_account_associations(cluster_name, aws_provider)

    vpc_filtered_associations = list(filter(lambda x: x.vpcId == vpc_id, associations))
    if not vpc_filtered_associations:
        logger.warning(f"VPC {vpc_id} is not associated with Cluster {cluster_name}; skipping...")
        return
    
    vpc_association = vpc_filtered_associations[0]
    other_vpcs_in_same_account = list(filter(lambda x: x.vpcAccount == vpc_association.vpcAccount and x.vpcId != vpc_id, associations))
    if other_vpcs_in_same_account:
        logger.info(f"There are {len(other_vpcs_in_same_account)} other VPCs currently using this permission; skipping...")
        logger.debug(f"Other VPCs still using the whitelist: {[vpc.vpcId for vpc in associations]}")
        return

    ec2_client = aws_provider.get_ec2()
    ec2_client.modify_vpc_endpoint_service_permissions(
        ServiceId=vpc_association.vpceServiceId,
        RemoveAllowedPrincipals=[
            f"arn:aws:iam::{vpc_association.vpcAccount}:root"
        ]
    )

def get_cross_account_associations(cluster_name: str, aws_provider: AwsClientProvider) -> List[CrossAccountAssociation]:
    """
    Gets all the cross-account associations for the cluster
    """

    cluster_ssm_param_name = constants.get_cluster_ssm_param_name(cluster_name)
    associations = []

    ssm_vpcs_path_prefix = f"{cluster_ssm_param_name}/vpcs"
    ssm_paths = ssm_ops.get_ssm_params_by_path(ssm_vpcs_path_prefix, aws_provider, recursive=True)

    cross_account_regex = re.compile(f"^{ssm_vpcs_path_prefix}/vpc\\-[a-zA-Z0-9]+/cross-account$")
    cross_account_params = [path for path in ssm_paths if cross_account_regex.match(path["Name"])]
    for cross_account_param in cross_account_params:
        associations.append(CrossAccountAssociation(**json.loads(cross_account_param["Value"])))
    
    return associations

@dataclass
class CrossAccountVpcDetail:
    busArn: str
    mirrorFilterId: str
    mirrorVni: str
    vpcAccount: str
    vpcId: str

    def __eq__(self, other) -> bool:
        return (self.busArn == other.busArn
                and self.mirrorFilterId == other.mirrorFilterId
                and self.mirrorVni == other.mirrorVni
                and self.vpcAccount == other.vpcAccount
                and self.vpcId == other.vpcId)

    def to_dict(self) -> Dict[str, str]:
        return {
            'busArn': self.busArn,
            'mirrorFilterId': self.mirrorFilterId,
            'mirrorVni': self.mirrorVni,
            'vpcAccount': self.vpcAccount,
            'vpcId': self.vpcId
        }

def get_cross_account_vpc_details(cluster_name: str, aws_provider: AwsClientProvider) -> List[CrossAccountVpcDetail]:
    """
    Gets the full details of all cross-account VPCs associated with the cluster
    """
    vpc_details = []
    cross_account_associations = get_cross_account_associations(cluster_name, aws_provider)

    for association in cross_account_associations:
        cross_account_role_arn = f"arn:aws:iam::{association.vpcAccount}:role/{association.roleName}"
        cross_account_provider = AwsClientProvider(
            aws_profile=aws_provider._aws_profile,
            aws_region=aws_provider._aws_region,
            assume_role_arn=cross_account_role_arn
        )

        # Get the VPC details from the Param entry using a cross-account call
        vpc_param_name = constants.get_vpc_ssm_param_name(association.clusterName, association.vpcId)
        vpc_detail = json.loads(ssm_ops.get_ssm_param_value(vpc_param_name, cross_account_provider))
        vpc_detail["vpcAccount"] = association.vpcAccount
        vpc_details.append(CrossAccountVpcDetail(**vpc_detail))        
    
    return vpc_details