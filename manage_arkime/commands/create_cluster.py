import json
import logging
from typing import Tuple

from aws_interactions.acm_interactions import upload_default_elb_cert
from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.ssm_operations as ssm_ops
from cdk_interactions.cdk_client import CdkClient
import cdk_interactions.cdk_context as context
import constants as constants
from core.capacity_planning import get_capture_node_capacity_plan, get_ecs_sys_resource_plan, CaptureNodesPlan, EcsSysResourcePlan, MINIMUM_TRAFFIC

logger = logging.getLogger(__name__)

def cmd_create_cluster(profile: str, region: str, name: str, expected_traffic: int):
    logger.debug(f"Invoking create-cluster with profile '{profile}' and region '{region}'")

    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)

    capture_plan, ecs_resource_plan = _get_capacity_plans(name, expected_traffic, aws_provider)

    cert_arn = _set_up_viewer_cert(name, aws_provider)

    cdk_client = CdkClient()
    stacks_to_deploy = [
        constants.get_capture_bucket_stack_name(name),
        constants.get_capture_nodes_stack_name(name),
        constants.get_capture_vpc_stack_name(name),
        constants.get_opensearch_domain_stack_name(name),
        constants.get_viewer_nodes_stack_name(name)
    ]
    create_context = context.generate_create_cluster_context(name, cert_arn, capture_plan, ecs_resource_plan)
    cdk_client.deploy(stacks_to_deploy, aws_profile=profile, aws_region=region, context=create_context)

def _get_capacity_plans(cluster_name: str, expected_traffic: int, aws_provider: AwsClientProvider) -> Tuple[CaptureNodesPlan, EcsSysResourcePlan]:
    
    if not expected_traffic:
        try:
            plan_json = ssm_ops.get_ssm_param_json_value(
                constants.get_cluster_ssm_param_name(cluster_name),
                "captureNodesPlan",
                aws_provider
            )
            capture_plan = CaptureNodesPlan(
                instance_type=plan_json["instanceType"],
                desired_count=plan_json["desiredCount"],
                max_count=plan_json["maxCount"],
                min_count=plan_json["minCount"],
            )

        except ssm_ops.ParamDoesNotExist:
            capture_plan = get_capture_node_capacity_plan(MINIMUM_TRAFFIC)
    else:
        capture_plan = get_capture_node_capacity_plan(expected_traffic)

    ecs_resource_plan = get_ecs_sys_resource_plan(capture_plan.instance_type)

    return (capture_plan, ecs_resource_plan)
        

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