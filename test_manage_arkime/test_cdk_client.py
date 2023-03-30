import pytest
import unittest.mock as mock

import manage_arkime.constants as constants
import manage_arkime.cdk_client as cdk
from manage_arkime.cdk_environment import CdkEnvironment
import manage_arkime.cdk_exceptions as exceptions


def test_WHEN_get_command_prefix_called_AND_no_args_THEN_gens_correctly():
    # Run our test
    actual_value = cdk.get_command_prefix()

    # Check our results
    expected_value = "cdk"
    assert expected_value == actual_value

def test_WHEN_get_command_prefix_called_AND_profile_THEN_gens_correctly():
    # Run our test
    actual_value = cdk.get_command_prefix(aws_profile="my_profile")

    # Check our results
    expected_value = "cdk --profile my_profile"
    assert expected_value == actual_value

def test_WHEN_get_command_prefix_called_AND_region_THEN_gens_correctly():
    # Run our test
    actual_value = cdk.get_command_prefix(aws_region="mars-north-1")

    # Check our results
    expected_value = f"cdk --context {constants.CDK_CONTEXT_REGION_VAR}=mars-north-1"
    assert expected_value == actual_value

def test_WHEN_get_command_prefix_called_AND_context_THEN_gens_correctly():
    # Set up our test
    test_context = {
        "k1": "v1",
        "k2": "v2",
    }

    # Run our test
    actual_value = cdk.get_command_prefix(aws_region="mars-north-1", context=test_context)

    # Check our results
    expected_value = f"cdk --context {constants.CDK_CONTEXT_REGION_VAR}=mars-north-1 --context k1=v1 --context k2=v2"
    assert expected_value == actual_value

@mock.patch('manage_arkime.cdk_client.get_cdk_env')
@mock.patch('manage_arkime.cdk_client.shell')
def test_WHEN_bootstrap_called_THEN_executes_command(mock_shell, mock_get_env):
    # Set up our mock
    mock_call_shell = mock_shell.call_shell_command
    mock_call_shell.return_value = [0, ["success"]]

    test_env = CdkEnvironment(aws_account="XXXXXXXXXXXX", aws_region="my-region-1")
    mock_get_env.return_value = test_env

    # Run our test
    client = cdk.CdkClient()
    client.bootstrap()

    # Check our results
    expected_calls = [mock.call(command=f"cdk bootstrap {str(test_env)}")]
    assert expected_calls == mock_shell.call_shell_command.call_args_list

    expected_env_calls = [mock.call(aws_profile=None, aws_region=None)]
    assert expected_env_calls == mock_get_env.call_args_list

@mock.patch('manage_arkime.cdk_client.get_cdk_env')
@mock.patch('manage_arkime.cdk_client.shell')
def test_WHEN_bootstrap_called_AND_profile_region_THEN_executes_command(mock_shell, mock_get_env):
    # Set up our mock
    mock_call_shell = mock_shell.call_shell_command
    mock_call_shell.return_value = [0, ["success"]]

    test_env = CdkEnvironment(aws_account="XXXXXXXXXXXX", aws_region="my-region-1")
    mock_get_env.return_value = test_env

    # Run our test
    client = cdk.CdkClient()
    client.bootstrap(aws_profile="my_profile", aws_region="region")

    # Check our results
    expected_command = cdk.get_command_prefix(aws_profile="my_profile", aws_region="region") + f" bootstrap {str(test_env)}"
    expected_calls = [mock.call(command=expected_command)]
    assert expected_calls == mock_shell.call_shell_command.call_args_list

    expected_env_calls = [mock.call(aws_profile="my_profile", aws_region="region")]
    assert expected_env_calls == mock_get_env.call_args_list

@mock.patch('manage_arkime.cdk_client.get_cdk_env', mock.Mock())
@mock.patch('manage_arkime.cdk_client.shell')
def test_WHEN_bootstrap_called_AND_fails_unknown_THEN_raises(mock_shell):
    # Set up our mock
    mock_call_shell = mock_shell.call_shell_command
    mock_call_shell.return_value = [1, ["failed for reasons"]]

    # Run our test
    client = cdk.CdkClient()
    with pytest.raises(exceptions.CdkBootstrapFailedUnknown):
        client.bootstrap()

