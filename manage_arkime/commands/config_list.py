import json
import logging
import sys

import arkime_interactions.config_wrangling as config_wrangling
from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.s3_interactions as s3
import aws_interactions.ssm_operations as ssm_ops
import core.constants as constants

logger = logging.getLogger(__name__)

def cmd_config_list(profile: str, region: str, cluster_name: str, capture: bool, viewer: bool, deployed: bool):
    logger.debug(f"Invoking config-list with profile '{profile}' and region '{region}'")

    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)

    if not (capture or viewer):
        logger.error("You must indicate whether to operate on the Capture or Viewer config; see --help.")
        sys.exit(1)
    elif capture and viewer:
        logger.error("You must indicate either to operate on the Capture or Viewer config, not both; see --help.")
        sys.exit(1)
    elif deployed:
        logger.info("Retrieving config details...")
        config_details = _get_deployed_config(cluster_name, capture, viewer, aws_provider)
        logger.info(f"Config Details:\n{config_details}")
    else:
        logger.info("Retrieving config details (may take a while)...")
        config_details = _get_all_configs(cluster_name, capture, viewer, aws_provider)
        logger.info(f"Config Details:\n{config_details}")

def _get_deployed_config(cluster_name: str, capture: bool, viewer: bool, aws_provider: AwsClientProvider) -> str:
    config_details_param = (
        constants.get_capture_config_details_ssm_param_name(cluster_name)
        if capture
        else constants.get_viewer_config_details_ssm_param_name(cluster_name)
    )
    raw_param_val = ssm_ops.get_ssm_param_value(config_details_param, aws_provider)
    config = config_wrangling.ConfigDetails.from_dict(json.loads(raw_param_val))

    return_value = {
        "current": config.self_to_dict()
    }
    if not config.previous:
        return_value["previous"] = "None"
    else:
        return_value["previous"] = config.previous.self_to_dict()
    
    return json.dumps(return_value, indent=4)

def _get_all_configs(cluster_name: str, capture: bool, viewer: bool, aws_provider: AwsClientProvider) -> str:
    aws_env = aws_provider.get_aws_env()
    bucket_name = constants.get_config_bucket_name(aws_env.aws_account, aws_env.aws_region, cluster_name)
    key_prefix = "capture" if capture else "viewer"

    # Get the raw object listings, sorted newest to oldest
    logger.debug(f"Listing S3 objects for bucket {bucket_name} and key prefix {key_prefix}")
    config_objects = s3.list_bucket_objects(bucket_name, aws_provider, prefix=key_prefix)
    config_objects.sort(key=lambda x: x['date_modified'], reverse=True)

    # Get the metadata for each config
    all_config_details = []
    for config in config_objects:
        logger.debug(f"Getting S3 metadata for bucket {bucket_name} and key {config['key']}")
        metadata_json = s3.get_object_user_metadata(bucket_name, config["key"], aws_provider)

        config_details = config_wrangling.ConfigDetails(
            config_wrangling.S3Details(bucket_name, config["key"]),
            config_wrangling.VersionInfo(**metadata_json)
        )
        all_config_details.append(config_details.self_to_dict())    
    
    # Return as a string
    return json.dumps(all_config_details, indent=4)

    

    