import os
import re

# =================================================================================================
# These constant values cross the boundary between the Python and CDK sides of the solution.
# They should probably live in a shared config file or something.
# =================================================================================================

# The context key that the CDK App is looking for to know what command the user ran.  This is relevant as it helps the
# CDK know which CloudFormation templates to generate.
CDK_CONTEXT_CMD_VAR: str = "ARKIME_CMD"

# The context key that the CDK App is looking for to receive stack configuration details through.  This configuration
# must flow from the Python side to the CDK side because the management CLI is tracking the application "state", not
# the CDK App.  It's unclear how sustainable this approach will be as the configuration could become large over time.
CDK_CONTEXT_PARAMS_VAR: str = "ARKIME_PARAMS"

# The context key that the CDK App is looking for to know if the user specified an AWS region different than the one
# associated with their AWS Credential profile
CDK_CONTEXT_REGION_VAR: str = "ARKIME_REGION"

# The names of the management operations we can perform; will be received/parsed on the CDK side so needs to match.
CMD_DEPLOY_DEMO = "DeployDemoTraffic"
CMD_DESTROY_DEMO = "DestroyDemoTraffic"
CMD_cluster_create = "CreateCluster"
CMD_cluster_destroy = "DestroyCluster"
CMD_vpc_add = "AddVpc"
CMD_vpc_remove = "RemoveVpc"

# The names of static CDK Stacks defined in our App
NAME_DEMO_STACK_1: str = "DemoTrafficGen01"
NAME_DEMO_STACK_2: str = "DemoTrafficGen02"

# The names of EventBridge items and fields
EVENT_SOURCE = "arkime"
EVENT_DETAIL_TYPE_CONFIGURE_ISM = "ConfigureIsm"
EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR = "CreateEniMirror"
EVENT_DETAIL_TYPE_DESTROY_ENI_MIRROR = "DestroyEniMirror"

# =================================================================================================
# These names cross the boundary between the Python and CDK sides of the solution, but are not hardcoded on the
# CDK side as well.  They are defined on the Python side because we need to know in-Python the names of the CDK stacks
# we want to manipulate.
# =================================================================================================
SSM_CLUSTERS_PREFIX = "/arkime/clusters"

def get_capture_bucket_stack_name(cluster_name: str) -> str:
    return f"{cluster_name}-CaptureBucket"

def get_capture_bucket_ssm_param_name(cluster_name: str) -> str:
    return f"{SSM_CLUSTERS_PREFIX}/{cluster_name}/capture-bucket-name"

def get_capture_config_details_ssm_param_name(cluster_name: str) -> str:
    return f"{SSM_CLUSTERS_PREFIX}/{cluster_name}/capture-config-details"

def get_capture_config_s3_key(config_version: str) -> str:
    return f"capture/{config_version}/archive.zip"

def get_capture_details_ssm_param_name(cluster_name: str) -> str:
    return f"/arkime/clusters/{cluster_name}/capture-details"

def get_capture_nodes_stack_name(cluster_name: str) -> str:
    return f"{cluster_name}-CaptureNodes"

def get_capture_vpc_stack_name(cluster_name: str) -> str:
    return f"{cluster_name}-CaptureVPC"

def get_config_bucket_name(account: str, region: str, cluster_name: str):
    return f"arkimeconfig-{account}-{region}-{cluster_name.lower()}"

def get_config_bucket_ssm_param_name(cluster_name: str):
    return f"{SSM_CLUSTERS_PREFIX}/{cluster_name}/config-bucket-name"

def get_cluster_ssm_param_name(cluster_name: str) -> str:
    return f"{SSM_CLUSTERS_PREFIX}/{cluster_name}"

def get_cluster_vpc_cross_account_ssm_param_name(cluster_name: str, vpc_id: str) -> str:
    return f"{SSM_CLUSTERS_PREFIX}/{cluster_name}/vpcs/{vpc_id}/cross-account"

def get_opensearch_domain_stack_name(cluster_name: str) -> str:
    return f"{cluster_name}-OSDomain"

