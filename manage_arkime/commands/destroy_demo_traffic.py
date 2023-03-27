import logging

import manage_arkime.cdk_client as cdk
import manage_arkime.constants as constants

logger = logging.getLogger(__name__)

def cmd_destroy_demo_traffic(profile: str, region: str):
    logger.debug(f"Invoking destroy-demo-traffic with profile '{profile}' and region '{region}'")

    cdk_client = cdk.CdkClient()
    stacks_to_destroy = [constants.NAME_DEMO_STACK_1, constants.NAME_DEMO_STACK_2]
    cdk_client.destroy(stacks_to_destroy, aws_profile=profile, aws_region=region)