import json
import logging
from typing import Tuple

from aws_interactions.acm_interactions import upload_default_elb_cert
from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.ssm_operations as ssm_ops
from cdk_interactions.cdk_client import CdkClient
import cdk_interactions.cdk_context as context
import constants as constants
from core.capacity_planning import (get_capture_node_capacity_plan, get_ecs_sys_resource_plan, get_os_domain_plan, ClusterPlan,
                                    CaptureNodesPlan, CaptureVpcPlan, EcsSysResourcePlan, OSDomainPlan, MINIMUM_TRAFFIC,
                                    DEFAULT_SPI_DAYS, DEFAULT_SPI_REPLICAS, DEFAULT_NUM_AZS)

logger = logging.getLogger(__name__)

class MustProvideAllParams(Exception):
    def __init__(self):
        super().__init__("If you specify one of the optional capacity parameters, you must specify all of them.")

def cmd_create_cluster(profile: str, region: str, name: str, expected_traffic: float, spi_days: int, replicas: int):
    logger.debug(f"Invoking create-cluster with profile '{profile}' and region '{region}'")

    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)

    capacity_plan = _get_capacity_plan(name, expected_traffic, spi_days, replicas, aws_provider)

    cert_arn = _set_up_viewer_cert(name, aws_provider)

    cdk_client = CdkClient()
    stacks_to_deploy = [
        constants.get_capture_bucket_stack_name(name),
        constants.get_capture_nodes_stack_name(name),
        constants.get_capture_vpc_stack_name(name),
        constants.get_opensearch_domain_stack_name(name),
        constants.get_viewer_nodes_stack_name(name)
    ]
    create_context = context.generate_create_cluster_context(name, cert_arn, capacity_plan)
    cdk_client.deploy(stacks_to_deploy, aws_profile=profile, aws_region=region, context=create_context)

def _get_capacity_plan(cluster_name: str, expected_traffic: float, spi_days: int, replicas: int, aws_provider: AwsClientProvider) -> ClusterPlan:
    
    # None of the parameters defined
    if (not expected_traffic) and (not spi_days) and (not replicas):
        # Re-use the existing configuration if it exists
        try:
            plan_json = ssm_ops.get_ssm_param_json_value(
                constants.get_cluster_ssm_param_name(cluster_name),
                "capacityPlan",
                aws_provider
            )
            capacity_plan = ClusterPlan.from_dict(plan_json)

            return capacity_plan

        # Existing configuration doesn't exist, use defaults
        except ssm_ops.ParamDoesNotExist:
            capture_plan = get_capture_node_capacity_plan(MINIMUM_TRAFFIC)
            capture_vpc_plan = CaptureVpcPlan(DEFAULT_NUM_AZS)
            os_domain_plan = get_os_domain_plan(MINIMUM_TRAFFIC, DEFAULT_SPI_DAYS, DEFAULT_SPI_REPLICAS, capture_vpc_plan.numAzs)
    # All of the parameters defined
    elif expected_traffic and spi_days and replicas:
        capture_plan = get_capture_node_capacity_plan(expected_traffic)
        capture_vpc_plan = CaptureVpcPlan(DEFAULT_NUM_AZS)
        os_domain_plan = get_os_domain_plan(expected_traffic, spi_days, replicas, capture_vpc_plan.numAzs)
    # Some, but not all, of the parameters defined
    else:
        raise MustProvideAllParams()

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