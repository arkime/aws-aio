import json
import logging
import sys
from typing import Dict, List

import arkime_interactions.config_wrangling as config_wrangling
from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.s3_interactions as s3
import aws_interactions.ssm_operations as ssm_ops
import core.constants as constants

logger = logging.getLogger(__name__)

def cmd_config_pull(profile: str, region: str, cluster_name: str, capture: bool, viewer: bool):
    logger.debug(f"Invoking config-list with profile '{profile}' and region '{region}'")

    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)

    if not (capture or viewer):
        logger.error("You must indicate whether to operate on the Capture or Viewer config; see --help.")
        sys.exit(1)
    elif capture and viewer:
        logger.error("You must indicate either to operate on the Capture or Viewer config, not both; see --help.")
        sys.exit(1)
    else:
        logger.info("Retrieving config bundle...")
        disk_location = _get_current_config(cluster_name, capture, viewer, aws_provider)
        logger.info(f"Placed config bundle on disk:\n{disk_location}")

def _get_current_config(cluster_name: str, capture: bool, viewer: bool, aws_provider: AwsClientProvider) -> str:
    config_details_param = (
        constants.get_capture_config_details_ssm_param_name(cluster_name)
        if capture
        else constants.get_viewer_config_details_ssm_param_name(cluster_name)
    )
    raw_param_val = ssm_ops.get_ssm_param_value(config_details_param, aws_provider)
    current_config = config_wrangling.ConfigDetails.from_dict(json.loads(raw_param_val))

    aws_env = aws_provider.get_aws_env()
    local_path = (
        config_wrangling.get_capture_config_copy_path(cluster_name, aws_env, current_config.version.config_version)
        if capture
        else config_wrangling.get_viewer_config_copy_path(cluster_name, aws_env, current_config.version.config_version)
    )

    s3_file = s3.get_object(
        current_config.s3.bucket,
        current_config.s3.key,
        local_path,
        aws_provider
    )
    
    return s3_file.local_path

    

    