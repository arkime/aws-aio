import json
import logging

from manage_arkime.aws_interactions.aws_client_provider import AwsClientProvider
from manage_arkime.aws_interactions.destroy_os_domain import destroy_os_domain_and_wait
from manage_arkime.aws_interactions.destroy_s3_bucket import destroy_s3_bucket
import aws_interactions.ssm_operations as ssm_ops
from manage_arkime.cdk_client import CdkClient
import manage_arkime.constants as constants
import manage_arkime.cdk_context as context

logger = logging.getLogger(__name__)

def cmd_add_vpc(profile: str, region: str, cluster_name: str, vpc_id: str):
    logger.debug(f"Invoking add-vpc with profile '{profile}' and region '{region}'")

    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)

    # Confirm the Cluster exists before proceeding
    try:
        ssm_ops.get_ssm_param_value(constants.get_cluster_ssm_param_name(cluster_name), aws_provider)
    except ssm_ops.ParamDoesNotExist:
        logger.warning(f"The cluster {cluster_name} does not exist; try using the list-clusters command to see the clusters you have created.")
        logger.warning("Aborting operation...")
        return

    # Get all the subnets in the VPC
    # TODO: Handle pagination
    logger.info("Retrieving required information from your AWS account...")
    ec2_client = aws_provider.get_ec2()
    subnets_response = ec2_client.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )
    if not subnets_response["Subnets"]: # will be [] if the subnet does not exist
        logger.warning(f"The VPC {vpc_id} does not exist in the account/region")
        logger.warning("Aborting operation...")
        return
    subnet_ids = [subnet["SubnetId"] for subnet in subnets_response["Subnets"]]

    # Get the VPCE Service ID we set up with our Capture VPC
    cluster_param = ssm_ops.get_ssm_param_value(constants.get_cluster_ssm_param_name(cluster_name), aws_provider)
    vpce_service_id = json.loads(cluster_param)["vpceServiceId"]

    # Deploy the resources we need in the user's VPC and Subnets
    logger.info("Deploying shared mirroring components via CDK...")
    stacks_to_deploy = [
        constants.get_vpc_mirror_setup_stack_name(cluster_name, vpc_id)
    ]
    add_vpc_context = context.generate_add_vpc_context(cluster_name, vpc_id, subnet_ids, vpce_service_id)

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
    traffic_filter_id = json.loads(ssm_ops.get_ssm_param_value(constants.get_vpc_ssm_param_name(cluster_name, vpc_id), aws_provider))["mirrorFilterId"]
    for subnet_id in subnet_ids:
        describe_eni_response = ec2_client.describe_network_interfaces(
            Filters=[{"Name": "subnet-id", "Values": [subnet_id]}]
        )
        eni_ids_and_types = [(eni["NetworkInterfaceId"], eni["InterfaceType"]) for eni in describe_eni_response.get("NetworkInterfaces", [])]

        for eni_id, eni_type in eni_ids_and_types:
            eni_param_name = constants.get_eni_ssm_param_name(cluster_name, vpc_id, subnet_id, eni_id)

            try:
                ssm_ops.get_ssm_param_value(eni_param_name, aws_provider)
                logger.info(f"Mirroring already configured for ENI {eni_id}")
                continue
            except ssm_ops.ParamDoesNotExist:
                pass
            
            if eni_type in ["gateway_load_balancer_endpoint", "nat_gateway"]:
                logger.info(f"Eni {eni_id} is of unsupport type {eni_type}; skipping")
                continue

            logger.info(f"Creating mirroring session for ENI {eni_id}")

            subnet_param_name = constants.get_subnet_ssm_param_name(cluster_name, vpc_id, subnet_id)
            subnet_param_value = json.loads(ssm_ops.get_ssm_param_value(subnet_param_name, aws_provider))
            traffic_target_id = subnet_param_value["mirrorTargetId"]

            create_session_response = ec2_client.create_traffic_mirror_session(
                NetworkInterfaceId=eni_id,
                TrafficMirrorTargetId=traffic_target_id,
                TrafficMirrorFilterId=traffic_filter_id,
                SessionNumber=1,
                VirtualNetworkId=123
            )

            aws_provider.get_ssm().put_parameter(
                Name=eni_param_name,
                Description=f"Mirroring details for {eni_id}",
                Value=json.dumps({
                    "eniId": eni_id,
                    "trafficSessionId": create_session_response["TrafficMirrorSession"]["TrafficMirrorSessionId"]
                }),
                Type="String",
                AllowedPattern=".*",
                Tier='Standard',
            )