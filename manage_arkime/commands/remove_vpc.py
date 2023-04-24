import json
import logging

from botocore.exceptions import ClientError

from manage_arkime.aws_interactions.aws_client_provider import AwsClientProvider
import manage_arkime.aws_interactions.ec2_interactions as ec2i
import manage_arkime.aws_interactions.ssm_operations as ssm_ops
from manage_arkime.cdk_client import CdkClient
import manage_arkime.constants as constants
import manage_arkime.cdk_context as context
from manage_arkime.vni_provider import SsmVniProvider

logger = logging.getLogger(__name__)


# vni = ssm_ops.get_ssm_param_json_value(vpc_ssm_param, "mirrorVni", aws_provider)

def cmd_remove_vpc(profile: str, region: str, cluster_name: str, vpc_id: str):
    logger.debug(f"Invoking remove-vpc with profile '{profile}' and region '{region}'")

    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)

    # Confirm the Cluster exists before proceeding
    try:
        vpce_service_id = ssm_ops.get_ssm_param_json_value(constants.get_cluster_ssm_param_name(cluster_name), "vpceServiceId", aws_provider)
    except ssm_ops.ParamDoesNotExist:
        logger.error(f"The cluster {cluster_name} does not exist; try using the list-clusters command to see the clusters you have created.")
        logger.warning("Aborting...")
        return

    # Pull all our deployed configuration from SSM and tear down the ENI-specific resources
    vpc_ssm_param = constants.get_vpc_ssm_param_name(cluster_name, vpc_id)
    subnet_search_path = f"{vpc_ssm_param}/subnets"
    subnet_configs = [json.loads(config["Value"]) for config in ssm_ops.get_ssm_params_by_path(subnet_search_path, aws_provider)]
    subnet_ids = [config['subnetId'] for config in subnet_configs]
    for subnet_id in subnet_ids:
        eni_search_path = f"{constants.get_subnet_ssm_param_name(cluster_name, vpc_id, subnet_id)}/enis"
        eni_ids = ssm_ops.get_ssm_names_by_path(eni_search_path, aws_provider)
        
        for eni_id in eni_ids:
            _remove_mirroring_for_eni(cluster_name, vpc_id, subnet_id, eni_id, aws_provider)

    # Make the VNI available to for re-use by another VPC.  Technically, the VNI's usage is tied to the ENI-specific
    # AWS resources rather than the CDK-generated ones, so we perform this before our CDK operation in case it fails.
    vpc_vni = ssm_ops.get_ssm_param_json_value(vpc_ssm_param, "mirrorVni", aws_provider)
    vni_provider = SsmVniProvider(cluster_name, aws_provider)
    vni_provider.relinquish_vni(int(vpc_vni), vpc_id)

    # Destroy the VPC-specific mirroring components in CloudFormation
    logger.info("Tearing down shared mirroring components via CDK...")
    stacks_to_destroy = [
        constants.get_vpc_mirror_setup_stack_name(cluster_name, vpc_id)
    ]
    add_vpc_context = context.generate_remove_vpc_context(cluster_name, vpc_id, subnet_ids, vpce_service_id)

    cdk_client = CdkClient()
    cdk_client.destroy(stacks_to_destroy, aws_profile=profile, aws_region=region, context=add_vpc_context)

def _remove_mirroring_for_eni(cluster_name: str, vpc_id: str, subnet_id: str, eni_id: str, aws_provider: AwsClientProvider):
    eni_param = constants.get_eni_ssm_param_name(cluster_name, vpc_id, subnet_id, eni_id)
    traffic_session_id = ssm_ops.get_ssm_param_json_value(eni_param, "trafficSessionId", aws_provider)

    logger.info(f"Removing mirroring session for eni {eni_id}; deleting mirroring session {traffic_session_id}...")
    try:
        ec2i.delete_eni_mirroring(traffic_session_id, aws_provider)
    except ec2i.MirrorDoesntExist as ex:
        logger.info(f"Traffic mirroring session {traffic_session_id} not found; something else must have deleted it. Skipping...")

    logger.info(f"Deleting SSM parameter for ENI {eni_id}...")
    ssm_ops.delete_ssm_param(eni_param, aws_provider)
