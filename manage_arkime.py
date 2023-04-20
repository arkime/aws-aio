#!/usr/bin/env python3
import logging

import click

from manage_arkime.commands.add_vpc import cmd_add_vpc
from manage_arkime.commands.create_cluster import cmd_create_cluster
from manage_arkime.commands.destroy_cluster import cmd_destroy_cluster
from manage_arkime.commands.deploy_demo_traffic import cmd_deploy_demo_traffic
from manage_arkime.commands.destroy_demo_traffic import cmd_destroy_demo_traffic
from manage_arkime.commands.get_login_details import cmd_get_login_details
from manage_arkime.commands.list_clusters import cmd_list_clusters
from manage_arkime.commands.remove_vpc import cmd_remove_vpc
import manage_arkime.constants as constants
from manage_arkime.logging_wrangler import LoggingWrangler

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
def deploy_demo_traffic(ctx):
    profile = ctx.obj.get("profile")
    region = ctx.obj.get("region")
    cmd_deploy_demo_traffic(profile, region)
cli.add_command(deploy_demo_traffic)

@click.command(help="Uses CDK to destroy previously-deployed sample traffic sources in your account")
@click.pass_context
def destroy_demo_traffic(ctx):
    profile = ctx.obj.get("profile")
    region = ctx.obj.get("region")
    cmd_destroy_demo_traffic(profile, region)
cli.add_command(destroy_demo_traffic)

@click.command(help="Creates an Arkime Cluster in your account")
@click.option("--name", help="The name you want your Arkime Cluster and its associated resources to have", required=True)
@click.pass_context
def create_cluster(ctx, name):
    profile = ctx.obj.get("profile")
    region = ctx.obj.get("region")
    cmd_create_cluster(profile, region, name)
cli.add_command(create_cluster)

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
def destroy_cluster(ctx, name, destroy_everything):
    profile = ctx.obj.get("profile")
    region = ctx.obj.get("region")
    cmd_destroy_cluster(profile, region, name, destroy_everything)
cli.add_command(destroy_cluster)

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
def list_clusters(ctx):
    profile = ctx.obj.get("profile")
    region = ctx.obj.get("region")
    cmd_list_clusters(profile, region)
cli.add_command(list_clusters)

@click.command(help="Sets up the specified VPC to have its traffic monitored by the specified, existing Arkime Cluster")
@click.option("--cluster-name", help="The name of the Arkime Cluster to monitor with", required=True)
@click.option("--vpc-id", help="The VPC ID to begin monitoring.  Must be in the same account/region as the Cluster.", required=True)
@click.option("--vni", help="The Virtual Network Interface ID (24-bit int) to assign to the VPC.  Can be used to uniquely identify the VPC on the capture side.",
        default=constants.VNI_DEFAULT, type=int)
@click.pass_context
def add_vpc(ctx, cluster_name, vpc_id, vni):
    profile = ctx.obj.get("profile")
    region = ctx.obj.get("region")
    cmd_add_vpc(profile, region, cluster_name, vpc_id, vni)
cli.add_command(add_vpc)

@click.command(help="Removes traffic monitoring from the specified VPC being performed by the specified Arkime Cluster")
@click.option("--cluster-name", help="The name of the Arkime Cluster performing monitoring", required=True)
@click.option("--vpc-id", help="The VPC ID to remove monitoring from", required=True)
@click.pass_context
def remove_vpc(ctx, cluster_name, vpc_id):
    profile = ctx.obj.get("profile")
    region = ctx.obj.get("region")
    cmd_remove_vpc(profile, region, cluster_name, vpc_id)
cli.add_command(remove_vpc)


def main():
    logging_wrangler = LoggingWrangler()
    logger.info(f"Debug-level logs save to file: {logging_wrangler.log_file}")
    cli()


if __name__ == "__main__":
    main()