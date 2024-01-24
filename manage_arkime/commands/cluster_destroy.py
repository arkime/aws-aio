import logging
from typing import Dict, List

from aws_interactions.acm_interactions import destroy_cert
from aws_interactions.aws_client_provider import AwsClientProvider
from aws_interactions.destroy_os_domain import destroy_os_domain_and_wait
from aws_interactions.s3_interactions import destroy_bucket
from aws_interactions.ssm_operations import get_ssm_param_json_value, get_ssm_param_value, get_ssm_names_by_path, delete_ssm_param, ParamDoesNotExist
from cdk_interactions.cdk_client import CdkClient
from core.capacity_planning import ClusterPlan
import core.constants as constants
import core.versioning as ver
import cdk_interactions.cdk_context as context

logger = logging.getLogger(__name__)

def cmd_cluster_destroy(profile: str, region: str, name: str, destroy_everything: bool, retain_traffic_data: bool):
    logger.debug(f"Invoking cluster-destroy with profile '{profile}' and region '{region}'")

    if not (destroy_everything or retain_traffic_data):
        logger.error("You must specify either --destroy-everything or --retain-traffic-data")
        logger.warning("Aborting...")
        return

    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)
    cdk_client = CdkClient(aws_provider.get_aws_env())

    try:
        ver.confirm_aws_aio_version_compatibility(name, aws_provider)
    except (ver.CliClusterVersionMismatch, ver.CaptureViewerVersionMismatch, ver.UnableToRetrieveClusterVersion) as e:
        logger.error(e)
        logger.warning("Aborting...")
        return

    cluster_plan_str = get_ssm_param_json_value(constants.get_cluster_ssm_param_name(name), "capacityPlan", aws_provider)
    cluster_plan = ClusterPlan.from_dict(cluster_plan_str)

    vpcs_search_path = f"{constants.get_cluster_ssm_param_name(name)}/vpcs"
    monitored_vpcs = get_ssm_names_by_path(vpcs_search_path, aws_provider)
    if monitored_vpcs:
        logger.error("Your cluster is currently monitoring VPCs.  Please stop monitoring these VPCs using the"
            + f" vpc-remove command before destroying your cluster:\n{monitored_vpcs}")
        logger.warning("Aborting...")
        return

    if destroy_everything:
        logger.info("Destroying User Data...")
        os_domain_name = get_ssm_param_json_value(
            param_name=constants.get_opensearch_domain_ssm_param_name(name),
            key="domainName",
            aws_client_provider=aws_provider
        )
        destroy_os_domain_and_wait(domain_name=os_domain_name, aws_client_provider=aws_provider)

        bucket_name = get_ssm_param_value(param_name=constants.get_capture_bucket_ssm_param_name(name), aws_client_provider=aws_provider)
        destroy_bucket(bucket_name=bucket_name, aws_provider=aws_provider)

    has_viewer_vpc = cluster_plan.viewerVpc is not None
    stacks_to_destroy = _get_stacks_to_destroy(name, destroy_everything, has_viewer_vpc)
    destroy_context = _get_cdk_context(name, cluster_plan)

    cdk_client.destroy(stacks_to_destroy, context=destroy_context)

    # Destroy our cert
    _destroy_viewer_cert(name, aws_provider)

    # Destroy any additional remaining state
    _delete_arkime_config_from_datastore(name, aws_provider)

def _destroy_viewer_cert(cluster_name: str, aws_provider: AwsClientProvider):
    # Only destroy up the certificate if it exists
    cert_ssm_param = constants.get_viewer_cert_ssm_param_name(cluster_name)
    try:
        cert_arn = get_ssm_param_value(cert_ssm_param, aws_provider)
    except ParamDoesNotExist:        
        logger.debug(f"Viewer certificate does not exist; skipping destruction")
        return

    # Destroy the cert and state
    logger.debug("Destroying certificate and SSM parameter...")
    destroy_cert(cert_arn, aws_provider) # destroy first so if op fails we still know the ARN
    delete_ssm_param(cert_ssm_param, aws_provider)

def _delete_arkime_config_from_datastore(cluster_name: str, aws_provider: AwsClientProvider):
    # Delete the Arkime config details in Param Store
    delete_ssm_param(
        constants.get_capture_config_details_ssm_param_name(cluster_name),
        aws_provider
    )

    delete_ssm_param(
        constants.get_viewer_config_details_ssm_param_name(cluster_name),
        aws_provider
    )

    # Tear down the S3 bucket containing the configuration tarballs
    aws_env = aws_provider.get_aws_env()
    destroy_bucket(
        bucket_name=constants.get_config_bucket_name(
            aws_env.aws_account,
            aws_env.aws_region,
            cluster_name
        ),
        aws_provider=aws_provider
    )

def _get_stacks_to_destroy(cluster_name: str, destroy_everything: bool, has_viewer_vpc: bool) -> List[str]:
    stacks = []

    if not destroy_everything:
        # By default, cluster-destroy just tears down the capture/viewer nodes in order to preserve the user's data.  We
        # could tear down the OpenSearch Domain and Bucket stacks, but that would leave loose (non-CloudFormation managed)
        # resources in the user's account that they'd likely stumble across later, so it's probably better to leave those
        # stacks intact.  We can't delete the VPC stack because the OpenSearch Domain has the VPC as a dependency, as we're
        # keeping the Domain.
        stacks.extend([
            constants.get_capture_nodes_stack_name(cluster_name),
            constants.get_viewer_nodes_stack_name(cluster_name)
        ])
    else:
        # Because we've destroyed the user data, we can tear down all CloudFormation stacks.
        stacks.extend([
            constants.get_capture_bucket_stack_name(cluster_name),
            constants.get_capture_nodes_stack_name(cluster_name),
            constants.get_capture_vpc_stack_name(cluster_name),
            constants.get_opensearch_domain_stack_name(cluster_name),
            constants.get_viewer_nodes_stack_name(cluster_name),
        ])
    
    if has_viewer_vpc:
        stacks.extend([
            constants.get_capture_tgw_stack_name(cluster_name),
            constants.get_viewer_vpc_stack_name(cluster_name),
        ])

    return stacks

def _get_cdk_context(cluster_name: str, cluster_plan: ClusterPlan) -> Dict[str, any]:
    stack_names = context.ClusterStackNames(
        captureBucket=constants.get_capture_bucket_stack_name(cluster_name),
        captureNodes=constants.get_capture_nodes_stack_name(cluster_name),
        captureTgw=constants.get_capture_tgw_stack_name(cluster_name),
        captureVpc=constants.get_capture_vpc_stack_name(cluster_name),
        osDomain=constants.get_opensearch_domain_stack_name(cluster_name),
        viewerNodes=constants.get_viewer_nodes_stack_name(cluster_name),
        viewerVpc=constants.get_viewer_vpc_stack_name(cluster_name),
    )
    return context.generate_cluster_destroy_context(cluster_name, stack_names, cluster_plan)