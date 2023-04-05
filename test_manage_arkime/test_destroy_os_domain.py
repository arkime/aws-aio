import unittest.mock as mock

from botocore.exceptions import ClientError

from manage_arkime.aws_interactions.destroy_os_domain import destroy_os_domain_and_wait

@mock.patch("manage_arkime.aws_interactions.destroy_os_domain.time")
def test_WHEN_destroy_os_domain_and_wait_called_AND_exists_THEN_destroys_it(mock_time):
    # Set up our mock
    mock_os_client = mock.Mock()
    mock_os_client.describe_domain.side_effect = [
        {}, # Initial check
        {}, # Wait once
        {}, # Wait twice
        ClientError(error_response={"Error": {"Code": "ResourceNotFoundException"}}, operation_name="") # Destroyed
    ]

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_opensearch.return_value = mock_os_client    

    # Run our test
    destroy_os_domain_and_wait("my-domain", mock_aws_provider)

    # Check our results
    expected_delete_calls = [
        mock.call(DomainName="my-domain")
    ]
    assert expected_delete_calls == mock_os_client.delete_domain.call_args_list
    assert 3 == mock_time.sleep.call_count

@mock.patch("manage_arkime.aws_interactions.destroy_os_domain.time")
def test_WHEN_destroy_os_domain_and_wait_called_AND_doesnt_exist_THEN_skips_destruction(mock_time):
    # Set up our mock
    mock_os_client = mock.Mock()
    mock_os_client.describe_domain.side_effect = [
        ClientError(error_response={"Error": {"Code": "ResourceNotFoundException"}}, operation_name="") # Already gone
    ]

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_opensearch.return_value = mock_os_client    

    # Run our test
    destroy_os_domain_and_wait("my-domain", mock_aws_provider)

    # Check our results
    assert not mock_os_client.delete_domain.called
    assert not mock_time.sleep.called