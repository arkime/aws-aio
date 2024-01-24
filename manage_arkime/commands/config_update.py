import json
import logging
from sys import exit
from time import sleep
from typing import Callable

import arkime_interactions.config_wrangling as config_wrangling
from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.ecs_interactions as ecs
import aws_interactions.s3_interactions as s3
import aws_interactions.ssm_operations as ssm_ops
import core.compatibility as compat
import core.constants as constants
from core.local_file import LocalFile, S3File
import core.versioning as ver

logger = logging.getLogger(__name__)

def cmd_config_update(profile: str, region: str, cluster_name: str, capture: bool, viewer: bool, force_bounce: bool,
                      config_version: int):
    logger.debug(f"Invoking config-update with profile '{profile}' and region '{region}'")

    one_component_specified = (capture or viewer) and not (capture and viewer) # XOR
    no_component_specified = not (capture or viewer)
    if config_version and (not one_component_specified):
        logger.error("If you specify a specific config version to deploy, you must indicate whether to deploy it to"
                     + " either the Capture or Viewer nodes.")
        logger.warning("Aborting...")
        exit(1)

    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)
    aws_env = aws_provider.get_aws_env()

    try:
        compat.confirm_aws_aio_version_compatibility(cluster_name, aws_provider)
    except (compat.CliClusterVersionMismatch, compat.CaptureViewerVersionMismatch, compat.UnableToRetrieveClusterVersion) as e:
        logger.error(e)
        logger.warning("Aborting...")
        return

    # Update Capture/Viewer config in the cloud, if there's a new version locally.  Bounce the associated ECS Tasks
    # if we updated the configuration so that they pick it up.    
    bucket_name = constants.get_config_bucket_name(aws_env.aws_account, aws_env.aws_region, cluster_name)

    logger.info("Updating Arkime config for Capture Nodes, if necessary...")
    if capture or no_component_specified:
        should_bounce_capture_nodes = _update_config_if_necessary(
            cluster_name,
            bucket_name,
            constants.get_capture_config_s3_key,
            constants.get_capture_config_details_ssm_param_name(cluster_name),
            config_wrangling.get_capture_config_archive,
            config_version,
            aws_provider
        )

        if should_bounce_capture_nodes or force_bounce:
            raw_capture_details = ssm_ops.get_ssm_param_value(
                constants.get_capture_details_ssm_param_name(cluster_name),
                aws_provider
            )
            capture_details = config_wrangling.CaptureDetails(**json.loads(raw_capture_details))
            _bounce_ecs_service(
                capture_details.ecsCluster,
                capture_details.ecsService,
                constants.get_capture_config_details_ssm_param_name(cluster_name),
                aws_provider
            )
    else:
        logger.info("Skipping Capture Nodes due to user parameters supplied")

    logger.info("Updating Arkime config for Viewer Nodes, if necessary...")
    if viewer or no_component_specified:
        should_bounce_viewer_nodes = _update_config_if_necessary(
            cluster_name,
            bucket_name,
            constants.get_viewer_config_s3_key,
            constants.get_viewer_config_details_ssm_param_name(cluster_name),
            config_wrangling.get_viewer_config_archive,
            config_version,
            aws_provider
        )
        
        if should_bounce_viewer_nodes or force_bounce:
            raw_viewer_details = ssm_ops.get_ssm_param_value(
                constants.get_viewer_details_ssm_param_name(cluster_name),
                aws_provider
            )
            viewer_details = config_wrangling.ViewerDetails(**json.loads(raw_viewer_details))
            _bounce_ecs_service(
                viewer_details.ecsCluster,
                viewer_details.ecsService,
                constants.get_viewer_config_details_ssm_param_name(cluster_name),
                aws_provider
            )
    else:
        logger.info("Skipping Viewer Nodes due to user parameters supplied")

