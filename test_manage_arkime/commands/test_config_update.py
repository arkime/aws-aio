import json
import pytest
import unittest.mock as mock

import arkime_interactions.config_wrangling as config_wrangling
from aws_interactions.aws_environment import AwsEnvironment
from aws_interactions.events_interactions import ConfigureIsmEvent
import aws_interactions.s3_interactions as s3
import aws_interactions.ssm_operations as ssm_ops
from commands.config_update import (cmd_config_update, _update_config_if_necessary, _revert_arkime_config, 
                                    NoPreviousConfig, _bounce_ecs_service)
import core.constants as constants
import core.local_file as local_file
from core.versioning import VersionInfo, CliClusterVersionMismatch


@mock.patch("commands.cluster_register_vpc.ver.confirm_aws_aio_version_compatibility", mock.Mock())
@mock.patch("commands.config_update._bounce_ecs_service")
@mock.patch("commands.config_update.ssm_ops.get_ssm_param_value")
@mock.patch("commands.config_update._update_config_if_necessary")
@mock.patch("commands.config_update.AwsClientProvider")
def test_WHEN_cmd_config_update_called_AND_happy_path_THEN_as_expected(mock_provider_cls, mock_update_config,
                                                                       mock_get_param, mock_bounce):
    # Set up our mock
    aws_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")
    cluster_name = "cluster_name"
    bucket_name = constants.get_config_bucket_name(aws_env.aws_account, aws_env.aws_region, cluster_name)

    mock_provider = mock.Mock()
    mock_provider.get_aws_env.return_value = aws_env
    mock_provider_cls.return_value = mock_provider

    mock_update_config.side_effect = [True, True]
    mock_get_param.side_effect = [
        '{"ecsCluster": "cluster-name-cap", "ecsService": "service-name-cap"}',
        '{"dns": "dns-v", "ecsCluster": "cluster-name-v", "ecsService": "service-name-v", "passwordArn": "pass-arn", "user": "user-v"}',
    ]    

    # Run our test
    cmd_config_update("profile", "region", cluster_name, False, False, False, None)

    # Check our results
    expected_update_config_calls = [
        mock.call(
            cluster_name,
            bucket_name,
            constants.get_capture_config_s3_key,
            constants.get_capture_config_details_ssm_param_name(cluster_name),
            config_wrangling.get_capture_config_archive,
            None,
            mock_provider

        ),
        mock.call(
            cluster_name,
            bucket_name,
            constants.get_viewer_config_s3_key,
            constants.get_viewer_config_details_ssm_param_name(cluster_name),
            config_wrangling.get_viewer_config_archive,
            None,
            mock_provider
        ),
    ]
    assert expected_update_config_calls == mock_update_config.call_args_list

    expected_get_param_calls = [
        mock.call(
            constants.get_capture_details_ssm_param_name(cluster_name),
            mock_provider

        ),
        mock.call(
            constants.get_viewer_details_ssm_param_name(cluster_name),
            mock_provider
        ),
    ]
    assert expected_get_param_calls == mock_get_param.call_args_list

    expected_bounce_calls = [
        mock.call(
            "cluster-name-cap",
            "service-name-cap",
            constants.get_capture_config_details_ssm_param_name(cluster_name),
            mock_provider
        ),
        mock.call(
            "cluster-name-v",
            "service-name-v",
            constants.get_viewer_config_details_ssm_param_name(cluster_name),
            mock_provider
        ),
    ]
    assert expected_bounce_calls == mock_bounce.call_args_list

