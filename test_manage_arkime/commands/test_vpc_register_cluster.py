import json
import unittest.mock as mock

from aws_interactions.aws_environment import AwsEnvironment
import commands.vpc_register_cluster as vrc
import core.constants as constants
from core.cross_account_wrangling import CrossAccountAssociation

@mock.patch("commands.vpc_register_cluster.ssm_ops.put_ssm_param")
@mock.patch("commands.vpc_register_cluster.AwsClientProvider")
def test_WHEN_cmd_vpc_register_cluster_called_THEN_as_expected(mock_provider_cls, mock_put_ssm):
    # Set up our mock
    test_env = AwsEnvironment("YYYYYYYYYYYY", "region", "profile")
    mock_provider = mock.Mock()
    mock_provider.get_aws_env.return_value = test_env
    mock_provider_cls.return_value = mock_provider

    # Run our test
    vrc.cmd_vpc_register_cluster("profile", "region", "XXXXXXXXXXXX", "my_cluster", "role_arn", "YYYYYYYYYYYY", "vpc", "vpce_id")

    # Check our results

    expected_association = CrossAccountAssociation(
        "XXXXXXXXXXXX", "my_cluster", "role_arn", "YYYYYYYYYYYY", "vpc", "vpce_id"
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

@mock.patch("commands.vpc_register_cluster.ssm_ops.put_ssm_param")
@mock.patch("commands.vpc_register_cluster.AwsClientProvider")
def test_WHEN_cmd_vpc_register_cluster_called_AND_wrong_account_THEN_as_expected(mock_provider_cls, mock_put_ssm):
    # Set up our mock
    test_env = AwsEnvironment("ZZZZZZZZZZZZ", "region", "profile")
    mock_provider = mock.Mock()
    mock_provider.get_aws_env.return_value = test_env
    mock_provider_cls.return_value = mock_provider

    # Run our test
    vrc.cmd_vpc_register_cluster("profile", "region", "XXXXXXXXXXXX", "my_cluster", "role_arn", "YYYYYYYYYYYY", "vpc", "vpce_id")

    # Check our results
    expected_put_ssm_calls = []
    assert expected_put_ssm_calls == mock_put_ssm.call_args_list

