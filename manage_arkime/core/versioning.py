from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Dict

import arkime_interactions.config_wrangling as config_wrangling
from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.ssm_operations as ssm_ops
import core.constants as constants
from core.local_file import LocalFile
from core.shell_interactions import call_shell_command

logger = logging.getLogger(__name__)

"""
Manually updated/managed version number.  Increment if/when a backwards incompatible change is made.
"""
AWS_AIO_VERSION=2

class CouldntReadSourceVersion(Exception):
    def __init__(self):
        super().__init__("Could not read the source version for unknown reason; check the logs")

def get_md5_of_file(file: LocalFile) -> str:
    hash_md5 = hashlib.md5()

    # Read the file as bytes in 4096-byte chunks and write to a buffer until we hit end of file
    with open(file.local_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    
    # Turn the buffer into the md5
    return hash_md5.hexdigest()

def get_source_version() -> str:
    """
    Gets the version string for the AWS AIO source code.  This is used to correlate behavior (bugs or otherwise) to a
    specific change version.
    """
    exit_code, stdout = call_shell_command("git describe --tags")

    if exit_code != 0:
        raise CouldntReadSourceVersion()
    
    return stdout[0]

@dataclass
class VersionInfo:
    aws_aio_version: str
    config_version: str
    md5_version: str
    source_version: str
    time_utc: str

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VersionInfo):
            return False

        return (self.aws_aio_version == other.aws_aio_version
                    and self.config_version == other.config_version
                    and self.md5_version == other.md5_version
                    and self.source_version == other.source_version
                    and self.time_utc == other.time_utc)

    def to_dict(self) -> Dict[str, str]:
        return {
            "aws_aio_version": self.aws_aio_version,
            "config_version": self.config_version,
            "md5_version": self.md5_version,
            "source_version": self.source_version,
            "time_utc": self.time_utc
        }

def get_version_info(config_file: LocalFile, config_version: str = None) -> VersionInfo:
    return VersionInfo(
        str(AWS_AIO_VERSION),
        config_version if config_version else "1",
        get_md5_of_file(config_file),
        get_source_version(),
        datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    )

class UnableToRetrieveClusterVersion(Exception):
    def __init__(self, cluster_name: str, cli_version: int):
        super().__init__(f"It appears the cluster {cluster_name} does not exist.  There's also a chance the AWS AIO version"
                        + f" of the CLI ({cli_version}) is incompatible with your Cluster.  If you're confident the Cluster"
                        + " exists, you can try checking the AWS AIO version of your cluster using the clusters-list"
                        + " command.  The CLI and Cluster versions must match.")

class CaptureViewerVersionMismatch(Exception):
    def __init__(self, capture_version: int, viewer_version: int):
        super().__init__(f"The AWS AIO versions of your Capture ({capture_version}) and Viewer ({viewer_version}) components"
                         + " do not match.  This is unexpected and should not happen.  Please cut us a ticket at:"
                         + " https://github.com/arkime/aws-aio/issues/new")

class CliClusterVersionMismatch(Exception):
    def __init__(self, cli_version: int, cluster_version: int):
        super().__init__(f"The AWS AIO versions of your CLI ({cli_version}) and Cluster ({cluster_version}) do not"
                         + " match.  This is likely to result in unexpected behavior.  Please revert your CLI to the latest"
                         + f" minor version under the major version ({cluster_version}).  You can see a version listing of"
                         + " the CLI using the command: git ls-remote --tags git@github.com:arkime/aws-aio.git")

def confirm_aws_aio_version_compatibility(cluster_name: str, aws_provider: AwsClientProvider, cli_version: int = AWS_AIO_VERSION):
    # Unfortunately, it appears currently impossible to distinguish between the scenarios where the cluster doesn't
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