@mock.patch("commands.cluster_register_vpc.ver.confirm_aws_aio_version_compatibility", mock.Mock())
@mock.patch("commands.config_update._bounce_ecs_service")
@mock.patch("commands.config_update.ssm_ops.get_ssm_param_value")
@mock.patch("commands.config_update._update_config_if_necessary")
@mock.patch("commands.config_update.AwsClientProvider")
def test_WHEN_cmd_config_update_called_AND_shouldnt_bounce_THEN_as_expected(mock_provider_cls, mock_update_config,
                                                                       mock_get_param, mock_bounce):
    # Set up our mock
    aws_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")
    cluster_name = "cluster_name"
    bucket_name = constants.get_config_bucket_name(aws_env.aws_account, aws_env.aws_region, cluster_name)

    mock_provider = mock.Mock()
    mock_provider.get_aws_env.return_value = aws_env
    mock_provider_cls.return_value = mock_provider

    mock_update_config.side_effect = [False, False]

    # Run our test
    cmd_config_update("profile", "region", cluster_name, False, False, False, None)

    # Check our results
    expected_update_config_calls = [
        mock.call(
            cluster_name,
            bucket_name,
            constants.get_capture_config_s3_key,
            constants.get_capture_config_details_ssm_param_name(cluster_name),
            config_wrangling.get_capture_config_archive,
            None,
            mock_provider

        ),
        mock.call(
            cluster_name,
            bucket_name,
            constants.get_viewer_config_s3_key,
            constants.get_viewer_config_details_ssm_param_name(cluster_name),
            config_wrangling.get_viewer_config_archive,
            None,
            mock_provider
        ),
    ]
    assert expected_update_config_calls == mock_update_config.call_args_list

    expected_get_param_calls = []
    assert expected_get_param_calls == mock_get_param.call_args_list

    expected_bounce_calls = []
    assert expected_bounce_calls == mock_bounce.call_args_list

@mock.patch("commands.cluster_register_vpc.ver.confirm_aws_aio_version_compatibility", mock.Mock())
@mock.patch("commands.config_update._bounce_ecs_service")
@mock.patch("commands.config_update.ssm_ops.get_ssm_param_value")
@mock.patch("commands.config_update._update_config_if_necessary")
@mock.patch("commands.config_update.AwsClientProvider")
def test_WHEN_cmd_config_update_called_AND_force_bounce_THEN_as_expected(mock_provider_cls, mock_update_config,
                                                                       mock_get_param, mock_bounce):
    # Set up our mock
    aws_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")
    cluster_name = "cluster_name"
    bucket_name = constants.get_config_bucket_name(aws_env.aws_account, aws_env.aws_region, cluster_name)

    mock_provider = mock.Mock()
    mock_provider.get_aws_env.return_value = aws_env
    mock_provider_cls.return_value = mock_provider

    mock_update_config.side_effect = [False, False]
    mock_get_param.side_effect = [
        '{"ecsCluster": "cluster-name-cap", "ecsService": "service-name-cap"}',
        '{"dns": "dns-v", "ecsCluster": "cluster-name-v", "ecsService": "service-name-v", "passwordArn": "pass-arn", "user": "user-v"}',
    ]

    # Run our test
    cmd_config_update("profile", "region", cluster_name, False, False, True, None)

    # Check our results
    expected_update_config_calls = [
        mock.call(
            cluster_name,
            bucket_name,
            constants.get_capture_config_s3_key,
            constants.get_capture_config_details_ssm_param_name(cluster_name),
            config_wrangling.get_capture_config_archive,
            None,
            mock_provider

        ),
        mock.call(
            cluster_name,
            bucket_name,
            constants.get_viewer_config_s3_key,
            constants.get_viewer_config_details_ssm_param_name(cluster_name),
            config_wrangling.get_viewer_config_archive,
            None,
            mock_provider
        ),
    ]
    assert expected_update_config_calls == mock_update_config.call_args_list

    expected_get_param_calls = [
        mock.call(
            constants.get_capture_details_ssm_param_name(cluster_name),
            mock_provider

        ),
        mock.call(
            constants.get_viewer_details_ssm_param_name(cluster_name),
            mock_provider
        ),
    ]
    assert expected_get_param_calls == mock_get_param.call_args_list

    expected_bounce_calls = [
        mock.call(
            "cluster-name-cap",
            "service-name-cap",
            constants.get_capture_config_details_ssm_param_name(cluster_name),
            mock_provider
        ),
        mock.call(
            "cluster-name-v",
            "service-name-v",
            constants.get_viewer_config_details_ssm_param_name(cluster_name),
            mock_provider
        ),
    ]
    assert expected_bounce_calls == mock_bounce.call_args_list


