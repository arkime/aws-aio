import json
import logging
from typing import Callable, Dict, List

import arkime_interactions.config_wrangling as config_wrangling
from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.s3_interactions as s3
import aws_interactions.ssm_operations as ssm_ops
import core.constants as constants
from core.local_file import LocalFile, S3File
from core.versioning import get_version_info

logger = logging.getLogger(__name__)

def cmd_config_update(profile: str, region: str, cluster_name: str):
    logger.debug(f"Invoking config-update with profile '{profile}' and region '{region}'")

    # Confirm that the config directory exists; abort if it doesn't

    # Update Capture/Viewer config in the cloud, if there's a new version locally
    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)
    aws_env = aws_provider.get_aws_env()
    bucket_name = constants.get_config_bucket_name(aws_env.aws_account, aws_env.aws_region, cluster_name)

    logger.info("Updating Arkime config for Capture Nodes, if necessary...")
    _update_config_if_necessary(
        cluster_name,
        bucket_name,
        constants.get_capture_config_s3_key,
        constants.get_capture_config_details_ssm_param_name(cluster_name),
        config_wrangling.get_capture_config_archive,
        aws_provider
    )

    logger.info("Updating Arkime config for Viewer Nodes, if necessary...")
    _update_config_if_necessary(
        cluster_name,
        bucket_name,
        constants.get_viewer_config_s3_key,
        constants.get_viewer_config_details_ssm_param_name(cluster_name),
        config_wrangling.get_viewer_config_archive,
        aws_provider
    )

    # Kick off ECS force deployment; poll using DescribeService and look for failed tasks; revert param store if see them



def _update_config_if_necessary(cluster_name: str, bucket_name: str, s3_key_provider: Callable[[str], str], ssm_param: str,
                                archive_provider: Callable[[str], LocalFile], aws_provider: AwsClientProvider
                                ):
    # Create the local config archive and its metadata
    archive = archive_provider(cluster_name)
    archive_md5 = get_version_info(archive).md5_version

    # See if we need to update the configuration
    try:
        logger.info(f"Pulling existing configuration details from Param Store at: {ssm_param}")
        raw_param_val = ssm_ops.get_ssm_param_value(ssm_param, aws_provider)
        cloud_config_details = config_wrangling.ConfigDetails.from_dict(json.loads(raw_param_val))
    except ssm_ops.ParamDoesNotExist:
        logger.debug(f"No existing configuration details at: {ssm_param}")
        cloud_config_details = None

    if cloud_config_details and cloud_config_details.version.md5_version == archive_md5:
        logger.info(f"Local config is the same as what's currently deployed; skipping")
        return
    
    # Create the config details for the local archive.  The ConfigDetails contains a reference to the previous,
    # which means it's a recursive data structure.  For now, we limit ourselves to only tracking the current and
    # previous versions of the configuration to avoid running into storage limits.  We can explore maintaining a
    # deeper structure later if there's a need to track the full deployed version history.
    next_config_version = str(int(cloud_config_details.version.config_version) + 1)

    if cloud_config_details:
        cloud_config_details.previous = None

    local_config_details = config_wrangling.ConfigDetails(
        s3=config_wrangling.S3Details(bucket_name, s3_key_provider(next_config_version)),
        version=get_version_info(archive, config_version=next_config_version),
        previous=cloud_config_details
    )
    
    # Upload the archive to S3.  Do this first so that if this operation succeeds, but the update of Parameter Store
    # fails afterwards, then another run of the CLI command should fix things.
    logger.info(f"Uploading config archive to S3 bucket: {bucket_name}")
    s3.put_file_to_bucket(
        S3File(archive, metadata=local_config_details.version.to_dict()),
        bucket_name,
        s3_key_provider(next_config_version),
        aws_provider
    )

    # Update Parameter Store
    logger.info(f"Updating config details in Param Store at: {ssm_param}")
    ssm_ops.put_ssm_param(
        ssm_param,
        json.dumps(local_config_details.to_dict()),
        aws_provider,
        description="The currently deployed configuration details",
        overwrite=True
    )