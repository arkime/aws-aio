import logging
from typing import List

import manage_arkime.shell_interactions as shell
from manage_arkime.cdk_environment import get_cdk_env
import manage_arkime.cdk_exceptions as exceptions
import manage_arkime.constants as constants

logger = logging.getLogger(__name__)

def get_command_prefix(aws_profile: str = None, aws_region: str = None) -> str:
    prefix_sections = ["cdk"]

    if aws_profile:
        prefix_sections.append(f"--profile {aws_profile}")

    if aws_region:
        prefix_sections.append(f"--context {constants.CDK_CONTEXT_REGION_VAR}={aws_region}")

    return " ".join(prefix_sections)


class CdkClient:
    """
    This class provides a Python wrapper around the CDK CLI, surfacing CDK actions into the realm of the Management CLI.
    """

    def __init__(self, profile: str = None, region: str = None):
        self.profile = profile
        self.region = region
    
    def bootstrap(self, aws_profile: str = None, aws_region: str = None) -> None:
        command_prefix = get_command_prefix(aws_profile=aws_profile, aws_region=aws_region)
        cdk_env = get_cdk_env(aws_profile=aws_profile, aws_region=aws_region)
        command_suffix = f"bootstrap {str(cdk_env)}"
        command = f"{command_prefix} {command_suffix}"
        
        logger.info(f"Executing command: {command_suffix}")
        logger.warning(f"NOTE: This operation can take a while.  You can 'tail -f' the logfile to track the status.")
        exit_code, stdout = shell.call_shell_command(command=command)
        exceptions.raise_common_exceptions(exit_code, stdout)

        if exit_code != 0:
            raise exceptions.CdkBootstrapFailedUnknown()

    def deploy(self, stack_names: List[str], aws_profile: str = None, aws_region: str = None) -> None:
        command_prefix = get_command_prefix(aws_profile=aws_profile, aws_region=aws_region)
        command_suffix = f"deploy {' '.join(stack_names)}"
        command = f"{command_prefix} {command_suffix}"

        # There are a number of circumstances where the CDK CLI asks the user to confirm before beginning a deployment.
        # Common examples include making IAM and VPC security group changes.  There's no CDK CLI option to "auto-yes".
        # As a quick solution, we perform that confirmation using pexpect but this can be quite dangerous and we should
        # find a better answer, ideally surfacing this to the user somehow.
        cdk_confirmation_dialogue = ("Do you wish to deploy these changes (y/n)?", "yes")

        logger.info(f"Executing command: {command_suffix}")
        logger.warning(f"NOTE: This operation can take a while.  You can 'tail -f' the logfile to track the status.")
        exit_code, stdout = shell.call_shell_command(command=command, request_response_pairs=[cdk_confirmation_dialogue])

        try:
            exceptions.raise_common_exceptions(exit_code, stdout)
        except exceptions.CommonCdkNotBootstrapped as exception:
            # If the CDK setup isn't bootstrapped, attempt to bootstrap and redeploy
            self.bootstrap(aws_profile=aws_profile, aws_region=aws_region)
            logger.info(f"Executing command: {command_suffix}")
            exit_code, stdout = shell.call_shell_command(command=command, request_response_pairs=[cdk_confirmation_dialogue])
            exceptions.raise_common_exceptions(exit_code, stdout)

        if exit_code != 0:
            raise exceptions.CdkDeployFailedUnknown()

    def deploy_single_stack(self, stack_name, aws_profile: str = None, aws_region: str = None):
        self.deploy([stack_name], aws_profile=aws_profile, aws_region=aws_region)

    def deploy_all_stacks(self, aws_profile: str = None, aws_region: str = None):
        self.deploy(["--all"], aws_profile=aws_profile, aws_region=aws_region)
        