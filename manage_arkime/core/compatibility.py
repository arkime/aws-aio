import json

import arkime_interactions.config_wrangling as config_wrangling
from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.ssm_operations as ssm_ops
import core.constants as constants
from core.versioning import AWS_AIO_VERSION

class UnableToRetrieveClusterVersion(Exception):
    def __init__(self, cluster_name: str, cli_version: int):
        super().__init__(f"It appears the cluster {cluster_name} does not exist.  There's also a chance the AWS AIO version"
                        + f" of the CLI ({cli_version}) is incompatible with your Cluster.  If you're confident the Cluster"
                        + " exists, you can try checking the AWS AIO version of your cluster using the clusters-list"
                        + " command.  The CLI and Cluster versions must match.")

class CaptureViewerVersionMismatch(Exception):
    def __init__(self, capture_version: int, viewer_version: int):
        super().__init__(f"The AWS AIO versions of your Capture ({capture_version}) and Viewer ({viewer_version})"
                         + " components do not match.  This is unexpected and should not happen.  Please cut us a"
                         + " ticket at: https://github.com/arkime/aws-aio/issues/new")

class CliClusterVersionMismatch(Exception):
    def __init__(self, cli_version: int, cluster_version: int):
        super().__init__(f"The AWS AIO versions of your CLI ({cli_version}) and Cluster ({cluster_version}) do not"
                         + " match.  This is likely to result in unexpected behavior.  Please change your CLI to the"
                         + f" latest minor version under the major version ({cluster_version}).  Check out the"
                         + " following README section for more details:"
                         + " https://github.com/arkime/aws-aio#aws-aio-version-mismatch")

def confirm_aws_aio_version_compatibility(cluster_name: str, aws_provider: AwsClientProvider,
                                          cli_version: int = AWS_AIO_VERSION):
    # Unfortunately, it currently appears impossible to distinguish between the scenarios where the cluster doesn't
    # exist and the cluster exists but is a different version.  In either case, we could get the ParamDoesNotExist
    # exception.
    try:
        raw_capture_details_val = ssm_ops.get_ssm_param_value(
            constants.get_capture_config_details_ssm_param_name(cluster_name),
            aws_provider
        )
        capture_config_details = config_wrangling.ConfigDetails.from_dict(json.loads(raw_capture_details_val))

        raw_viewer_details_val = ssm_ops.get_ssm_param_value(
            constants.get_viewer_config_details_ssm_param_name(cluster_name),
            aws_provider
        )
        viewer_config_details = config_wrangling.ConfigDetails.from_dict(json.loads(raw_viewer_details_val))
    except ssm_ops.ParamDoesNotExist:
        raise UnableToRetrieveClusterVersion(cluster_name, cli_version)
    
    capture_version = int(capture_config_details.version.aws_aio_version)
    viewer_version = int(viewer_config_details.version.aws_aio_version)

    if capture_version != viewer_version:
        raise CaptureViewerVersionMismatch(capture_version, viewer_version)

    if capture_version != cli_version:
        raise CliClusterVersionMismatch(cli_version, capture_version)
    
    # Everything matches, we're good to go
    return