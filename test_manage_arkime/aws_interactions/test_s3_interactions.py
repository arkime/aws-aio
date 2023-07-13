import pytest
import unittest.mock as mock

from botocore.exceptions import ClientError

from aws_interactions.aws_environment import AwsEnvironment
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

def test_WHEN_create_bucket_called_THEN_as_expected():
    # Set up our mock    
    mock_s3_client = mock.Mock()
    test_env = AwsEnvironment("XXXXXXXXXXX", "my-region-1", "profile")

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_s3.return_value = mock_s3_client
    mock_aws_provider.get_aws_env.return_value = test_env

    # TEST: Bucket doesn't exist and we create it
    s3.create_bucket("bucket-name", mock_aws_provider)
    create_bucket_calls = [
        mock.call(        
            ACL="private",
            Bucket="bucket-name",
            CreateBucketConfiguration={
                "LocationConstraint": "my-region-1"
            },
            ObjectOwnership="BucketOwnerPreferred"
        )
    ]
    assert create_bucket_calls == mock_s3_client.create_bucket.call_args_list

    # TEST: Bucket exists and we own it
    mock_s3_client.create_bucket.side_effect = ClientError(error_response={"Error": {"Message": "BucketAlreadyOwnedByYou"}}, operation_name="")
    s3.create_bucket("bucket-name", mock_aws_provider)
    assert True # The ClientError was swallowed

    # TEST: Bucket exists but we don't own it
    mock_s3_client.create_bucket.side_effect = ClientError(error_response={"Error": {"Message": "BucketAlreadyExists"}}, operation_name="")
    with pytest.raises(s3.BucketNameNotAvailable):
        s3.create_bucket("bucket-name", mock_aws_provider)

    # TEST: Some other, unexpected problem
    mock_s3_client.create_bucket.side_effect = ClientError(error_response={"Error": {"Message": "Other problem"}}, operation_name="")
    with pytest.raises(ClientError):
        s3.create_bucket("bucket-name", mock_aws_provider)

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
    s3.destroy_bucket("my-bucket", mock_aws_provider)

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
    s3.destroy_bucket("my-bucket", mock_aws_provider)

    # Check our results
    expected_bucket_call = [
        mock.call("my-bucket")
    ]
    assert expected_bucket_call == mock_s3_resource.Bucket.call_args_list

    assert not mock_objects_all.delete.called
    assert not mock_bucket.delete.called

@mock.patch("aws_interactions.s3_interactions.create_bucket")
@mock.patch("aws_interactions.s3_interactions.get_bucket_status")
def test_WHEN_ensure_bucket_exists_called_THEN_as_expected(mock_get_status, mock_create_bucket):
    # Set up our mock
    test_env = AwsEnvironment("XXXXXXXXXXX", "my-region-1", "profile")

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_aws_env.return_value = test_env

    # TEST: Bucket does not exists and it creates it
    mock_get_status.return_value = s3.BucketStatus.DOES_NOT_EXIST
    s3.ensure_bucket_exists("bucket-name", mock_aws_provider)
    expected_create_calls = [mock.call("bucket-name", mock_aws_provider)]
    assert expected_create_calls == mock_create_bucket.call_args_list

    # TEST: Bucket does not exists and then it's taken before we can create it
    mock_get_status.return_value = s3.BucketStatus.DOES_NOT_EXIST
    mock_create_bucket.side_effect = s3.BucketNameNotAvailable("bucket-name")
    with pytest.raises(s3.CouldntEnsureBucketExists):
        s3.ensure_bucket_exists("bucket-name", mock_aws_provider)

    # TEST: Bucket exists and we have access
    mock_get_status.return_value = s3.BucketStatus.EXISTS_HAVE_ACCESS
    s3.ensure_bucket_exists("bucket-name", mock_aws_provider)
    assert True # should just return

    # TEST: Bucket exists and we don't have access
    mock_get_status.return_value = s3.BucketStatus.EXISTS_NO_ACCESS
    with pytest.raises(s3.CouldntEnsureBucketExists):
        s3.ensure_bucket_exists("bucket-name", mock_aws_provider)

    # TEST: We have a new enum we're not covering
    mock_get_status.return_value = "blah"
    with pytest.raises(RuntimeError):
        s3.ensure_bucket_exists("bucket-name", mock_aws_provider)