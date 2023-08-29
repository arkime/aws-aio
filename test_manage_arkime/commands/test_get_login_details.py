import pytest
import unittest.mock as mock

from commands.get_login_details import cmd_get_login_details, LoginDetails, DEFAULT_UNKNOWN_VAL
from aws_interactions.ssm_operations import ParamDoesNotExist
import core.constants as constants

@mock.patch("commands.get_login_details.AwsClientProvider")
@mock.patch("commands.get_login_details.ssm_ops")
def test_WHEN_cmd_get_login_details_called_THEN_retrieves_them(mock_ssm_ops, mock_provider_cls):
    # Set up our mock
    mock_secrets_client = mock.Mock()
    mock_secrets_client.get_secret_value.return_value = {"SecretString": "{\"adminPassword\": \"password\"}"}
    mock_provider = mock.Mock()
    mock_provider.get_secretsmanager.return_value = mock_secrets_client
    mock_provider_cls.return_value = mock_provider

    mock_ssm_ops.ParamDoesNotExist = ParamDoesNotExist
    mock_ssm_ops.get_ssm_param_value.return_value = '{"dns":"dns-name.com","ecsCluster":"cluster-name","ecsService":"service-name","passwordArn":"secrets-arn","user":"username"}'

    # Run our test
    result = cmd_get_login_details("profile", "region", "cluster-1")

    # Check our results
    expected_get_pass_call = [
        mock.call(SecretId="secrets-arn")
    ]
    assert expected_get_pass_call == mock_secrets_client.get_secret_value.call_args_list

    expected_result = LoginDetails(password="password", username="username", url="dns-name.com")
    assert expected_result == result


class SysExitCalled(Exception):
    pass

@mock.patch("commands.get_login_details.sys.exit")
@mock.patch("commands.get_login_details.AwsClientProvider")
@mock.patch("commands.get_login_details.ssm_ops")
def test_WHEN_cmd_get_login_details_called_AND_cant_retrieve_THEN_handles_gracefully(mock_ssm_ops, mock_provider_cls, mock_exit):
    # Set up our mock
    mock_secrets_client = mock.Mock()
    mock_secrets_client.get_secret_value.return_value = {"SecretString": "password"}
    mock_provider = mock.Mock()
    mock_provider.get_secretsmanager.return_value = mock_secrets_client
    mock_provider_cls.return_value = mock_provider

    mock_ssm_ops.ParamDoesNotExist = ParamDoesNotExist
    mock_ssm_ops.get_ssm_param_value.side_effect = ParamDoesNotExist("param-1")

    mock_exit.side_effect = SysExitCalled()

    # Run our test
    with pytest.raises(SysExitCalled):
        cmd_get_login_details("profile", "region", "cluster-1")

    # Check our results
    expected_get_pass_call = []
    assert expected_get_pass_call == mock_secrets_client.get_secret_value.call_args_list

