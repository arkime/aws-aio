
# =================================================================================================
# These constant values cross the boundary between the Python and CDK sides of the solution.
# They should probably live in a shared config file or something.
# =================================================================================================

# The context key that the CDK App is looking for to know if the user specified an AWS region different than the one
# associated with their AWS Credential profile
CDK_CONTEXT_REGION_VAR: str = "ARKIME_REGION"

# The names of CDK Stacks defined in our App
NAME_DEMO_STACK_1: str = "DemoTrafficGen01"
NAME_DEMO_STACK_2: str = "DemoTrafficGen02"