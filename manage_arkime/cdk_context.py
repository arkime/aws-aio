import json
import shlex
from typing import Dict

import manage_arkime.constants as constants

def generate_create_cluster_context(name: str) -> Dict[str, str]:
    create_context = _generate_cluster_context(name)
    create_context[constants.CDK_CONTEXT_CMD_VAR] = constants.CMD_CREATE_CLUSTER
    return create_context

def generate_destroy_cluster_context(name: str) -> Dict[str, str]:
    destroy_context = _generate_cluster_context(name)
    destroy_context[constants.CDK_CONTEXT_CMD_VAR] = constants.CMD_DESTROY_CLUSTER
    return destroy_context

def _generate_cluster_context(name: str) -> Dict[str, str]:
    cmd_params = {
        "nameCluster": name,
        "nameCaptureBucket": constants.get_capture_bucket_stack_name(name),
        "nameCaptureNodes": constants.get_capture_nodes_stack_name(name),
        "nameCaptureVpc": constants.get_capture_vpc_stack_name(name),
        "nameOSDomain": constants.get_opensearch_domain_stack_name(name),
    }

    return {
        constants.CDK_CONTEXT_PARAMS_VAR: shlex.quote(json.dumps(cmd_params))
    }