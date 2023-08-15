import logging
import shutil

from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.ec2_interactions as ec2i
import aws_interactions.events_interactions as events
import aws_interactions.ssm_operations as ssm_ops
from cdk_interactions.cdk_client import CdkClient
import cdk_interactions.cfn_wrangling as cfn
import core.constants as constants
import cdk_interactions.cdk_context as context
from core.vni_provider import SsmVniProvider, VniAlreadyUsed, VniOutsideRange, VniPoolExhausted

logger = logging.getLogger(__name__)

def cmd_vpc_add(profile: str, region: str, cluster_name: str, vpc_id: str, user_vni: int, just_print_cfn: bool):
    logger.debug(f"Invoking vpc-add with profile '{profile}' and region '{region}'")

    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)
    aws_env = aws_provider.get_aws_env()
    cdk_client = CdkClient(aws_env)
    vni_provider = SsmVniProvider(cluster_name, aws_provider)

    # If the user didn't supply a VNI, try to find one
    if not user_vni:
        try:
            next_vni = vni_provider.get_next_vni()
        except VniPoolExhausted:
            logger.error(f"There are no remaining VNIs in the range {constants.VNI_MIN} to {constants.VNI_MAX} to assign for this cluster")
            logger.warning("Aborting...")
            return

    # Confirm the user-supplied VNI is available
    else:
        next_vni = user_vni

        try:
            if not vni_provider.is_vni_available(next_vni):
                logger.error(f"VNI {next_vni} is already in use and cannot be used again.  Use clusters-list to see the VNIs"
                            + " assigned to your clusters.")
                logger.warning("Aborting...")
                return            
        except VniAlreadyUsed:
            logger.error(f"VNI {next_vni} is already in use; you can use the clusters-list command to see which VPC it is assigned to.")
            logger.warning("Aborting...")
            return
        except VniOutsideRange:
            logger.error(f"VNI {next_vni} is outside the acceptable range of {constants.VNI_MIN} to {constants.VNI_MAX} (inclusive)")
            logger.warning("Aborting...")
            return

    # Confirm the Cluster exists before proceeding
    try:
        ssm_ops.get_ssm_param_value(constants.get_cluster_ssm_param_name(cluster_name), aws_provider)
    except ssm_ops.ParamDoesNotExist:
        logger.error(f"The cluster {cluster_name} does not exist; try using the clusters-list command to see the clusters you have created.")
        logger.warning("Aborting...")
        return

    # Get information about the VPC
    try:
        subnet_ids = ec2i.get_subnets_of_vpc(vpc_id, aws_provider)
        vpc_details = ec2i.get_vpc_details(vpc_id, aws_provider)
    except ec2i.VpcDoesNotExist as ex:
        logger.error(f"The VPC {vpc_id} does not exist in the account/region")
        logger.warning("Aborting...")
        return

    # Get the VPCE Service ID we set up with our Capture VPC
    vpce_service_id = ssm_ops.get_ssm_param_json_value(constants.get_cluster_ssm_param_name(cluster_name), "vpceServiceId", aws_provider)
    event_bus_arn = ssm_ops.get_ssm_param_json_value(constants.get_cluster_ssm_param_name(cluster_name), "busArn", aws_provider)

    # Define the CFN Resources and CDK Context
    stacks_to_deploy = [
        constants.get_vpc_mirror_setup_stack_name(cluster_name, vpc_id)
    ]
    vpc_add_context = context.generate_vpc_add_context(cluster_name, vpc_id, subnet_ids, vpce_service_id, event_bus_arn,
                                                       next_vni, vpc_details.cidr_blocks)

    if just_print_cfn:
        # Remove the CDK output directory to ensure we don't copy over stale templates
        cdk_out_dir_path = cfn.get_cdk_out_dir_path()
        shutil.rmtree(cdk_out_dir_path)

        # Generate the CloudFormation templates (without deploying them)
        cdk_client.synthesize(stacks_to_deploy, context=vpc_add_context)

        # Copy them over
        parent_dir = constants.get_repo_root_dir()
        cfn.set_up_cloudformation_template_dir(cluster_name, aws_env, parent_dir)
    else:
        # Deploy the resources we need in the user's VPC and Subnets
        logger.info("Deploying shared mirroring components via CDK...")
        cdk_client.deploy(stacks_to_deploy, context=vpc_add_context)

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
            _mirror_enis_in_subnet(event_bus_arn, cluster_name, vpc_id, subnet_id, traffic_filter_id, next_vni, aws_provider)

        # Register the VNI as used.  The VNI's usage is tied to the ENI-specific configuration, so we perform this
        # after that is set up.
        if user_vni:
            vni_provider.register_user_vni(next_vni, vpc_id)
        else:
            vni_provider.use_next_vni(next_vni)

def _mirror_enis_in_subnet(event_bus_arn: str, cluster_name: str, vpc_id: str, subnet_id: str, traffic_filter_id: str, vni: int, aws_provider: AwsClientProvider):
    enis = ec2i.get_enis_of_subnet(subnet_id, aws_provider)

    for eni in enis:
        # TODO: Instead of blindly emitting events for each ENI and letting our Lambda Handler figure out if it should
        # actually create the mirroring configuration, we should pre-screen (hasn't already been mirrored; right eni
        # type).

        logger.info(f"Initiating creation of mirroring session for ENI {eni.eni_id}")

        events.put_events(
            [events.CreateEniMirrorEvent(cluster_name, vpc_id, subnet_id, eni.eni_id, eni.eni_type, traffic_filter_id, vni)],
            event_bus_arn,
            aws_provider
        )