import json
import logging

from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.iam_interactions as iami
import aws_interactions.ssm_operations as ssm_ops
import core.constants as constants
from core.cross_account_wrangling import CrossAccountAssociation, remove_vpce_permissions

logger = logging.getLogger(__name__)

def cmd_cluster_deregister_vpc(profile: str, region: str, cluster_name: str, vpc_id: str):
    logger.debug(f"Invoking cluster-deregister-vpc with profile '{profile}' and region '{region}'")

    logger.info("Deregistering the VPC with the Cluster...")
    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)

    # Confirm the cross-account link exists
    try:
        ssm_param_name = constants.get_cluster_vpc_cross_account_ssm_param_name(cluster_name, vpc_id)
        raw_association = ssm_ops.get_ssm_param_value(
            ssm_param_name,
            aws_provider
        )
        association = CrossAccountAssociation(**json.loads(raw_association))
    except ssm_ops.ParamDoesNotExist:
        logger.warning(f"The cluster {cluster_name} is not registered with VPC {vpc_id}")
        logger.warning("Aborting...")
        return
    
    aws_env = aws_provider.get_aws_env()
    if aws_env.aws_account != association.clusterAccount:
        logger.error("This command must be called with AWS Credential associated with the same AWS Account as the Cluster"
                     + f" {cluster_name}.  Expected Account: {association.clusterAccount}, Actual Account: {aws_env.aws_account}."
                     + " Aborting...")
        return
    
    # Delete the cross-account IAM role
    logger.info(f"Removing the cross-account access role: {association.roleName}")
    iami.delete_iam_role(association.roleName, aws_provider)

    # Removing the GWLB permissions
    logger.info(f"Removing permissions for Account {association.vpcAccount} to create GWLBE Endpoints on: {association.vpceServiceId}")
    remove_vpce_permissions(cluster_name, vpc_id, aws_provider)

    # Remove the Param Store entry
    logger.info(f"Removing association details from Param Store at: {ssm_param_name}")
    ssm_ops.delete_ssm_param(
        ssm_param_name,
        aws_provider
    )





    

    