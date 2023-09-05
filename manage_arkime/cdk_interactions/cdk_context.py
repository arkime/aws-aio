import json
import shlex
from typing import Dict, List

import core.constants as constants
from core.capacity_planning import (CaptureNodesPlan, ViewerNodesPlan, VpcPlan, ClusterPlan, DataNodesPlan, EcsSysResourcePlan,
                                    MasterNodesPlan, OSDomainPlan, DEFAULT_NUM_AZS, S3Plan, DEFAULT_S3_STORAGE_CLASS,
                                    DEFAULT_VPC_CIDR, DEFAULT_CAPTURE_PUBLIC_MASK)
from core.user_config import UserConfig

def generate_cluster_create_context(name: str, viewer_cert_arn: str, cluster_plan: ClusterPlan,
                                    user_config: UserConfig, cluster_config_bucket_name: str) -> Dict[str, str]:
    create_context = _generate_cluster_context(
        name,
        viewer_cert_arn,
        cluster_plan,
        user_config,
        cluster_config_bucket_name
    )
    create_context[constants.CDK_CONTEXT_CMD_VAR] = constants.CMD_cluster_create
    return create_context

def generate_cluster_destroy_context(name: str) -> Dict[str, str]:
    # Hardcode these value because it saves us some implementation headaches and it doesn't matter what it is. Since
    # we're tearing down the Cfn stack in which it would be used, the operation either succeeds they are irrelevant
    # or it fails/rolls back they are irrelevant.
    fake_arn = "N/A"
    fake_cluster_plan = ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 1, 2, 1),
        VpcPlan(DEFAULT_VPC_CIDR, DEFAULT_NUM_AZS, DEFAULT_CAPTURE_PUBLIC_MASK),
        EcsSysResourcePlan(1, 1),
        OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search")),
        S3Plan(DEFAULT_S3_STORAGE_CLASS, 1),
        ViewerNodesPlan(4, 2),
        None
    )
    fake_user_config = UserConfig(1, 1, 1, 1, 1)
    fake_bucket_name = ""

    destroy_context = _generate_cluster_context(name, fake_arn, fake_cluster_plan, fake_user_config, fake_bucket_name)
    destroy_context[constants.CDK_CONTEXT_CMD_VAR] = constants.CMD_cluster_destroy
    return destroy_context

def _generate_cluster_context(name: str, viewer_cert_arn: str, cluster_plan: ClusterPlan, user_config: UserConfig,
                              cluster_config_bucket_name: str) -> Dict[str, str]:
    cmd_params = {
        "nameCluster": name,
        "nameCaptureBucketStack": constants.get_capture_bucket_stack_name(name),
        "nameCaptureBucketSsmParam": constants.get_capture_bucket_ssm_param_name(name),
        "nameCaptureConfigSsmParam": constants.get_capture_config_details_ssm_param_name(name),
        "nameCaptureDetailsSsmParam": constants.get_capture_details_ssm_param_name(name),
        "nameCaptureNodesStack": constants.get_capture_nodes_stack_name(name),
        "nameCaptureVpcStack": constants.get_capture_vpc_stack_name(name),
        "nameClusterConfigBucket": cluster_config_bucket_name,
        "nameClusterSsmParam": constants.get_cluster_ssm_param_name(name),
        "nameOSDomainStack": constants.get_opensearch_domain_stack_name(name),
        "nameOSDomainSsmParam": constants.get_opensearch_domain_ssm_param_name(name),
        "nameViewerCertArn": viewer_cert_arn,
        "nameViewerConfigSsmParam": constants.get_viewer_config_details_ssm_param_name(name),
        "nameViewerDetailsSsmParam": constants.get_viewer_details_ssm_param_name(name),
        "nameViewerNodesStack": constants.get_viewer_nodes_stack_name(name),
        "planCluster": json.dumps(cluster_plan.to_dict()),
        "userConfig": json.dumps(user_config.to_dict()),
    }

    return {
        constants.CDK_CONTEXT_PARAMS_VAR: shlex.quote(json.dumps(cmd_params))
    }

def generate_vpc_add_context(cluster_name: str, vpc_id: str, subnet_ids: str, vpce_service_id: str, vni: int,
                             cidrs: List[str]) -> Dict[str, str]:
    add_context = _generate_mirroring_context(cluster_name, vpc_id, subnet_ids, vpce_service_id, vni, cidrs)
    add_context[constants.CDK_CONTEXT_CMD_VAR] = constants.CMD_vpc_add
    return add_context

def generate_vpc_remove_context(cluster_name: str, vpc_id: str, subnet_ids: str, vpce_service_id: str) -> Dict[str, str]:
    # Hardcode these values because it saves us some implementation headaches and it doesn't matter what they are. Since
    # we're tearing down the Cfn stack in which it would be used, the operation either succeeds and the it's
    # irrelevant or it fails/rolls back and it's irrelevant.
    vni = constants.VNI_DEFAULT
    cidrs = ["0.0.0.0/0"]
    remove_context = _generate_mirroring_context(cluster_name, vpc_id, subnet_ids, vpce_service_id, vni, cidrs)
    remove_context[constants.CDK_CONTEXT_CMD_VAR] = constants.CMD_vpc_remove
    return remove_context

def _generate_mirroring_context(cluster_name: str, vpc_id: str, subnet_ids: str, vpce_service_id: str, vni: int,
                                cidrs: List[str]) -> Dict[str, str]:
    cmd_params = {
        "nameCluster": cluster_name,
        "nameVpcMirrorStack": constants.get_vpc_mirror_setup_stack_name(cluster_name, vpc_id),
        "nameVpcSsmParam": constants.get_vpc_ssm_param_name(cluster_name, vpc_id),
        "idVni": str(vni),
        "idVpc": vpc_id,
        "idVpceService": vpce_service_id,
        "listSubnetIds": subnet_ids,
        "listSubnetSsmParams": [constants.get_subnet_ssm_param_name(cluster_name, vpc_id, subnet_id) for subnet_id in subnet_ids],
        "vpcCidrs": cidrs
    }

    return {
        constants.CDK_CONTEXT_PARAMS_VAR: shlex.quote(json.dumps(cmd_params))
    }
