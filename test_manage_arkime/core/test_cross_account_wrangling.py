import json
import unittest.mock as mock

from aws_interactions.aws_environment import AwsEnvironment
import core.cross_account_wrangling as caw

def test_WHEN_get_iam_role_name_called_THEN_as_expected():
    # TEST: Cluster Name is nice and short
    result = caw.get_iam_role_name("ThisIsMyRoleName", "vpc-12345678901234567")
    assert "arkime_ThisIsMyRoleName_vpc-12345678901234567" == result

    # TEST: Cluster Name is longer than will fit naturally
    result = caw.get_iam_role_name("ThisIsAVeryLongClusterNameThatHopefulyWontHappenForReal", "vpc-12345678901234567")
    assert "arkime_ThisIsAVeryLongClusterNameThatHopef_vpc-12345678901234567" == result

@mock.patch("core.cross_account_wrangling.does_iam_role_exist")
@mock.patch("core.cross_account_wrangling.get_iam_role_name")
def test_WHEN_ensure_cross_account_role_exists_called_AND_doesnt_exist_THEN_as_expected(mock_get_name, mock_does_exist):
    # Set up our mock
    mock_iam_client = mock.Mock()

    mock_provider = mock.Mock()
    mock_provider.get_iam.return_value = mock_iam_client
    test_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")

    mock_get_name.return_value = "role_name"
    mock_does_exist.return_value = False

    # Run our test
    result = caw.ensure_cross_account_role_exists("my_cluster", "XXXXXXXXXXXX", "vpc", mock_provider, test_env)

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

@mock.patch("core.cross_account_wrangling.does_iam_role_exist")
@mock.patch("core.cross_account_wrangling.get_iam_role_name")
def test_WHEN_ensure_cross_account_role_exists_called_AND_does_exist_THEN_as_expected(mock_get_name, mock_does_exist):
    # Set up our mock
    mock_iam_client = mock.Mock()

    mock_provider = mock.Mock()
    mock_provider.get_iam.return_value = mock_iam_client
    test_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")

    mock_get_name.return_value = "role_name"
    mock_does_exist.return_value = True

    # Run our test
    result = caw.ensure_cross_account_role_exists("my_cluster", "XXXXXXXXXXXX", "vpc", mock_provider, test_env)

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

def test_WHEN_add_vpce_permissions_called_THEN_as_expected():
    # Set up our mock
    mock_ec2_client = mock.Mock()

    mock_provider = mock.Mock()
    mock_provider.get_ec2.return_value = mock_ec2_client

    # Run our test
    caw.add_vpce_permissions("vpce_id", "YYYYYYYYYYYY", mock_provider)

    # Check our results
    expected_modify_calls = [
        mock.call(
            ServiceId="vpce_id",
            AddAllowedPrincipals=[
                f"arn:aws:iam::YYYYYYYYYYYY:root"
            ]
        )
    ]
    assert expected_modify_calls == mock_ec2_client.modify_vpc_endpoint_service_permissions.call_args_list

