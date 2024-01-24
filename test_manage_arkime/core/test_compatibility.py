import py
import pytest
import unittest.mock as mock

import aws_interactions.ssm_operations as ssm_ops
import core.compatibility as compat


@mock.patch("commands.config_list.ssm_ops.get_ssm_param_value")
def test_WHEN_confirm_aws_aio_version_compatibility_called_AND_compatible_THEN_no_op(mock_get_val):
    # Set up our mock
    mock_aws = mock.Mock()
    mock_get_val.side_effect = [
        '{"s3": {"bucket": "bucket-name","key": "capture/6/archive.zip"}, "version": {"aws_aio_version": "1","config_version": "6","md5_version": "3333","source_version": "v1.0.0","time_utc": "now"}, "previous": "None"}',
        '{"s3": {"bucket": "bucket-name","key": "viewer/6/archive.zip"}, "version": {"aws_aio_version": "1","config_version": "6","md5_version": "3333","source_version": "v1.0.0","time_utc": "now"}, "previous": "None"}',
    ]

    # Run our test
    compat.confirm_aws_aio_version_compatibility("MyCluster", mock_aws, cli_version=1)

@mock.patch("commands.config_list.ssm_ops.get_ssm_param_value")
def test_WHEN_confirm_aws_aio_version_compatibility_called_AND_cant_get_versions_THEN_raises(mock_get_val):
    # Set up our mock
    mock_aws = mock.Mock()
    mock_get_val.side_effect = ssm_ops.ParamDoesNotExist("")

    # Run our test
    with pytest.raises(compat.UnableToRetrieveClusterVersion):
        compat.confirm_aws_aio_version_compatibility("MyCluster", mock_aws, cli_version=1)

@mock.patch("commands.config_list.ssm_ops.get_ssm_param_value")
def test_WHEN_confirm_aws_aio_version_compatibility_called_AND_comp_mismatch_THEN_raises(mock_get_val):
    # Set up our mock
    mock_aws = mock.Mock()
    mock_get_val.side_effect = [
        '{"s3": {"bucket": "bucket-name","key": "capture/6/archive.zip"}, "version": {"aws_aio_version": "2","config_version": "6","md5_version": "3333","source_version": "v1.0.0","time_utc": "now"}, "previous": "None"}',
        '{"s3": {"bucket": "bucket-name","key": "viewer/6/archive.zip"}, "version": {"aws_aio_version": "1","config_version": "6","md5_version": "3333","source_version": "v1.0.0","time_utc": "now"}, "previous": "None"}',
    ]

    # Run our test
    with pytest.raises(compat.CaptureViewerVersionMismatch):
        compat.confirm_aws_aio_version_compatibility("MyCluster", mock_aws, cli_version=1)

@mock.patch("commands.config_list.ssm_ops.get_ssm_param_value")
def test_WHEN_confirm_aws_aio_version_compatibility_called_AND_cli_mismatch_THEN_raises(mock_get_val):
    # Set up our mock
    mock_aws = mock.Mock()
    mock_get_val.side_effect = [
        '{"s3": {"bucket": "bucket-name","key": "capture/6/archive.zip"}, "version": {"aws_aio_version": "1","config_version": "6","md5_version": "3333","source_version": "v1.0.0","time_utc": "now"}, "previous": "None"}',
        '{"s3": {"bucket": "bucket-name","key": "viewer/6/archive.zip"}, "version": {"aws_aio_version": "1","config_version": "6","md5_version": "3333","source_version": "v1.0.0","time_utc": "now"}, "previous": "None"}',
    ]

    # Run our test
    with pytest.raises(compat.CliClusterVersionMismatch):
        compat.confirm_aws_aio_version_compatibility("MyCluster", mock_aws, cli_version=2)