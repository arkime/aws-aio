import json
import logging

from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.ssm_operations as ssm_ops
import core.constants as constants
from core.cross_account_wrangling import CrossAccountAssociation, ensure_cross_account_role_exists, add_vpce_permissions

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

    # Create the cross account IAM role for the VPC account to access the Cluster account
    role_name = ensure_cross_account_role_exists(cluster_name, vpc_account_id, vpc_id, aws_provider, aws_env)

    # Add the GWLB permissions
    add_vpce_permissions(vpce_service_id, vpc_account_id, aws_provider)

    # Create the association Param
    ssm_param = constants.get_cluster_vpc_cross_account_ssm_param_name(cluster_name, vpc_id)
    association = CrossAccountAssociation(
        aws_env.aws_account, cluster_name, role_name, vpc_account_id, vpc_id, vpce_service_id
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
                + f" --cluster-name {association.clusterName} --cross-account-role {association.roleName}"
                + f" --vpc-account-id {association.vpcAccount} --vpc-id {association.vpcId} --vpce-service-id {association.vpceServiceId}"
    )
    