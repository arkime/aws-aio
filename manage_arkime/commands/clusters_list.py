import json
import logging
import re
from typing import Dict, List

import arkime_interactions.config_wrangling as config_wrangling
from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.ssm_operations as ssm_ops
import core.constants as constants
from core.cross_account_wrangling import CrossAccountAssociation

logger = logging.getLogger(__name__)

def cmd_clusters_list(profile: str, region: str) -> List[Dict[str, str]]:
    logger.debug(f"Invoking clusters-list with profile '{profile}' and region '{region}'")

    logger.info("Retrieving cluster details...")
    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)
    this_account_env = aws_provider.get_aws_env()
    cluster_names = ssm_ops.get_ssm_names_by_path(constants.SSM_CLUSTERS_PREFIX, aws_provider)
    cluster_details = []
    for cluster_name in cluster_names:
        cluster_ssm_param_name = constants.get_cluster_ssm_param_name(cluster_name)
        vpc_details = []

        ssm_vpcs_path_prefix = f"{cluster_ssm_param_name}/vpcs"
        ssm_paths = ssm_ops.get_ssm_params_by_path(ssm_vpcs_path_prefix, aws_provider, recursive=True)

        # Get the details for same-account monitored VPCs
        same_account_regex = re.compile(f"^{ssm_vpcs_path_prefix}/vpc\\-[a-zA-Z0-9]+$")
        same_account_params = [path for path in ssm_paths if same_account_regex.match(path["Name"])]
        for same_account_param in same_account_params:
            vni = json.loads(same_account_param["Value"])["mirrorVni"]
            vpc_id = json.loads(same_account_param["Value"])["vpcId"]

            vpc_details.append({
                "vpc_account": this_account_env.aws_account,
                "vpc_id": vpc_id,
                "vni": vni,
            })

        # Get the details for cross-account monitored VPCs
        cross_account_regex = re.compile(f"^{ssm_vpcs_path_prefix}/vpc\\-[a-zA-Z0-9]+/cross-account$")
        cross_account_params = [path for path in ssm_paths if cross_account_regex.match(path["Name"])]
        for cross_account_param in cross_account_params:
            # Create an AWS Client using a cross-account role to read VPC details in the VPC Account
            association = CrossAccountAssociation(**json.loads(cross_account_param["Value"]))
            cross_account_role_arn = f"arn:aws:iam::{association.vpcAccount}:role/{association.roleName}"
            cross_account_provider = AwsClientProvider(aws_profile=profile, aws_region=region, assume_role_arn=cross_account_role_arn)

            # Get the VPC details from the Param entry using a cross-account call
            vpc_param_name = constants.get_vpc_ssm_param_name(association.clusterName, association.vpcId)
            vni = ssm_ops.get_ssm_param_json_value(vpc_param_name, "mirrorVni", cross_account_provider)
            vpc_id = ssm_ops.get_ssm_param_json_value(vpc_param_name, "vpcId", cross_account_provider)
            
            vpc_details.append({
                "vpc_account": association.vpcAccount,
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

    