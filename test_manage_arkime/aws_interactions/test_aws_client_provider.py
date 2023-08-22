import pytest
import unittest.mock as mock

from aws_interactions.aws_client_provider import AwsClientProvider, AssumeRoleNotSupported
from aws_interactions.aws_environment import AwsEnvironment

class FailedTest(Exception):
    def __init__(self):
        super().__init__("This should not have been raised")

@mock.patch("aws_interactions.aws_client_provider.boto3.Session")
def test_WHEN_get_session_called_AND_aws_compute_not_assume_THEN_as_expected(mock_session_cls):
    # Set up our mock
    mock_client = mock.Mock()
    mock_session = mock.Mock()
    mock_session.client.return_value = mock_client

    mock_session_cls.side_effect = [mock_session, FailedTest()]

    # Run our test
    aws_provider = AwsClientProvider(aws_compute=True)
    test_client = aws_provider.get_acm()

    # Check our results
    assert test_client == mock_client

@mock.patch("aws_interactions.aws_client_provider.boto3.Session")
def test_WHEN_get_session_called_AND_not_aws_compute_not_assume_THEN_as_expected(mock_session_cls):
    # Set up our mock
    mock_client = mock.Mock()
    mock_session = mock.Mock()
    mock_session.client.return_value = mock_client

    mock_session_cls.side_effect = [mock_session, FailedTest()]

    # Run our test
    aws_provider = AwsClientProvider(aws_region="region", aws_profile="profile")
    test_client = aws_provider.get_acm()

    # Check our results
    assert test_client == mock_client

    expected_session_calls = [
        mock.call(profile_name="profile", region_name="region")
    ]
    assert expected_session_calls == mock_session_cls.call_args_list

@mock.patch("aws_interactions.aws_client_provider.boto3.Session")
def test_WHEN_get_session_called_AND_not_aws_compute_assume_THEN_as_expected(mock_session_cls):
    # Set up our mock
    mock_initial_client = mock.Mock()
    mock_initial_client.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "access",
            "SecretAccessKey": "secret",
            "SessionToken": "token",
        }        
    }
    mock_initial_session = mock.Mock()
    mock_initial_session.client.return_value = mock_initial_client

    mock_assumed_client = mock.Mock()
    mock_assumed_session = mock.Mock()
    mock_assumed_session.client.return_value = mock_assumed_client

    mock_session_cls.side_effect = [mock_initial_session, mock_assumed_session, FailedTest()]

    # Run our test
    aws_provider = AwsClientProvider(aws_region="region", aws_profile="profile", assume_role_arn="role:arn")
    test_client = aws_provider.get_acm()

    # Check our results
    assert test_client == mock_assumed_client

    expected_sts_calls = [
        mock.call(RoleArn="role:arn", RoleSessionName="ArkimeAwsAioCLI")
    ]
    assert expected_sts_calls == mock_initial_client.assume_role.call_args_list

    expected_session_calls = [
        mock.call(profile_name="profile", region_name="region"),
        mock.call(
            aws_access_key_id = "access",
            aws_secret_access_key = "secret",
            aws_session_token = "token",
            region_name = "region"
        ),
    ]
    assert expected_session_calls == mock_session_cls.call_args_list

def test_WHEN_get_aws_env_called_AND_no_args_THEN_gens_correctly():
    # Set up our mock
    mock_meta = mock.Mock()
    mock_meta.region_name = "my-region-1"
    mock_sts_client = mock.Mock()
    mock_sts_client.meta = mock_meta
    mock_sts_client.get_caller_identity.return_value = {"Account": "XXXXXXXXXXXX"}    
    mock_get_sts = mock.Mock()
    mock_get_sts.return_value = mock_sts_client
    
    mocked_client = AwsClientProvider()
    mocked_client.get_sts = mock_get_sts

    # Run our test
    result = mocked_client.get_aws_env()

    # Check our results
    expected_value = "aws://XXXXXXXXXXXX/my-region-1"
    assert expected_value == str(result)
    assert "XXXXXXXXXXXX" == result.aws_account
    assert "my-region-1" == result.aws_region

def test_WHEN_get_aws_env_called_AND_region_supplied_THEN_gens_correctly():
    # Set up our mock
    mock_sts_client = mock.Mock()
    mock_sts_client.get_caller_identity.return_value = {"Account": "XXXXXXXXXXXX"}    
    mock_get_sts = mock.Mock()
    mock_get_sts.return_value = mock_sts_client
    
    mocked_client = AwsClientProvider(aws_region="my-region-1")
    mocked_client.get_sts = mock_get_sts

    # Run our test
    result = mocked_client.get_aws_env()

    # Check our results
    expected_value = "aws://XXXXXXXXXXXX/my-region-1"
    assert expected_value == str(result)
    assert "XXXXXXXXXXXX" == result.aws_account
    assert "my-region-1" == result.aws_region

def test_WHEN_get_aws_env_called_AND_profile_supplied_THEN_gens_correctly():
    # Set up our mock
    mock_meta = mock.Mock()
    mock_meta.region_name = "my-region-1"
    mock_sts_client = mock.Mock()
    mock_sts_client.meta = mock_meta
    mock_sts_client.get_caller_identity.return_value = {"Account": "XXXXXXXXXXXX"}
    mock_get_sts = mock.Mock()
    mock_get_sts.return_value = mock_sts_client
    
    mocked_client = AwsClientProvider(aws_profile="my-profile")
    mocked_client.get_sts = mock_get_sts

    # Run our test
    result = mocked_client.get_aws_env()

    # Check our results
    expected_value = "aws://XXXXXXXXXXXX/my-region-1"
    assert expected_value == str(result)
    assert "XXXXXXXXXXXX" == result.aws_account
    assert "my-region-1" == result.aws_region