import json
import unittest.mock as mock

import commands.config_list as cl
import core.constants as constants


@mock.patch("commands.config_list._get_all_configs")
@mock.patch("commands.config_list._get_deployed_config")
@mock.patch("commands.config_list.sys.exit")
def test_WHEN_cmd_config_list_called_AND_dont_specify_which_THEN_exits(mock_exit, mock_get_deployed, mock_get_all):
    # Run our test
    cl.cmd_config_list("profile", "region", "MyCluster", False, False, False)

    # Check our results
    assert mock_exit.called_once_with(1)
    assert not mock_get_deployed.called
    assert not mock_get_all.called

@mock.patch("commands.config_list._get_all_configs")
@mock.patch("commands.config_list._get_deployed_config")
@mock.patch("commands.config_list.sys.exit")
def test_WHEN_cmd_config_list_called_AND_specify_both_which_THEN_exits(mock_exit, mock_get_deployed, mock_get_all):
    # Run our test
    cl.cmd_config_list("profile", "region", "MyCluster", True, True, False)

    # Check our results
    assert mock_exit.called_once_with(1)
    assert not mock_get_deployed.called
    assert not mock_get_all.called

@mock.patch("commands.config_list._get_all_configs")
@mock.patch("commands.config_list._get_deployed_config")
def test_WHEN_cmd_config_list_called_AND_default_THEN_as_expected(mock_get_deployed, mock_get_all):
    # Run our test
    cl.cmd_config_list("profile", "region", "MyCluster", True, False, False)

    # Check our results
    expected_get_deployed_calls = []
    assert expected_get_deployed_calls == mock_get_deployed.call_args_list

    expected_get_all_calls = [
        mock.call("MyCluster", True, False, mock.ANY)
    ]
    assert expected_get_all_calls == mock_get_all.call_args_list

@mock.patch("commands.config_list._get_all_configs")
@mock.patch("commands.config_list._get_deployed_config")
def test_WHEN_cmd_config_list_called_AND_deployed_flag_THEN_as_expected(mock_get_deployed, mock_get_all):
    # Run our test
    cl.cmd_config_list("profile", "region", "MyCluster", True, False, True)

    # Check our results
    expected_get_deployed_calls = [
        mock.call("MyCluster", True, False, mock.ANY)
    ]
    assert expected_get_deployed_calls == mock_get_deployed.call_args_list

    expected_get_all_calls = []
    assert expected_get_all_calls == mock_get_all.call_args_list

@mock.patch("commands.config_list.ssm_ops.get_ssm_param_value")
def test_WHEN_get_deployed_config_called_AND_capture_THEN_as_expected(mock_get_val):
    # Set up our mock
    mock_aws = mock.Mock()

    mock_get_val.return_value = '{"s3": {"bucket": "bucket-name","key": "capture/6/archive.zip"}, "version": {"aws_aio_version": "1","config_version": "6","md5_version": "3333","source_version": "v0.1.1","time_utc": "now"}, "previous": {"s3": {"bucket": "bucket-name","key": "capture/5/archive.zip"}, "version": {"aws_aio_version": "1","config_version": "5","md5_version": "2222","source_version": "v0.1.1","time_utc": "then"}, "previous": "None"}}'

    # Run our test
    result = cl._get_deployed_config("MyCluster", True, False, mock_aws)

    # Check our results
    expected_result_dict = {
        "current": {
            "s3": {"bucket": "bucket-name","key": "capture/6/archive.zip"},
            "version": {"aws_aio_version": "1","config_version": "6","md5_version": "3333","source_version": "v0.1.1","time_utc": "now"}
        },
        "previous": {
            "s3": {"bucket": "bucket-name","key": "capture/5/archive.zip"},
            "version": {"aws_aio_version": "1","config_version": "5","md5_version": "2222","source_version": "v0.1.1","time_utc": "then"}
        }
    }
    expected_result = json.dumps(expected_result_dict, indent=4)
    assert expected_result == result

    expected_get_ssm_calls = [
        mock.call(constants.get_capture_config_details_ssm_param_name("MyCluster"), mock_aws)
    ]
    assert expected_get_ssm_calls == mock_get_val.call_args_list

