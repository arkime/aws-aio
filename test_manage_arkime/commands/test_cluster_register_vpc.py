import json
import unittest.mock as mock

from aws_interactions.aws_environment import AwsEnvironment
from aws_interactions.ssm_operations import ParamDoesNotExist
import commands.cluster_register_vpc as crv
import core.constants as constants
from core.cross_account_wrangling import CrossAccountAssociation


@mock.patch("commands.cluster_register_vpc.add_vpce_permissions")
@mock.patch("commands.cluster_register_vpc.ensure_cross_account_role_exists")
@mock.patch("commands.cluster_register_vpc.ssm_ops.put_ssm_param")
@mock.patch("commands.cluster_register_vpc.ssm_ops.get_ssm_param_json_value")
@mock.patch("commands.cluster_register_vpc.AwsClientProvider")
def test_WHEN_cmd_cluster_register_vpc_called_THEN_as_expected(mock_provider_cls, mock_get_ssm_json, mock_put_ssm, mock_ensure,
                                                               mock_add_perms):
    # Set up our mock
    test_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")
    mock_provider = mock.Mock()
    mock_provider.get_aws_env.return_value = test_env
    mock_provider_cls.return_value = mock_provider

    mock_get_ssm_json.return_value = "vpce_id"
    mock_ensure.return_value = "role_name"

    # Run our test
    crv.cmd_cluster_register_vpc("profile", "region", "my_cluster", "YYYYYYYYYYYY", "vpc")

    # Check our results
    expected_get_ssm_calls = [
        mock.call(
            constants.get_cluster_ssm_param_name("my_cluster"),
            "vpceServiceId",
            mock_provider
        )
    ]
    assert expected_get_ssm_calls == mock_get_ssm_json.call_args_list

    expected_ensure_calls = [
        mock.call("my_cluster", "YYYYYYYYYYYY", "vpc", mock_provider, test_env)
    ]
    assert expected_ensure_calls == mock_ensure.call_args_list

    expected_add_perms_calls = [
        mock.call("vpce_id", "YYYYYYYYYYYY", mock_provider)
    ]
    assert expected_add_perms_calls == mock_add_perms.call_args_list

    expected_association = CrossAccountAssociation(
        "XXXXXXXXXXXX", "my_cluster", "role_name", "YYYYYYYYYYYY", "vpc", "vpce_id"
    )
    expected_put_ssm_calls = [
        mock.call(
            constants.get_cluster_vpc_cross_account_ssm_param_name("my_cluster", "vpc"),
            json.dumps(expected_association.to_dict()),
            mock_provider,
            description=mock.ANY,
            overwrite=True
        )
    ]
    assert expected_put_ssm_calls == mock_put_ssm.call_args_list

@mock.patch("commands.cluster_register_vpc.add_vpce_permissions")
@mock.patch("commands.cluster_register_vpc.ensure_cross_account_role_exists")
@mock.patch("commands.cluster_register_vpc.ssm_ops.put_ssm_param")
@mock.patch("commands.cluster_register_vpc.ssm_ops.get_ssm_param_json_value")
@mock.patch("commands.cluster_register_vpc.AwsClientProvider")
def test_WHEN_cmd_cluster_register_vpc_called_AND_doesnt_exist_THEN_as_expected(mock_provider_cls, mock_get_ssm_json,
                                                                                mock_put_ssm, mock_ensure, 
                                                                                mock_add_perms):
    # Set up our mock
    test_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")
    mock_provider = mock.Mock()
    mock_provider.get_aws_env.return_value = test_env
    mock_provider_cls.return_value = mock_provider

    mock_get_ssm_json.side_effect = ParamDoesNotExist("")

    # Run our test
    crv.cmd_cluster_register_vpc("profile", "region", "my_cluster", "YYYYYYYYYYYY", "vpc")

    # Check our results
    expected_get_ssm_calls = [
        mock.call(
            constants.get_cluster_ssm_param_name("my_cluster"),
            "vpceServiceId",
            mock_provider
        )
    ]
    assert expected_get_ssm_calls == mock_get_ssm_json.call_args_list

    expected_ensure_calls = []
    assert expected_ensure_calls == mock_ensure.call_args_list

    expected_add_perms_calls = []
    assert expected_add_perms_calls == mock_add_perms.call_args_list

    expected_put_ssm_calls = []
    assert expected_put_ssm_calls == mock_put_ssm.call_args_list    

