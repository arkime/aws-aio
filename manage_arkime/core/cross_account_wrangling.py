from dataclasses import dataclass
import json
import logging
from typing import Dict

from aws_interactions.aws_client_provider import AwsClientProvider
from aws_interactions.aws_environment import AwsEnvironment
from aws_interactions.iam_interactions import does_iam_role_exist


logger = logging.getLogger(__name__)

@dataclass
class CrossAccountAssociation:
    clusterAccount: str
    clusterName: str
    roleName: str
    vpcAccount: str
    vpcId: str
    vpceServiceId: str

    def __equal__(self, other) -> bool:
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