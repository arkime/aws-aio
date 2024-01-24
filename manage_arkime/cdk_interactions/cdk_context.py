from dataclasses import dataclass
import json
import shlex
from typing import Dict, List

import core.constants as constants
from core.capacity_planning import ClusterPlan
from core.user_config import UserConfig

@dataclass
class ClusterStackNames:
    captureBucket: str
    captureNodes: str
    captureTgw: str
    captureVpc: str
    osDomain: str
    viewerNodes: str
    viewerVpc: str

    def __eq__(self, other) -> bool:
        return (
            self.captureBucket == other.captureBucket and self.captureNodes == other.captureNodes
            and self.captureTgw == other.captureTgw and self.captureVpc == other.captureVpc
            and self.osDomain == other.osDomain and self.viewerNodes == other.viewerNodes
            and self.viewerVpc == other.viewerVpc    
        )
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "captureBucket": self.captureBucket,
            "captureNodes": self.captureNodes,
            "captureTgw": self.captureTgw,
            "captureVpc": self.captureVpc,
            "osDomain": self.osDomain,
            "viewerNodes": self.viewerNodes,
            "viewerVpc": self.viewerVpc,
        }

def generate_cluster_create_context(name: str, viewer_cert_arn: str, cluster_plan: ClusterPlan,
                                    user_config: UserConfig, cluster_config_bucket_name: str,
                                    stack_names: ClusterStackNames) -> Dict[str, str]:
    create_context = _generate_cluster_context(
        name,
        viewer_cert_arn,
        cluster_plan,
        user_config,
        cluster_config_bucket_name,
        stack_names
    )
    create_context[constants.CDK_CONTEXT_CMD_VAR] = constants.CMD_cluster_create
    return create_context

def generate_cluster_destroy_context(name: str, stack_names: ClusterStackNames, cluster_plan: ClusterPlan) -> Dict[str, str]:
    # Hardcode most of these value because it saves us some implementation headaches and it doesn't matter what it is.
    # Since we're tearing down the Cfn stack in which it would be used, the operation either succeeds they are
    # irrelevant or it fails/rolls back they are irrelevant.
    # 
    # We have to pass the Cluster Plan or else the CDK will fail to start up properly
    fake_arn = "N/A"
    fake_user_config = UserConfig(1, 1, 1, 1, 1)
    fake_bucket_name = ""

    destroy_context = _generate_cluster_context(
        name,
        fake_arn,
        cluster_plan,
        fake_user_config,
        fake_bucket_name,
        stack_names
    )
    destroy_context[constants.CDK_CONTEXT_CMD_VAR] = constants.CMD_cluster_destroy
    return destroy_context

def _generate_cluster_context(name: str, viewer_cert_arn: str, cluster_plan: ClusterPlan, user_config: UserConfig,
                              cluster_config_bucket_name: str, stack_names: ClusterStackNames) -> Dict[str, str]:
    cmd_params = {
        "nameCluster": name,
        "nameCaptureBucketSsmParam": constants.get_capture_bucket_ssm_param_name(name),
        "nameCaptureConfigSsmParam": constants.get_capture_config_details_ssm_param_name(name),
        "nameCaptureDetailsSsmParam": constants.get_capture_details_ssm_param_name(name),
        "nameClusterConfigBucket": cluster_config_bucket_name,
        "nameClusterSsmParam": constants.get_cluster_ssm_param_name(name),
        "nameOSDomainSsmParam": constants.get_opensearch_domain_ssm_param_name(name),
        "nameViewerCertArn": viewer_cert_arn,
        "nameViewerConfigSsmParam": constants.get_viewer_config_details_ssm_param_name(name),
        "nameViewerDetailsSsmParam": constants.get_viewer_details_ssm_param_name(name),
        "planCluster": json.dumps(cluster_plan.to_dict()),
        "stackNames": json.dumps(stack_names.to_dict()),
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
