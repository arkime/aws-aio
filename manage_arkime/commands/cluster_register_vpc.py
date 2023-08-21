import json
import logging
from typing import Dict, List

from botocore.exceptions import ClientError

import arkime_interactions.config_wrangling as config_wrangling
from aws_interactions.aws_client_provider import AwsClientProvider
from aws_interactions.aws_environment import AwsEnvironment
import aws_interactions.ssm_operations as ssm_ops
import core.constants as constants
from core.cross_account_wrangling import CrossAccountAssociation

logger = logging.getLogger(__name__)

def cmd_cluster_register_vpc(profile: str, region: str, cluster_name: str, vpc_account_id: str, vpc_id: str):
    logger.debug(f"Invoking cluster-register-vpc with profile '{profile}' and region '{region}'")

    logger.info("Registering the VPC with the Cluster...")
    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)
    aws_env = aws_provider.get_aws_env()

    # Confirm the cluster exists
    try:
        vpce_service_id = ssm_ops.get_ssm_param_json_value(
            constants.get_cluster_ssm_param_name(cluster_name),
            "vpceServiceId",
            aws_provider
        )
    except ssm_ops.ParamDoesNotExist:
        logger.error(f"The cluster {cluster_name} does not exist; try using the clusters-list command to see the clusters you have created.")
        logger.warning("Aborting...")
        return

    # Create the cross account IAM role
    role_arn = _ensure_cross_account_role_exists(cluster_name, vpc_account_id, vpc_id, aws_provider, aws_env)

    # Add the GWLB permissions
    _add_vpce_permissions(vpce_service_id, vpc_account_id, aws_provider)

    # Create the association Param
    ssm_param = constants.get_cluster_vpc_cross_account_ssm_param_name(cluster_name, vpc_id)
    association = CrossAccountAssociation(
        aws_env.aws_account, cluster_name, role_arn, vpc_account_id, vpc_id, vpce_service_id
    )
    logger.info(f"Updating config details in Param Store at: {ssm_param}")
    ssm_ops.put_ssm_param(
        ssm_param,
        json.dumps(association.to_dict()),
        aws_provider,
        description=f"The cross-account configuration details for {cluster_name} and {vpc_id}",
        overwrite=True
    )

    logger.info(f"Cross-account association details: \n{json.dumps(association.to_dict(), indent=4)}")
    logger.info("CLI Command to register the Cluster with the VPC in the VPC Account: \n"
                + f"./manage_arkime.py vpc-register-cluster --cluster-account-id {association.clusterAccount}"
                + f" --cluster-name {association.clusterName} --cross-account-role {association.roleArn}"
                + f" --vpc-account-id {association.vpcAccount} --vpc-id {association.vpcId} --vpce-service-id {association.vpceServiceId}"
    )

def _get_iam_role_name(cluster_name: str, vpc_id: str):
    # There's a maximum length of 64 characters we have to work around.  VPC IDs are quite unique, so we'll lean
    # on that to make our life easier.  We take as many of the characters from the cluster name as we can fit.
    prefix = "arkime_"
    suffix = f"_{vpc_id}"
    max_chars_from_cluster_name = 64 - len(prefix) - len(suffix)
    beginning_of_cluster_name = cluster_name[:max_chars_from_cluster_name]
    return f"{prefix}{beginning_of_cluster_name}{suffix}" # Like: arkime_MyCluster_vpc-0f08710cdbc32d58a

def _does_iam_role_exist(role_name: str, aws_provider: AwsClientProvider):
    iam_client = aws_provider.get_iam()

    try:
        iam_client.get_role(RoleName=role_name)
        return True
    except ClientError as ex:
        if ex.response['Error']['Code'] == 'NoSuchEntity':
            return False
        raise ex

def _ensure_cross_account_role_exists(cluster_name: str, vpc_account_id: str, vpc_id: str,
                                      aws_provider: AwsClientProvider, aws_env: AwsEnvironment):
    logger.info("Ensuring the cross-account IAM role exists, as expected...")

    role_name = _get_iam_role_name(cluster_name, vpc_id)
    iam_client = aws_provider.get_iam()

    trust_relationship = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": f"arn:aws:iam::{vpc_account_id}:root"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    if _does_iam_role_exist(role_name, aws_provider):
        # Make sure the trust policy is as we expect
        iam_client.update_assume_role_policy(
            RoleName=role_name,
            PolicyDocument=json.dumps(trust_relationship)
        )
    else:
        iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_relationship),
            Description=f"Arkime cross-account role assumable by {vpc_account_id}",
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

    role_arn = f"arn:aws:iam::{aws_env.aws_account}:role/{role_name}"
    logger.info(f"Cross account role exists and is configured: {role_arn}")
    return role_arn

def _add_vpce_permissions(vpce_service_id: str, vpc_account_id: str, aws_provider: AwsClientProvider):
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

    

    