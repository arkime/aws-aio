import json
import logging

from botocore.exceptions import ClientError

from manage_arkime.aws_interactions.aws_client_provider import AwsClientProvider
from manage_arkime.aws_interactions.destroy_os_domain import destroy_os_domain_and_wait
from manage_arkime.aws_interactions.destroy_s3_bucket import destroy_s3_bucket
import aws_interactions.ssm_operations as ssm_ops
from manage_arkime.cdk_client import CdkClient
import manage_arkime.constants as constants
import manage_arkime.cdk_context as context

logger = logging.getLogger(__name__)

def cmd_remove_vpc(profile: str, region: str, cluster_name: str, vpc_id: str):
    logger.debug(f"Invoking remove-vpc with profile '{profile}' and region '{region}'")

    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)

    # Confirm the Cluster exists before proceeding
    try:
        cluster_config = ssm_ops.get_ssm_param_value(constants.get_cluster_ssm_param_name(cluster_name), aws_provider)
    except ssm_ops.ParamDoesNotExist:
        logger.warning(f"The cluster {cluster_name} does not exist; try using the list-clusters command to see the clusters you have created.")
        logger.warning("Aborting operation...")
        return
    vpce_service_id = json.loads(cluster_config)["vpceServiceID"]

    ec2_client = aws_provider.get_ec2()
    ssm_client = aws_provider.get_ssm()

    # Pull all our deployed configuration from SSM and tear down the ENI-specific resources
    subnet_search_path = f"{constants.get_vpc_ssm_param_name(cluster_name, vpc_id)}/subnets"
    subnet_configs = [json.loads(config["Value"]) for config in ssm_ops.get_ssm_params_by_path(subnet_search_path, aws_provider)]
    subnet_ids = [config['subnetId'] for config in subnet_configs]
    for subnet_id in subnet_ids:
        eni_search_path = f"{constants.get_subnet_ssm_param_name(cluster_name, vpc_id, subnet_id)}/enis"
        eni_params = ssm_ops.get_ssm_params_by_path(eni_search_path, aws_provider)
        eni_paths = [param["Name"] for param in eni_params]
        eni_configs = [json.loads(config["Value"]) for config in eni_params]
        eni_configs_and_paths = list(zip(eni_configs, eni_paths))

        for eni_config, eni_path in eni_configs_and_paths:
            logger.info(f"Deleting traffic mirroring session {eni_config['trafficSessionId']}...")
            try:
                ec2_client.delete_traffic_mirror_session(
                    TrafficMirrorSessionId=eni_config["trafficSessionId"]
                )
            except ClientError as exc:
                if exc.response['Error']['Code'] == 'InvalidTrafficMirrorSessionId.NotFound':
                    logger.info(f"Traffic mirroring session {eni_config['trafficSessionId']} not found; something else must have deleted it")
                else:
                    raise

            logger.info(f"Deleting SSM parameter for ENI {eni_config['eniId']}...")
            ssm_client.delete_parameter(
                Name=eni_path
            )

    # Destroy the VPC-specific mirroring components in CloudFormation
    logger.info("Tearing down shared mirroring components via CDK...")
    stacks_to_destroy = [
        constants.get_vpc_mirror_setup_stack_name(cluster_name, vpc_id)
    ]
    add_vpc_context = context.generate_remove_vpc_context(cluster_name, vpc_id, subnet_ids, vpce_service_id)

    cdk_client = CdkClient()
    cdk_client.destroy(stacks_to_destroy, aws_profile=profile, aws_region=region, context=add_vpc_context)
