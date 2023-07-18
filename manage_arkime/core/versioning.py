import hashlib
from typing import Dict

from core.local_file import LocalFile
from core.shell_interactions import call_shell_command

"""
Manually updated/managed version number.  Increment if/when a backwards incompatible change is made.
"""
AWS_AIO_VERSION=1

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

def get_version_info(config_file: LocalFile, config_version: str = None) -> Dict[str, str]:
    return {
        "aws_aio_version": str(AWS_AIO_VERSION),
        "config_version": config_version if config_version else "1",
        "md5_version": get_md5_of_file(config_file),
        "source_version": get_source_version(),
    }


