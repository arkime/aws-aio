import json
import logging

from aws_interactions.acm_interactions import upload_default_elb_cert
from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.ssm_operations as ssm_ops
from cdk_interactions.cdk_client import CdkClient
import cdk_interactions.cdk_context as context
import constants as constants
from core.capacity_planning import (get_capture_node_capacity_plan, get_ecs_sys_resource_plan, get_os_domain_plan, ClusterPlan,
                                    CaptureVpcPlan, MINIMUM_TRAFFIC, DEFAULT_SPI_DAYS, DEFAULT_SPI_REPLICAS, DEFAULT_NUM_AZS)
from core.user_config import UserConfig

logger = logging.getLogger(__name__)

def cmd_create_cluster(profile: str, region: str, name: str, expected_traffic: float, spi_days: int, replicas: int):
    logger.debug(f"Invoking create-cluster with profile '{profile}' and region '{region}'")

    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)

    user_config = _get_user_config(name, expected_traffic, spi_days, replicas, aws_provider)
    capacity_plan = _get_capacity_plan(user_config)

    cert_arn = _set_up_viewer_cert(name, aws_provider)

    cdk_client = CdkClient()
    stacks_to_deploy = [
        constants.get_capture_bucket_stack_name(name),
        constants.get_capture_nodes_stack_name(name),
        constants.get_capture_vpc_stack_name(name),
        constants.get_opensearch_domain_stack_name(name),
        constants.get_viewer_nodes_stack_name(name)
    ]
    create_context = context.generate_create_cluster_context(name, cert_arn, capacity_plan, user_config)
    cdk_client.deploy(stacks_to_deploy, aws_profile=profile, aws_region=region, context=create_context)

def _get_user_config(cluster_name: str, expected_traffic: float, spi_days: int, replicas: int, aws_provider: AwsClientProvider) -> UserConfig:
    # At least one parameter isn't defined
    if None in [expected_traffic, spi_days, replicas]:
        # Re-use the existing configuration if it exists
        try:
            stored_config_json = ssm_ops.get_ssm_param_json_value(
                constants.get_cluster_ssm_param_name(cluster_name),
                "userConfig",
                aws_provider
            )
            user_config = UserConfig(**stored_config_json)

            if expected_traffic is not None:
                user_config.expectedTraffic = expected_traffic
            if spi_days is not None:
                user_config.spiDays = spi_days
            if replicas is not None:
                user_config.replicas = replicas

            return user_config

        # Existing configuration doesn't exist, use defaults
        except ssm_ops.ParamDoesNotExist:
            return UserConfig(MINIMUM_TRAFFIC, DEFAULT_SPI_DAYS, DEFAULT_SPI_REPLICAS)
    # All of the parameters defined
    else:
        return UserConfig(expected_traffic, spi_days, replicas)

def _get_capacity_plan(user_config: UserConfig) -> ClusterPlan:
    capture_plan = get_capture_node_capacity_plan(user_config.expectedTraffic)
    capture_vpc_plan = CaptureVpcPlan(DEFAULT_NUM_AZS)
    os_domain_plan = get_os_domain_plan(user_config.expectedTraffic, user_config.spiDays, user_config.replicas, capture_vpc_plan.numAzs)
    ecs_resource_plan = get_ecs_sys_resource_plan(capture_plan.instanceType)

    return ClusterPlan(capture_plan, capture_vpc_plan, ecs_resource_plan, os_domain_plan)
        

def _set_up_viewer_cert(name: str, aws_provider: AwsClientProvider) -> str:
    # Only set up the certificate if it doesn't exist
    cert_ssm_param = constants.get_viewer_cert_ssm_param_name(name)
    try:
        cert_arn = ssm_ops.get_ssm_param_value(cert_ssm_param, aws_provider)
        logger.debug(f"Viewer certificate already exists ({cert_arn}); skipping creation")
        return cert_arn
    except ssm_ops.ParamDoesNotExist:
        pass

    # Create our cert and set up our state
    logger.debug("Viewer certificate does not exist; creating...")
    cert_arn = upload_default_elb_cert(aws_provider)
    logger.debug(f"Viewer certificate created: {cert_arn}")

    logger.debug("Setting SSM Param for viewer certificate...")
    ssm_ops.put_ssm_param(
        cert_ssm_param,
        cert_arn,
        aws_provider,
        f"A self-signed certificate for the Cluster {name} Viewer Nodes' ALB"
    )

    return cert_arn