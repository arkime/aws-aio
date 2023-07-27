import json
import logging

from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.events_interactions as events
import aws_interactions.ssm_operations as ssm_ops
from cdk_interactions.cdk_client import CdkClient
import core.constants as constants
import cdk_interactions.cdk_context as context
from core.vni_provider import SsmVniProvider

logger = logging.getLogger(__name__)


def cmd_vpc_remove(profile: str, region: str, cluster_name: str, vpc_id: str):
    logger.debug(f"Invoking vpc-remove with profile '{profile}' and region '{region}'")

    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)
    cdk_client = CdkClient(aws_provider.get_aws_env())

    # Confirm the Cluster exists before proceeding
    try:
        vpce_service_id = ssm_ops.get_ssm_param_json_value(constants.get_cluster_ssm_param_name(cluster_name), "vpceServiceId", aws_provider)
        event_bus_arn = ssm_ops.get_ssm_param_json_value(constants.get_cluster_ssm_param_name(cluster_name), "busArn", aws_provider)
    except ssm_ops.ParamDoesNotExist:
        logger.error(f"The cluster {cluster_name} does not exist; try using the clusters-list command to see the clusters you have created.")
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
            logger.info(f"Initiating teardown of mirroring session for ENI {eni_id}")
            destroy_event = events.DestroyEniMirrorEvent(cluster_name, vpc_id, subnet_id, eni_id)
            events.put_events([destroy_event], event_bus_arn, aws_provider)

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
    vpc_add_context = context.generate_vpc_remove_context(cluster_name, vpc_id, subnet_ids, vpce_service_id, event_bus_arn)

    cdk_client.destroy(stacks_to_destroy, context=vpc_add_context)
