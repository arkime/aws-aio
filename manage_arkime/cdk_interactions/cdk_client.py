import logging
import re
from typing import Dict, List

import shell_interactions as shell
from aws_interactions.aws_environment import AwsEnvironment
import cdk_interactions.cdk_exceptions as exceptions
import constants as constants

logger = logging.getLogger(__name__)

def get_command_prefix(aws_profile: str = None, aws_region: str = None, context: Dict[str, str] = None) -> str:
    prefix_sections = ["cdk"]

    if aws_profile:
        prefix_sections.append(f"--profile {aws_profile}")

    if aws_region:
        prefix_sections.append(f"--context {constants.CDK_CONTEXT_REGION_VAR}={aws_region}")

    if context:
        for context_key, context_value in context.items():
            prefix_sections.append(f"--context {context_key}={context_value}")

    return " ".join(prefix_sections)


class CdkClient:
    """
    This class provides a Python wrapper around the CDK CLI, surfacing CDK actions into the realm of the Management CLI.
    """

    def __init__(self, aws_env: AwsEnvironment):
        self._aws_env = aws_env
    
    def bootstrap(self, context: Dict[str, str] = None) -> None:
        command_prefix = get_command_prefix(aws_profile=self._aws_env.aws_profile, aws_region=self._aws_env.aws_region, context=context)
        command_suffix = f"bootstrap {str(self._aws_env)}"
        command = f"{command_prefix} {command_suffix}"
        
        logger.info(f"Executing command: {command_suffix}")
        logger.warning("NOTE: This operation can take a while.  You can 'tail -f' the logfile to track the status.")
        exit_code, stdout = shell.call_shell_command(command=command)
        exceptions.raise_common_exceptions(exit_code, stdout)

        if exit_code != 0:
            logger.error(f"Bootstrap failed")
            raise exceptions.CdkBootstrapFailedUnknown()

        logger.info(f"Bootstrap succeeded")

    def deploy(self, stack_names: List[str], context: Dict[str, str] = None) -> None:
        command_prefix = get_command_prefix(aws_profile=self._aws_env.aws_profile, aws_region=self._aws_env.aws_region, context=context)
        command_suffix = f"deploy {' '.join(stack_names)}"
        command = f"{command_prefix} {command_suffix}"

        # There are a number of circumstances where the CDK CLI asks the user to confirm before beginning a deployment.
        # Common examples include making IAM and VPC security group changes.  There's no CDK CLI option to "auto-yes".
        # As a quick solution, we perform that confirmation using pexpect but this can be quite dangerous and we should
        # find a better answer, ideally surfacing this to the user somehow.
        cdk_confirmation_dialogue = ("Do you wish to deploy these changes (y/n)?", "yes")

        logger.info(f"Executing command: {command_suffix}")
        logger.warning("NOTE: This operation can take a while.  You can 'tail -f' the logfile to track the status.")
        exit_code, stdout = shell.call_shell_command(command=command, request_response_pairs=[cdk_confirmation_dialogue])

        try:
            exceptions.raise_common_exceptions(exit_code, stdout)
        except exceptions.CommonCdkNotBootstrapped as exception:
            # If the CDK setup isn't bootstrapped, attempt to bootstrap and redeploy
            logger.warning("The AWS Account/Region does not appear to be CDK Bootstrapped, which is required for"
                        + " deployment.  Attempting to bootstrap now...")
            self.bootstrap(context=context)
            logger.info(f"Executing command: {command_suffix}")
            exit_code, stdout = shell.call_shell_command(command=command, request_response_pairs=[cdk_confirmation_dialogue])
            exceptions.raise_common_exceptions(exit_code, stdout)

        if exit_code != 0:
            logger.error(f"Deployment failed")
            exceptions.raise_deploy_exceptions(exit_code, stdout)

        logger.info(f"Deployment succeeded")

    def deploy_single_stack(self, stack_name, context: Dict[str, str] = None):
        self.deploy([stack_name], context=context)

    def deploy_all_stacks(self, context: Dict[str, str] = None):
        self.deploy(["--all"], context=context)

    def destroy(self, stack_names: List[str], context: Dict[str, str] = None) -> None:
        command_prefix = get_command_prefix(aws_profile=self._aws_env.aws_profile, aws_region=self._aws_env.aws_region, context=context)
        command_suffix = f"destroy --force {' '.join(stack_names)}"
        command = f"{command_prefix} {command_suffix}"

        # Get the CDK Environment and confirm user wants to tear down the stacks, abort if not
        destroy_prompt = ("Your command will result in the the following CloudFormation stacks being destroyed in"
                           + f" AWS Account {self._aws_env.aws_account} and Region {self._aws_env.aws_region}: {stack_names}"
                           + "\n\n"
                           + "Do you wish to proceed (y/yes or n/no)? ")
        prompt_response = shell.louder_input(message=destroy_prompt, print_header=True)
        if prompt_response.strip().lower() not in ["y", "yes"]:
            logger.info("Aborting per user response")
            return

        # Execute the command.  We should be checking the output to confirm the stacks that the user agreed to destroy
        # above are actually the ones being destroyed (e.g. don't use the --force option), but I wasn't able to get
        # pepexpect to reliably match the output the CDK CLI provided.
        # See: https://github.com/arkime/cloud-demo/issues/12

        logger.info(f"Executing command: {command_suffix}")
        logger.warning("NOTE: This operation can take a while.  You can 'tail -f' the logfile to track the status.")
        exit_code, stdout = shell.call_shell_command(command=command)
        exceptions.raise_common_exceptions(exit_code, stdout)

        if exit_code != 0:
            logger.error(f"Destruction failed")
            raise exceptions.CdkDestroyFailedUnknown()

        logger.info(f"Destruction succeeded")
        