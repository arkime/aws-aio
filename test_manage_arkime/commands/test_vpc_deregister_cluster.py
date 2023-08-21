import json
import unittest.mock as mock

from aws_interactions.aws_environment import AwsEnvironment
import aws_interactions.ssm_operations as ssm_ops
import commands.vpc_deregister_cluster as vdc
import core.constants as constants

@mock.patch("commands.vpc_deregister_cluster.ssm_ops.delete_ssm_param")
@mock.patch("commands.vpc_deregister_cluster.ssm_ops.get_ssm_param_value")
@mock.patch("commands.vpc_deregister_cluster.AwsClientProvider")
def test_WHEN_cmd_vpc_deregister_cluster_called_THEN_as_expected(mock_provider_cls, mock_get_ssm, mock_delete_ssm):
    # Set up our mock
    test_env = AwsEnvironment("YYYYYYYYYYYY", "region", "profile")
    mock_provider = mock.Mock()
    mock_provider.get_aws_env.return_value = test_env
    mock_provider_cls.return_value = mock_provider

    mock_get_ssm.return_value = json.dumps({
        "clusterAccount": "XXXXXXXXXXXX",
        "clusterName": "my_cluster",
        "roleArn": "role_arn",
        "vpcAccount": "YYYYYYYYYYYY",
        "vpcId": "vpc",
        "vpceServiceId": "vpce_id",
    })

    # Run our test
    vdc.cmd_vpc_deregister_cluster("profile", "region", "my_cluster", "vpc")

    # Check our results
    expected_delete_ssm_calls = [
        mock.call(
            constants.get_cluster_vpc_cross_account_ssm_param_name("my_cluster", "vpc"),
            mock_provider
        )
    ]
    assert expected_delete_ssm_calls == mock_delete_ssm.call_args_list

@mock.patch("commands.vpc_deregister_cluster.ssm_ops.delete_ssm_param")
@mock.patch("commands.vpc_deregister_cluster.ssm_ops.get_ssm_param_value")
@mock.patch("commands.vpc_deregister_cluster.AwsClientProvider")
def test_WHEN_cmd_vpc_deregister_cluster_called_AND_not_associated_THEN_as_expected(mock_provider_cls, mock_get_ssm, mock_delete_ssm):
    # Set up our mock
    test_env = AwsEnvironment("YYYYYYYYYYYY", "region", "profile")
    mock_provider = mock.Mock()
    mock_provider.get_aws_env.return_value = test_env
    mock_provider_cls.return_value = mock_provider

    mock_get_ssm.side_effect = ssm_ops.ParamDoesNotExist("")

    # Run our test
    vdc.cmd_vpc_deregister_cluster("profile", "region", "my_cluster", "vpc")

    # Check our results
    expected_delete_ssm_calls = []
    assert expected_delete_ssm_calls == mock_delete_ssm.call_args_list

@mock.patch("commands.vpc_deregister_cluster.ssm_ops.delete_ssm_param")
@mock.patch("commands.vpc_deregister_cluster.ssm_ops.get_ssm_param_value")
@mock.patch("commands.vpc_deregister_cluster.AwsClientProvider")
def test_WHEN_cmd_vpc_deregister_cluster_called_AND_wrong_account_THEN_as_expected(mock_provider_cls, mock_get_ssm, mock_delete_ssm):
    # Set up our mock
    test_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")
    mock_provider = mock.Mock()
    mock_provider.get_aws_env.return_value = test_env
    mock_provider_cls.return_value = mock_provider

    mock_get_ssm.return_value = json.dumps({
        "clusterAccount": "XXXXXXXXXXXX",
        "clusterName": "my_cluster",
        "roleArn": "role_arn",
        "vpcAccount": "YYYYYYYYYYYY",
        "vpcId": "vpc",
        "vpceServiceId": "vpce_id",
    })

    # Run our test
    vdc.cmd_vpc_deregister_cluster("profile", "region", "my_cluster", "vpc")

    # Check our results
    expected_delete_ssm_calls = []
    assert expected_delete_ssm_calls == mock_delete_ssm.call_args_list



