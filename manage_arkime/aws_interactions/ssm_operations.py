import json
import logging
from typing import Dict, List

from botocore.exceptions import ClientError

from manage_arkime.aws_interactions.aws_client_provider import AwsClientProvider

logger = logging.getLogger(__name__)

class ParamDoesNotExist(Exception):
    def __init__(self, param_name: str):
        super().__init__(f"The SSM Parameter {param_name} does not exist")

def get_ssm_param_value(param_name: str, aws_client_provider: AwsClientProvider) -> str:
    return _get_ssm_param(param_name, aws_client_provider)["Value"]

def get_ssm_param_json_value(param_name: str, key: str, aws_client_provider: AwsClientProvider) -> str:
    return json.loads(get_ssm_param_value(param_name, aws_client_provider))[key]

def _get_ssm_param(param_name: str, aws_client_provider: AwsClientProvider) -> Dict[str, str]:
    ssm_client = aws_client_provider.get_ssm()

    try:
        logger.info(f"Pulling SSM Parameter {param_name}...")
        return ssm_client.get_parameter(Name=param_name)["Parameter"]
    except ClientError as exc:
        if exc.response['Error']['Code'] == 'ParameterNotFound':
            raise ParamDoesNotExist(param_name=param_name)
        raise

def get_ssm_params_by_path(param_path: str, aws_client_provider: AwsClientProvider) -> List[Dict[str, str]]:
    ssm_client = aws_client_provider.get_ssm()

    logger.info(f"Pulling SSM Parameters for Path {param_path}...")
    response: Dict = ssm_client.get_parameters_by_path(Path=param_path)

    if not response: # Will be [] if no params or path doesn't exist
        return response

    return_params = []
    return_params.extend(response["Parameters"])
    next_token = response.get("NextToken")

    while next_token:
        next_response: Dict = ssm_client.get_parameters_by_path(Path=param_path, NextToken=next_token)
        return_params.extend(next_response["Parameters"])
        next_token = next_response.get("NextToken")

    return return_params

def get_ssm_names_by_path(param_path: str, aws_client_provider: AwsClientProvider) -> List[str]:
    raw_params = get_ssm_params_by_path(param_path, aws_client_provider)
    return [param["Name"].split("/")[-1] for param in raw_params]

def put_ssm_param(param_name: str, param_value: str, aws_client_provider: AwsClientProvider, description: str = None, 
        pattern: str = None, overwrite=False):
    ssm_client = aws_client_provider.get_ssm()

    ssm_client.put_parameter(
        Name=param_name,
        Description=description,
        Value=param_value,
        Type="String",
        AllowedPattern=".*",
        Tier='Standard',
        Overwrite=overwrite
    )

def delete_ssm_param(param_name: str, aws_client_provider: AwsClientProvider):
    ssm_client = aws_client_provider.get_ssm()

    ssm_client.delete_parameter(
        Name=param_name
    )