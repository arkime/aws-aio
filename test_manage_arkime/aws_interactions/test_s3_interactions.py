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
    test_env_use1 = AwsEnvironment("XXXXXXXXXXX", "us-east-1", "profile")

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_s3.return_value = mock_s3_client

    # TEST: Bucket doesn't exist and we create it
    mock_aws_provider.get_aws_env.return_value = test_env
    s3.create_bucket("bucket-name", mock_aws_provider)

    mock_aws_provider.get_aws_env.return_value = test_env_use1
    s3.create_bucket("bucket-name", mock_aws_provider)

    create_bucket_calls = [
        mock.call(        
            ACL="private",
            Bucket="bucket-name",
            CreateBucketConfiguration={
                "LocationConstraint": "my-region-1"
            },
            ObjectOwnership="BucketOwnerPreferred"
        ),
        mock.call(        
            ACL="private",
            Bucket="bucket-name",
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

@mock.patch("aws_interactions.s3_interactions.open")
def test_WHEN_put_file_to_bucket_called_THEN_as_expected(mock_open):
    # Set up our mock
    bucket_name = "my-bucket"
    s3_key = "the/s3/key.tgz"
    mock_s3_file = mock.Mock()
    mock_s3_file.local_path = "/the/path/file.tgz"
    mock_s3_file.metadata = {"key": "value"}

    mock_s3_client = mock.Mock()

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_s3.return_value = mock_s3_client

    mock_data = mock.Mock()
    mock_open.return_value.__enter__.return_value = mock_data

    # TEST: Everything goes right
    s3.put_file_to_bucket(mock_s3_file, bucket_name, s3_key, mock_aws_provider)
    assert [mock.call(mock_s3_file.local_path, "rb") == mock_open.call_args_list]
    
    expected_s3_put_calls = [
        mock.call(
            ACL="bucket-owner-full-control",
            Body=mock_data,
            Bucket=bucket_name,
            Key=s3_key,
            Metadata=mock_s3_file.metadata,
            ServerSideEncryption='aws:kms',
            StorageClass='STANDARD'            
        )
    ]
    assert expected_s3_put_calls == mock_s3_client.put_object.call_args_list

    # TEST: If no bucket access then raises
    mock_s3_client.put_object.side_effect = s3.BucketAccessDenied(bucket_name)
    with pytest.raises(s3.BucketAccessDenied):
        s3.put_file_to_bucket(mock_s3_file, bucket_name, s3_key, mock_aws_provider)

    # TEST: If the bucket doesn't exist then raises
    mock_s3_client.put_object.side_effect = s3.BucketDoesntExist(bucket_name)
    with pytest.raises(s3.BucketDoesntExist):
        s3.put_file_to_bucket(mock_s3_file, bucket_name, s3_key, mock_aws_provider)

def test_WHEN_list_bucket_objects_called_THEN_as_expected():
    # Set up our mock
    mock_s3_client = mock.Mock()
    mock_paginator = mock.Mock()
    mock_s3_client.get_paginator.return_value = mock_paginator

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_s3.return_value = mock_s3_client

    page_1 = {
        "Contents": [
            {"Key": "prefix/file1.txt", "LastModified": "2021-01-01T12:00:00"},
            {"Key": "prefix/file2.txt", "LastModified": "2021-01-02T12:00:00"}
        ]
    }
    page_2 = {
        "Contents": [
            {"Key": "prefix/file3.txt", "LastModified": "2021-01-03T12:00:00"}
        ]
    }
    mock_paginator.paginate.return_value = [page_1, page_2]

    # Run our test
    result = s3.list_bucket_objects("my-bucket", mock_aws_provider, prefix="prefix")

    # Check the results
    expected_result = [
        {"key": "prefix/file1.txt", "date_modified": "2021-01-01T12:00:00"},
        {"key": "prefix/file2.txt", "date_modified": "2021-01-02T12:00:00"},
        {"key": "prefix/file3.txt", "date_modified": "2021-01-03T12:00:00"},
    ]
    assert expected_result == result

    expected_paginate_calls = [
        mock.call(Bucket="my-bucket", Prefix="prefix")
    ]
    assert expected_paginate_calls == mock_paginator.paginate.call_args_list


def test_WHEN_get_object_user_metadata_called_THEN_as_expected():
    # Set up our mock
    mock_s3_client = mock.Mock()
    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_s3.return_value = mock_s3_client

    # TEST: Has metadata
    mock_metadata = {
        "Metadata": {
            "time_utc": "2023-09-22 16:05:28",
            "aws_aio_version": "1",
            "config_version": "1",
            "source_version": "v0.1.1-62-g8ac9e44",
            "md5_version": "1c42f3c8f3b70abe58afac52df89ba15"
        }
    }
    mock_s3_client.head_object.return_value = mock_metadata

    result = s3.get_object_user_metadata("my-bucket", "key", mock_aws_provider)

    assert mock_metadata["Metadata"] == result

    # TEST: Does not have metadata
    mock_metadata = {
        "SomethingElse": {
            "foo": "bar",
        }
    }
    mock_s3_client.head_object.return_value = mock_metadata

    result = s3.get_object_user_metadata("my-bucket", "key", mock_aws_provider)

    assert None == result

@mock.patch("aws_interactions.s3_interactions.os.path.exists")
@mock.patch("aws_interactions.s3_interactions.AwsClientProvider")
def test_WHEN_get_object_called_AND_file_exists_THEN_raises(mock_aws_provider, mock_exists):
    # Set up our mock
    mock_exists.side_effect = lambda path: True

    # Run our test
    with pytest.raises(s3.CantWriteFileAlreadyExists):
        s3.get_object("test_bucket", "test_key", "test_local_path", mock_aws_provider)

@mock.patch("aws_interactions.s3_interactions.os.path.dirname", mock.Mock())
@mock.patch("aws_interactions.s3_interactions.os.path.exists")
@mock.patch("aws_interactions.s3_interactions.AwsClientProvider")
def test_WHEN_get_object_called_AND_dir_doesnt_exist_THEN_raises(mock_aws_provider, mock_exists):
    # Set up our mock
    mock_exists.side_effect = [False, False]

    # Run our test
    with pytest.raises(s3.CantWriteFileDirDoesntExist):
        s3.get_object("test_bucket", "test_key", "test_local_path", mock_aws_provider)

@mock.patch("aws_interactions.s3_interactions.open")
@mock.patch("aws_interactions.s3_interactions.os.path.exists")
@mock.patch("aws_interactions.s3_interactions.AwsClientProvider")
def test_WHEN_get_object_called_AND_lack_perms_THEN_raises(mock_aws_provider, mock_exists, mock_open):
    # Set up our mock
    mock_exists.side_effect = [False, True]
    mock_open.side_effect = PermissionError

    # Run our test
    with pytest.raises(s3.CantWriteFileLackPermission):
        s3.get_object("test_bucket", "test_key", "test_local_path", mock_aws_provider)

@mock.patch("aws_interactions.s3_interactions.os.path.exists")
@mock.patch("aws_interactions.s3_interactions.open", new_callable=mock.mock_open)
@mock.patch("aws_interactions.s3_interactions.AwsClientProvider")
def test_WHEN_get_object_called_AND_happy_path_THEN_as_expected(mock_aws_provider, mock_open, mock_exists):
    # Set up our mock
    mock_exists.side_effect = [False, True]
    mock_s3_client = mock.Mock()
    mock_response = {
        'Body': mock.Mock(read=mock.Mock(return_value=b'test data')),
        'Metadata': {'key1': 'value1'}
    }
    mock_s3_client.get_object.return_value = mock_response
    mock_aws_provider.get_s3.return_value = mock_s3_client

    # Run our test
    result = s3.get_object("test_bucket", "test_key", "test_local_path", mock_aws_provider)

    # Check our results
    mock_open.assert_called_once_with("test_local_path", 'wb')
    handle = mock_open()
    handle.write.assert_called_once_with(b'test data')

    expected_result = s3.S3File(
        s3.PlainFile("test_local_path"),
        metadata={'key1': 'value1'}
    )
    assert expected_result == result