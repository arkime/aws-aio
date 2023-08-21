#!/usr/bin/env python3
import logging

import click

from commands.vpc_add import cmd_vpc_add
from commands.config_update import cmd_config_update
from commands.cluster_create import cmd_cluster_create
from commands.cluster_destroy import cmd_cluster_destroy
from commands.cluster_register_vpc import cmd_cluster_register_vpc
from commands.demo_traffic_deploy import cmd_demo_traffic_deploy
from commands.demo_traffic_destroy import cmd_demo_traffic_destroy
from commands.get_login_details import cmd_get_login_details
from commands.clusters_list import cmd_clusters_list
from commands.vpc_deregister_cluster import cmd_vpc_deregister_cluster
from commands.vpc_register_cluster import cmd_vpc_register_cluster
from commands.vpc_remove import cmd_vpc_remove
import core.constants as constants
from core.capacity_planning import MAX_TRAFFIC, DEFAULT_SPI_DAYS, DEFAULT_REPLICAS, DEFAULT_S3_STORAGE_DAYS, DEFAULT_HISTORY_DAYS
from core.logging_wrangler import LoggingWrangler, set_boto_log_level

logger = logging.getLogger(__name__)

@click.group(
    help=("Command-line tool to create/manage Arkime clusters in an AWS Account."
          + "  Uses the credentials in your AWS profile to determine which account it will act against.")
)
@click.option(
    "--profile", 
    help="The AWS credential profile to perform the operation with.  Uses 'default' if not supplied.",
    default="default"
)
@click.option("--region", help="The AWS Region to perform the operation in.  Uses your AWS Config default if not supplied.")
@click.pass_context
def cli(ctx, profile, region):
    ctx.ensure_object(dict)
    ctx.obj["profile"] = profile
    ctx.obj["region"] = region

    logger.info(f"Using AWS Credential Profile: {profile}")
    region_str = region if region else "default from AWS Config settings"
    logger.info(f"Using AWS Region: {region_str}")

@click.command(help="Uses CDK to deploy a sample traffic source to your account")
@click.pass_context
def demo_traffic_deploy(ctx):
    profile = ctx.obj.get("profile")
    region = ctx.obj.get("region")
    cmd_demo_traffic_deploy(profile, region)
cli.add_command(demo_traffic_deploy)

@click.command(help="Uses CDK to destroy previously-deployed sample traffic sources in your account")
@click.pass_context
def demo_traffic_destroy(ctx):
    profile = ctx.obj.get("profile")
    region = ctx.obj.get("region")
    cmd_demo_traffic_destroy(profile, region)
cli.add_command(demo_traffic_destroy)

@click.command(help="Creates an Arkime Cluster in your account")
@click.option("--name", help="The name you want your Arkime Cluster and its associated resources to have", required=True)
@click.option(
    "--expected-traffic", 
    help=("The average amount of traffic, in gigabits-per-second, you expect your Arkime Cluster to receive."
        + f"Maximum: {MAX_TRAFFIC} Gbps"),
    default=None,
    type=click.FLOAT,
    required=False)
@click.option(
    "--spi-days", 
    help=(f"The number of days to store SPI metadata in the OpenSearch Domain.  Default: {DEFAULT_SPI_DAYS}"),
    default=None,
    type=click.INT,
    required=False)
@click.option(
    "--history-days", 
    help=(f"The number of days to store Arkime Viewer user history in the OpenSearch Domain.  Default: {DEFAULT_HISTORY_DAYS}"),
    default=None,
    type=click.INT,
    required=False)
@click.option(
    "--replicas", 
    help=(f"The number replicas to make of the SPI metadata in the OpenSearch Domain.  Default: {DEFAULT_REPLICAS}"),
    default=None,
    type=click.INT,
    required=False)
@click.option(
    "--pcap-days", 
    help=(f"The number of days to store PCAP files in S3.  Default: {DEFAULT_S3_STORAGE_DAYS}"),
    default=None,
    type=click.INT,
    required=False)
