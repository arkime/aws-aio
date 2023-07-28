import json
import logging
from typing import Dict, List

import arkime_interactions.config_wrangling as config_wrangling
from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.ssm_operations as ssm_ops
import core.constants as constants

logger = logging.getLogger(__name__)

def cmd_clusters_list(profile: str, region: str) -> List[Dict[str, str]]:
    logger.debug(f"Invoking clusters-list with profile '{profile}' and region '{region}'")

    logger.info("Retrieving cluster details...")
    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)
    cluster_names = ssm_ops.get_ssm_names_by_path(constants.SSM_CLUSTERS_PREFIX, aws_provider)
    cluster_details = []
    for cluster_name in cluster_names:
        cluster_ssm_param_name = constants.get_cluster_ssm_param_name(cluster_name)

        # Get the details for the monitored VPCs
        ssm_vpcs_path_prefix = f"{cluster_ssm_param_name}/vpcs"
        vpc_ids = ssm_ops.get_ssm_names_by_path(ssm_vpcs_path_prefix, aws_provider)
        vpc_details = []
        for vpc_id in vpc_ids:
            vpc_ssm_param = constants.get_vpc_ssm_param_name(cluster_name, vpc_id)
            vni = ssm_ops.get_ssm_param_json_value(vpc_ssm_param, "mirrorVni", aws_provider)
            vpc_details.append({
                "vpc_id": vpc_id,
                "vni": vni,
            })

        # Get the OpenSearch Domain details
        opensearch_domain = ssm_ops.get_ssm_param_json_value(cluster_ssm_param_name, "osDomainName", aws_provider)

        # Get the Arkime Config details
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

        cluster_details.append({
            "cluster_name": cluster_name,
            "opensearch_domain": opensearch_domain,
            "configuration_capture": capture_config_details.version.to_dict(),
            "configuration_viewer": viewer_config_details.version.to_dict(),
            "monitored_vpcs": vpc_details
        })

    formatted_details = json.dumps(cluster_details, indent=4)
    logger.info(f"Deployed Clusters: \n{formatted_details}")
    return cluster_details

    