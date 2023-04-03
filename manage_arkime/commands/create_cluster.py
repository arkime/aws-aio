import json
import logging
import shlex
from typing import Dict

from manage_arkime.cdk_client import CdkClient
import manage_arkime.constants as constants

logger = logging.getLogger(__name__)

def cmd_create_cluster(profile: str, region: str, name: str):
    logger.debug(f"Invoking create-cluster with profile '{profile}' and region '{region}'")

    cdk_client = CdkClient()
    stacks_to_deploy = [
        constants.get_capture_bucket_stack_name(name),
        constants.get_capture_nodes_stack_name(name),
        constants.get_capture_vpc_stack_name(name),
        constants.get_opensearch_domain_stack_name(name)
    ]
    context = _generate_cdk_context(name)
    cdk_client.deploy(stacks_to_deploy, aws_profile=profile, aws_region=region, context=context)

def _generate_cdk_context(name: str) -> Dict[str, str]:
    cmd_params = {
        "nameCluster": name,
        "nameCaptureBucket": constants.get_capture_bucket_stack_name(name),
        "nameCaptureNodes": constants.get_capture_nodes_stack_name(name),
        "nameCaptureVpc": constants.get_capture_vpc_stack_name(name),
        "nameOSDomain": constants.get_opensearch_domain_stack_name(name),
    }

    return {
        constants.CDK_CONTEXT_CMD_VAR: constants.CMD_CREATE_CLUSTER,
        constants.CDK_CONTEXT_PARAMS_VAR: shlex.quote(json.dumps(cmd_params))
    }