@click.option(
    "--preconfirm-usage", 
    help="Skips the manual confirmation that the capacity to be provisioned is as expected.",
    is_flag=True,
    show_default=True,
    default=False
)
@click.option(
    "--just-print-cfn", 
    help="Skips a full deployment and just creates a copy of the CloudFormation templates to be deployed in a local directory",
    is_flag=True,
    show_default=True,
    default=False
)
@click.pass_context
def cluster_create(ctx, name, expected_traffic, spi_days, history_days, replicas, pcap_days, preconfirm_usage, just_print_cfn):
    profile = ctx.obj.get("profile")
    region = ctx.obj.get("region")
    cmd_cluster_create(profile, region, name, expected_traffic, spi_days, history_days, replicas, pcap_days, preconfirm_usage, just_print_cfn)
cli.add_command(cluster_create)

@click.command(help="Tears down the Arkime Cluster in your account; by default, leaves your data intact")
@click.option("--name", help="The name of the Arkime Cluster to tear down", required=True)
@click.option(
    "--destroy-everything", 
    help="Tears down all resources and ALL DATA associated with the cluster instead of preserving that data",
    is_flag=True,
    show_default=True,
    default=False
)
@click.pass_context
def cluster_destroy(ctx, name, destroy_everything):
    profile = ctx.obj.get("profile")
    region = ctx.obj.get("region")
    cmd_cluster_destroy(profile, region, name, destroy_everything)
cli.add_command(cluster_destroy)

@click.command(help="Retrieves the login details of a cluster's the Arkime Viewer(s)")
@click.option("--name", help="The name of the Arkime Cluster to get the login details for", required=True)
@click.pass_context
def get_login_details(ctx, name):
    profile = ctx.obj.get("profile")
    region = ctx.obj.get("region")
    cmd_get_login_details(profile, region, name)
cli.add_command(get_login_details)

@click.command(help="Lists the currently deployed Arkime Clusters and their VPCs")
@click.pass_context
def clusters_list(ctx):
    profile = ctx.obj.get("profile")
    region = ctx.obj.get("region")
    cmd_clusters_list(profile, region)
cli.add_command(clusters_list)

@click.command(help=("Sets up the specified VPC to have its traffic monitored by the specified, existing Arkime Cluster."
                    + "  By default, each VPC is assigned a Virtual Network Interface ID (VNI) unused by any other VPC"
                    + f" in the Cluster to uniquely identify it.  The starting default value is {constants.VNI_MIN}."))
@click.option("--cluster-name", help="The name of the Arkime Cluster to monitor with", required=True)
@click.option("--vpc-id", help="The VPC ID to begin monitoring.  Must be in the same region as the Cluster."
              " If in a different AWS Account than the Cluster, must be registered (see README).", required=True)
@click.option("--force-vni", help=("POWER USER OPTION.  Forcefully assign the VPC to use a specific VNI.  This can"
              + " result in multiple VPCs using the same VNI, and VNIs to potentially be re-used long after they are"
              + " relinquished."), default=None, type=int)
@click.option(
    "--just-print-cfn", 
    help="Skips a full deployment and just creates a copy of the CloudFormation templates to be deployed in a local directory",
    is_flag=True,
    show_default=True,
    default=False
)
@click.pass_context
def vpc_add(ctx, cluster_name, vpc_id, force_vni, just_print_cfn):
    profile = ctx.obj.get("profile")
    region = ctx.obj.get("region")
    cmd_vpc_add(profile, region, cluster_name, vpc_id, force_vni, just_print_cfn)
cli.add_command(vpc_add)

@click.command(help="Removes traffic monitoring from the specified VPC being performed by the specified Arkime Cluster")
@click.option("--cluster-name", help="The name of the Arkime Cluster performing monitoring", required=True)
@click.option("--vpc-id", help="The VPC ID to remove monitoring from", required=True)
@click.pass_context
def vpc_remove(ctx, cluster_name, vpc_id):
    profile = ctx.obj.get("profile")
    region = ctx.obj.get("region")
    cmd_vpc_remove(profile, region, cluster_name, vpc_id)
cli.add_command(vpc_remove)

