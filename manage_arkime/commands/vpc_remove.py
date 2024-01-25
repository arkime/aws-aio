import json
import logging

from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.events_interactions as events
import aws_interactions.ssm_operations as ssm_ops
from cdk_interactions.cdk_client import CdkClient
import cdk_interactions.cdk_context as context
import core.compatibility as compat
import core.constants as constants
from core.cross_account_wrangling import CrossAccountAssociation
from core.vni_provider import SsmVniProvider

logger = logging.getLogger(__name__)


def cmd_vpc_remove(profile: str, region: str, cluster_name: str, vpc_id: str):
    logger.debug(f"Invoking vpc-remove with profile '{profile}' and region '{region}'")

    # Use the current AWS Account to figure out if we need to do any cross-account actions
    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)
    try:
        raw_association = ssm_ops.get_ssm_param_value(
            constants.get_cluster_vpc_cross_account_ssm_param_name(cluster_name, vpc_id),
            aws_provider
        )
        association = CrossAccountAssociation(**json.loads(raw_association))
    except ssm_ops.ParamDoesNotExist:
        association = None

    if association:
        role_arn = f"arn:aws:iam::{association.clusterAccount}:role/{association.roleName}"
        cluster_acct_provider = AwsClientProvider(aws_profile=profile, aws_region=region, assume_role_arn=role_arn)
        vpc_acct_provider = aws_provider
    if not association:
        cluster_acct_provider = vpc_acct_provider = aws_provider

    vpc_aws_env = vpc_acct_provider.get_aws_env()
    cdk_client = CdkClient(vpc_aws_env)

    # Abort if we're not calling in the correct account
    if association and vpc_aws_env.aws_account != association.vpcAccount:
        logger.error("This command must be called with AWS Credential associated with the same AWS Account as the VPC"
                     + f" {vpc_id}.  Expected Account: {association.vpcAccount}, Actual Account: {vpc_aws_env.aws_account}."
                     + " Aborting...")
        return

    # Confirm the Cluster exists and is compatible before proceeding
    try:
        compat.confirm_aws_aio_version_compatibility(cluster_name, cluster_acct_provider)
    except (compat.CliClusterVersionMismatch, compat.CaptureViewerVersionMismatch, compat.UnableToRetrieveClusterVersion) as e:
        logger.error(e)
        logger.warning("Aborting...")
        return

    # Pull all our deployed configuration from SSM and tear down the ENI-specific resources
    vpce_service_id = ssm_ops.get_ssm_param_json_value(
        constants.get_cluster_ssm_param_name(cluster_name),
        "vpceServiceId",
        cluster_acct_provider
    )
    vpc_ssm_param = constants.get_vpc_ssm_param_name(cluster_name, vpc_id)
    event_bus_arn = ssm_ops.get_ssm_param_json_value(vpc_ssm_param, "busArn", vpc_acct_provider)
    subnet_search_path = f"{vpc_ssm_param}/subnets"
    subnet_configs = [json.loads(config["Value"]) for config in ssm_ops.get_ssm_params_by_path(subnet_search_path, vpc_acct_provider)]
    subnet_ids = [config['subnetId'] for config in subnet_configs]
    for subnet_id in subnet_ids:
        eni_search_path = f"{constants.get_subnet_ssm_param_name(cluster_name, vpc_id, subnet_id)}/enis"
        eni_ids = ssm_ops.get_ssm_names_by_path(eni_search_path, vpc_acct_provider)
        
        for eni_id in eni_ids:
            logger.info(f"Initiating teardown of mirroring session for ENI {eni_id}")
            destroy_event = events.DestroyEniMirrorEvent(cluster_name, vpc_id, subnet_id, eni_id)
            events.put_events([destroy_event], event_bus_arn, vpc_acct_provider)

    # Make the VNI available to for re-use by another VPC.  Technically, the VNI's usage is tied to the ENI-specific
    # AWS resources rather than the CDK-generated ones, so we perform this before our CDK operation in case it fails.
    vpc_vni = ssm_ops.get_ssm_param_json_value(vpc_ssm_param, "mirrorVni", vpc_acct_provider)
    vni_provider = SsmVniProvider(cluster_name, cluster_acct_provider)
    vni_provider.relinquish_vni(int(vpc_vni), vpc_id)

    # Destroy the VPC-specific mirroring components in CloudFormation
    logger.info("Tearing down shared mirroring components via CDK...")
    stacks_to_destroy = [
        constants.get_vpc_mirror_setup_stack_name(cluster_name, vpc_id)
    ]
    vpc_remove_context = context.generate_vpc_remove_context(cluster_name, vpc_id, subnet_ids, vpce_service_id)

    cdk_client.destroy(stacks_to_destroy, context=vpc_remove_context)
