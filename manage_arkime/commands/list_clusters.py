import json
import logging
from typing import Dict, List

from manage_arkime.aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.ssm_operations as ssm_ops
import manage_arkime.constants as constants

logger = logging.getLogger(__name__)

def cmd_list_clusters(profile: str, region: str) -> List[Dict[str, str]]:
    logger.debug(f"Invoking list-clusters with profile '{profile}' and region '{region}'")

    logger.info("Retrieving cluster details...")
    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)
    cluster_names = ssm_ops.get_ssm_names_by_path(constants.SSM_CLUSTERS_PREFIX, aws_provider)
    cluster_details = []
    for cluster_name in cluster_names:
        ssm_vpcs_path_prefix = f"{constants.get_cluster_ssm_param_name(cluster_name)}/vpcs"
        vpc_ids = ssm_ops.get_ssm_names_by_path(ssm_vpcs_path_prefix, aws_provider)
        cluster_details.append({
            "cluster_name": cluster_name,
            "monitored_vpcs": vpc_ids
        })

    formatted_details = json.dumps(cluster_details, indent=4)
    logger.info(f"Deployed Clusters: \n{formatted_details}")
    return cluster_details

    