@mock.patch("commands.config_list.ssm_ops.get_ssm_param_value")
def test_WHEN_get_deployed_config_called_AND_viewer_THEN_as_expected(mock_get_val):
    # Set up our mock
    mock_aws = mock.Mock()

    mock_get_val.return_value = '{"s3": {"bucket": "bucket-name","key": "viewer/6/archive.zip"}, "version": {"aws_aio_version": "1","config_version": "6","md5_version": "3333","source_version": "v0.1.1","time_utc": "now"}, "previous": {"s3": {"bucket": "bucket-name","key": "viewer/5/archive.zip"}, "version": {"aws_aio_version": "1","config_version": "5","md5_version": "2222","source_version": "v0.1.1","time_utc": "then"}, "previous": "None"}}'

    # Run our test
    result = cl._get_deployed_config("MyCluster", False, True, mock_aws)

    # Check our results
    expected_result_dict = {
        "current": {
            "s3": {"bucket": "bucket-name","key": "viewer/6/archive.zip"},
            "version": {"aws_aio_version": "1","config_version": "6","md5_version": "3333","source_version": "v0.1.1","time_utc": "now"}
        },
        "previous": {
            "s3": {"bucket": "bucket-name","key": "viewer/5/archive.zip"},
            "version": {"aws_aio_version": "1","config_version": "5","md5_version": "2222","source_version": "v0.1.1","time_utc": "then"}
        }
    }
    expected_result = json.dumps(expected_result_dict, indent=4)
    assert expected_result == result

    expected_get_ssm_calls = [
        mock.call(constants.get_viewer_config_details_ssm_param_name("MyCluster"), mock_aws)
    ]
    assert expected_get_ssm_calls == mock_get_val.call_args_list

@mock.patch("commands.config_list.ssm_ops.get_ssm_param_value")
def test_WHEN_get_deployed_config_called_AND_no_previous_THEN_as_expected(mock_get_val):
    # Set up our mock
    mock_aws = mock.Mock()

    mock_get_val.return_value = '{"s3": {"bucket": "bucket-name","key": "capture/6/archive.zip"}, "version": {"aws_aio_version": "1","config_version": "6","md5_version": "3333","source_version": "v0.1.1","time_utc": "now"}, "previous": "None"}'

    # Run our test
    result = cl._get_deployed_config("MyCluster", True, False, mock_aws)

    # Check our results
    expected_result_dict = {
        "current": {
            "s3": {"bucket": "bucket-name","key": "capture/6/archive.zip"},
            "version": {"aws_aio_version": "1","config_version": "6","md5_version": "3333","source_version": "v0.1.1","time_utc": "now"}
        },
        "previous": "None"
    }
    expected_result = json.dumps(expected_result_dict, indent=4)
    assert expected_result == result


@mock.patch("commands.config_list.s3.get_object_user_metadata")
@mock.patch("commands.config_list.s3.list_bucket_objects")
def test_WHEN_get_all_configs_called_THEN_as_expected(mock_list_objects, mock_get_metadata):
    # Set up our mock
    mock_aws_env = mock.Mock()
    mock_aws_env.aws_account = "XXXXXXXXXXXX"
    mock_aws_env.aws_region = "us-fake-1"
    mock_aws = mock.Mock()
    mock_aws.get_aws_env.return_value = mock_aws_env

    mock_objects_list = [
        {"key": "capture/1/archive.zip", "date_modified": "2021-01-01T12:00:00"},
        {"key": "capture/2/archive.zip", "date_modified": "2021-01-02T12:00:00"},
        {"key": "capture/3/archive.zip", "date_modified": "2021-01-03T12:00:00"},
    ]
    mock_list_objects.return_value = mock_objects_list

    mock_metadata = [
        {"aws_aio_version": "1", "config_version": "3", "md5_version": "3333", "source_version": "v0.1.1", "time_utc": "2021-01-03T12:00:00"},
        {"aws_aio_version": "1", "config_version": "2", "md5_version": "2222", "source_version": "v0.1.1", "time_utc": "2021-01-02T12:00:00"},
        {"aws_aio_version": "1", "config_version": "1", "md5_version": "1111", "source_version": "v0.1.1", "time_utc": "2021-01-01T12:00:00"},
    ]
    mock_get_metadata.side_effect = mock_metadata

    # Run our test
    result = cl._get_all_configs("MyCluster", True, False, mock_aws)

    # Check our results
    expected_result_dict = [
        {
            "s3": {"bucket": constants.get_config_bucket_name("XXXXXXXXXXXX", "us-fake-1", "MyCluster"), "key": "capture/3/archive.zip"},
            "version": {"aws_aio_version": "1", "config_version": "3", "md5_version": "3333", "source_version": "v0.1.1", "time_utc": "2021-01-03T12:00:00"}
        },
        {
            "s3": {"bucket": constants.get_config_bucket_name("XXXXXXXXXXXX", "us-fake-1", "MyCluster"), "key": "capture/2/archive.zip"},
            "version": {"aws_aio_version": "1", "config_version": "2", "md5_version": "2222", "source_version": "v0.1.1", "time_utc": "2021-01-02T12:00:00"}
        },
        {
            "s3": {"bucket": constants.get_config_bucket_name("XXXXXXXXXXXX", "us-fake-1", "MyCluster"), "key": "capture/1/archive.zip"},
            "version": {"aws_aio_version": "1", "config_version": "1", "md5_version": "1111", "source_version": "v0.1.1", "time_utc": "2021-01-01T12:00:00"}
        },
    ]
    expected_result = json.dumps(expected_result_dict, indent=4)
    assert expected_result == result