def _update_config_if_necessary(cluster_name: str, bucket_name: str, s3_key_provider: Callable[[str], str], ssm_param: str,
                                archive_provider: Callable[[str], LocalFile], switch_to_version: int,
                                aws_provider: AwsClientProvider) -> bool:
    # Create the local config archive and its metadata
    aws_env = aws_provider.get_aws_env()
    archive = archive_provider(cluster_name, aws_env)
    archive_md5 = ver.get_version_info(archive).md5_version

    # Confirm the requested version exists, if specified
    if switch_to_version:
        try:
            raw_metadata = s3.get_object_user_metadata(bucket_name, s3_key_provider(switch_to_version), aws_provider)
            switch_version_info = config_wrangling.VersionInfo(**raw_metadata)
        except s3.S3ObjectDoesntExist:
            logger.warning(f"The requested config version ({switch_to_version}) does not exist; aborting...")
            return False

    # Pull the currently deployed config details from the cloud so we can see if we need to update the configuration.
    # If there isn't a current version in the cloud, we know we should perform the update.
    try:
        logger.info(f"Pulling existing configuration details from Param Store at: {ssm_param}")
        raw_param_val = ssm_ops.get_ssm_param_value(ssm_param, aws_provider)
        cloud_config_details = config_wrangling.ConfigDetails.from_dict(json.loads(raw_param_val))
    except ssm_ops.ParamDoesNotExist:
        logger.debug(f"No existing configuration details at: {ssm_param}")
        cloud_config_details = None

    if cloud_config_details:
        same_md5 = (cloud_config_details.version.md5_version == archive_md5)
        same_config_version = (cloud_config_details.version.config_version == switch_to_version)

        if switch_to_version and same_config_version: # Comparing to the previous S3 object's version
            logger.info(f"The previous version you specified is the same as what's currently deployed; skipping swap")
            return False
        elif same_md5 and not switch_to_version: # Comparing to the local config archive's version
            logger.info(f"The local config is the same as what's currently deployed; skipping upload")
            return False

    # Assemble the config details for the next config version.  This can be either the config on the local file system
    # or a previously deployed version already in the cloud.
    # 
    # The ConfigDetails contains a reference to the previous, which means it's a recursive data structure.  For now,
    # we limit ourselves to only tracking the current and previous versions of the configuration to avoid running into
    # storage limits.  We can explore maintaining a deeper structure later if there's a need to track the full deployed
    # version history.
    next_config_version = (
       str(switch_to_version)
        if switch_to_version
        else str(int(cloud_config_details.version.config_version) + 1)
    )    

    if cloud_config_details:
        cloud_config_details.previous = None

    next_config_details = (
        config_wrangling.ConfigDetails(
            s3=config_wrangling.S3Details(bucket_name, s3_key_provider(next_config_version)),
            version=switch_version_info,
            previous=cloud_config_details
        )
        if switch_to_version
        else config_wrangling.ConfigDetails(
            s3=config_wrangling.S3Details(bucket_name, s3_key_provider(next_config_version)),
            version=ver.get_version_info(archive, config_version=next_config_version),
            previous=cloud_config_details
        )        
    )   

    # Upload the archive to S3.  Do this first so that if this operation succeeds, but the update of Parameter Store
    # fails afterwards, then another run of the CLI command should fix things.  Unnecessary if we're switching to a
    # previous version (it's already in S3).
    if not switch_to_version:
        logger.info(f"Uploading config archive to S3 bucket: {bucket_name}")
        s3.put_file_to_bucket(
            S3File(archive, metadata=next_config_details.version.to_dict()),
            bucket_name,
            s3_key_provider(next_config_version),
            aws_provider
        )

    # Update Parameter Store.  This switches the pointer to what version the containers should pull from S3 when they
    # start up.  The containers then unpack the config bundle as part of their bootstrapping process.
    logger.info(f"Updating config details in Param Store at: {ssm_param}")
    ssm_ops.put_ssm_param(
        ssm_param,
        json.dumps(next_config_details.to_dict()),
        aws_provider,
        description="The currently deployed configuration details",
        overwrite=True
    )

    return True

class NoPreviousConfig(Exception):
    def __init__(self):
        super().__init__(f"There is no known previous configuration to roll back to.")

def _revert_arkime_config(ssm_param: str, aws_provider: AwsClientProvider):
    # Pull the existing Arkime config details
    logger.info(f"Pulling in-progress configuration details from Param Store at: {ssm_param}")
    raw_param_val = ssm_ops.get_ssm_param_value(ssm_param, aws_provider)
    in_progress_config_details = config_wrangling.ConfigDetails.from_dict(json.loads(raw_param_val))

    # Revert to the previous configuration
    reverted_config_details = in_progress_config_details.previous

    if not reverted_config_details:
        logger.error(f"The parameter store value {ssm_param} does not have a set previous configuration to roll back"
                     + " to.  This is unexpected, and should not occur in normal operation.  You will need to take"
                     + " manual action in order to rectify the situation.  You can find your other configuration"
                     + f" versions in the S3 bucket {in_progress_config_details.s3.bucket}; each object has the"
                     + " version information embedded in the S3 metadata.  You can manually update the SSM parameter"
                     + " to refer to a specific config version you know is good using that metadata.  The ECS service"
                     + " will keep attemping to spin up new containers and pulling down the configuration specified in"
                     + " the SSM parameter until it succeeds (or times out).")
        raise NoPreviousConfig()

    # Upload new object
    logger.info(f"Uploading reverted config details to Param Store at: {ssm_param}")
    ssm_ops.put_ssm_param(
        ssm_param,
        json.dumps(reverted_config_details.to_dict()),
        aws_provider,
        description="The currently deployed configuration details",
        overwrite=True
    )

def _bounce_ecs_service(ecs_cluster: str, ecs_service: str, ssm_param: str, aws_provider: AwsClientProvider):
    logger.info(f"Bouncing ECS Service {ecs_service} to pick up the new Arkime config...")
    # Kick off a force deployment to recycle the ECS containers
    ecs.force_ecs_deployment(ecs_cluster, ecs_service, aws_provider)

    try:
        failed_task_limit = 3 # arbitrarily chosen
        wait_time_sec = 15 # arbitrarily chosen
        reverted = False
        while ecs.is_deployment_in_progress(ecs_cluster, ecs_service, aws_provider):
            failed_task_count = ecs.get_failed_task_count(ecs_cluster, ecs_service, aws_provider)
            if failed_task_count >= failed_task_limit and not reverted:
                logger.warning(f"Failed task limit of {failed_task_limit} exceeded; rolling back to previous config")
                _revert_arkime_config(ssm_param, aws_provider)
                reverted = True
            logger.info(f"Waiting {wait_time_sec} more seconds for ECS service to finish bouncing...")
            sleep(wait_time_sec)

        if not reverted:
            logger.info(f"ECS Service {ecs_service} bounced successfully")
        else:
            logger.warning(f"ECS Service {ecs_service} did not stabilize with the new config.  Config was reverted.")
    except NoPreviousConfig:
        logger.error("Unable to roll back to previous config; exiting")
        exit(1)
    except KeyboardInterrupt:
        logger.info("Received a keyboard interrupt")

        if not reverted:
            logger.info("Rolling back to previous configuration")
            _revert_arkime_config(ssm_param, aws_provider)

        logger.info("Exiting...")
        exit(0)

