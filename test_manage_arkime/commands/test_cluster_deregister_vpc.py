import json
import unittest.mock as mock

from aws_interactions.aws_environment import AwsEnvironment
import aws_interactions.ssm_operations as ssm_ops
import commands.cluster_deregister_vpc as cdv
import core.constants as constants
from core.compatibility import CliClusterVersionMismatch

@mock.patch("commands.cluster_deregister_vpc.compat.confirm_aws_aio_version_compatibility", mock.Mock())
@mock.patch("commands.cluster_deregister_vpc.remove_vpce_permissions")
@mock.patch("commands.cluster_deregister_vpc.ssm_ops.delete_ssm_param")
@mock.patch("commands.cluster_deregister_vpc.iami.delete_iam_role")
@mock.patch("commands.cluster_deregister_vpc.ssm_ops.get_ssm_param_value")
@mock.patch("commands.cluster_deregister_vpc.AwsClientProvider")
def test_WHEN_cmd_cluster_deregister_vpc_called_THEN_as_expected(mock_provider_cls, mock_get_ssm, mock_delete_role, mock_delete_ssm,
                                                                 mock_remove_perms):
    # Set up our mock
    test_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")
    mock_provider = mock.Mock()
    mock_provider.get_aws_env.return_value = test_env
    mock_provider_cls.return_value = mock_provider

    mock_get_ssm.return_value = json.dumps({
        "clusterAccount": "XXXXXXXXXXXX",
        "clusterName": "my_cluster",
        "roleName": "role_name",
        "vpcAccount": "YYYYYYYYYYYY",
        "vpcId": "vpc",
        "vpceServiceId": "vpce_id",
    })

    # Run our test
    cdv.cmd_cluster_deregister_vpc("profile", "region", "my_cluster", "vpc")

    # Check our results
    expected_delete_role_calls = [
        mock.call("role_name", mock_provider)
    ]
    assert expected_delete_role_calls == mock_delete_role.call_args_list
    
    expected_remove_perms_calls = [
        mock.call("my_cluster", "vpc", mock_provider)
    ]
    assert expected_remove_perms_calls == mock_remove_perms.call_args_list

    expected_delete_ssm_calls = [
        mock.call(
            constants.get_cluster_vpc_cross_account_ssm_param_name("my_cluster", "vpc"),
            mock_provider
        )
    ]
    assert expected_delete_ssm_calls == mock_delete_ssm.call_args_list

@mock.patch("commands.cluster_deregister_vpc.compat.confirm_aws_aio_version_compatibility", mock.Mock())
@mock.patch("commands.cluster_deregister_vpc.remove_vpce_permissions")
@mock.patch("commands.cluster_deregister_vpc.ssm_ops.delete_ssm_param")
@mock.patch("commands.cluster_deregister_vpc.iami.delete_iam_role")
@mock.patch("commands.cluster_deregister_vpc.ssm_ops.get_ssm_param_value")
@mock.patch("commands.cluster_deregister_vpc.AwsClientProvider")
def test_WHEN_cmd_vpc_deregister_cluster_called_AND_not_associated_THEN_as_expected(mock_provider_cls, mock_get_ssm, mock_delete_role, mock_delete_ssm,
                                                                                    mock_remove_perms):
    # Set up our mock
    test_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")
    mock_provider = mock.Mock()
    mock_provider.get_aws_env.return_value = test_env
    mock_provider_cls.return_value = mock_provider

    mock_get_ssm.side_effect = ssm_ops.ParamDoesNotExist("")

    # Run our test
    cdv.cmd_cluster_deregister_vpc("profile", "region", "my_cluster", "vpc")

    # Check our results
    expected_delete_role_calls = []
    assert expected_delete_role_calls == mock_delete_role.call_args_list
    
    expected_remove_perms_calls = []
    assert expected_remove_perms_calls == mock_remove_perms.call_args_list

    expected_delete_ssm_calls = []
    assert expected_delete_ssm_calls == mock_delete_ssm.call_args_list

@mock.patch("commands.cluster_deregister_vpc.compat.confirm_aws_aio_version_compatibility", mock.Mock())
@mock.patch("commands.cluster_deregister_vpc.remove_vpce_permissions")
@mock.patch("commands.cluster_deregister_vpc.ssm_ops.delete_ssm_param")
@mock.patch("commands.cluster_deregister_vpc.iami.delete_iam_role")
@mock.patch("commands.cluster_deregister_vpc.ssm_ops.get_ssm_param_value")
@mock.patch("commands.cluster_deregister_vpc.AwsClientProvider")
def test_WHEN_cmd_vpc_deregister_cluster_called_AND_wrong_account_THEN_as_expected(mock_provider_cls, mock_get_ssm, mock_delete_role, mock_delete_ssm,
                                                                                   mock_remove_perms):
    # Set up our mock
    test_env = AwsEnvironment("YYYYYYYYYYYY", "region", "profile")
    mock_provider = mock.Mock()
    mock_provider.get_aws_env.return_value = test_env
    mock_provider_cls.return_value = mock_provider

    mock_get_ssm.return_value = json.dumps({
        "clusterAccount": "XXXXXXXXXXXX",
        "clusterName": "my_cluster",
        "roleName": "role_name",
        "vpcAccount": "YYYYYYYYYYYY",
        "vpcId": "vpc",
        "vpceServiceId": "vpce_id",
    })

    # Run our test
    cdv.cmd_cluster_deregister_vpc("profile", "region", "my_cluster", "vpc")

    # Check our results
    expected_delete_role_calls = []
    assert expected_delete_role_calls == mock_delete_role.call_args_list
    
    expected_remove_perms_calls = []
    assert expected_remove_perms_calls == mock_remove_perms.call_args_list

    expected_delete_ssm_calls = []
    assert expected_delete_ssm_calls == mock_delete_ssm.call_args_list

@mock.patch("commands.cluster_deregister_vpc.compat.confirm_aws_aio_version_compatibility")
@mock.patch("commands.cluster_deregister_vpc.remove_vpce_permissions")
@mock.patch("commands.cluster_deregister_vpc.ssm_ops.delete_ssm_param")
@mock.patch("commands.cluster_deregister_vpc.iami.delete_iam_role")
@mock.patch("commands.cluster_deregister_vpc.AwsClientProvider")
def test_WHEN_cmd_vpc_deregister_cluster_called_AND_cli_version_THEN_as_expected(mock_provider_cls, mock_delete_role, mock_delete_ssm,
                                                                                   mock_remove_perms, mock_confirm_ver):
    # Set up our mock
    mock_provider = mock.Mock()
    mock_provider_cls.return_value = mock_provider

    mock_confirm_ver.side_effect = CliClusterVersionMismatch(2, 1)

    # Run our test
    cdv.cmd_cluster_deregister_vpc("profile", "region", "my_cluster", "vpc")

    # Check our results
    expected_delete_role_calls = []
    assert expected_delete_role_calls == mock_delete_role.call_args_list
    
    expected_remove_perms_calls = []
    assert expected_remove_perms_calls == mock_remove_perms.call_args_list

    expected_delete_ssm_calls = []
    assert expected_delete_ssm_calls == mock_delete_ssm.call_args_list



