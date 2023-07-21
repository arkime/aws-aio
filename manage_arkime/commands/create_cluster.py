import json
import logging
import sys
from typing import Callable

import arkime_interactions.config_wrangling as config_wrangling
from aws_interactions.acm_interactions import upload_default_elb_cert
from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.events_interactions as events
import aws_interactions.s3_interactions as s3
import aws_interactions.ssm_operations as ssm_ops
from cdk_interactions.cdk_client import CdkClient
from aws_interactions.aws_environment import AwsEnvironment
import cdk_interactions.cdk_context as context
import core.constants as constants
from core.local_file import LocalFile, TarGzDirectory, S3File
from core.usage_report import UsageReport
from core.capacity_planning import (get_capture_node_capacity_plan, get_ecs_sys_resource_plan, get_os_domain_plan, ClusterPlan,
                                    CaptureVpcPlan, MINIMUM_TRAFFIC, DEFAULT_SPI_DAYS, DEFAULT_REPLICAS, DEFAULT_NUM_AZS,
                                    S3Plan, DEFAULT_S3_STORAGE_CLASS, DEFAULT_S3_STORAGE_DAYS, DEFAULT_HISTORY_DAYS, CaptureNodesPlan, DataNodesPlan, EcsSysResourcePlan, MasterNodesPlan, OSDomainPlan)
from core.versioning import get_version_info
from core.user_config import UserConfig

logger = logging.getLogger(__name__)

def cmd_create_cluster(profile: str, region: str, name: str, expected_traffic: float, spi_days: int, history_days: int, replicas: int,
                       pcap_days: int, preconfirm_usage: bool):
    logger.debug(f"Invoking create-cluster with profile '{profile}' and region '{region}'")

    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)
    aws_env = aws_provider.get_aws_env()
    cdk_client = CdkClient(aws_env)

    # Generate our capacity plan and confirm it's what the user expected
    previous_user_config = _get_previous_user_config(name, aws_provider)
    next_user_config = _get_next_user_config(name, expected_traffic, spi_days, history_days, replicas, pcap_days, aws_provider)
    previous_capacity_plan = _get_previous_capacity_plan(name, aws_provider)
    next_capacity_plan = _get_next_capacity_plan(next_user_config)

    if not _confirm_usage(previous_capacity_plan, next_capacity_plan, previous_user_config, next_user_config, preconfirm_usage):
        logger.info("Aborting per user response")
        return

    # Set up the cert the Viewers use for HTTPS
    cert_arn = _set_up_viewer_cert(name, aws_provider)

    # Set up the Arkime Config so it's available in-AWS
    _set_up_arkime_config(name, aws_provider)

    # Deploy the CFN Resources
    stacks_to_deploy = [
        constants.get_capture_bucket_stack_name(name),
        constants.get_capture_nodes_stack_name(name),
        constants.get_capture_vpc_stack_name(name),
        constants.get_opensearch_domain_stack_name(name),
        constants.get_viewer_nodes_stack_name(name)
    ]
    create_context = context.generate_create_cluster_context(
        name,
        cert_arn,
        next_capacity_plan,
        next_user_config,
        constants.get_config_bucket_name(aws_env.aws_account, aws_env.aws_region, name)
    )
    cdk_client.deploy(stacks_to_deploy, context=create_context)

    # Kick off Events to ensure that ISM is set up on the CFN-created OpenSearch Domain
    _configure_ism(name, next_user_config.historyDays, next_user_config.spiDays, next_user_config.replicas, aws_provider)

def _get_previous_user_config(cluster_name: str, aws_provider: AwsClientProvider) -> UserConfig:
    # Pull the existing config, if possible
    try:
        stored_config_json = ssm_ops.get_ssm_param_json_value(
            constants.get_cluster_ssm_param_name(cluster_name),
            "userConfig",
            aws_provider
        )
        return UserConfig(**stored_config_json)

    # Existing config doesn't exist; return a blank config
    except ssm_ops.ParamDoesNotExist:
        return UserConfig(None, None, None, None, None)