class ExpectedExit(Exception):
    pass

@mock.patch("commands.cluster_register_vpc.ver.confirm_aws_aio_version_compatibility", mock.Mock())
@mock.patch("commands.config_update.exit")
@mock.patch("commands.config_update._bounce_ecs_service")
@mock.patch("commands.config_update.ssm_ops.get_ssm_param_value")
@mock.patch("commands.config_update._update_config_if_necessary")
@mock.patch("commands.config_update.AwsClientProvider")
def test_WHEN_cmd_config_update_called_AND_config_ver_no_component_THEN_as_expected(
        mock_provider_cls, mock_update_config, mock_get_param, mock_bounce, mock_exit):
    # Set up our mock
    mock_exit.side_effect = ExpectedExit()

    # Run our test
    with pytest.raises(ExpectedExit):
        cmd_config_update("profile", "region", "MyCluster", False, False, False, 3)

    # Check our results
    mock_exit.assert_called_with(1)

    expected_update_config_calls = []
    assert expected_update_config_calls == mock_update_config.call_args_list

    expected_get_param_calls = []
    assert expected_get_param_calls == mock_get_param.call_args_list

    expected_bounce_calls = []
    assert expected_bounce_calls == mock_bounce.call_args_list


@mock.patch("commands.config_update.AwsClientProvider", mock.Mock())
@mock.patch("commands.cluster_register_vpc.ver.confirm_aws_aio_version_compatibility")
@mock.patch("commands.config_update.exit")
@mock.patch("commands.config_update._bounce_ecs_service")
@mock.patch("commands.config_update.ssm_ops.get_ssm_param_value")
@mock.patch("commands.config_update._update_config_if_necessary")
def test_WHEN_cmd_config_update_called_AND_cli_version_THEN_as_expected(mock_update_config, mock_get_param, mock_bounce, 
                                                                        mock_exit, mock_confirm_ver):
    # Set up our mock
    mock_confirm_ver.side_effect = CliClusterVersionMismatch(2, 1)

    # Run our test
    cmd_config_update("profile", "region", "MyCluster", True, False, False, 3)

    # Check our results
    expected_update_config_calls = []
    assert expected_update_config_calls == mock_update_config.call_args_list

    expected_get_param_calls = []
    assert expected_get_param_calls == mock_get_param.call_args_list

    expected_bounce_calls = []
    assert expected_bounce_calls == mock_bounce.call_args_list

@mock.patch("commands.config_update.ssm_ops.put_ssm_param")
@mock.patch("commands.config_update.ssm_ops.get_ssm_param_value")
def test_WHEN_revert_arkime_config_called_AND_happy_path_THEN_as_expected(mock_get_ssm_param, mock_put_ssm_param):
    # Set up our mock
    ssm_param = "ssm_param"

    mock_provider = mock.Mock()

    in_progress_config = '{"s3": {"bucket": "bucket-name","key": "v3/archive.zip"},"version": {"aws_aio_version": "1","config_version": "3","md5_version": "3333","source_version": "v1","time_utc": "now"},"previous": {"s3": {"bucket": "bucket-name","key": "v2/archive.zip"},"version": {"aws_aio_version": "1","config_version": "2","md5_version": "2222","source_version": "v1","time_utc": "yesterday"},"previous": "None"}}'
    mock_get_ssm_param.return_value = in_progress_config

    # Run our test
    _revert_arkime_config(ssm_param, mock_provider)

    # Check our results
    expected_get_ssm_param_calls = [
        mock.call(ssm_param, mock_provider),
    ]
    assert expected_get_ssm_param_calls == mock_get_ssm_param.call_args_list

    expected_put_ssm_param_calls = [
        mock.call(
            ssm_param,
            json.dumps(
                config_wrangling.ConfigDetails(
                    s3=config_wrangling.S3Details("bucket-name", "v2/archive.zip"),
                    version=VersionInfo("1", "2", "2222", "v1", "yesterday"),
                    previous=None
                ).to_dict()
            ),
            mock.ANY,
            description=mock.ANY,
            overwrite=True,
        ),
    ]
    assert expected_put_ssm_param_calls == mock_put_ssm_param.call_args_list

