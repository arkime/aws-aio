import unittest.mock as mock

from manage_arkime.commands.get_login_details import cmd_get_login_details, LoginDetails, DEFAULT_UNKNOWN_VAL
from manage_arkime.aws_interactions.ssm_operations import ParamDoesNotExist
import manage_arkime.constants as constants

@mock.patch("manage_arkime.commands.get_login_details.AwsClientProvider")
@mock.patch("manage_arkime.commands.get_login_details.ssm_ops")
def test_WHEN_cmd_get_login_details_called_THEN_retrieves_them(mock_ssm_ops, mock_provider_cls):
    # Set up our mock
    mock_secrets_client = mock.Mock()
    mock_secrets_client.get_secret_value.return_value = {"SecretString": "password"}
    mock_provider = mock.Mock()
    mock_provider.get_secretsmanager.return_value = mock_secrets_client
    mock_provider_cls.return_value = mock_provider

    mock_ssm_ops.get_ssm_param_value.side_effect = ["url", "username", "arn"]

    # Run our test
    result = cmd_get_login_details("profile", "region", "cluster-1")

    # Check our results
    expected_get_pass_call = [
        mock.call(SecretId="arn")
    ]
    assert expected_get_pass_call == mock_secrets_client.get_secret_value.call_args_list

    expected_result = LoginDetails(password="password", username="username", url="url")
    assert expected_result == result

@mock.patch("manage_arkime.commands.get_login_details.AwsClientProvider")
@mock.patch("manage_arkime.commands.get_login_details.ssm_ops")
def test_WHEN_cmd_get_login_details_called_AND_cant_retrieve_THEN_handles_gracefully(mock_ssm_ops, mock_provider_cls):
    # Set up our mock
    mock_secrets_client = mock.Mock()
    mock_secrets_client.get_secret_value.return_value = {"SecretString": "password"}
    mock_provider = mock.Mock()
    mock_provider.get_secretsmanager.return_value = mock_secrets_client
    mock_provider_cls.return_value = mock_provider

    mock_ssm_ops.ParamDoesNotExist = ParamDoesNotExist
    mock_ssm_ops.get_ssm_param_value.side_effect = ParamDoesNotExist("param-1")

    # Run our test
    result = cmd_get_login_details("profile", "region", "cluster-1")

    # Check our results
    expected_get_pass_call = []
    assert expected_get_pass_call == mock_secrets_client.get_secret_value.call_args_list

    expected_result = LoginDetails(password=DEFAULT_UNKNOWN_VAL, username=DEFAULT_UNKNOWN_VAL, url=DEFAULT_UNKNOWN_VAL)
    assert expected_result == result

