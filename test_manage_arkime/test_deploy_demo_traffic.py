import unittest.mock as mock

from manage_arkime.commands.deploy_demo_traffic import cmd_deploy_demo_traffic
import manage_arkime.constants as constants

@mock.patch("manage_arkime.commands.deploy_demo_traffic.CdkClient")
def test_WHEN_cmd_deploy_demo_traffic_called_THEN_cdk_command_correct(mock_cdk_client_cls):
    # Set up our mock
    mock_client = mock.Mock()
    mock_cdk_client_cls.return_value = mock_client

    # Run our test
    cmd_deploy_demo_traffic("profile", "region")

    # Check our results
    expected_calls = [
        mock.call(
            [constants.NAME_DEMO_STACK_1, constants.NAME_DEMO_STACK_2],
            aws_profile="profile",
            aws_region="region",
            context={constants.CDK_CONTEXT_CMD_VAR: constants.CMD_DEPLOY_DEMO}
        )
    ]
    assert expected_calls == mock_client.deploy.call_args_list