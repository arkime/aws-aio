import logging

from aws_interactions.aws_client_provider import AwsClientProvider
from cdk_interactions.cdk_client import CdkClient
import constants as constants

logger = logging.getLogger(__name__)

def cmd_destroy_demo_traffic(profile: str, region: str):
    logger.debug(f"Invoking destroy-demo-traffic with profile '{profile}' and region '{region}'")

    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)
    cdk_client = CdkClient(aws_provider.get_aws_env())

    stacks_to_destroy = [constants.NAME_DEMO_STACK_1, constants.NAME_DEMO_STACK_2]
    context = {
        constants.CDK_CONTEXT_CMD_VAR: constants.CMD_DESTROY_DEMO
    }
    cdk_client.destroy(stacks_to_destroy, context=context)