def _get_next_user_config(cluster_name: str, expected_traffic: float, spi_days: int, history_days: int, replicas: int, 
                     pcap_days: int, aws_provider: AwsClientProvider) -> UserConfig:
    # At least one parameter isn't defined
    if None in [expected_traffic, spi_days, replicas, pcap_days, history_days]:
        # Re-use the existing configuration if it exists
        try:
            stored_config_json = ssm_ops.get_ssm_param_json_value(
                constants.get_cluster_ssm_param_name(cluster_name),
                "userConfig",
                aws_provider
            )
            user_config = UserConfig(**stored_config_json)

            if expected_traffic is not None:
                user_config.expectedTraffic = expected_traffic
            if spi_days is not None:
                user_config.spiDays = spi_days
            if history_days is not None:
                user_config.historyDays = history_days
            if replicas is not None:
                user_config.replicas = replicas
            if pcap_days is not None:
                user_config.pcapDays = pcap_days

            return user_config

        # Existing configuration doesn't exist, use defaults
        except ssm_ops.ParamDoesNotExist:
            return UserConfig(MINIMUM_TRAFFIC, DEFAULT_SPI_DAYS, DEFAULT_HISTORY_DAYS, DEFAULT_REPLICAS, DEFAULT_S3_STORAGE_DAYS)
    # All of the parameters defined
    else:
        return UserConfig(expected_traffic, spi_days, history_days, replicas, pcap_days)
    
def _get_previous_capacity_plan(cluster_name: str, aws_provider: AwsClientProvider) -> ClusterPlan:
    # Pull the existing plan, if possible
    try:
        stored_plan_json = ssm_ops.get_ssm_param_json_value(
            constants.get_cluster_ssm_param_name(cluster_name),
            "capacityPlan",
            aws_provider
        )
        return ClusterPlan.from_dict(stored_plan_json)

    # Existing plan doesn't exist; return a blank plan
    except ssm_ops.ParamDoesNotExist:
        return ClusterPlan(
            CaptureNodesPlan(None, None, None, None),
            CaptureVpcPlan(None),
            EcsSysResourcePlan(None, None),
            OSDomainPlan(DataNodesPlan(None, None, None), MasterNodesPlan(None, None)),
            S3Plan(None, None)
        )

def _get_next_capacity_plan(user_config: UserConfig) -> ClusterPlan:
    capture_plan = get_capture_node_capacity_plan(user_config.expectedTraffic)
    capture_vpc_plan = CaptureVpcPlan(DEFAULT_NUM_AZS)
    os_domain_plan = get_os_domain_plan(user_config.expectedTraffic, user_config.spiDays, user_config.replicas, capture_vpc_plan.numAzs)
    ecs_resource_plan = get_ecs_sys_resource_plan(capture_plan.instanceType)
    s3_plan = S3Plan(DEFAULT_S3_STORAGE_CLASS, user_config.pcapDays)

    return ClusterPlan(capture_plan, capture_vpc_plan, ecs_resource_plan, os_domain_plan, s3_plan)

def _confirm_usage(prev_capacity_plan: ClusterPlan, next_capacity_plan: ClusterPlan, prev_user_config: UserConfig,
                   next_user_config: UserConfig, preconfirm_usage: bool) -> bool:

    report = UsageReport(prev_capacity_plan, next_capacity_plan, prev_user_config, next_user_config)

    if preconfirm_usage:
        logger.info(f"Usage report:\n{report.get_report()}")
        return True
    return report.get_confirmation()

