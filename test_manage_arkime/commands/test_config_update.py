import json
import pytest
import shlex
import unittest.mock as mock

import arkime_interactions.config_wrangling as config_wrangling
from aws_interactions.aws_environment import AwsEnvironment
from aws_interactions.events_interactions import ConfigureIsmEvent
import aws_interactions.s3_interactions as s3
import aws_interactions.ssm_operations as ssm_ops

from commands.config_update import (cmd_config_update, _update_config_if_necessary)
import core.constants as constants
import core.local_file as local_file
from core.versioning import VersionInfo


@mock.patch("commands.config_update._update_config_if_necessary")
@mock.patch("commands.config_update.AwsClientProvider")
def test_WHEN_cmd_config_update_called_AND_happy_path_THEN_as_expected(mock_provider_cls, mock_update_config):
    # Set up our mock
    aws_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")
    cluster_name = "cluster_name"
    bucket_name = constants.get_config_bucket_name(aws_env.aws_account, aws_env.aws_region, cluster_name)

    mock_provider = mock.Mock()
    mock_provider.get_aws_env.return_value = aws_env
    mock_provider_cls.return_value = mock_provider

    # Run our test
    cmd_config_update("profile", "region", cluster_name)

    # Check our results
    expected_update_config_calls = [
        mock.call(            
            cluster_name,
            bucket_name,
            constants.get_capture_config_s3_key,
            constants.get_capture_config_details_ssm_param_name(cluster_name),
            config_wrangling.get_capture_config_archive,
            mock_provider

        ),
        mock.call(            
            cluster_name,
            bucket_name,
            constants.get_viewer_config_s3_key,
            constants.get_viewer_config_details_ssm_param_name(cluster_name),
            config_wrangling.get_viewer_config_archive,
            mock_provider
        ),
    ]
    assert expected_update_config_calls == mock_update_config.call_args_list


@mock.patch("commands.config_update.ssm_ops.put_ssm_param")
@mock.patch("commands.config_update.s3.put_file_to_bucket")
@mock.patch("commands.config_update.ssm_ops.get_ssm_param_value")
@mock.patch("commands.config_update.get_version_info")
def test_WHEN_update_config_if_necessary_called_AND_happy_path_THEN_as_expected(mock_get_version, mock_get_ssm_param,
                                                                                mock_put_file, mock_put_ssm_param):
    # Set up our mock
    bucket_name = "bucket_name"
    cluster_name = "cluster_name"
    md5_version = "22222222"
    s3_key = "s3_key"
    ssm_param = "ssm_param"

    mock_provider = mock.Mock()
    mock_s3_key_provider = mock.Mock()
    mock_s3_key_provider.return_value = s3_key

    mock_archive = mock.Mock()
    mock_archive_provider = mock.Mock()
    mock_archive_provider.return_value = mock_archive

    v1 = mock.Mock()
    v1.md5_version = md5_version
    v2 = VersionInfo("aws_aio", "2", md5_version, "source", "time")
    mock_get_version.side_effect = [v1, v2]

    current_config = '{"s3": {"bucket": "arkimeconfig-XXXXXXXXXXXX-us-east-2-mycluster3", "key": "capture/1/archive.zip"}, "version": {"aws_aio_version": "1", "config_version": "1", "md5_version": "11111111", "source_version": "v0.1.1-7-g9c2d7ca", "time_utc": "2023-07-24 17:04:24"}, "previous": "None"}'
    mock_get_ssm_param.return_value = current_config

    # Run our test
    _update_config_if_necessary(cluster_name, bucket_name, mock_s3_key_provider, ssm_param,
                                mock_archive_provider, mock_provider)

    # Check our results
    expected_get_version_info_calls = [
        mock.call(mock_archive),
        mock.call(mock_archive, config_version="2"),
    ]
    assert expected_get_version_info_calls == mock_get_version.call_args_list

    expected_get_ssm_param_calls = [
        mock.call(ssm_param, mock_provider),
    ]
    assert expected_get_ssm_param_calls == mock_get_ssm_param.call_args_list

    expected_put_file_calls = [
        mock.call(
            local_file.S3File(mock_archive, metadata=v2.to_dict()),
            bucket_name,
            s3_key,
            mock.ANY
        )
    ]
    assert expected_put_file_calls == mock_put_file.call_args_list

    expected_put_ssm_param_calls = [
        mock.call(
            ssm_param,
            json.dumps(
                config_wrangling.ConfigDetails(
                    s3=config_wrangling.S3Details(bucket_name, s3_key),
                    version=v2,
                    previous=config_wrangling.ConfigDetails.from_dict(json.loads(current_config))
                ).to_dict()
            ),
            mock.ANY,
            description=mock.ANY,
            overwrite=True,
        ),
    ]
    assert expected_put_ssm_param_calls == mock_put_ssm_param.call_args_list

@mock.patch("commands.config_update.ssm_ops.put_ssm_param")
@mock.patch("commands.config_update.s3.put_file_to_bucket")
@mock.patch("commands.config_update.ssm_ops.get_ssm_param_value")
@mock.patch("commands.config_update.get_version_info")
def test_WHEN_update_config_if_necessary_called_AND_same_config_THEN_as_expected(mock_get_version, mock_get_ssm_param,
                                                                                 mock_put_file, mock_put_ssm_param):
    # Set up our mock
    bucket_name = "bucket_name"
    cluster_name = "cluster_name"
    md5_version = "11111111"
    s3_key = "s3_key"
    ssm_param = "ssm_param"

    mock_provider = mock.Mock()
    mock_s3_key_provider = mock.Mock()
    mock_s3_key_provider.return_value = s3_key

    mock_archive = mock.Mock()
    mock_archive_provider = mock.Mock()
    mock_archive_provider.return_value = mock_archive

    v1 = mock.Mock()
    v1.md5_version = md5_version
    v2 = VersionInfo("aws_aio", "2", md5_version, "source", "time")
    mock_get_version.side_effect = [v1, v2]

    current_config = '{"s3": {"bucket": "arkimeconfig-XXXXXXXXXXXX-us-east-2-mycluster3", "key": "capture/1/archive.zip"}, "version": {"aws_aio_version": "1", "config_version": "1", "md5_version": "11111111", "source_version": "v0.1.1-7-g9c2d7ca", "time_utc": "2023-07-24 17:04:24"}, "previous": "None"}'
    mock_get_ssm_param.return_value = current_config

    # Run our test
    _update_config_if_necessary(cluster_name, bucket_name, mock_s3_key_provider, ssm_param,
                                mock_archive_provider, mock_provider)

    # Check our results
    expected_get_version_info_calls = [
        mock.call(mock_archive)
    ]
    assert expected_get_version_info_calls == mock_get_version.call_args_list

    expected_get_ssm_param_calls = [
        mock.call(ssm_param, mock_provider),
    ]
    assert expected_get_ssm_param_calls == mock_get_ssm_param.call_args_list

    expected_put_file_calls = []
    assert expected_put_file_calls == mock_put_file.call_args_list

    expected_put_ssm_param_calls = []
    assert expected_put_ssm_param_calls == mock_put_ssm_param.call_args_list

