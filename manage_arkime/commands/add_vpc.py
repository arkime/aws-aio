import json
import logging

from manage_arkime.aws_interactions.aws_client_provider import AwsClientProvider
from manage_arkime.aws_interactions.destroy_os_domain import destroy_os_domain_and_wait
from manage_arkime.aws_interactions.destroy_s3_bucket import destroy_s3_bucket
import aws_interactions.ssm_operations as ssm_ops
from manage_arkime.cdk_client import CdkClient
import manage_arkime.constants as constants
import manage_arkime.cdk_context as context

logger = logging.getLogger(__name__)

def cmd_add_vpc(profile: str, region: str, cluster_name: str, vpc_id: str):
    logger.debug(f"Invoking add-vpc with profile '{profile}' and region '{region}'")

    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)

    # Confirm the Cluster exists before proceeding
    try:
        ssm_ops.get_ssm_param_value(constants.get_cluster_ssm_param_name(cluster_name), aws_provider)
    except ssm_ops.ParamDoesNotExist:
        logger.warning(f"The cluster {cluster_name} does not exist; try using the list-clusters command to see the clusters you have created.")
        logger.warning("Aborting operation...")
        return

    # Get all the subnets in the VPC
    # TODO: Handle pagination
    logger.info("Retrieving required information from your AWS account...")
    ec2_client = aws_provider.get_ec2()
    subnets_response = ec2_client.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )
    if not subnets_response["Subnets"]: # will be [] if the subnet does not exist
        logger.warning(f"The VPC {vpc_id} does not exist in the account/region")
        logger.warning("Aborting operation...")
        return
    subnet_ids = [subnet["SubnetId"] for subnet in subnets_response["Subnets"]]

    # Get the VPCE Service ID we set up with our Capture VPC
    cluster_param = ssm_ops.get_ssm_param_value(constants.get_cluster_ssm_param_name(cluster_name), aws_provider)
    vpce_service_id = json.loads(cluster_param)["vpceServiceID"]

    # Deploy the resources we need in the user's VPC and Subnets
    logger.info("Deploying shared mirroring components via CDK...")
    stacks_to_deploy = [
        constants.get_vpc_mirror_setup_stack_name(cluster_name, vpc_id)
    ]
    add_vpc_context = context.generate_add_vpc_context(cluster_name, vpc_id, subnet_ids, vpce_service_id)

    cdk_client = CdkClient()
    cdk_client.deploy(stacks_to_deploy, aws_profile=profile, aws_region=region, context=add_vpc_context)
    

    # if destroy_everything:
    #     logger.info("Destroying User Data...")
    #     aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)
    #     os_domain_name = get_ssm_param_value(param_name=constants.get_opensearch_domain_ssm_param_name(name), aws_client_provider=aws_provider)
    #     destroy_os_domain_and_wait(domain_name=os_domain_name, aws_client_provider=aws_provider)

    #     bucket_name = get_ssm_param_value(param_name=constants.get_capture_bucket_ssm_param_name(name), aws_client_provider=aws_provider)
    #     destroy_s3_bucket(bucket_name=bucket_name, aws_client_provider=aws_provider)

    # if not destroy_everything:
    #     # By default, destroy-cluster just tears down the capture/viewer nodes in order to preserve the user's data.  We
    #     # could tear down the OpenSearch Domain and Bucket stacks, but that would leave loose (non-CloudFormation managed)
    #     # resources in the user's account that they'd likely stumble across later, so it's probably better to leave those
    #     # stacks intact.  We can't delete the VPC stack because the OpenSearch Domain has the VPC as a dependency, as we're
    #     # keeping the Domain.
    #     stacks_to_destroy = [
    #         constants.get_capture_nodes_stack_name(name),
    #     ]
    # else:
    #     # Because we've destroyed the user data, we can tear down all CloudFormation stacks.
    #     stacks_to_destroy = [
    #         constants.get_capture_bucket_stack_name(name),
    #         constants.get_capture_nodes_stack_name(name),
    #         constants.get_capture_vpc_stack_name(name),
    #         constants.get_opensearch_domain_stack_name(name)
    #     ]
    # destroy_context = context.generate_destroy_cluster_context(name)

    # cdk_client = CdkClient()
    # cdk_client.destroy(stacks_to_destroy, aws_profile=profile, aws_region=region, context=destroy_context)