def _upload_arkime_config_if_necessary(cluster_name: str, bucket_name: str, s3_key: str, ssm_param: str,
                                       tarball_provider: Callable[[str], LocalFile], aws_provider: AwsClientProvider):
    """
    The argument list is a bit ugly, but this allows us to avoid having too much duplicated logic.  Will be looking
    for a better way to handle the two very similar but annoyingly different logics for the capture/viewer config.
    """

    # Check if the Arkime config info exists in Param Store to see if we need to do any other work.
    # If it does exists, we can return.
    try:
        ssm_ops.get_ssm_param_value(ssm_param, aws_provider)
        logger.info("Config has been uploaded previously; skipping")
        return
    except ssm_ops.ParamDoesNotExist:
        pass # We need to actually do work

    # Create the Capture and Viewer config tarballs
    tarball = tarball_provider(cluster_name)

    # Generate their metadata
    next_metadata = config_wrangling.ConfigDetails(
        s3=config_wrangling.S3Details(bucket_name, s3_key),
        version=get_version_info(tarball)
    )
    
    # Upload the tarballs to S3
    logger.info(f"Uploading config tarball to S3 bucket: {bucket_name}")
    s3.put_file_to_bucket(
        S3File(tarball, metadata=next_metadata.version.to_dict()),
        bucket_name,
        s3_key,
        aws_provider
    )

    # Update Parameter Store
    ssm_ops.put_ssm_param(
        ssm_param,
        json.dumps(next_metadata.to_dict()),
        aws_provider,
        description="The currently deployed configuration details",
        overwrite=True
    )

def _set_up_arkime_config(cluster_name: str, aws_provider: AwsClientProvider):
    # Create a copy of the the default Arkime config (if necessary)
    cluster_config_parent_dir_path = constants.get_cluster_config_parent_dir()
    config_wrangling.set_up_arkime_config_dir(cluster_name, cluster_config_parent_dir_path)

    # Check whether the S3 bucket exists and whether we have access; error and abort if we don't have access
    aws_env = aws_provider.get_aws_env()
    bucket_name = constants.get_config_bucket_name(aws_env.aws_account, aws_env.aws_region, cluster_name)
    capture_s3_key = constants.get_capture_config_s3_key("1")
    viewer_s3_key = constants.get_viewer_config_s3_key("1")

    try:
        s3.ensure_bucket_exists(bucket_name, aws_provider)
    except s3.CouldntEnsureBucketExists:
        logger.error(f"Couldn't ensure S3 bucket {bucket_name} exists; aborting operation")
        sys.exit(1)

    # Upload the Capture Config if we need to
    logger.info("Uploading Arkime config for Capture Nodes...")
    _upload_arkime_config_if_necessary(
        cluster_name,
        bucket_name,
        capture_s3_key,
        constants.get_capture_config_details_ssm_param_name(cluster_name),
        config_wrangling.get_capture_config_tarball,
        aws_provider
    )

    # Upload the Viewer Config if we need to
    logger.info("Uploading Arkime config for Viewer Nodes...")
    _upload_arkime_config_if_necessary(
        cluster_name,
        bucket_name,
        viewer_s3_key,
        constants.get_viewer_config_details_ssm_param_name(cluster_name),
        config_wrangling.get_viewer_config_tarball,
        aws_provider
    )

def _set_up_viewer_cert(name: str, aws_provider: AwsClientProvider) -> str:
    # Only set up the certificate if it doesn't exist
    cert_ssm_param = constants.get_viewer_cert_ssm_param_name(name)
    try:
        cert_arn = ssm_ops.get_ssm_param_value(cert_ssm_param, aws_provider)
        logger.debug(f"Viewer certificate already exists ({cert_arn}); skipping creation")
        return cert_arn
    except ssm_ops.ParamDoesNotExist:
        pass

    # Create our cert and set up our state
    logger.debug("Viewer certificate does not exist; creating...")
    cert_arn = upload_default_elb_cert(aws_provider)
    logger.debug(f"Viewer certificate created: {cert_arn}")

    logger.debug("Setting SSM Param for viewer certificate...")
    ssm_ops.put_ssm_param(
        cert_ssm_param,
        cert_arn,
        aws_provider,
        f"A self-signed certificate for the Cluster {name} Viewer Nodes' ALB"
    )

    return cert_arn

def _configure_ism(cluster_name: str, history_days: int, spi_days: int, replicas: int, aws_provider: AwsClientProvider):
    event_bus_arn = ssm_ops.get_ssm_param_json_value(constants.get_cluster_ssm_param_name(cluster_name), "busArn", aws_provider)

    # Configure ISM on the OpenSearch Domain
    events.put_events(
        [events.ConfigureIsmEvent(history_days, spi_days, replicas)],
        event_bus_arn,
        aws_provider
    )