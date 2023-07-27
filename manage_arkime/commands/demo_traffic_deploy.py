import logging

from aws_interactions.aws_client_provider import AwsClientProvider
from cdk_interactions.cdk_client import CdkClient
import core.constants as constants

logger = logging.getLogger(__name__)

def cmd_demo_traffic_deploy(profile: str, region: str):
    logger.debug(f"Invoking demo-traffic-deploy with profile '{profile}' and region '{region}'")

    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)
    cdk_client = CdkClient(aws_provider.get_aws_env())

    stacks_to_deploy = [constants.NAME_DEMO_STACK_1, constants.NAME_DEMO_STACK_2]
    context = {
        constants.CDK_CONTEXT_CMD_VAR: constants.CMD_DEPLOY_DEMO
    }
    cdk_client.deploy(stacks_to_deploy, context=context)