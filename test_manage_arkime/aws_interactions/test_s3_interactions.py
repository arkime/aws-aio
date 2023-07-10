import pytest
import unittest.mock as mock

from botocore.exceptions import ClientError

import aws_interactions.s3_interactions as s3

def test_WHEN_get_bucket_status_called_THEN_as_expected():
    # Set up our mock    
    mock_s3_client = mock.Mock()

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_s3.return_value = mock_s3_client

    # TEST: Bucket exists and we have access to it
    mock_s3_client.head_bucket.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
    actual_value = s3.get_bucket_status("bucket-name", mock_aws_provider)
    assert actual_value == s3.BucketStatus.EXISTS_HAVE_ACCESS

    # TEST: Bucket exists but we don't have access to it
    mock_s3_client.head_bucket.side_effect = ClientError(error_response={"Error": {"Code": "403", "Message": "Forbidden"}}, operation_name="")
    actual_value = s3.get_bucket_status("bucket-name", mock_aws_provider)
    assert actual_value == s3.BucketStatus.EXISTS_NO_ACCESS

    # TEST: Bucket does not exist
    mock_s3_client.head_bucket.side_effect = ClientError(error_response={"Error": {"Code": "404", "Message": "Not found"}}, operation_name="")
    actual_value = s3.get_bucket_status("bucket-name", mock_aws_provider)
    assert actual_value == s3.BucketStatus.DOES_NOT_EXIST

    # TEST: Unexpected error
    mock_s3_client.head_bucket.side_effect = ClientError(error_response={"Error": {"Code": "500", "Message": "Oops"}}, operation_name="")
    with pytest.raises(ClientError):
        actual_value = s3.get_bucket_status("bucket-name", mock_aws_provider)

def test_WHEN_destroy_s3_bucket_called_AND_exists_THEN_destroys_it():
    # Set up our mock
    mock_objects_all = mock.Mock()

    mock_objects = mock.Mock()
    mock_objects.all.return_value = mock_objects_all

    mock_bucket = mock.Mock()
    mock_bucket.creation_date = "recently"
    mock_bucket.objects = mock_objects
    
    mock_s3_resource = mock.Mock()
    mock_s3_resource.Bucket.return_value = mock_bucket

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_s3_resource.return_value = mock_s3_resource    

    # Run our test
    s3.destroy_s3_bucket("my-bucket", mock_aws_provider)

    # Check our results
    expected_bucket_call = [
        mock.call("my-bucket")
    ]
    assert expected_bucket_call == mock_s3_resource.Bucket.call_args_list

    assert 1 == mock_objects_all.delete.call_count
    assert 1 == mock_bucket.delete.call_count

def test_WHEN_destroy_s3_bucket_called_AND_doesnt_exist_THEN_skips_destruction():
    # Set up our mock
    mock_objects_all = mock.Mock()

    mock_objects = mock.Mock()
    mock_objects.all.return_value = mock_objects_all

    mock_bucket = mock.Mock()
    mock_bucket.creation_date = None
    mock_bucket.objects = mock_objects
    
    mock_s3_resource = mock.Mock()
    mock_s3_resource.Bucket.return_value = mock_bucket

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_s3_resource.return_value = mock_s3_resource    

    # Run our test
    s3.destroy_s3_bucket("my-bucket", mock_aws_provider)

    # Check our results
    expected_bucket_call = [
        mock.call("my-bucket")
    ]
    assert expected_bucket_call == mock_s3_resource.Bucket.call_args_list

    assert not mock_objects_all.delete.called
    assert not mock_bucket.delete.called