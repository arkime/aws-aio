import json
import logging

from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.ssm_operations as ssm_ops
import core.constants as constants
from core.cross_account_wrangling import CrossAccountAssociation

logger = logging.getLogger(__name__)

def cmd_vpc_deregister_cluster(profile: str, region: str, cluster_name: str, vpc_id: str):
    logger.debug(f"Invoking vpc-register-cluster with profile '{profile}' and region '{region}'")

    logger.info("De-registering the Cluster with the VPC...")
    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)    

    # Create the association Param
    ssm_param = constants.get_cluster_vpc_cross_account_ssm_param_name(cluster_name, vpc_id)

    try:
        raw_association = ssm_ops.get_ssm_param_value(
            constants.get_cluster_vpc_cross_account_ssm_param_name(cluster_name, vpc_id),
            aws_provider
        )
        association = CrossAccountAssociation(**json.loads(raw_association))
    except ssm_ops.ParamDoesNotExist:
        logger.warning(f"VPC {vpc_id} does not appear to be associated with Cluster {cluster_name}; aborting...")
        return
    
    aws_env = aws_provider.get_aws_env()
    if aws_env.aws_account != association.vpcAccount:
        logger.error("This command must be called with AWS Credential associated with the same AWS Account as the VPC"
                     + f" {vpc_id}.  Expected Account: {association.vpcAccount}, Actual Account: {aws_env.aws_account}."
                     + " Aborting...")
        return

    logger.info(f"Removing association details from Param Store at: {ssm_param}")
    ssm_ops.delete_ssm_param(
        ssm_param,
        aws_provider
    )



    