@mock.patch("commands.config_update.ssm_ops.put_ssm_param")
@mock.patch("commands.config_update.ssm_ops.get_ssm_param_value")
def test_WHEN_revert_arkime_config_called_AND_no_previous_THEN_as_expected(mock_get_ssm_param, mock_put_ssm_param):
    # Set up our mock
    ssm_param = "ssm_param"

    mock_provider = mock.Mock()

    in_progress_config = '{"s3": {"bucket": "bucket-name","key": "v3/archive.zip"},"version": {"aws_aio_version": "1","config_version": "3","md5_version": "3333","source_version": "v1","time_utc": "now"},"previous": "None"}'
    mock_get_ssm_param.return_value = in_progress_config

    # Run our test
    with pytest.raises(NoPreviousConfig):
        _revert_arkime_config(ssm_param, mock_provider)

    # Check our results
    expected_get_ssm_param_calls = [
        mock.call(ssm_param, mock_provider),
    ]
    assert expected_get_ssm_param_calls == mock_get_ssm_param.call_args_list

    expected_put_ssm_param_calls = []
    assert expected_put_ssm_param_calls == mock_put_ssm_param.call_args_list

@mock.patch("commands.config_update.ssm_ops.put_ssm_param")
@mock.patch("commands.config_update.s3.put_file_to_bucket")
@mock.patch("commands.config_update.ssm_ops.get_ssm_param_value")
@mock.patch("commands.config_update.ver.get_version_info")
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
    actual_value = _update_config_if_necessary(cluster_name, bucket_name, mock_s3_key_provider, ssm_param,
                                mock_archive_provider, None, mock_provider)

    # Check our results
    assert True == actual_value

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
@mock.patch("commands.config_update.ver.get_version_info")
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
    actual_value = _update_config_if_necessary(cluster_name, bucket_name, mock_s3_key_provider, ssm_param,
                                mock_archive_provider, None, mock_provider)

    # Check our results
    assert False == actual_value

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

@mock.patch("commands.config_update.s3.get_object_user_metadata")
@mock.patch("commands.config_update.ssm_ops.put_ssm_param")
@mock.patch("commands.config_update.s3.put_file_to_bucket")
@mock.patch("commands.config_update.ssm_ops.get_ssm_param_value")
@mock.patch("commands.config_update.ver.get_version_info")
def test_WHEN_update_config_if_necessary_called_AND_switch_to_version_THEN_as_expected(
        mock_get_version, mock_get_ssm_param, mock_put_file, mock_put_ssm_param, mock_get_metadata):
    # Set up our mock
    bucket_name = "bucket_name"
    cluster_name = "cluster_name"
    s3_key = "s3_key"
    ssm_param = "ssm_param"

    mock_provider = mock.Mock()
    mock_s3_key_provider = mock.Mock()
    mock_s3_key_provider.return_value = s3_key

    mock_archive = mock.Mock()
    mock_archive_provider = mock.Mock()
    mock_archive_provider.return_value = mock_archive

    v1 = mock.Mock(md5_version = "5555") # the "local" config version
    mock_get_version.return_value = v1

    current_config = '{"s3": {"bucket": "arkimeconfig-XXXXXXXXXXXX-us-east-2-mycluster3", "key": "capture/4/archive.zip"}, "version": {"aws_aio_version": "1", "config_version": "4", "md5_version": "4444", "source_version": "v0.1.1-7-g9c2d7ca", "time_utc": "2023-07-24 17:04:24"}, "previous": "None"}'
    mock_get_ssm_param.return_value = current_config

    switch_to_version_dict = {"aws_aio_version": "1", "config_version": "2", "md5_version": "2222", "source_version": "v0.1.1-7-g9c2d7ca", "time_utc": "2023-07-24 17:04:24"}
    mock_get_metadata.return_value = switch_to_version_dict

    # Run our test
    actual_value = _update_config_if_necessary(cluster_name, bucket_name, mock_s3_key_provider, ssm_param,
                                mock_archive_provider, 1, mock_provider)

    # Check our results
    assert True == actual_value

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

    expected_put_ssm_param_calls = [
        mock.call(
            ssm_param,
            json.dumps(
                config_wrangling.ConfigDetails(
                    s3=config_wrangling.S3Details(bucket_name, s3_key),
                    version=config_wrangling.VersionInfo(**switch_to_version_dict),
                    previous=config_wrangling.ConfigDetails.from_dict(json.loads(current_config))
                ).to_dict()
            ),
            mock.ANY,
            description=mock.ANY,
            overwrite=True,
        ),
    ]
    assert expected_put_ssm_param_calls == mock_put_ssm_param.call_args_list

