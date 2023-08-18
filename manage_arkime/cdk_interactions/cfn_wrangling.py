import logging
import os
import re
import shutil

from aws_interactions.aws_environment import AwsEnvironment
from core.constants import is_valid_cluster_name, InvalidClusterName, get_repo_root_dir


logger = logging.getLogger(__name__)

class CdkOutNotPresent(Exception):
    def __init__(self, cdk_out_dir: str):
        super().__init__(f"The CDK Output directory is not present at the expected location: {cdk_out_dir}")

def get_cfn_dir_name(cluster_name: str, aws_env: AwsEnvironment) -> str:
    # We should validate earlier, but practice defense in depth
    if not is_valid_cluster_name(cluster_name):
        raise InvalidClusterName(cluster_name)
    
    # We want to avoid collisions between Clusters across accounts/regions
    return f"cfn-{cluster_name}-{aws_env.aws_account}-{aws_env.aws_region}"

def get_cfn_dir_path(cluster_name: str, aws_env: AwsEnvironment, parent_dir: str) -> str:
    cluster_dir_name = get_cfn_dir_name(cluster_name, aws_env)
    return os.path.join(parent_dir, cluster_dir_name)

def get_cdk_out_dir_path() -> str:
    # It's possible for the user to move where the cdk.out directory is created if they tweak the CDK configuration, so
    # this might return the wrong value.  However, the ways to address that appear to be heavyweight compared to the
    # (small) risk the user moves the directory.
    cdk_out_dir = os.path.join(get_repo_root_dir(), "cdk.out")

    if not os.path.isdir(cdk_out_dir):
        raise CdkOutNotPresent(cdk_out_dir)

    return cdk_out_dir

def _copy_templates_to_cfn_dir(cluster_name: str, cfn_dir_path: str, cdk_out_dir_path: str):
    template_regex = re.compile(f"^{cluster_name}-.*template\\.json$")

    # Copy over the files that match the Cluster's expected CloudFormation template name scheme
    for item in os.listdir(cdk_out_dir_path):
        source_file_path = os.path.join(cdk_out_dir_path, item)
        if template_regex.match(item) and os.path.isfile(source_file_path):
            destination_file_path = os.path.join(cfn_dir_path, item)
            shutil.copyfile(source_file_path, destination_file_path)

def set_up_cloudformation_template_dir(cluster_name: str, aws_env: AwsEnvironment, parent_dir: str):
    logger.info(f"Setting up the CloudFormation template directory for cluster: {cluster_name}")

    logger.info(f"Removing any existing CloudFormation templates...")
    cfn_dir_path = get_cfn_dir_path(cluster_name, aws_env, parent_dir)
    if os.path.exists(cfn_dir_path):
        shutil.rmtree(cfn_dir_path)
    
    logger.info(f"Copying over CloudFormation templates for current command...")
    os.makedirs(cfn_dir_path)
    cdk_out_dir_path = get_cdk_out_dir_path()
    _copy_templates_to_cfn_dir(cluster_name, cfn_dir_path, cdk_out_dir_path)

    logger.info(f"CloudFormation template dir exists at: \n{cfn_dir_path}")