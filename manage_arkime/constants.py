
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

# The names of static CDK Stacks defined in our App
NAME_DEMO_STACK_1: str = "DemoTrafficGen01"
NAME_DEMO_STACK_2: str = "DemoTrafficGen02"

# Static type names for our various stacks
STACK_TYPE_CAPTURE_VPC = "CaptureVpcStack"

# =================================================================================================
# These stack names cross the boundary between the Python and CDK sides of the solution, but are not hardcoded on the
# CDK side as well.  They are defined on the Python side because we need to know in-Python the names of the CDK stacks
# we want to manipulate.
# =================================================================================================
def get_capture_vpc_stack_name(cluster_name: str) -> str:
    return f"{cluster_name}-CaptureVPC"



















