import json
import logging
import sys

import arkime_interactions.config_wrangling as config_wrangling
from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.s3_interactions as s3
import aws_interactions.ssm_operations as ssm_ops
import core.constants as constants

logger = logging.getLogger(__name__)

def cmd_config_pull(profile: str, region: str, cluster_name: str, capture: bool, viewer: bool, previous: bool,
                    config_version: int):
    logger.debug(f"Invoking config-list with profile '{profile}' and region '{region}'")

    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)

    try:
        if not (capture or viewer):
            logger.error("You must indicate whether to operate on the Capture or Viewer config; see --help.")
            sys.exit(1)
        elif capture and viewer:
            logger.error("You must indicate either to operate on the Capture or Viewer config, not both; see --help.")
            sys.exit(1)
        elif 1 < sum([1 for param in [config_version, previous] if param]):
            logger.error("You can only select one filter from the set: --config-version, --previous.")
            sys.exit(1)
        elif previous:
            logger.info("Retrieving previous config bundle...")
            disk_location = _get_previous_config(cluster_name, capture, viewer, aws_provider)
            if not disk_location:
                logger.warning("There was no previously deployed config; aborting...")
            else:
                logger.info(f"Placed config bundle on disk:\n{disk_location}")
        elif config_version:
            logger.info(f"Retrieving version {config_version} config bundle...")
            try:
                disk_location = _get_specific_config(cluster_name, capture, viewer, config_version, aws_provider)
            except s3.S3ObjectDoesntExist:
                logger.warning(f"The config version you requested ({config_version}) does not appear to exist; aborting...")
            else:
                logger.info(f"Placed config bundle on disk:\n{disk_location}")
        else:
            logger.info("Retrieving current config bundle...")
            disk_location = _get_current_config(cluster_name, capture, viewer, aws_provider)
            logger.info(f"Placed config bundle on disk:\n{disk_location}")
    except (s3.CantWriteFileAlreadyExists, s3.CantWriteFileDirDoesntExist, s3.CantWriteFileLackPermission, 
            s3.S3ObjectDoesntExist) as ex:
        logger.error(str(ex))
        sys.exit(1)

def _get_deployed_config_metadata(cluster_name: str, capture: bool, viewer: bool,
                                  aws_provider: AwsClientProvider)-> config_wrangling.ConfigDetails:
    config_details_param = (
        constants.get_capture_config_details_ssm_param_name(cluster_name)
        if capture
        else constants.get_viewer_config_details_ssm_param_name(cluster_name)
    )
    raw_param_val = ssm_ops.get_ssm_param_value(config_details_param, aws_provider)
    return config_wrangling.ConfigDetails.from_dict(json.loads(raw_param_val))


def _get_current_config(cluster_name: str, capture: bool, viewer: bool, aws_provider: AwsClientProvider) -> str:
    deployed_config = _get_deployed_config_metadata(cluster_name, capture, viewer, aws_provider)

    aws_env = aws_provider.get_aws_env()
    local_path = (
        config_wrangling.get_capture_config_copy_path(cluster_name, aws_env, deployed_config.version.config_version)
        if capture
        else config_wrangling.get_viewer_config_copy_path(cluster_name, aws_env, deployed_config.version.config_version)
    )

    s3_file = s3.get_object(
        deployed_config.s3.bucket,
        deployed_config.s3.key,
        local_path,
        aws_provider
    )
    
    return s3_file.local_path

def _get_previous_config(cluster_name: str, capture: bool, viewer: bool, aws_provider: AwsClientProvider) -> str:
    deployed_config = _get_deployed_config_metadata(cluster_name, capture, viewer, aws_provider)
    previous_config = deployed_config.previous
    if not previous_config:
        return None

    aws_env = aws_provider.get_aws_env()
    local_path = (
        config_wrangling.get_capture_config_copy_path(cluster_name, aws_env, previous_config.version.config_version)
        if capture
        else config_wrangling.get_viewer_config_copy_path(cluster_name, aws_env, previous_config.version.config_version)
    )

    s3_file = s3.get_object(
        previous_config.s3.bucket,
        previous_config.s3.key,
        local_path,
        aws_provider
    )
    
    return s3_file.local_path

def _get_specific_config(cluster_name: str, capture: bool, viewer: bool, config_version: int, aws_provider: AwsClientProvider) -> str:
    config_version_str = str(config_version)
    
    aws_env = aws_provider.get_aws_env()

    bucket_name = constants.get_config_bucket_name(aws_env.aws_account, aws_env.aws_region, cluster_name)
    s3_key = (
        constants.get_capture_config_s3_key(config_version_str)
        if capture
        else constants.get_viewer_config_s3_key(config_version_str)
    )

    local_path = (
        config_wrangling.get_capture_config_copy_path(cluster_name, aws_env, config_version_str)
        if capture
        else config_wrangling.get_viewer_config_copy_path(cluster_name, aws_env, config_version_str)
    )

    s3_file = s3.get_object(
        bucket_name,
        s3_key,
        local_path,
        aws_provider
    )
    
    return s3_file.local_path

    

    