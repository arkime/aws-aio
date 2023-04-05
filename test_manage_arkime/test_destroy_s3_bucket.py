import unittest.mock as mock

from manage_arkime.aws_interactions.destroy_s3_bucket import destroy_s3_bucket

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
    destroy_s3_bucket("my-bucket", mock_aws_provider)

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
    destroy_s3_bucket("my-bucket", mock_aws_provider)

    # Check our results
    expected_bucket_call = [
        mock.call("my-bucket")
    ]
    assert expected_bucket_call == mock_s3_resource.Bucket.call_args_list

    assert not mock_objects_all.delete.called
    assert not mock_bucket.delete.called