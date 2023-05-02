from dataclasses import dataclass
import logging
from typing import Dict, List

from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.ssm_operations as ssm_ops
import constants as constants

logger = logging.getLogger(__name__)

DEFAULT_UNKNOWN_VAL = "unknown"

@dataclass
class LoginDetails:
    password: str
    username: str
    url: str

    def __str__(self):
        return f"URL: {self.url}\nUsername: {self.username}\nPassword: {self.password}"

def cmd_get_login_details(profile: str, region: str, name: str) -> LoginDetails:
    logger.debug(f"Invoking get-login-details with profile '{profile}' and region '{region}'")

    logger.info("Retrieving login details...")
    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)

    # Get the URL
    try:
        login_url = ssm_ops.get_ssm_param_value(constants.get_viewer_dns_ssm_param_name(name), aws_provider)
    except ssm_ops.ParamDoesNotExist:
        logger.warning("Unable to retrieve Login URL from SSM Parameter Store")
        login_url = DEFAULT_UNKNOWN_VAL

    # Get the username
    try:
        username = ssm_ops.get_ssm_param_value(constants.get_viewer_user_ssm_param_name(name), aws_provider)
    except ssm_ops.ParamDoesNotExist:
        logger.warning("Unable to retrieve Username from SSM Parameter Store")
        username = DEFAULT_UNKNOWN_VAL

    # Get the password
    try:
        pass_arn = ssm_ops.get_ssm_param_value(constants.get_viewer_password_ssm_param_name(name), aws_provider)
        secrets_client = aws_provider.get_secretsmanager()
        password = secrets_client.get_secret_value(SecretId=pass_arn)["SecretString"]
    except ssm_ops.ParamDoesNotExist:
        logger.warning("Unable to retrieve Password from SSM Parameter Store")
        password = DEFAULT_UNKNOWN_VAL

    # Display the result without logging it
    login_details = LoginDetails(password=password, username=username, url=login_url)
    print(f"Log-in Details for Cluster '{name}'\n==============================\n{login_details}")

    return login_details

    