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
        "nameCaptureBucketStack": constants.get_capture_bucket_stack_name(name),
        "nameCaptureBucketSsmParam": constants.get_capture_bucket_ssm_param_name(name),
        "nameCaptureNodesStack": constants.get_capture_nodes_stack_name(name),
        "nameCaptureVpcStack": constants.get_capture_vpc_stack_name(name),
        "nameClusterSsmParam": constants.get_cluster_ssm_param_name(name),
        "nameOSDomainStack": constants.get_opensearch_domain_stack_name(name),
        "nameOSDomainSsmParam": constants.get_opensearch_domain_ssm_param_name(name),
        "nameViewerNodesStack": constants.get_viewer_nodes_stack_name(name),
    }

    return {
        constants.CDK_CONTEXT_PARAMS_VAR: shlex.quote(json.dumps(cmd_params))
    }

def generate_add_vpc_context(cluster_name: str, vpc_id: str, subnet_ids: str, vpce_service_id: str) -> Dict[str, str]:
    destroy_context = _generate_mirroring_context(cluster_name, vpc_id, subnet_ids, vpce_service_id)
    destroy_context[constants.CDK_CONTEXT_CMD_VAR] = constants.CMD_ADD_VPC
    return destroy_context

def generate_remove_vpc_context(cluster_name: str, vpc_id: str, subnet_ids: str, vpce_service_id: str) -> Dict[str, str]:
    destroy_context = _generate_mirroring_context(cluster_name, vpc_id, subnet_ids, vpce_service_id)
    destroy_context[constants.CDK_CONTEXT_CMD_VAR] = constants.CMD_REMOVE_VPC
    return destroy_context

def _generate_mirroring_context(cluster_name: str, vpc_id: str, subnet_ids: str, vpce_service_id: str) -> Dict[str, str]:
    cmd_params = {
        "nameVpcMirrorStack": constants.get_vpc_mirror_setup_stack_name(cluster_name, vpc_id),
        "nameVpcSsmParam": constants.get_vpc_ssm_param_name(cluster_name, vpc_id),
        "idVpc": vpc_id,
        "idVpceService": vpce_service_id,
        "listSubnetIds": subnet_ids,
        "listSubnetSsmParams": [constants.get_subnet_ssm_param_name(cluster_name, vpc_id, subnet_id) for subnet_id in subnet_ids]
    }

    return {
        constants.CDK_CONTEXT_PARAMS_VAR: shlex.quote(json.dumps(cmd_params))
    }