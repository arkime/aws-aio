import logging
import os
import shutil

from constants import is_valid_cluster_name, InvalidClusterName


logger = logging.getLogger(__name__)

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
        os.path.join(cluster_dir_path, "capture")
    )
    shutil.copytree(
        _get_default_viewer_config_dir_path(),
        os.path.join(cluster_dir_path, "viewer")
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






