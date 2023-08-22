import json
import unittest.mock as mock

from aws_interactions.aws_environment import AwsEnvironment
from aws_interactions.ssm_operations import ParamDoesNotExist
import commands.cluster_register_vpc as crv
import core.constants as constants
from core.cross_account_wrangling import CrossAccountAssociation

def test_WHEN_get_iam_role_name_called_THEN_as_expected():
    # TEST: Cluster Name is nice and short
    result = crv._get_iam_role_name("ThisIsMyRoleName", "vpc-12345678901234567")
    assert "arkime_ThisIsMyRoleName_vpc-12345678901234567" == result

    # TEST: Cluster Name is longer than will fit naturally
    result = crv._get_iam_role_name("ThisIsAVeryLongClusterNameThatHopefulyWontHappenForReal", "vpc-12345678901234567")
    assert "arkime_ThisIsAVeryLongClusterNameThatHopef_vpc-12345678901234567" == result

@mock.patch("commands.cluster_register_vpc.does_iam_role_exist")
@mock.patch("commands.cluster_register_vpc._get_iam_role_name")
def test_WHEN_ensure_cross_account_role_exists_called_AND_doesnt_exist_THEN_as_expected(mock_get_name, mock_does_exist):
    # Set up our mock
    mock_iam_client = mock.Mock()

    mock_provider = mock.Mock()
    mock_provider.get_iam.return_value = mock_iam_client
    test_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")

    mock_get_name.return_value = "role_name"
    mock_does_exist.return_value = False

    # Run our test
    result = crv._ensure_cross_account_role_exists("my_cluster", "XXXXXXXXXXXX", "vpc", mock_provider, test_env)

    # Check our results
    assert "role_name" == result

    expected_trust = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": f"arn:aws:iam::XXXXXXXXXXXX:root"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    expected_update_calls = []
    assert expected_update_calls == mock_iam_client.update_assume_role_policy.call_args_list

    expected_create_calls = [
        mock.call(            
            RoleName="role_name",
            AssumeRolePolicyDocument=json.dumps(expected_trust),
            Description=mock.ANY,
        )
    ]
    assert expected_create_calls == mock_iam_client.create_role.call_args_list

    expected_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ssm:DeleteParameter",
                    "ssm:GetParameter",
                    "ssm:GetParameters",
                    "ssm:PutParameter",
                ],
                "Resource": f"arn:aws:ssm:region:XXXXXXXXXXXX:parameter/arkime/clusters/my_cluster*"
            }
        ]
    }
    expected_put_calls = [
        mock.call(
            RoleName="role_name",
            PolicyName='CrossAcctSSMAccessPolicy',
            PolicyDocument=json.dumps(expected_policy)
        )
    ]
    assert expected_put_calls == mock_iam_client.put_role_policy.call_args_list

@mock.patch("commands.cluster_register_vpc.does_iam_role_exist")
@mock.patch("commands.cluster_register_vpc._get_iam_role_name")
def test_WHEN_ensure_cross_account_role_exists_called_AND_does_exist_THEN_as_expected(mock_get_name, mock_does_exist):
    # Set up our mock
    mock_iam_client = mock.Mock()

    mock_provider = mock.Mock()
    mock_provider.get_iam.return_value = mock_iam_client
    test_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")

    mock_get_name.return_value = "role_name"
    mock_does_exist.return_value = True

    # Run our test
    result = crv._ensure_cross_account_role_exists("my_cluster", "XXXXXXXXXXXX", "vpc", mock_provider, test_env)

    # Check our results
    assert "role_name" == result

    expected_trust = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": f"arn:aws:iam::XXXXXXXXXXXX:root"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    expected_update_calls = [
        mock.call(            
            RoleName="role_name",
            PolicyDocument=json.dumps(expected_trust)
        )
    ]
    assert expected_update_calls == mock_iam_client.update_assume_role_policy.call_args_list

    expected_create_calls = []
    assert expected_create_calls == mock_iam_client.create_role.call_args_list

    expected_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ssm:DeleteParameter",
                    "ssm:GetParameter",
                    "ssm:GetParameters",
                    "ssm:PutParameter",
                ],
                "Resource": f"arn:aws:ssm:region:XXXXXXXXXXXX:parameter/arkime/clusters/my_cluster*"
            }
        ]
    }
    expected_put_calls = [
        mock.call(
            RoleName="role_name",
            PolicyName='CrossAcctSSMAccessPolicy',
            PolicyDocument=json.dumps(expected_policy)
        )
    ]
    assert expected_put_calls == mock_iam_client.put_role_policy.call_args_list

@mock.patch("commands.cluster_register_vpc._add_vpce_permissions")
@mock.patch("commands.cluster_register_vpc._ensure_cross_account_role_exists")
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
        "XXXXXXXXXXXX", "my_cluster", "arn:aws:iam::XXXXXXXXXXXX:role/role_name", "role_name", "YYYYYYYYYYYY", "vpc", "vpce_id"
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

@mock.patch("commands.cluster_register_vpc._add_vpce_permissions")
@mock.patch("commands.cluster_register_vpc._ensure_cross_account_role_exists")
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

