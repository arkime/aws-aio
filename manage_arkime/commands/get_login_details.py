from dataclasses import dataclass
import json
import logging
import sys
from typing import Dict, List

from arkime_interactions.config_wrangling import ViewerDetails
from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.ssm_operations as ssm_ops
import core.constants as constants

logger = logging.getLogger(__name__)

DEFAULT_UNKNOWN_VAL = "unknown"

@dataclass
class LoginDetails:
    password: str
    username: str
    url: str

    def __str__(self):
        return f"URL: https://{self.url}\nUsername: {self.username}\nPassword: {self.password}"

def cmd_get_login_details(profile: str, region: str, name: str) -> LoginDetails:
    logger.debug(f"Invoking get-login-details with profile '{profile}' and region '{region}'")

    logger.info("Retrieving login details...")
    aws_provider = AwsClientProvider(aws_profile=profile, aws_region=region)

    # Get the Viewer Details
    try:
        raw_viewer_details = ssm_ops.get_ssm_param_value(constants.get_viewer_details_ssm_param_name(name), aws_provider)
        viewer_details = ViewerDetails(**json.loads(raw_viewer_details))
    except ssm_ops.ParamDoesNotExist:
        logger.warning("Unable to retrieve viewer details from SSM Parameter Store")
        logger.error(f"We weren't able to pull the Viewer details for cluster '{name}'; is it deployed correctly?")
        sys.exit(1)

    username = viewer_details.user
    login_url = viewer_details.dns
    secrets_client = aws_provider.get_secretsmanager()
    password = json.loads(secrets_client.get_secret_value(SecretId=viewer_details.passwordArn)["SecretString"])

    # Display the result without logging it
    login_details = LoginDetails(password=password['adminPassword'], username=username, url=login_url)
    print(f"Log-in Details for Cluster '{name}'\n==============================\n{login_details}")

    return login_details