@mock.patch('manage_arkime.cdk_client.shell')
def test_WHEN_deploy_called_THEN_executes_command(mock_shell):
    # Set up our mock
    mock_call_shell = mock_shell.call_shell_command
    mock_call_shell.return_value = [0, ["success"]]

    # Run our test
    client = cdk.CdkClient()
    client.deploy(["MyStack1", "MyStack2"])

    # Check our results
    expected_calls = [
        mock.call(
            command="cdk deploy MyStack1 MyStack2",
            request_response_pairs=[("Do you wish to deploy these changes (y/n)?", "yes")]
        )
    ]
    assert expected_calls == mock_shell.call_shell_command.call_args_list

@mock.patch('manage_arkime.cdk_client.shell')
def test_WHEN_deploy_called_AND_profile_region_context_THEN_executes_command(mock_shell):
    # Set up our mock
    mock_call_shell = mock_shell.call_shell_command
    mock_call_shell.return_value = [0, ["success"]]

    # Run our test
    client = cdk.CdkClient()
    client.deploy(["MyStack"], aws_profile="my_profile", aws_region="region", context={"key": "value"})

    # Check our results
    expected_command = cdk.get_command_prefix(aws_profile="my_profile", aws_region="region", context={"key": "value"}) + " deploy MyStack"
    expected_calls = [mock.call(command=expected_command, request_response_pairs=mock.ANY)]
    assert expected_calls == mock_shell.call_shell_command.call_args_list

@mock.patch('manage_arkime.cdk_client.get_cdk_env')
@mock.patch('manage_arkime.cdk_client.shell')
def test_WHEN_deploy_called_AND_not_bootstrapped_THEN_executes_command(mock_shell, mock_get_env):
    # Set up our mock
    mock_call_shell = mock_shell.call_shell_command
    mock_call_shell.side_effect = [
        (1, [exceptions.NOT_BOOTSTRAPPED_1]),
        (0, ["bootstrap success"]),
        (0, ["deploy success"])
    ]

    test_env = CdkEnvironment(aws_account="XXXXXXXXXXXX", aws_region="my-region-1")
    mock_get_env.return_value = test_env

    # Run our test
    client = cdk.CdkClient()
    client.deploy(["MyStack"])

    # Check our results
    expected_calls = [
        mock.call(
            command="cdk deploy MyStack",
            request_response_pairs=[("Do you wish to deploy these changes (y/n)?", "yes")]
        ),
        mock.call(command=f"cdk bootstrap {str(test_env)}"),
        mock.call(
            command="cdk deploy MyStack",
            request_response_pairs=[("Do you wish to deploy these changes (y/n)?", "yes")]
        )
    ]
    assert expected_calls == mock_shell.call_shell_command.call_args_list

@mock.patch('manage_arkime.cdk_client.get_cdk_env')
@mock.patch('manage_arkime.cdk_client.shell')
def test_WHEN_deploy_called_AND_cant_bootstrap_THEN_raises(mock_shell, mock_get_env):
    # Set up our mock
    mock_call_shell = mock_shell.call_shell_command
    mock_call_shell.side_effect = [
        (1, [exceptions.NOT_BOOTSTRAPPED_1]),
        (1, ["bootstrap failed for reasons"])
    ]

    test_env = CdkEnvironment(aws_account="XXXXXXXXXXXX", aws_region="my-region-1")
    mock_get_env.return_value = test_env

    # Run our test
    client = cdk.CdkClient()
    with pytest.raises(exceptions.CdkBootstrapFailedUnknown):
        client.deploy(["MyStack"])
    
    # Check our results
    expected_calls = [
        mock.call(command="cdk deploy MyStack", request_response_pairs=mock.ANY),
        mock.call(command=f"cdk bootstrap {str(test_env)}")
    ]
    assert expected_calls == mock_shell.call_shell_command.call_args_list

@mock.patch('manage_arkime.cdk_client.shell')
def test_WHEN_deploy_called_AND_fails_THEN_raises(mock_shell):
    # Set up our mock
    mock_call_shell = mock_shell.call_shell_command
    mock_call_shell.side_effect = [
        (1, ["deploy failed for reasons"])
    ]

    # Run our test
    client = cdk.CdkClient()
    with pytest.raises(exceptions.CdkDeployFailedUnknown):
        client.deploy(["MyStack"])
    
    # Check our results
    expected_calls = [mock.call(command="cdk deploy MyStack", request_response_pairs=mock.ANY)]
    assert expected_calls == mock_shell.call_shell_command.call_args_list

@mock.patch('manage_arkime.cdk_client.shell')
def test_WHEN_deploy_single_stack_called_THEN_executes_command(mock_shell):
    # Set up our mock
    mock_call_shell = mock_shell.call_shell_command
    mock_call_shell.return_value = [0, ["success"]]

    # Run our test
    client = cdk.CdkClient()
    client.deploy_single_stack("MyStack")

    # Check our results
    expected_calls = [mock.call(command="cdk deploy MyStack", request_response_pairs=mock.ANY)]
    assert expected_calls == mock_shell.call_shell_command.call_args_list

