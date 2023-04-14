import logging

from manage_arkime.cdk_client import CdkClient
import manage_arkime.constants as constants
import manage_arkime.cdk_context as context

logger = logging.getLogger(__name__)

def cmd_create_cluster(profile: str, region: str, name: str):
    logger.debug(f"Invoking create-cluster with profile '{profile}' and region '{region}'")

    cdk_client = CdkClient()
    stacks_to_deploy = [
        constants.get_capture_bucket_stack_name(name),
        constants.get_capture_nodes_stack_name(name),
        constants.get_capture_vpc_stack_name(name),
        constants.get_opensearch_domain_stack_name(name),
        constants.get_viewer_nodes_stack_name(name)
    ]
    create_context = context.generate_create_cluster_context(name)
    cdk_client.deploy(stacks_to_deploy, aws_profile=profile, aws_region=region, context=create_context)