import logging

from cdk_interactions.cdk_client import CdkClient
import constants as constants

logger = logging.getLogger(__name__)

def cmd_deploy_demo_traffic(profile: str, region: str):
    logger.debug(f"Invoking deploy-demo-traffic with profile '{profile}' and region '{region}'")

    cdk_client = CdkClient()
    stacks_to_deploy = [constants.NAME_DEMO_STACK_1, constants.NAME_DEMO_STACK_2]
    context = {
        constants.CDK_CONTEXT_CMD_VAR: constants.CMD_DEPLOY_DEMO
    }
    cdk_client.deploy(stacks_to_deploy, aws_profile=profile, aws_region=region, context=context)