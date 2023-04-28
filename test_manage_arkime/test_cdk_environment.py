import unittest.mock as mock

import cdk_interactions.cdk_environment as cdk_env

@mock.patch('cdk_interactions.cdk_environment.AwsClientProvider')
def test_WHEN_get_cdk_env_called_AND_no_args_THEN_gens_correctly(mock_provider_cls):
    # Set up our mock
    mock_meta = mock.Mock()
    mock_meta.region_name = "my-region-1"
    mock_sts_client = mock.Mock()
    mock_sts_client.meta = mock_meta
    mock_sts_client.get_caller_identity.return_value = {"Account": "XXXXXXXXXXXX"}
    mock_provider = mock.Mock()
    mock_provider.get_sts.return_value = mock_sts_client
    mock_provider_cls.return_value = mock_provider

    # Run our test
    result = cdk_env.get_cdk_env()

    # Check our results
    expected_calls = [mock.call(aws_profile=None, aws_region=None)]
    assert expected_calls == mock_provider_cls.call_args_list

    expected_value = "aws://XXXXXXXXXXXX/my-region-1"
    assert expected_value == str(result)
    assert "XXXXXXXXXXXX" == result.aws_account
    assert "my-region-1" == result.aws_region

@mock.patch('cdk_interactions.cdk_environment.AwsClientProvider')
def test_WHEN_get_cdk_env_called_AND_region_supplied_THEN_gens_correctly(mock_provider_cls):
    # Set up our mock
    mock_sts_client = mock.Mock()
    mock_sts_client.get_caller_identity.return_value = {"Account": "XXXXXXXXXXXX"}
    mock_provider = mock.Mock()
    mock_provider.get_sts.return_value = mock_sts_client
    mock_provider_cls.return_value = mock_provider

    # Run our test
    result = cdk_env.get_cdk_env(aws_region="my-region-1")

    # Check our results
    expected_calls = [mock.call(aws_profile=None, aws_region="my-region-1")]
    assert expected_calls == mock_provider_cls.call_args_list

    expected_value = "aws://XXXXXXXXXXXX/my-region-1"
    assert expected_value == str(result)
    assert "XXXXXXXXXXXX" == result.aws_account
    assert "my-region-1" == result.aws_region

@mock.patch('cdk_interactions.cdk_environment.AwsClientProvider')
def test_WHEN_get_cdk_env_called_AND_profile_supplied_THEN_gens_correctly(mock_provider_cls):
    # Set up our mock
    mock_meta = mock.Mock()
    mock_meta.region_name = "my-region-1"
    mock_sts_client = mock.Mock()
    mock_sts_client.meta = mock_meta
    mock_sts_client.get_caller_identity.return_value = {"Account": "XXXXXXXXXXXX"}
    mock_provider = mock.Mock()
    mock_provider.get_sts.return_value = mock_sts_client
    mock_provider_cls.return_value = mock_provider

    # Run our test
    result = cdk_env.get_cdk_env(aws_profile="my-profile")

    # Check our results
    expected_calls = [mock.call(aws_profile="my-profile", aws_region=None)]
    assert expected_calls == mock_provider_cls.call_args_list

    expected_value = "aws://XXXXXXXXXXXX/my-region-1"
    assert expected_value == str(result)
    assert "XXXXXXXXXXXX" == result.aws_account
    assert "my-region-1" == result.aws_region