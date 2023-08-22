from dataclasses import dataclass
import logging
from typing import List, Dict

from botocore.exceptions import ClientError

from aws_interactions.aws_client_provider import AwsClientProvider

logger = logging.getLogger(__name__)

def does_iam_role_exist(role_name: str, aws_provider: AwsClientProvider):
    iam_client = aws_provider.get_iam()

    try:
        iam_client.get_role(RoleName=role_name)
        return True
    except ClientError as ex:
        if ex.response['Error']['Code'] == 'NoSuchEntity':
            return False
        raise ex

def delete_iam_role(role_name: str, aws_provider: AwsClientProvider):
    """
    One does not simply delete an IAM role; you have to follow the right steps.
    https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_manage_delete.html#roles-managingrole-deleting-cli
    """

    iam_client = aws_provider.get_iam()

    if not does_iam_role_exist(role_name, aws_provider):
        logger.debug(f"Role {role_name} does not exist; skipping deletion steps")
        return
    logger.debug(f"Deleting role: {role_name}")

    # Remove any attached instance profiles
    list_profiles_response = iam_client.list_instance_profiles_for_role(RoleName=role_name)
    for profile in list_profiles_response["InstanceProfiles"]:
        iam_client.remove_role_from_instance_profile(
            InstanceProfileName=profile["InstanceProfileName"],
            RoleName=role_name
        )
        
    # Remove any inline policies
    list_inline_policies_response = iam_client.list_role_policies(RoleName=role_name)
    for inline_policy_name in list_inline_policies_response["PolicyNames"]:
        iam_client.delete_role_policy(
            RoleName=role_name,
            PolicyName=inline_policy_name
        )
        
    # Detach any managed policies
    list_managed_policies_response = iam_client.list_attached_role_policies(RoleName=role_name)
    for managed_policy in list_managed_policies_response["AttachedPolicies"]:
        iam_client.detach_role_policy(
            RoleName=role_name,
            PolicyArn=managed_policy["PolicyArn"]
        )

    # Now we can delete the IAM role
    iam_client.delete_role(RoleName=role_name)