@mock.patch("commands.config_update.s3.get_object_user_metadata")
@mock.patch("commands.config_update.ssm_ops.put_ssm_param")
@mock.patch("commands.config_update.s3.put_file_to_bucket")
@mock.patch("commands.config_update.ssm_ops.get_ssm_param_value")
@mock.patch("commands.config_update.ver.get_version_info")
def test_WHEN_update_config_if_necessary_called_AND_switch_ver_doesnt_exist_THEN_as_expected(
        mock_get_version, mock_get_ssm_param, mock_put_file, mock_put_ssm_param, mock_get_metadata):
    # Set up our mock
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

    mock_get_metadata.side_effect = s3.S3ObjectDoesntExist("blah", "blah")

    # Run our test

    actual_value = _update_config_if_necessary(cluster_name, bucket_name, mock_s3_key_provider, ssm_param,
                                mock_archive_provider, 3, mock_provider)

    # Check our results
    assert False == actual_value

    expected_get_version_info_calls = [
        mock.call(mock_archive)
    ]
    assert expected_get_version_info_calls == mock_get_version.call_args_list

    expected_get_ssm_param_calls = []
    assert expected_get_ssm_param_calls == mock_get_ssm_param.call_args_list

    expected_put_file_calls = []
    assert expected_put_file_calls == mock_put_file.call_args_list

    expected_put_ssm_param_calls = []
    assert expected_put_ssm_param_calls == mock_put_ssm_param.call_args_list

@mock.patch("commands.config_update.exit")
@mock.patch("commands.config_update.sleep")
@mock.patch("commands.config_update._revert_arkime_config")
@mock.patch("commands.config_update.ecs.get_failed_task_count")
@mock.patch("commands.config_update.ecs.is_deployment_in_progress")
@mock.patch("commands.config_update.ecs.force_ecs_deployment")
def test_WHEN_bounce_ecs_service_called_AND_happy_path_THEN_as_expected(mock_force_deploy, mock_is_in_progress,
                                                                        mock_get_fails, mock_revert, mock_sleep,
                                                                        mock_exit):
    # Set up our mock
    mock_provider = mock.Mock()

    mock_is_in_progress.side_effect = [True, True, False]
    mock_get_fails.return_value = 0

    # Run our test
    _bounce_ecs_service("cluster-name", "service-name", "ssm-param", mock_provider)

    # Check our results
    expected_force_deploy_calls = [
        mock.call("cluster-name", "service-name", mock_provider),
    ]
    assert expected_force_deploy_calls == mock_force_deploy.call_args_list

    assert not mock_revert.called
    assert 2 == mock_sleep.call_count
    assert not mock_exit.called

