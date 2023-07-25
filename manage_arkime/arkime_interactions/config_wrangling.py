from __future__ import annotations
from dataclasses import dataclass
import logging
import os
import shutil
from typing import Dict, Type, TypeVar

from core.constants import get_cluster_config_parent_dir, is_valid_cluster_name, InvalidClusterName
from core.local_file import LocalFile, ZipDirectory
from core.versioning import VersionInfo

logger = logging.getLogger(__name__)


@dataclass
class S3Details:
    bucket: str
    key: str

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, S3Details):
            return False

        return (self.bucket == other.bucket) and (self.key == other.key)

    def to_dict(self) -> Dict[str, str]:
        return {
            "bucket": self.bucket,
            "key": self.key
        }

T_ConfigDetails = TypeVar('T_ConfigDetails', bound='ConfigDetails')

@dataclass
class ConfigDetails:
    s3: S3Details
    version: VersionInfo
    previous: ConfigDetails = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConfigDetails):
            return False

        return (self.s3 == other.s3
                and self.version == other.version
                and self.previous == other.previous)

    def to_dict(self) -> Dict[str, str]:
        return {
            "s3": self.s3.to_dict(),
            "version": self.version.to_dict(),
            "previous": self.previous.to_dict() if self.previous else "None",
        }
    
    @classmethod
    def from_dict(cls: Type[T_ConfigDetails], input: Dict[str, any]) -> T_ConfigDetails:
        s3 = S3Details(**input["s3"])
        version = VersionInfo(**input["version"])
        previous = ConfigDetails.from_dict(input["previous"]) if input["previous"] != "None" else None
        return cls(s3, version, previous)

@dataclass
class ViewerDetails:
    dns: str
    ecsService: str
    passwordArn: str
    user: str

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ViewerDetails):
            return False

        return (self.dns == other.dns
                and self.ecsService == other.ecsService
                and self.passwordArn == other.passwordArn
                and self.user == other.user)

    def to_dict(self) -> Dict[str, str]:
        return {
            "dns": self.dns,
            "ecsService": self.ecsService,
            "passwordArn": self.passwordArn,
            "user": self.user
        }

class ConfigDirNotEmpty(Exception):
    def __init__(self, cluster_dir_path: str):
        self.cluster_dir_path = cluster_dir_path
        super().__init__(f"The Cluster config directory is not empty: {cluster_dir_path}")

def _get_default_capture_config_dir_path() -> str:
    current_file_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(current_file_path, "default_config", "capture")

def _get_default_viewer_config_dir_path() -> str:
    current_file_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(current_file_path, "default_config", "viewer")

def get_cluster_dir_name(cluster_name: str) -> str:
    # We should validate earlier, but practice defense in depth
    if not is_valid_cluster_name(cluster_name):
        raise InvalidClusterName(cluster_name)
    
    return f"config-{cluster_name}"

def get_cluster_dir_path(cluster_name: str, parent_dir: str):
    cluster_dir_name = get_cluster_dir_name(cluster_name)
    return os.path.join(parent_dir, cluster_dir_name)

def get_capture_dir_path(cluster_name: str, parent_dir: str):
    cluster_dir_path = get_cluster_dir_path(cluster_name, parent_dir)
    return os.path.join(cluster_dir_path, "capture")

def get_capture_archive_path(cluster_name: str, parent_dir: str):
    cluster_dir_path = get_cluster_dir_path(cluster_name, parent_dir)
    return os.path.join(cluster_dir_path, "capture.zip")

def get_viewer_dir_path(cluster_name: str, parent_dir: str):
    cluster_dir_path = get_cluster_dir_path(cluster_name, parent_dir)
    return os.path.join(cluster_dir_path, "viewer")

def get_viewer_archive_path(cluster_name: str, parent_dir: str):
    cluster_dir_path = get_cluster_dir_path(cluster_name, parent_dir)
    return os.path.join(cluster_dir_path, "viewer.zip")

def _create_config_dir(cluster_name: str, parent_dir: str) -> str:
    cluster_dir_path = get_cluster_dir_path(cluster_name, parent_dir)

    logger.debug(f"Checking if config dir for cluster {cluster_name} already exists at: {cluster_dir_path}")
    if os.path.exists(cluster_dir_path):
        logger.debug(f"Config dir for cluster {cluster_name} already exists")
        return cluster_dir_path

    logger.debug(f"Config dir for cluster {cluster_name} does not exist; creating...")
    os.makedirs(cluster_dir_path)

    return cluster_dir_path

def _copy_default_config_to_cluster_dir(cluster_name: str, parent_dir: str):
    # If there is anything in the directory, abort
    cluster_dir_path = get_cluster_dir_path(cluster_name, parent_dir)
    directory_not_empty = len(os.listdir(cluster_dir_path)) > 0

    logger.debug(f"Confirming config dir for cluster {cluster_name} is empty...")
    if directory_not_empty:
        raise ConfigDirNotEmpty(cluster_dir_path)
    
    # Copy over the default config for the capture and viewer nodes
    logger.debug(f"Config dir for cluster {cluster_name} is empty; copying default config to: {cluster_dir_path}")
    shutil.copytree(
        _get_default_capture_config_dir_path(),
        get_capture_dir_path(cluster_name, parent_dir)
    )
    shutil.copytree(
        _get_default_viewer_config_dir_path(),
        get_viewer_dir_path(cluster_name, parent_dir)
    )

def set_up_arkime_config_dir(cluster_name: str, parent_dir: str):
    logger.info(f"Ensuring Arkime Config dir exists for cluster: {cluster_name}")
    cluster_config_dir_path = _create_config_dir(cluster_name, parent_dir)
    logger.info(f"Arkime Config dir exists at: {cluster_config_dir_path}")

    try:
        logger.info(f"Copying default Arkime Config to dir: {cluster_config_dir_path}")
        _copy_default_config_to_cluster_dir(cluster_name, parent_dir)
    except ConfigDirNotEmpty as ex:
        logger.info("Cluster config directory not empty; skipping copy")

def get_capture_config_archive(cluster_name: str) -> LocalFile:
    cluster_config_parent_dir_path = get_cluster_config_parent_dir()
    capture_config_dir_path = get_capture_dir_path(cluster_name, cluster_config_parent_dir_path)
    capture_config_archive_path = get_capture_archive_path(cluster_name, cluster_config_parent_dir_path)

    logger.info(f"Turning Capture configuration at {capture_config_dir_path} into archive at {capture_config_archive_path}")
    capture_config_archive = ZipDirectory(capture_config_dir_path, capture_config_archive_path)
    capture_config_archive.generate()

    return capture_config_archive

def get_viewer_config_archive(cluster_name: str) -> LocalFile:
    cluster_config_parent_dir_path = get_cluster_config_parent_dir()
    viewer_config_dir_path = get_viewer_dir_path(cluster_name, cluster_config_parent_dir_path)
    viewer_config_archive_path = get_viewer_archive_path(cluster_name, cluster_config_parent_dir_path)

    logger.info(f"Turning Viewer configuration at {viewer_config_dir_path} into archive at {viewer_config_archive_path}")
    viewer_config_archive = ZipDirectory(viewer_config_dir_path, viewer_config_archive_path)
    viewer_config_archive.generate()

    return viewer_config_archive






