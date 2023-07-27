import unittest.mock as mock

from aws_interactions.aws_environment import AwsEnvironment
from commands.demo_traffic_destroy import cmd_demo_traffic_destroy
import core.constants as constants

@mock.patch("commands.demo_traffic_destroy.AwsClientProvider")
@mock.patch("commands.demo_traffic_destroy.CdkClient")
def test_WHEN_cmd_demo_traffic_destroy_called_THEN_cdk_command_correct(mock_cdk_client_cls, mock_aws_provider_cls):
    # Set up our mock
    mock_client = mock.Mock()
    mock_cdk_client_cls.return_value = mock_client

    aws_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")
    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_aws_env.return_value = aws_env
    mock_aws_provider_cls.return_value = mock_aws_provider

    # Run our test
    cmd_demo_traffic_destroy("profile", "region")

    # Check our results
    expected_calls = [
        mock.call(
            [constants.NAME_DEMO_STACK_1, constants.NAME_DEMO_STACK_2],
            context={constants.CDK_CONTEXT_CMD_VAR: constants.CMD_DESTROY_DEMO}
        )
    ]
    assert expected_calls == mock_client.destroy.call_args_list

    expected_cdk_client_create_calls = [
        mock.call(aws_env)
    ]
    assert expected_cdk_client_create_calls == mock_cdk_client_cls.call_args_list