
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
CMD_CREATE_CLUSTER = "CreateCluster"
CMD_DESTROY_CLUSTER = "DestroyCluster"
CMD_ADD_VPC = "AddVpc"

# The names of static CDK Stacks defined in our App
NAME_DEMO_STACK_1: str = "DemoTrafficGen01"
NAME_DEMO_STACK_2: str = "DemoTrafficGen02"

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

def get_capture_nodes_stack_name(cluster_name: str) -> str:
    return f"{cluster_name}-CaptureNodes"

def get_capture_vpc_stack_name(cluster_name: str) -> str:
    return f"{cluster_name}-CaptureVPC"

def get_cluster_initialized_ssm_param_name(cluster_name: str) -> str:
    return f"{SSM_CLUSTERS_PREFIX}/{cluster_name}/initialized"

def get_cluster_ssm_param_name(cluster_name: str) -> str:
    return f"{SSM_CLUSTERS_PREFIX}/{cluster_name}"

def get_opensearch_domain_stack_name(cluster_name: str) -> str:
    return f"{cluster_name}-OSDomain"

def get_opensearch_domain_ssm_param_name(cluster_name: str) -> str:
    return f"{SSM_CLUSTERS_PREFIX}/{cluster_name}/os-domain-name"

def get_subnet_ssm_param_name(cluster_name: str, vpc_id: str, subnet_id: str) -> str:
    return f"{SSM_CLUSTERS_PREFIX}/{cluster_name}/vpcs/{vpc_id}/subnets/{subnet_id}"

def get_vpc_mirror_setup_stack_name(cluster_name: str, vpc_id: str) -> str:
    return f"{cluster_name}-{vpc_id}-Mirror"

def get_vpc_ssm_param_name(cluster_name: str, vpc_id: str) -> str:
    return f"{SSM_CLUSTERS_PREFIX}/{cluster_name}/vpcs/{vpc_id}"