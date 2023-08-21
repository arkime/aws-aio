import json
import logging

from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.ssm_operations as ssm_ops
import core.constants as constants
from core.cross_account_wrangling import CrossAccountAssociation

logger = logging.getLogger(__name__)

def cmd_vpc_register_cluster(profile: str, region: str, cluster_account_id: str, cluster_name: str,
                             cross_account_role: str, vpc_account_id: str, vpc_id: str, vpce_service_id: str):
    logger.debug(f"Invoking vpc-register-cluster with profile '{profile}' and region '{region}'")

    logger.info("Registering the Cluster with the VPC...")
    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)
    aws_env = aws_provider.get_aws_env()

    if aws_env.aws_account != vpc_account_id:
        logger.error("This command must be called with AWS Credential associated with the same AWS Account as the VPC"
                     + f" {vpc_id}.  Expected Account: {vpc_account_id}, Actual Account: {aws_env.aws_account}."
                     + " Aborting...")
        return

    # Create the association Param
    ssm_param = constants.get_cluster_vpc_cross_account_ssm_param_name(cluster_name, vpc_id)
    association = CrossAccountAssociation(
        cluster_account_id, cluster_name, cross_account_role, aws_env.aws_account, vpc_id, vpce_service_id
    )
    logger.info(f"Updating config details in Param Store at: {ssm_param}")
    ssm_ops.put_ssm_param(
        ssm_param,
        json.dumps(association.to_dict()),
        aws_provider,
        description=f"The cross-account configuration details for {cluster_name} and {vpc_id}",
        overwrite=True
    )
    