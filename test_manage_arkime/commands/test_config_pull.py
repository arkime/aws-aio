import json
import unittest.mock as mock

import arkime_interactions.config_wrangling as config_wrangling
import aws_interactions.s3_interactions as s3
import commands.config_pull as cp
import core.constants as constants


@mock.patch("commands.config_pull._get_previous_config")
@mock.patch("commands.config_pull._get_current_config")
@mock.patch("commands.config_pull.sys.exit")
def test_WHEN_cmd_config_pull_called_AND_dont_specify_which_THEN_exits(mock_exit, mock_get_current, mock_get_previous):
    # Run our test
    cp.cmd_config_pull("profile", "region", "MyCluster", False, False, False)

    # Check our results
    assert mock_exit.called_once_with(1)
    assert not mock_get_current.called
    assert not mock_get_previous.called

@mock.patch("commands.config_pull._get_previous_config")
@mock.patch("commands.config_pull._get_current_config")
@mock.patch("commands.config_pull.sys.exit")
def test_WHEN_cmd_config_pull_called_AND_specify_both_which_THEN_exits(mock_exit, mock_get_current, mock_get_previous):
    # Run our test
    cp.cmd_config_pull("profile", "region", "MyCluster", True, True, False)

    # Check our results
    assert mock_exit.called_once_with(1)
    assert not mock_get_current.called
    assert not mock_get_previous.called

@mock.patch("commands.config_pull._get_previous_config")
@mock.patch("commands.config_pull._get_current_config")
def test_WHEN_cmd_config_pull_called_AND_default_THEN_as_expected(mock_get_current, mock_get_previous):
    # Run our test
    cp.cmd_config_pull("profile", "region", "MyCluster", True, False, False)

    # Check our results
    expected_get_current_config_calls = [
        mock.call("MyCluster", True, False, mock.ANY)
    ]
    assert expected_get_current_config_calls == mock_get_current.call_args_list
    assert not mock_get_previous.called

@mock.patch("commands.config_pull._get_previous_config", mock.Mock())
@mock.patch("commands.config_pull._get_current_config")
@mock.patch("commands.config_pull.sys.exit")
def test_WHEN_cmd_config_pull_called_AND_exception_THEN_handles_gracefully(mock_exit, mock_get_current):
    # Set up our mock
    exception_list = [
        s3.CantWriteFileAlreadyExists(""),
        s3.CantWriteFileDirDoesntExist(""),
        s3.CantWriteFileLackPermission(""),
    ]
    mock_get_current.side_effect = exception_list

    # Run our test
    for _ in range(len(exception_list)):
        cp.cmd_config_pull("profile", "region", "MyCluster", True, False, False)

    # Check our results
    expected_calls = [mock.call(1) for _ in range(len(exception_list))]
    assert expected_calls == mock_exit.call_args_list

@mock.patch("commands.config_pull._get_previous_config")
@mock.patch("commands.config_pull._get_current_config")
def test_WHEN_cmd_config_pull_called_AND_previous_THEN_as_expected(mock_get_current, mock_get_previous):
    # Run our test
    cp.cmd_config_pull("profile", "region", "MyCluster", True, False, True)

    # Check our results
    assert not mock_get_current.called

    expected_get_previous_config_calls = [
        mock.call("MyCluster", True, False, mock.ANY)
    ]
    assert expected_get_previous_config_calls == mock_get_previous.call_args_list

@mock.patch("commands.config_pull.s3.get_object")
@mock.patch("commands.config_pull.ssm_ops.get_ssm_param_value")
def test_WHEN_get_current_config_called_AND_capture_THEN_as_expected(mock_get_val, mock_get_obj):
    # Set up our mock
    mock_aws_env = mock.Mock(aws_account = "XXXXXXXXXXXX", aws_region = "us-fake-1")
    mock_aws = mock.Mock()
    mock_aws.get_aws_env.return_value = mock_aws_env

    mock_get_val.return_value = '{"s3": {"bucket": "bucket-name","key": "capture/6/archive.zip"}, "version": {"aws_aio_version": "1","config_version": "6","md5_version": "3333","source_version": "v0.1.1","time_utc": "now"}, "previous": {"s3": {"bucket": "bucket-name","key": "capture/5/archive.zip"}, "version": {"aws_aio_version": "1","config_version": "5","md5_version": "2222","source_version": "v0.1.1","time_utc": "then"}, "previous": "None"}}'

    local_path = config_wrangling.get_capture_config_copy_path("MyCluster", mock_aws_env, "6")
    mock_s3_file = s3.S3File(
        s3.PlainFile(local_path),
        metadata = {
            "s3": {"bucket": "bucket-name", "key": "capture/6/archive.zip"},
            "version": {"aws_aio_version": "1","config_version": "6","md5_version": "3333","source_version": "v0.1.1","time_utc": "now"}
        }
    )
    mock_get_obj.return_value = mock_s3_file    

    # Run our test
    result = cp._get_current_config("MyCluster", True, False, mock_aws)

    # Check our results
    expected_value = local_path
    assert expected_value == result

    expected_s3_get_calls = [
        mock.call(
            "bucket-name",
            "capture/6/archive.zip",
            local_path,
            mock_aws
        )
    ]
    assert expected_s3_get_calls == mock_get_obj.call_args_list

    expected_get_ssm_calls = [
        mock.call(constants.get_capture_config_details_ssm_param_name("MyCluster"), mock_aws)
    ]
    assert expected_get_ssm_calls == mock_get_val.call_args_list

@mock.patch("commands.config_pull.s3.get_object")
@mock.patch("commands.config_pull.ssm_ops.get_ssm_param_value")
def test_WHEN_get_previous_config_called_AND_capture_THEN_as_expected(mock_get_val, mock_get_obj):
    # Set up our mock
    mock_aws_env = mock.Mock(aws_account = "XXXXXXXXXXXX", aws_region = "us-fake-1")
    mock_aws = mock.Mock()
    mock_aws.get_aws_env.return_value = mock_aws_env

    mock_get_val.return_value = '{"s3": {"bucket": "bucket-name","key": "capture/6/archive.zip"}, "version": {"aws_aio_version": "1","config_version": "6","md5_version": "3333","source_version": "v0.1.1","time_utc": "now"}, "previous": {"s3": {"bucket": "bucket-name","key": "capture/5/archive.zip"}, "version": {"aws_aio_version": "1","config_version": "5","md5_version": "2222","source_version": "v0.1.1","time_utc": "then"}, "previous": "None"}}'

    local_path = config_wrangling.get_capture_config_copy_path("MyCluster", mock_aws_env, "5")
    mock_s3_file = s3.S3File(
        s3.PlainFile(local_path),
        metadata = {
            "s3": {"bucket": "bucket-name", "key": "capture/5/archive.zip"},
            "version": {"aws_aio_version": "1","config_version": "5","md5_version": "2222","source_version": "v0.1.1","time_utc": "now"}
        }
    )
    mock_get_obj.return_value = mock_s3_file    

    # Run our test
    result = cp._get_previous_config("MyCluster", True, False, mock_aws)

    # Check our results
    expected_value = local_path
    assert expected_value == result

    expected_s3_get_calls = [
        mock.call(
            "bucket-name",
            "capture/5/archive.zip",
            local_path,
            mock_aws
        )
    ]
    assert expected_s3_get_calls == mock_get_obj.call_args_list

    expected_get_ssm_calls = [
        mock.call(constants.get_capture_config_details_ssm_param_name("MyCluster"), mock_aws)
    ]
    assert expected_get_ssm_calls == mock_get_val.call_args_list

