import logging

from cdk_interactions.cdk_client import CdkClient
import constants as constants

logger = logging.getLogger(__name__)

def cmd_destroy_demo_traffic(profile: str, region: str):
    logger.debug(f"Invoking destroy-demo-traffic with profile '{profile}' and region '{region}'")

    cdk_client = CdkClient()
    stacks_to_destroy = [constants.NAME_DEMO_STACK_1, constants.NAME_DEMO_STACK_2]
    context = {
        constants.CDK_CONTEXT_CMD_VAR: constants.CMD_DESTROY_DEMO
    }
    cdk_client.destroy(stacks_to_destroy, aws_profile=profile, aws_region=region, context=context)