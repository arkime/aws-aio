from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import logging
from typing import Dict

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