def get_opensearch_domain_ssm_param_name(cluster_name: str) -> str:
    return f"{SSM_CLUSTERS_PREFIX}/{cluster_name}/os-domain-details"

def get_subnet_ssm_param_name(cluster_name: str, vpc_id: str, subnet_id: str) -> str:
    return f"{SSM_CLUSTERS_PREFIX}/{cluster_name}/vpcs/{vpc_id}/subnets/{subnet_id}"

def get_viewer_cert_ssm_param_name(cluster_name: str) -> str:
    return f"/arkime/clusters/{cluster_name}/viewer-cert"

def get_viewer_config_details_ssm_param_name(cluster_name: str) -> str:
    return f"{SSM_CLUSTERS_PREFIX}/{cluster_name}/viewer-config-details"

def get_viewer_config_s3_key(config_version: str) -> str:
    return f"viewer/{config_version}/archive.zip"

def get_viewer_details_ssm_param_name(cluster_name: str) -> str:
    return f"/arkime/clusters/{cluster_name}/viewer-details"

def get_viewer_dns_ssm_param_name(cluster_name: str) -> str:
    return f"/arkime/clusters/{cluster_name}/viewer-dns"

def get_viewer_password_ssm_param_name(cluster_name: str) -> str:
    return f"/arkime/clusters/{cluster_name}/viewer-pass-arn"

def get_viewer_user_ssm_param_name(cluster_name: str) -> str:
    return f"/arkime/clusters/{cluster_name}/viewer-user"

def get_viewer_nodes_stack_name(cluster_name: str) -> str:
    return f"{cluster_name}-ViewerNodes"

def get_vpc_mirror_setup_stack_name(cluster_name: str, vpc_id: str) -> str:
    return f"{cluster_name}-{vpc_id}-Mirror"

def get_vpc_ssm_param_name(cluster_name: str, vpc_id: str) -> str:
    return f"{SSM_CLUSTERS_PREFIX}/{cluster_name}/vpcs/{vpc_id}"

# =================================================================================================
# These constants are only used on the Python side of the solution.
# =================================================================================================

def get_eni_ssm_param_name(cluster_name: str, vpc_id: str, subnet_id: str, eni_id: str) -> str:
    return f"{SSM_CLUSTERS_PREFIX}/{cluster_name}/vpcs/{vpc_id}/subnets/{subnet_id}/enis/{eni_id}"

VNI_DEFAULT = 123
VNI_MIN = 1 # 0 is reserved for the default network segment
VNI_MAX = 16777215 # 2^24 - 1

def get_vnis_recycled_ssm_param_name(cluster_name: str) -> str:
    return f"{SSM_CLUSTERS_PREFIX}/{cluster_name}/vnis-recycled"

def get_vnis_user_ssm_param_name(cluster_name: str) -> str:
    return f"{SSM_CLUSTERS_PREFIX}/{cluster_name}/vnis-user"

def get_vni_current_ssm_param_name(cluster_name: str) -> str:
    return f"{SSM_CLUSTERS_PREFIX}/{cluster_name}/vni-current"

VALID_CLUSTER_REGEX = "^[a-zA-Z0-9_-]*$"

class InvalidClusterName(Exception):
    def __init__(self, cluster_name: str):
        self.cluster_name = cluster_name
        super().__init__(f"The cluster name {cluster_name} does not match the regex {VALID_CLUSTER_REGEX}")

def is_valid_cluster_name(cluster_name: str) -> bool:
    # Regex should return true if there is a character other than alphanumeric, hyphen, or underscore
    no_special_chars = re.compile(VALID_CLUSTER_REGEX)

    # There are no special characters and it's not an empty string
    return bool(no_special_chars.match(cluster_name)) and len(cluster_name) > 0

def get_repo_root_dir() -> str:
    """
    Returns the path to the location on disk of the repo's root directory
    """
    this_files_path = os.path.abspath(__file__)
    three_levels_up = os.path.dirname(os.path.dirname(os.path.dirname(this_files_path))) # should be repo root
    return three_levels_up
