import json
import logging

from manage_arkime.aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.ec2_interactions as ec2i
import aws_interactions.ssm_operations as ssm_ops
from manage_arkime.cdk_client import CdkClient
import manage_arkime.constants as constants
import manage_arkime.cdk_context as context

logger = logging.getLogger(__name__)

def cmd_add_vpc(profile: str, region: str, cluster_name: str, vpc_id: str, vni: int):
    logger.debug(f"Invoking add-vpc with profile '{profile}' and region '{region}'")

    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)

    # Confirm the VNI is valid
    if (vni <= constants.VNI_MIN) or (constants.VNI_MAX < vni):
        logger.error(f"VNI {vni} is outside the acceptable range of {constants.VNI_MIN} to {constants.VNI_MAX} (inclusive)")
        logger.warning("Aborting...")
        return

    # Confirm the Cluster exists before proceeding
    try:
        ssm_ops.get_ssm_param_value(constants.get_cluster_ssm_param_name(cluster_name), aws_provider)
    except ssm_ops.ParamDoesNotExist:
        logger.error(f"The cluster {cluster_name} does not exist; try using the list-clusters command to see the clusters you have created.")
        logger.warning("Aborting...")
        return

    # Get all the subnets in the VPC
    try:
        subnet_ids = ec2i.get_subnets_of_vpc(vpc_id, aws_provider)
    except ec2i.VpcDoesNotExist as ex:
        logger.error(f"The VPC {vpc_id} does not exist in the account/region")
        logger.warning("Aborting...")
        return

    # Get the VPCE Service ID we set up with our Capture VPC
    vpce_service_id = ssm_ops.get_ssm_param_json_value(constants.get_cluster_ssm_param_name(cluster_name), "vpceServiceId", aws_provider)

    # Deploy the resources we need in the user's VPC and Subnets
    logger.info("Deploying shared mirroring components via CDK...")
    stacks_to_deploy = [
        constants.get_vpc_mirror_setup_stack_name(cluster_name, vpc_id)
    ]
    add_vpc_context = context.generate_add_vpc_context(cluster_name, vpc_id, subnet_ids, vpce_service_id, vni)

    cdk_client = CdkClient()
    cdk_client.deploy(stacks_to_deploy, aws_profile=profile, aws_region=region, context=add_vpc_context)

    # Create the per-ENI Traffic Mirroring Sessions.
    #
    # Why create these using Boto instead of the CDK?  We expect the ENIs to change frequently and want a more nimble
    # way to update our configuration for them than using CloudFormation.  Additionally, CloudFormation has limits that
    # would be annoying to deal with (limits on the resources/stack most especially).  These limits mean we'd need to
    # split our Traffic Sessions across multiple stacks while maintaining consistent and safe ordering to prevent a Cfn
    # Stack Update from deleting Sessions in one stack only to move them to another Stack, and dealing with race
    # conditions on CloudFormation trying to have the same Session exist in two stacks momentarily.  Not a good
    # experience.
    vpc_param_name = constants.get_vpc_ssm_param_name(cluster_name, vpc_id)
    traffic_filter_id = ssm_ops.get_ssm_param_json_value(vpc_param_name, "mirrorFilterId", aws_provider)
    
    for subnet_id in subnet_ids:
        _mirror_enis_in_subnet(cluster_name, vpc_id, subnet_id, traffic_filter_id, vni, aws_provider)

def _mirror_enis_in_subnet(cluster_name: str, vpc_id: str, subnet_id: str, traffic_filter_id: str, vni: int, aws_provider: AwsClientProvider):
    enis = ec2i.get_enis_of_subnet(subnet_id, aws_provider)

    for eni in enis:
        eni_param_name = constants.get_eni_ssm_param_name(cluster_name, vpc_id, subnet_id, eni.id)

        try:
            ssm_ops.get_ssm_param_value(eni_param_name, aws_provider)
            logger.info(f"Mirroring already configured for ENI {eni.id}")
            continue
        except ssm_ops.ParamDoesNotExist:
            pass

        logger.info(f"Creating mirroring session for ENI {eni.id}")

        subnet_param_name = constants.get_subnet_ssm_param_name(cluster_name, vpc_id, subnet_id)
        traffic_target_id = ssm_ops.get_ssm_param_json_value(subnet_param_name, "mirrorTargetId", aws_provider)

        try:
            traffic_session_id = ec2i.mirror_eni(
                eni,
                traffic_target_id,
                traffic_filter_id,
                vpc_id,
                aws_provider,
                virtual_network=vni
            )
        except ec2i.NonMirrorableEniType as ex:
            logger.info(f"Eni {eni.id} is of unsupported type {eni.type}; skipping")
            continue

        ssm_ops.put_ssm_param(
            eni_param_name, 
            json.dumps({"eniId": eni.id, "trafficSessionId": traffic_session_id}),
            aws_provider,
            description=f"Mirroring details for {eni.id}",
            pattern=".*"
        )