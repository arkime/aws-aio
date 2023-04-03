import json
import logging
import shlex
from typing import Dict

from manage_arkime.cdk_client import CdkClient
import manage_arkime.constants as constants
import manage_arkime.cdk_context as context

logger = logging.getLogger(__name__)

def cmd_destroy_cluster(profile: str, region: str, name: str):
    logger.debug(f"Invoking destroy-cluster with profile '{profile}' and region '{region}'")

    cdk_client = CdkClient()

    # By default, destroy-cluster just tears down the capture/viewer nodes in order to preserve the user's data.  We
    # could tear down the OpenSearch Domain and Bucket stacks, but that would leave loose (non-CloudFormation managed)
    # resources in the user's account that they'd likely stumble across later, so it's probably better to leave those
    # stacks intact.  We can't delete the VPC stack because the OpenSearch Domain has the VPC as a dependency, as we're
    # keeping the Domain.
    stacks_to_destroy = [
        constants.get_capture_nodes_stack_name(name),
    ]
    destroy_context = context.generate_destroy_cluster_context(name)
    cdk_client.destroy(stacks_to_destroy, aws_profile=profile, aws_region=region, context=destroy_context)