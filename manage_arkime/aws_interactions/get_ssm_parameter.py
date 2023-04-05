import logging

from botocore.exceptions import ClientError

from manage_arkime.aws_interactions.aws_client_provider import AwsClientProvider

logger = logging.getLogger(__name__)

class ParamDoesNotExist(Exception):
    def __init__(self, param_name: str):
        super().__init__(f"The SSM Parameter {param_name} does not exist")

def get_ssm_param(param_name: str, aws_client_provider: AwsClientProvider):
    ssm_client = aws_client_provider.get_ssm()

    try:
        logger.info(f"Pulling SSM Parameter {param_name}...")
        return ssm_client.get_parameter(Name=param_name)["Parameter"]["Value"]
    except ClientError as exc:
        if exc.response['Error']['Code'] == 'ResourceNotFoundException':
            raise ParamDoesNotExist(param_name=param_name)
        raise