@mock.patch("commands.config_update.exit")
@mock.patch("commands.config_update.sleep")
@mock.patch("commands.config_update._revert_arkime_config")
@mock.patch("commands.config_update.ecs.get_failed_task_count")
@mock.patch("commands.config_update.ecs.is_deployment_in_progress")
@mock.patch("commands.config_update.ecs.force_ecs_deployment")
def test_WHEN_bounce_ecs_service_called_AND_need_rollback_THEN_as_expected(mock_force_deploy, mock_is_in_progress,
                                                                        mock_get_fails, mock_revert, mock_sleep,
                                                                        mock_exit):
    # Set up our mock
    mock_provider = mock.Mock()

    mock_is_in_progress.side_effect = [True, True, True, True, False]
    mock_get_fails.side_effect = [0, 10, 10, 0, 0]

    # Run our test
    _bounce_ecs_service("cluster-name", "service-name", "ssm-param", mock_provider)

    # Check our results
    expected_force_deploy_calls = [
        mock.call("cluster-name", "service-name", mock_provider),
    ]
    assert expected_force_deploy_calls == mock_force_deploy.call_args_list

    expected_revert_calls = [
        mock.call("ssm-param", mock_provider),
    ]
    assert expected_revert_calls == mock_revert.call_args_list

    assert 4 == mock_sleep.call_count
    assert not mock_exit.called

@mock.patch("commands.config_update.exit")
@mock.patch("commands.config_update.sleep")
@mock.patch("commands.config_update._revert_arkime_config")
@mock.patch("commands.config_update.ecs.get_failed_task_count")
@mock.patch("commands.config_update.ecs.is_deployment_in_progress")
@mock.patch("commands.config_update.ecs.force_ecs_deployment")
def test_WHEN_bounce_ecs_service_called_AND_rollback_failed_THEN_as_expected(mock_force_deploy, mock_is_in_progress,
                                                                        mock_get_fails, mock_revert, mock_sleep,
                                                                        mock_exit):
    # Set up our mock
    mock_provider = mock.Mock()

    mock_is_in_progress.return_value = True
    mock_get_fails.return_value = 10
    mock_revert.side_effect = NoPreviousConfig()

    # Run our test
    _bounce_ecs_service("cluster-name", "service-name", "ssm-param", mock_provider)

    # Check our results
    expected_force_deploy_calls = [
        mock.call("cluster-name", "service-name", mock_provider),
    ]
    assert expected_force_deploy_calls == mock_force_deploy.call_args_list

    expected_revert_calls = [
        mock.call("ssm-param", mock_provider),
    ]
    assert expected_revert_calls == mock_revert.call_args_list

    assert not mock_sleep.called

    expected_exit_calls = [mock.call(1)]
    assert expected_exit_calls == mock_exit.call_args_list

@mock.patch("commands.config_update.exit")
@mock.patch("commands.config_update.sleep")
@mock.patch("commands.config_update._revert_arkime_config")
@mock.patch("commands.config_update.ecs.get_failed_task_count")
@mock.patch("commands.config_update.ecs.is_deployment_in_progress")
@mock.patch("commands.config_update.ecs.force_ecs_deployment")
def test_WHEN_bounce_ecs_service_called_AND_sigint_THEN_as_expected(mock_force_deploy, mock_is_in_progress,
                                                                        mock_get_fails, mock_revert, mock_sleep,
                                                                        mock_exit):
    # Set up our mock
    mock_provider = mock.Mock()

    mock_is_in_progress.return_value = True
    mock_get_fails.return_value = 0
    mock_sleep.side_effect = KeyboardInterrupt()

    # Run our test
    _bounce_ecs_service("cluster-name", "service-name", "ssm-param", mock_provider)

    # Check our results
    expected_force_deploy_calls = [
        mock.call("cluster-name", "service-name", mock_provider),
    ]
    assert expected_force_deploy_calls == mock_force_deploy.call_args_list

    expected_revert_calls = [
        mock.call("ssm-param", mock_provider),
    ]
    assert expected_revert_calls == mock_revert.call_args_list

    assert mock_sleep.called

    expected_exit_calls = [mock.call(0)]
    assert expected_exit_calls == mock_exit.call_args_list
