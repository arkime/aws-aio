import logging

from manage_arkime.aws_interactions.aws_client_provider import AwsClientProvider
from manage_arkime.aws_interactions.destroy_os_domain import destroy_os_domain_and_wait
from manage_arkime.aws_interactions.destroy_s3_bucket import destroy_s3_bucket
from aws_interactions.ssm_operations import get_ssm_param_value
from manage_arkime.cdk_client import CdkClient
import manage_arkime.constants as constants
import manage_arkime.cdk_context as context

logger = logging.getLogger(__name__)

def cmd_destroy_cluster(profile: str, region: str, name: str, destroy_everything: bool):
    logger.debug(f"Invoking destroy-cluster with profile '{profile}' and region '{region}'")

    if destroy_everything:
        logger.info("Destroying User Data...")
        aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)
        os_domain_name = get_ssm_param_value(param_name=constants.get_opensearch_domain_ssm_param_name(name), aws_client_provider=aws_provider)
        destroy_os_domain_and_wait(domain_name=os_domain_name, aws_client_provider=aws_provider)

        bucket_name = get_ssm_param_value(param_name=constants.get_capture_bucket_ssm_param_name(name), aws_client_provider=aws_provider)
        destroy_s3_bucket(bucket_name=bucket_name, aws_client_provider=aws_provider)

    if not destroy_everything:
        # By default, destroy-cluster just tears down the capture/viewer nodes in order to preserve the user's data.  We
        # could tear down the OpenSearch Domain and Bucket stacks, but that would leave loose (non-CloudFormation managed)
        # resources in the user's account that they'd likely stumble across later, so it's probably better to leave those
        # stacks intact.  We can't delete the VPC stack because the OpenSearch Domain has the VPC as a dependency, as we're
        # keeping the Domain.
        stacks_to_destroy = [
            constants.get_capture_nodes_stack_name(name),
            constants.get_viewer_nodes_stack_name(name)
        ]
    else:
        # Because we've destroyed the user data, we can tear down all CloudFormation stacks.
        stacks_to_destroy = [
            constants.get_capture_bucket_stack_name(name),
            constants.get_capture_nodes_stack_name(name),
            constants.get_capture_vpc_stack_name(name),
            constants.get_opensearch_domain_stack_name(name),
            constants.get_viewer_nodes_stack_name(name)
        ]
    destroy_context = context.generate_destroy_cluster_context(name)

    cdk_client = CdkClient()
    cdk_client.destroy(stacks_to_destroy, aws_profile=profile, aws_region=region, context=destroy_context)