@click.command(help="Updates specified Arkime Cluster's Capture/Viewer configuration")
@click.option("--cluster-name", help="The name of the Arkime Cluster to update", required=True)
@click.option("--force-bounce-capture",
    help="Forces a bounce of the Capture Nodes, regardless of whether there is new config.",
    is_flag=True,
    show_default=True,
    default=False
)
@click.option("--force-bounce-viewer",
    help="Forces a bounce of the Viewer Nodes, regardless of whether there is new config.",
    is_flag=True,
    show_default=True,
    default=False
)
@click.pass_context
def config_update(ctx, cluster_name, force_bounce_capture, force_bounce_viewer):
    profile = ctx.obj.get("profile")
    region = ctx.obj.get("region")
    cmd_config_update(profile, region, cluster_name, force_bounce_capture, force_bounce_viewer)
cli.add_command(config_update)

@click.command(help="Registers a VPC in another AWS Account so it can be captured by the Cluster.  Not needed for VPCs"
               " in the same AWS Account as the Cluster.  Call w/ creds for the Cluster's AWS Account.")
@click.option("--cluster-name", help="The name of the Arkime Cluster to monitor with", required=True)
@click.option("--vpc-account-id", help="The AWS Account ID of the VPC you want to monitor", required=True)
@click.option("--vpc-id", help="The VPC ID you want to monitor.  This VPC should be in a different account than the"
              " Cluster is in.", required=True)
@click.pass_context
def cluster_register_vpc(ctx, cluster_name, vpc_account_id, vpc_id):
    profile = ctx.obj.get("profile")
    region = ctx.obj.get("region")
    cmd_cluster_register_vpc(profile, region, cluster_name, vpc_account_id, vpc_id)
cli.add_command(cluster_register_vpc)

@click.command(help="Registers an Arkime Cluster with a VPC in another AWS Account so its traffic can be captured."
               "  Not needed for VPCs in the same AWS Account as the Cluster.  Call w/ creds for the VPC's AWS Account.")
@click.option("--cluster-account-id", help="The AWS Account ID of the Cluster what will do monitoring", required=True)
@click.option("--cluster-name", help="The name of the Arkime Cluster to monitor with", required=True)
@click.option("--cross-account-role", help="The IAM Role ARN used to perform cross-account actions", required=True)
@click.option("--vpc-account-id", help="The AWS Account ID of the VPC you want to monitor", required=True)
@click.option("--vpc-id", help="The VPC ID you want to monitor.  This VPC should be in a different account than the"
              " Cluster is in.", required=True)
@click.option("--vpce-service-id", help="The VPC Endpoint Service ID of the Arkime Cluster", required=True)
@click.pass_context
def vpc_register_cluster(ctx, cluster_account_id, cluster_name, cross_account_role, vpc_account_id, vpc_id, vpce_service_id):
    profile = ctx.obj.get("profile")
    region = ctx.obj.get("region")
    cmd_vpc_register_cluster(profile, region, cluster_account_id, cluster_name, cross_account_role, vpc_account_id, vpc_id, vpce_service_id)
cli.add_command(vpc_register_cluster)


@click.command(help="Removes registration of the Arkime Cluster with a VPC in another AWS Account."
               "  Not needed for VPCs in the same AWS Account as the Cluster.  Call w/ creds for the VPC's AWS Account.")
@click.option("--cluster-name", help="The name of the Arkime Cluster to monitor with", required=True)
@click.option("--vpc-id", help="The VPC ID you want to monitor.  This VPC should be in a different account than the"
              " Cluster is in.", required=True)
@click.pass_context
def vpc_deregister_cluster(ctx, cluster_name, vpc_id):
    profile = ctx.obj.get("profile")
    region = ctx.obj.get("region")
    cmd_vpc_deregister_cluster(profile, region, cluster_name, vpc_id)
cli.add_command(vpc_deregister_cluster)

def main():
    logging_wrangler = LoggingWrangler()
    logger.info(f"Debug-level logs save to file: {logging_wrangler.log_file}")
    cli()

if __name__ == "__main__":
    with set_boto_log_level("WARNING"): # Prevent overwhelming boto spam in our debug log
        main()