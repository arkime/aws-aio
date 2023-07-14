import unittest.mock as mock

from aws_interactions.aws_client_provider import AwsClientProvider
from aws_interactions.aws_environment import AwsEnvironment

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