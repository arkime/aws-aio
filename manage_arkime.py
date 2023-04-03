#!/usr/bin/env python3
import logging

import click

from manage_arkime.commands.create_cluster import cmd_create_cluster
from manage_arkime.commands.deploy_demo_traffic import cmd_deploy_demo_traffic
from manage_arkime.commands.destroy_demo_traffic import cmd_destroy_demo_traffic
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


def main():
    logging_wrangler = LoggingWrangler()
    logger.info(f"Debug-level logs save to file: {logging_wrangler.log_file}")
    cli()


if __name__ == "__main__":
    main()