@mock.patch('manage_arkime.cdk_client.shell')
def test_WHEN_deploy_all_stacks_called_THEN_executes_command(mock_shell):
    # Set up our mock
    mock_call_shell = mock_shell.call_shell_command
    mock_call_shell.return_value = [0, ["success"]]

    # Run our test
    client = cdk.CdkClient()
    client.deploy_all_stacks()

    # Check our results
    expected_calls = [mock.call(command="cdk deploy --all", request_response_pairs=mock.ANY)]
    assert expected_calls == mock_shell.call_shell_command.call_args_list

@mock.patch('manage_arkime.cdk_client.get_cdk_env', mock.Mock())
@mock.patch('manage_arkime.cdk_client.shell')
def test_WHEN_destroy_called_THEN_executes_command(mock_shell):
    # Set up our mock
    mock_call_shell = mock_shell.call_shell_command
    mock_call_shell.return_value = [0, ["success"]]

    mock_input = mock_shell.louder_input
    mock_input.return_value = "yes"

    # Run our test
    client = cdk.CdkClient()
    client.destroy(["MyStack1", "MyStack2"])

    # Check our results
    expected_calls = [
        mock.call(
            command="cdk destroy --force MyStack1 MyStack2"
        )
    ]
    assert expected_calls == mock_shell.call_shell_command.call_args_list

@mock.patch('manage_arkime.cdk_client.get_cdk_env', mock.Mock())
@mock.patch('manage_arkime.cdk_client.shell')
def test_WHEN_destroy_called_AND_profile_region_context_THEN_executes_command(mock_shell):
    # Set up our mock
    mock_call_shell = mock_shell.call_shell_command
    mock_call_shell.return_value = [0, ["success"]]

    mock_input = mock_shell.louder_input
    mock_input.return_value = "yes"

    # Run our test
    client = cdk.CdkClient()
    client.destroy(["MyStack"], aws_profile="my_profile", aws_region="region", context={"key": "value"})

    # Check our results
    expected_command = cdk.get_command_prefix(aws_profile="my_profile", aws_region="region", context={"key": "value"}) + " destroy --force MyStack"
    expected_calls = [mock.call(command=expected_command)]
    assert expected_calls == mock_shell.call_shell_command.call_args_list

@mock.patch('manage_arkime.cdk_client.get_cdk_env', mock.Mock())
@mock.patch('manage_arkime.cdk_client.shell')
def test_WHEN_destroy_called_AND_no_confirmation_THEN_aborts_1(mock_shell):
    # Set up our mock
    mock_input = mock_shell.louder_input
    mock_input.return_value = "no"

    # Run our test
    client = cdk.CdkClient()
    client.destroy(["MyStack1", "MyStack2"])

    # Check our results
    expected_calls = []
    assert expected_calls == mock_shell.call_shell_command.call_args_list

@mock.patch('manage_arkime.cdk_client.get_cdk_env', mock.Mock())
@mock.patch('manage_arkime.cdk_client.shell')
def test_WHEN_destroy_called_AND_no_confirmation_THEN_aborts_2(mock_shell):
    # Set up our mock
    mock_input = mock_shell.louder_input
    mock_input.return_value = "bleh"

    # Run our test
    client = cdk.CdkClient()
    client.destroy(["MyStack1", "MyStack2"])

    # Check our results
    expected_calls = []
    assert expected_calls == mock_shell.call_shell_command.call_args_list

@mock.patch('manage_arkime.cdk_client.get_cdk_env', mock.Mock())
@mock.patch('manage_arkime.cdk_client.shell')
def test_WHEN_destroy_called_AND_fails_THEN_raises(mock_shell):
    # Set up our mock
    mock_call_shell = mock_shell.call_shell_command
    mock_call_shell.return_value = (1, ["deploy failed for reasons"])

    mock_input = mock_shell.louder_input
    mock_input.return_value = "yes"

    # Run our test
    client = cdk.CdkClient()
    with pytest.raises(exceptions.CdkDestroyFailedUnknown):
        client.destroy(["MyStack1", "MyStack2"])

    # Check our results
    expected_calls = [
        mock.call(
            command="cdk destroy --force MyStack1 MyStack2"
        )
    ]
    assert expected_calls == mock_shell.call_shell_command.call_args_list