import json
import pytest
import shlex
import unittest.mock as mock

import arkime_interactions.config_wrangling as config_wrangling
from aws_interactions.aws_environment import AwsEnvironment
from aws_interactions.events_interactions import ConfigureIsmEvent
import aws_interactions.s3_interactions as s3
import aws_interactions.ssm_operations as ssm_ops

from commands.cluster_create import (cmd_cluster_create, _set_up_viewer_cert, _get_next_capacity_plan, _get_next_user_config, _confirm_usage,
                                     _get_previous_capacity_plan, _get_previous_user_config, _configure_ism, _set_up_arkime_config,
                                     _tag_domain, _should_proceed_with_operation, _is_initial_invocation, _get_stacks_to_deploy, _get_cdk_context)
import core.constants as constants
from core.capacity_planning import (CaptureNodesPlan, ViewerNodesPlan, EcsSysResourcePlan, MINIMUM_TRAFFIC, OSDomainPlan, DataNodesPlan, MasterNodesPlan,
                                    VpcPlan, ClusterPlan, DEFAULT_SPI_DAYS, DEFAULT_REPLICAS, DEFAULT_NUM_AZS, S3Plan,
                                    DEFAULT_S3_STORAGE_CLASS, DEFAULT_S3_STORAGE_DAYS, DEFAULT_HISTORY_DAYS, Cidr, DEFAULT_VPC_CIDR, DEFAULT_CAPTURE_PUBLIC_MASK,
                                    DEFAULT_VIEWER_PUBLIC_MASK)
import core.local_file as local_file
from core.user_config import UserConfig
from core.versioning import VersionInfo


@mock.patch("commands.cluster_create.AwsClientProvider")
@mock.patch("commands.cluster_create._get_cdk_context")
@mock.patch("commands.cluster_create._get_stacks_to_deploy")
@mock.patch("commands.cluster_create._is_initial_invocation")
@mock.patch("commands.cluster_create._tag_domain")
@mock.patch("commands.cluster_create._set_up_arkime_config")
@mock.patch("commands.cluster_create._configure_ism")
@mock.patch("commands.cluster_create._get_previous_user_config")
@mock.patch("commands.cluster_create._get_previous_capacity_plan")
@mock.patch("commands.cluster_create._should_proceed_with_operation")
@mock.patch("commands.cluster_create._get_next_user_config")
@mock.patch("commands.cluster_create._get_next_capacity_plan")
@mock.patch("commands.cluster_create._set_up_viewer_cert")
@mock.patch("commands.cluster_create.CdkClient")
def test_WHEN_cmd_cluster_create_called_THEN_cdk_command_correct(mock_cdk_client_cls, mock_set_up, mock_get_plans, mock_get_config,
                                                                 mock_proceed, mock_get_prev_plan, mock_get_prev_config, mock_configure,
                                                                 mock_set_up_arkime_conf, mock_tag, mock_initial,mock_get_stacks,
                                                                 mock_get_context, mock_aws_provider_cls):
    # Set up our mock
    mock_set_up.return_value = "arn"

    mock_client = mock.Mock()
    mock_cdk_client_cls.return_value = mock_client

    aws_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")
    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_aws_env.return_value = aws_env
    mock_aws_provider_cls.return_value = mock_aws_provider

    user_config = UserConfig(1, 30, 365, 2, 30)
    mock_get_config.return_value = user_config

    cluster_plan = ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 20, 25, 1),
        VpcPlan(DEFAULT_VPC_CIDR, DEFAULT_NUM_AZS, DEFAULT_CAPTURE_PUBLIC_MASK),
        EcsSysResourcePlan(3584, 15360),
        OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search")),
        S3Plan(DEFAULT_S3_STORAGE_CLASS, DEFAULT_S3_STORAGE_DAYS),
        ViewerNodesPlan(20, 5),
        None
    )
    mock_get_plans.return_value = cluster_plan

    mock_initial.return_value = True
    mock_proceed.return_value = True

    mock_get_stacks.return_value = ["stack1", "stack2"]
    mock_get_context.return_value = {"key": "value"}

    # Run our test
    cmd_cluster_create("profile", "region", "my-cluster", None, None, None, None, None, True, False, None, None)

    # Check our results
    expected_calls = [
        mock.call(
            ["stack1", "stack2"],
            context={"key": "value"}
        )
    ]
    assert expected_calls == mock_client.deploy.call_args_list

    expected_cdk_client_create_calls = [
        mock.call(aws_env)
    ]
    assert expected_cdk_client_create_calls == mock_cdk_client_cls.call_args_list

    expected_set_up_calls = [
        mock.call("my-cluster", mock.ANY)
    ]
    assert expected_set_up_calls == mock_set_up.call_args_list

    expected_configure_calls = [
        mock.call("my-cluster", 365, 30, 2, mock.ANY)
    ]
    assert expected_configure_calls == mock_configure.call_args_list

    expected_set_up_arkime_conf_calls = [
        mock.call("my-cluster", mock.ANY)
    ]
    assert expected_set_up_arkime_conf_calls == mock_set_up_arkime_conf.call_args_list

    expected_tag_calls = [
        mock.call("my-cluster",mock.ANY)
    ]
    assert expected_tag_calls == mock_tag.call_args_list

@mock.patch("commands.cluster_create.AwsClientProvider", mock.Mock())
@mock.patch("commands.cluster_create._is_initial_invocation")
@mock.patch("commands.cluster_create._tag_domain")
@mock.patch("commands.cluster_create._set_up_arkime_config")
@mock.patch("commands.cluster_create._configure_ism")
@mock.patch("commands.cluster_create._get_previous_user_config")
@mock.patch("commands.cluster_create._get_previous_capacity_plan")
@mock.patch("commands.cluster_create._should_proceed_with_operation")
@mock.patch("commands.cluster_create._get_next_user_config")
@mock.patch("commands.cluster_create._get_next_capacity_plan")
@mock.patch("commands.cluster_create._set_up_viewer_cert")
@mock.patch("commands.cluster_create.CdkClient")
def test_WHEN_cmd_cluster_create_called_AND_shouldnt_proceed_THEN_as_expected(mock_cdk_client_cls, mock_set_up, mock_get_plans, mock_get_config,
                                                                         mock_proceed, mock_get_prev_plan, mock_get_prev_config, mock_configure,
                                                                         mock_set_up_arkime_conf, mock_tag, mock_initial):
    # Set up our mock
    mock_set_up.return_value = "arn"

    mock_client = mock.Mock()
    mock_cdk_client_cls.return_value = mock_client

    user_config = mock.Mock()
    mock_get_config.return_value = user_config
    mock_get_prev_config.return_value = user_config

    cluster_plan = mock.Mock()
    mock_get_plans.return_value = cluster_plan
    mock_get_prev_plan.return_value = cluster_plan

    mock_initial.return_value = True
    mock_proceed.return_value = False

    # Run our test
    cmd_cluster_create("profile", "region", "my-cluster", None, None, None, None, None, True, False, "1.2.3.4/24", "2.3.4.5/26")

    # Check our results
    expected_proceed_calls = [
        mock.call(True, cluster_plan, cluster_plan, user_config, user_config, True, "1.2.3.4/24", "2.3.4.5/26")
    ]
    assert expected_proceed_calls == mock_proceed.call_args_list

    expected_calls = []
    assert expected_calls == mock_client.deploy.call_args_list

    expected_set_up_calls = []
    assert expected_set_up_calls == mock_set_up.call_args_list

    expected_configure_calls = []
    assert expected_configure_calls == mock_configure.call_args_list

    expected_tag_calls = []
    assert expected_tag_calls == mock_tag.call_args_list

    expected_set_up_arkime_conf_calls = []
    assert expected_set_up_arkime_conf_calls == mock_set_up_arkime_conf.call_args_list


@mock.patch("commands.cluster_create._get_cdk_context")
@mock.patch("commands.cluster_create._get_stacks_to_deploy")
@mock.patch("commands.cluster_create._is_initial_invocation")
@mock.patch("commands.cluster_create._tag_domain")
@mock.patch("commands.cluster_create.cfn.set_up_cloudformation_template_dir")
@mock.patch("commands.cluster_create.constants.get_repo_root_dir")
@mock.patch("commands.cluster_create.shutil.rmtree")
@mock.patch("commands.cluster_create.cfn.get_cdk_out_dir_path")
@mock.patch("commands.cluster_create.AwsClientProvider")
@mock.patch("commands.cluster_create._set_up_arkime_config")
@mock.patch("commands.cluster_create._configure_ism")
@mock.patch("commands.cluster_create._get_previous_user_config")
@mock.patch("commands.cluster_create._get_previous_capacity_plan")
@mock.patch("commands.cluster_create._should_proceed_with_operation")
@mock.patch("commands.cluster_create._get_next_user_config")
@mock.patch("commands.cluster_create._get_next_capacity_plan")
@mock.patch("commands.cluster_create._set_up_viewer_cert")
@mock.patch("commands.cluster_create.CdkClient")
def test_WHEN_cmd_cluster_create_called_AND_just_print_THEN_as_expected(mock_cdk_client_cls, mock_set_up, mock_get_plans,
                                                                mock_get_config, mock_proceed, mock_get_prev_plan,
                                                                mock_get_prev_config, mock_configure, mock_set_up_arkime_conf,
                                                                mock_aws_provider_cls, mock_get_cdk_dir, mock_rmtree,
                                                                mock_get_root_dir, mock_set_up_cfn, mock_tag, mock_initial,
                                                                mock_get_stacks, mock_get_context):
    # Set up our mock
    mock_set_up.return_value = "arn"

    mock_client = mock.Mock()
    mock_cdk_client_cls.return_value = mock_client

    aws_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")
    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_aws_env.return_value = aws_env
    mock_aws_provider_cls.return_value = mock_aws_provider

    user_config = UserConfig(1, 30, 365, 2, 30)
    mock_get_config.return_value = user_config

    cluster_plan = ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 20, 25, 1),
        VpcPlan(DEFAULT_VPC_CIDR, DEFAULT_NUM_AZS, DEFAULT_CAPTURE_PUBLIC_MASK),
        EcsSysResourcePlan(3584, 15360),
        OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search")),
        S3Plan(DEFAULT_S3_STORAGE_CLASS, DEFAULT_S3_STORAGE_DAYS),
        ViewerNodesPlan(20, 5),
        None
    )
    mock_get_plans.return_value = cluster_plan

    mock_initial.return_value = True
    mock_proceed.return_value = True

    mock_get_cdk_dir.return_value = "/path/cdk.out"
    mock_get_root_dir.return_value = "/path"

    mock_get_stacks.return_value = ["stack1", "stack2"]
    mock_get_context.return_value = {"key": "value"}

    # Run our test
    cmd_cluster_create("profile", "region", "my-cluster", None, None, None, None, None, True, True, None, None)

    # Check our results
    expected_calls = [
        mock.call(
            ["stack1", "stack2"],
            context={"key": "value"}
        )
    ]
    assert expected_calls == mock_client.synthesize.call_args_list

    expected_deploy_calls = []
    assert expected_deploy_calls == mock_client.deploy.call_args_list

    expected_cdk_client_create_calls = [
        mock.call(aws_env)
    ]
    assert expected_cdk_client_create_calls == mock_cdk_client_cls.call_args_list

    expected_set_up_calls = [
        mock.call("my-cluster", mock.ANY)
    ]
    assert expected_set_up_calls == mock_set_up.call_args_list

    expected_configure_calls = []
    assert expected_configure_calls == mock_configure.call_args_list

    expected_tag_calls = []
    assert expected_tag_calls == mock_tag.call_args_list

    expected_set_up_arkime_conf_calls = [
        mock.call("my-cluster", mock.ANY)
    ]
    assert expected_set_up_arkime_conf_calls == mock_set_up_arkime_conf.call_args_list

    expected_set_up_arkime_conf_calls = [
        mock.call("my-cluster", mock.ANY)
    ]
    assert expected_set_up_arkime_conf_calls == mock_set_up_arkime_conf.call_args_list

    expected_rmtree_calls = [
        mock.call("/path/cdk.out")
    ]
    assert expected_rmtree_calls == mock_rmtree.call_args_list

    expected_set_up_cfn_calls = [
        mock.call("my-cluster", aws_env, "/path")
    ]
    assert expected_set_up_cfn_calls == mock_set_up_cfn.call_args_list

@mock.patch("commands.cluster_create._confirm_usage")
def test_WHEN_should_proceed_with_operation_AND_happy_path_THEN_as_expected(mock_confirm):
    # Set up our mock
    user_config = UserConfig(1, 30, 365, 2, 30)   

    cluster_plan = ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 1, 2, 1),
        VpcPlan(DEFAULT_VPC_CIDR, DEFAULT_NUM_AZS, DEFAULT_CAPTURE_PUBLIC_MASK),
        EcsSysResourcePlan(3584, 15360),
        OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search")),
        S3Plan(DEFAULT_S3_STORAGE_CLASS, DEFAULT_S3_STORAGE_DAYS),
        ViewerNodesPlan(4, 2),
        None
    )

    mock_confirm.return_value = True

    # Run our test
    actual_value = _should_proceed_with_operation(True, cluster_plan, cluster_plan, user_config, user_config, True,
                                                  "1.2.3.4/24", "2.3.4.5/26")

    # Check our results
    assert True == actual_value

    expected_confirm_calls = [
        mock.call(cluster_plan, cluster_plan, user_config, user_config, True)
    ]
    assert expected_confirm_calls == mock_confirm.call_args_list

@mock.patch("commands.cluster_create._confirm_usage")
def test_WHEN_should_proceed_with_operation_AND_change_capture_cidr_THEN_as_expected(mock_confirm):
    # Set up our mock
    user_config = UserConfig(1, 30, 365, 2, 30)  

    cluster_plan = ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 20, 25, 1),
        VpcPlan(DEFAULT_VPC_CIDR, DEFAULT_NUM_AZS, DEFAULT_CAPTURE_PUBLIC_MASK),
        EcsSysResourcePlan(3584, 15360),
        OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search")),
        S3Plan(DEFAULT_S3_STORAGE_CLASS, DEFAULT_S3_STORAGE_DAYS),
        ViewerNodesPlan(20, 5),
        None
    )

    mock_confirm.return_value = False

    # Run our test
    actual_value = _should_proceed_with_operation(False, cluster_plan, cluster_plan, user_config, user_config, True, "1.2.3.4/24", None)

    # Check our results
    assert False == actual_value

    expected_confirm_calls = []
    assert expected_confirm_calls == mock_confirm.call_args_list

@mock.patch("commands.cluster_create._confirm_usage")
def test_WHEN_should_proceed_with_operation_AND_change_viewer_cidr_THEN_as_expected(mock_confirm):
    # Set up our mock
    user_config = UserConfig(1, 30, 365, 2, 30)  

    cluster_plan = ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 20, 25, 1),
        VpcPlan(DEFAULT_VPC_CIDR, DEFAULT_NUM_AZS, DEFAULT_CAPTURE_PUBLIC_MASK),
        EcsSysResourcePlan(3584, 15360),
        OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search")),
        S3Plan(DEFAULT_S3_STORAGE_CLASS, DEFAULT_S3_STORAGE_DAYS),
        ViewerNodesPlan(20, 5),
        None
    )

    mock_confirm.return_value = False

    # Run our test
    actual_value = _should_proceed_with_operation(False, cluster_plan, cluster_plan, user_config, user_config, True, None, "1.2.3.4/24")

    # Check our results
    assert False == actual_value

    expected_confirm_calls = []
    assert expected_confirm_calls == mock_confirm.call_args_list

@mock.patch("commands.cluster_create._confirm_usage")
def test_WHEN_should_proceed_with_operation_AND_check_overlapping_cidrs_THEN_as_expected(mock_confirm):
    user_config = UserConfig(1, 30, 365, 2, 30)
    mock_confirm.return_value = True

    # TEST: Both specified, and don't overlap
    cluster_plan =  ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 20, 25, 1),
        VpcPlan(Cidr("1.2.3.4/24"), DEFAULT_NUM_AZS, DEFAULT_CAPTURE_PUBLIC_MASK),
        EcsSysResourcePlan(3584, 15360),
        OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search")),
        S3Plan(DEFAULT_S3_STORAGE_CLASS, DEFAULT_S3_STORAGE_DAYS),
        ViewerNodesPlan(20, 5),
        VpcPlan(Cidr("2.3.4.5/24"), DEFAULT_NUM_AZS, DEFAULT_CAPTURE_PUBLIC_MASK),
    )    

    actual_value = _should_proceed_with_operation(False, cluster_plan, cluster_plan, user_config, user_config, True, None, None)
    assert True == actual_value

    assert mock_confirm.called

    # TEST: Both specified, and do overlap
    cluster_plan =  ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 20, 25, 1),
        VpcPlan(Cidr("1.2.3.4/24"), DEFAULT_NUM_AZS, DEFAULT_CAPTURE_PUBLIC_MASK),
        EcsSysResourcePlan(3584, 15360),
        OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search")),
        S3Plan(DEFAULT_S3_STORAGE_CLASS, DEFAULT_S3_STORAGE_DAYS),
        ViewerNodesPlan(20, 5),
        VpcPlan(Cidr("1.2.3.48/26"), DEFAULT_NUM_AZS, DEFAULT_CAPTURE_PUBLIC_MASK),
    )
    user_config = UserConfig(1, 30, 365, 2, 30)

    actual_value = _should_proceed_with_operation(False, cluster_plan, cluster_plan, user_config, user_config, True, None, None)
    assert False == actual_value

@mock.patch("commands.cluster_create._confirm_usage")
def test_WHEN_should_proceed_with_operation_AND_abort_usage_THEN_as_expected(mock_confirm):
    # Set up our mock
    user_config = UserConfig(1, 30, 365, 2, 30) 

    cluster_plan = ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 1, 2, 1),
        VpcPlan(DEFAULT_VPC_CIDR, DEFAULT_NUM_AZS, DEFAULT_CAPTURE_PUBLIC_MASK),
        EcsSysResourcePlan(3584, 15360),
        OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search")),
        S3Plan(DEFAULT_S3_STORAGE_CLASS, DEFAULT_S3_STORAGE_DAYS),
        ViewerNodesPlan(4, 2),
        None
    )

    mock_confirm.return_value = False

    # Run our test
    actual_value = _should_proceed_with_operation(True, cluster_plan, cluster_plan, user_config, user_config, True, None, None)

    # Check our results
    assert False == actual_value

    expected_confirm_calls = [
        mock.call(cluster_plan, cluster_plan, user_config, user_config, True)
    ]
    assert expected_confirm_calls == mock_confirm.call_args_list

@mock.patch("commands.cluster_create._confirm_usage")
def test_WHEN_should_proceed_with_operation_AND_doesnt_fit_THEN_as_expected(mock_confirm):
    # Set up our mock
    user_config = UserConfig(1, 30, 365, 2, 30) 

    cluster_plan = ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 100, 200, 100),
        VpcPlan(Cidr("1.2.3.4/28"), DEFAULT_NUM_AZS, DEFAULT_CAPTURE_PUBLIC_MASK),
        EcsSysResourcePlan(3584, 15360),
        OSDomainPlan(DataNodesPlan(100, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search")),
        S3Plan(DEFAULT_S3_STORAGE_CLASS, DEFAULT_S3_STORAGE_DAYS),
        ViewerNodesPlan(4, 2),
        None
    )

    mock_confirm.return_value = True

    # Run our test
    actual_value = _should_proceed_with_operation(True, cluster_plan, cluster_plan, user_config, user_config, True, None, None)

    # Check our results
    assert False == actual_value

    expected_confirm_calls = [
        mock.call(cluster_plan, cluster_plan, user_config, user_config, True)
    ]
    assert expected_confirm_calls == mock_confirm.call_args_list

@mock.patch("commands.cluster_create.ssm_ops")
def test_WHEN_get_previous_user_config_called_AND_exists_THEN_as_expected(mock_ssm_ops):
    # Set up our mock
    mock_ssm_ops.get_ssm_param_json_value.return_value = {
        "expectedTraffic": 0.1,
        "spiDays": 30,
        "replicas": 1,
        "pcapDays": 30,
        "historyDays": 120
    }

    mock_provider = mock.Mock()

    # Run our test
    actual_value = _get_previous_user_config("cluster-name", mock_provider)

    # Check our results
    expected_value = UserConfig(0.1, 30, 120, 1, 30)
    assert expected_value == actual_value

    expected_get_ssm_calls = [
        mock.call(constants.get_cluster_ssm_param_name("cluster-name"), "userConfig", mock_provider)
    ]
    assert expected_get_ssm_calls == mock_ssm_ops.get_ssm_param_json_value.call_args_list


@mock.patch("commands.cluster_create.ssm_ops")
def test_WHEN_get_previous_user_config_called_AND_doesnt_exist_THEN_as_expected(mock_ssm_ops):
    # Set up our mock
    mock_ssm_ops.ParamDoesNotExist = ssm_ops.ParamDoesNotExist
    mock_ssm_ops.get_ssm_param_json_value.side_effect = ssm_ops.ParamDoesNotExist("")

    mock_provider = mock.Mock()

    # Run our test
    actual_value = _get_previous_user_config("cluster-name", mock_provider)

    # Check our results
    expected_value = UserConfig(None, None, None, None, None)
    assert expected_value == actual_value

    expected_get_ssm_calls = [
        mock.call(constants.get_cluster_ssm_param_name("cluster-name"), "userConfig", mock_provider)
    ]
    assert expected_get_ssm_calls == mock_ssm_ops.get_ssm_param_json_value.call_args_list

@mock.patch("commands.cluster_create.ssm_ops")
def test_WHEN_get_next_user_config_called_AND_use_existing_THEN_as_expected(mock_ssm_ops):
    # Set up our mock
    mock_ssm_ops.ParamDoesNotExist = ssm_ops.ParamDoesNotExist

    mock_ssm_ops.get_ssm_param_json_value.return_value = {
        "expectedTraffic": 1.2,
        "spiDays": 40,
        "historyDays": 120,
        "replicas": 2,
        "pcapDays": 35,
    }

    mock_provider = mock.Mock()

    # Run our test
    actual_value = _get_next_user_config("my-cluster", None, None, None, None, None, mock_provider)

    # Check our results
    assert UserConfig(1.2, 40, 120, 2, 35) == actual_value

    expected_get_ssm_calls = [
        mock.call(constants.get_cluster_ssm_param_name("my-cluster"), "userConfig", mock.ANY)
    ]
    assert expected_get_ssm_calls == mock_ssm_ops.get_ssm_param_json_value.call_args_list

@mock.patch("commands.cluster_create.ssm_ops")
def test_WHEN_get_next_user_config_called_AND_partial_update_THEN_as_expected(mock_ssm_ops):
    # Set up our mock
    mock_ssm_ops.ParamDoesNotExist = ssm_ops.ParamDoesNotExist

    mock_ssm_ops.get_ssm_param_json_value.return_value = {
        "expectedTraffic": 1.2,
        "spiDays": 40,
        "historyDays": 120,
        "replicas": 2,
        "pcapDays": 35,
    }

    mock_provider = mock.Mock()

    # Run our test
    actual_value = _get_next_user_config("my-cluster", None, 30, None, None, None, mock_provider)

    # Check our results
    assert UserConfig(1.2, 30, 120, 2, 35) == actual_value

    expected_get_ssm_calls = [
        mock.call(constants.get_cluster_ssm_param_name("my-cluster"), "userConfig", mock.ANY)
    ]
    assert expected_get_ssm_calls == mock_ssm_ops.get_ssm_param_json_value.call_args_list

@mock.patch("commands.cluster_create.ssm_ops")
def test_WHEN_get_next_user_config_called_AND_use_default_THEN_as_expected(mock_ssm_ops):
    # Set up our mock
    mock_ssm_ops.ParamDoesNotExist = ssm_ops.ParamDoesNotExist
    mock_ssm_ops.get_ssm_param_json_value.side_effect = ssm_ops.ParamDoesNotExist("")

    mock_provider = mock.Mock()

    # Run our test
    actual_value = _get_next_user_config("my-cluster", None, None, None, None, None, mock_provider)

    # Check our results
    assert UserConfig(MINIMUM_TRAFFIC, DEFAULT_SPI_DAYS, DEFAULT_HISTORY_DAYS, DEFAULT_REPLICAS, DEFAULT_S3_STORAGE_DAYS) == actual_value

    expected_get_ssm_calls = [
        mock.call(constants.get_cluster_ssm_param_name("my-cluster"), "userConfig", mock.ANY)
    ]
    assert expected_get_ssm_calls == mock_ssm_ops.get_ssm_param_json_value.call_args_list

@mock.patch("commands.cluster_create.ssm_ops")
def test_WHEN_get_next_user_config_called_AND_specify_all_THEN_as_expected(mock_ssm_ops):
    # Set up our mock
    mock_ssm_ops.ParamDoesNotExist = ssm_ops.ParamDoesNotExist

    mock_provider = mock.Mock()

    # Run our test
    actual_value = _get_next_user_config("my-cluster", 10, 40, 120, 2, 35, mock_provider)

    # Check our results
    assert UserConfig(10, 40, 120, 2, 35) == actual_value

    expected_get_ssm_calls = []
    assert expected_get_ssm_calls == mock_ssm_ops.get_ssm_param_json_value.call_args_list


@mock.patch("commands.cluster_create.ssm_ops")
def test_WHEN_get_previous_capacity_plan_called_AND_exists_THEN_as_expected(mock_ssm_ops):
    # Set up our mock
    mock_ssm_ops.ParamDoesNotExist = ssm_ops.ParamDoesNotExist

    mock_ssm_ops.get_ssm_param_json_value.return_value = {
        "captureNodes": {
            "instanceType": "m5.xlarge",
            "desiredCount": 1,
            "maxCount": 2,
            "minCount": 1
        },
        "captureVpc": {
            "cidr": {
                "block": "1.2.3.4/24",
                "prefix": "1.2.3.4",
                "mask": "24",
            },
            "numAzs": 2,
            "publicSubnetMask": 28,
        },
        "ecsResources": {
            "cpu": 3584,
            "memory": 15360
        },
        "osDomain": {
            "dataNodes": {
                "count": 2,
                "instanceType": "r6g.large.search",
                "volumeSize": 1024
            },
            "masterNodes": {
                "count": 3,
                "instanceType": "m6g.large.search"
            }
        },
        "s3": {
            "pcapStorageClass": "STANDARD",
            "pcapStorageDays": 30
        },
        "viewerNodes": {
            "maxCount": 4,
            "minCount": 2,
        },
        "viewerVpc": {
            "cidr": {
                "block": "2.3.4.5/26",
                "prefix": "2.3.4.5",
                "mask": "26",
            },
            "numAzs": 2,
            "publicSubnetMask": 28,
        },
    }

    mock_provider = mock.Mock()

    # Run our test
    actual_value = _get_previous_capacity_plan("cluster-name", mock_provider)

    # Check our results
    expected_value = ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 1, 2, 1),
        VpcPlan(Cidr("1.2.3.4/24"), DEFAULT_NUM_AZS, DEFAULT_CAPTURE_PUBLIC_MASK),
        EcsSysResourcePlan(3584, 15360),
        OSDomainPlan(DataNodesPlan(2, "r6g.large.search", 1024), MasterNodesPlan(3, "m6g.large.search")),
        S3Plan(DEFAULT_S3_STORAGE_CLASS, 30),
        ViewerNodesPlan(4, 2),
        VpcPlan(Cidr("2.3.4.5/26"), DEFAULT_NUM_AZS, DEFAULT_VIEWER_PUBLIC_MASK),
    )
    assert expected_value == actual_value

    expected_get_ssm_calls = [
        mock.call(constants.get_cluster_ssm_param_name("cluster-name"), "capacityPlan", mock_provider)
    ]
    assert expected_get_ssm_calls == mock_ssm_ops.get_ssm_param_json_value.call_args_list


@mock.patch("commands.cluster_create.ssm_ops")
def test_WHEN_get_previous_capacity_plan_called_AND_doesnt_exist_THEN_as_expected(mock_ssm_ops):
    # Set up our mock
    mock_ssm_ops.ParamDoesNotExist = ssm_ops.ParamDoesNotExist
    mock_ssm_ops.get_ssm_param_json_value.side_effect = ssm_ops.ParamDoesNotExist("")

    mock_provider = mock.Mock()

    # Run our test
    actual_value = _get_previous_capacity_plan("cluster-name", mock_provider)

    # Check our results
    expected_value = ClusterPlan(
        CaptureNodesPlan(None, None, None, None),
        VpcPlan(None, None, None),
        EcsSysResourcePlan(None, None),
        OSDomainPlan(DataNodesPlan(None, None, None), MasterNodesPlan(None, None)),
        S3Plan(None, None),
        ViewerNodesPlan(None, None),
        None
    )
    assert expected_value == actual_value

    expected_get_ssm_calls = [
        mock.call(constants.get_cluster_ssm_param_name("cluster-name"), "capacityPlan", mock_provider)
    ]
    assert expected_get_ssm_calls == mock_ssm_ops.get_ssm_param_json_value.call_args_list


@mock.patch("commands.cluster_create.get_viewer_vpc_plan")
@mock.patch("commands.cluster_create.get_capture_vpc_plan")
@mock.patch("commands.cluster_create.get_os_domain_plan")
@mock.patch("commands.cluster_create.get_capture_node_capacity_plan")
@mock.patch("commands.cluster_create.ssm_ops")
def test_WHEN_get_next_capacity_plan_called_THEN_as_expected(mock_ssm_ops, mock_get_cap, mock_get_os, mock_get_capture, mock_get_viewer):
    # Set up our mock
    mock_ssm_ops.ParamDoesNotExist = ssm_ops.ParamDoesNotExist
    mock_ssm_ops.get_ssm_param_json_value.side_effect = ssm_ops.ParamDoesNotExist("")

    mock_get_cap.return_value = CaptureNodesPlan("m5.xlarge", 1, 2, 1)
    mock_get_os.return_value = OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search"))
    mock_get_capture.return_value = VpcPlan(Cidr("1.2.3.4/24"), DEFAULT_NUM_AZS, DEFAULT_CAPTURE_PUBLIC_MASK)
    mock_get_viewer.return_value = VpcPlan(Cidr("2.3.4.5/26"), DEFAULT_NUM_AZS, DEFAULT_VIEWER_PUBLIC_MASK)

    previous_cluster_plan = ClusterPlan(
        CaptureNodesPlan(None, None, None, None),
        VpcPlan(None, None, None),
        EcsSysResourcePlan(None, None),
        OSDomainPlan(DataNodesPlan(None, None, None), MasterNodesPlan(None, None)),
        S3Plan(None, None),
        ViewerNodesPlan(None, None),
        None
    )

    mock_provider = mock.Mock()

    # Run our test
    actual_value = _get_next_capacity_plan(UserConfig(1, 40, 120, 2, 35), previous_cluster_plan, "1.2.3.4/24", "2.3.4.5/26")

    # Check our results
    assert mock_get_cap.return_value == actual_value.captureNodes
    assert VpcPlan(Cidr("1.2.3.4/24"), DEFAULT_NUM_AZS, DEFAULT_CAPTURE_PUBLIC_MASK) == actual_value.captureVpc
    assert mock_get_os.return_value == actual_value.osDomain
    assert EcsSysResourcePlan(3584, 15360) == actual_value.ecsResources
    assert S3Plan(DEFAULT_S3_STORAGE_CLASS, 35) == actual_value.s3
    assert VpcPlan(Cidr("2.3.4.5/26"), DEFAULT_NUM_AZS, DEFAULT_VIEWER_PUBLIC_MASK) == actual_value.viewerVpc

    expected_get_cap_calls = [
        mock.call(1)
    ]
    assert expected_get_cap_calls == mock_get_cap.call_args_list

    expected_get_os_calls = [
        mock.call(1, 40, 2, DEFAULT_NUM_AZS)
    ]
    assert expected_get_os_calls == mock_get_os.call_args_list

    expected_get_capture_vpc_calls = [
        mock.call(VpcPlan(None, None, None), "1.2.3.4/24")
    ]
    assert expected_get_capture_vpc_calls == mock_get_capture.call_args_list

    expected_get_viewer_vpc_calls = [
        mock.call(None, "2.3.4.5/26")
    ]
    assert expected_get_viewer_vpc_calls == mock_get_viewer.call_args_list


@mock.patch("commands.cluster_create.UsageReport")
@mock.patch("commands.cluster_create.PriceReport")
def test_WHEN_confirm_usage_called_THEN_as_expected(mock_price_report_cls, mock_report_cls):
    # Shared Setup
    mock_plan_prev = mock.Mock()
    mock_plan_next = mock.Mock()
    mock_config_prev = mock.Mock()
    mock_config_next = mock.Mock()
    mock_report = mock.Mock()
    mock_report_cls.return_value = mock_report
    mock_price_report = mock.Mock()
    mock_price_report_cls.return_value = mock_price_report

    # TEST: pre-confirm is true
    actual_value = _confirm_usage(mock_plan_prev, mock_plan_next, mock_config_prev, mock_config_next, True)

    assert True == actual_value
    assert not mock_report.get_confirmation.called
    assert mock_price_report.get_report.called

    # TEST: pre-confirm is false, user says yes
    mock_report.get_confirmation.return_value = True

    actual_value = _confirm_usage(mock_plan_prev, mock_plan_next, mock_config_prev, mock_config_next, False)

    assert True == actual_value
    assert mock_report.get_confirmation.called

    # TEST: pre-confirm is false, user says no
    mock_report.get_confirmation.return_value = False

    actual_value = _confirm_usage(mock_plan_prev, mock_plan_next, mock_config_prev, mock_config_next, False)

    assert False == actual_value
    assert mock_report.get_confirmation.called

@mock.patch("commands.cluster_create.upload_default_elb_cert")
@mock.patch("commands.cluster_create.ssm_ops")
def test_WHEN_set_up_viewer_cert_called_THEN_set_up_correctly(mock_ssm_ops, mock_upload):
    # Set up our mock
    mock_ssm_ops.ParamDoesNotExist = ssm_ops.ParamDoesNotExist
    mock_ssm_ops.get_ssm_param_value.side_effect = ssm_ops.ParamDoesNotExist("")

    mock_upload.return_value = "arn"

    mock_provider = mock.Mock()

    # Run our test
    actual_value = _set_up_viewer_cert("my-cluster", mock_provider)

    # Check our results
    assert "arn" == actual_value

    expected_get_ssm_calls = [
        mock.call(constants.get_viewer_cert_ssm_param_name("my-cluster"), mock.ANY)
    ]
    assert expected_get_ssm_calls == mock_ssm_ops.get_ssm_param_value.call_args_list

    expected_upload_calls = [
        mock.call(mock.ANY)
    ]
    assert expected_upload_calls == mock_upload.call_args_list

    expected_put_ssm_calls = [
        mock.call(
            constants.get_viewer_cert_ssm_param_name("my-cluster"),
            "arn",
            mock.ANY,
            mock.ANY
        )
    ]
    assert expected_put_ssm_calls == mock_ssm_ops.put_ssm_param.call_args_list

@mock.patch("commands.cluster_create.AwsClientProvider", mock.Mock())
@mock.patch("commands.cluster_create.upload_default_elb_cert")
@mock.patch("commands.cluster_create.ssm_ops")
def test_WHEN_set_up_viewer_cert_called_AND_already_exists_THEN_skips_creation(mock_ssm_ops, mock_upload):
    # Set up our mock
    mock_ssm_ops.ParamDoesNotExist = ssm_ops.ParamDoesNotExist
    mock_ssm_ops.get_ssm_param_value.return_value = "arn"

    mock_provider = mock.Mock()

    # Run our test
    actual_value = _set_up_viewer_cert("my-cluster", mock_provider)

    # Check our results
    assert "arn" == actual_value

    expected_get_ssm_calls = [
        mock.call(constants.get_viewer_cert_ssm_param_name("my-cluster"), mock.ANY)
    ]
    assert expected_get_ssm_calls == mock_ssm_ops.get_ssm_param_value.call_args_list

    expected_upload_calls = []
    assert expected_upload_calls == mock_upload.call_args_list

    expected_put_ssm_calls = []
    assert expected_put_ssm_calls == mock_ssm_ops.put_ssm_param.call_args_list


@mock.patch("commands.cluster_create.ssm_ops")
@mock.patch("commands.cluster_create.events")
def test_WHEN_configure_ism_called_THEN_as_expected(mock_events, mock_ssm):
    # Set up our mock
    mock_ssm.get_ssm_param_json_value.return_value = "arn"
    mock_events.ConfigureIsmEvent = ConfigureIsmEvent

    mock_provider = mock.Mock()

    # Run our test
    actual_value = _configure_ism("my-cluster", 365, 30, 1, mock_provider)

    # Check our results
    expected_get_ssm_calls = [
        mock.call(
            constants.get_cluster_ssm_param_name("my-cluster"),
            "busArn",
            mock_provider
        )
    ]
    assert expected_get_ssm_calls == mock_ssm.get_ssm_param_json_value.call_args_list

    expected_put_events_calls = [
        mock.call(
            [ConfigureIsmEvent(365, 30, 1)],
            "arn",
            mock_provider
        )
    ]
    assert expected_put_events_calls == mock_events.put_events.call_args_list

@mock.patch("commands.cluster_create.ssm_ops.get_ssm_param_value")
@mock.patch("commands.cluster_create.ssm_ops.put_ssm_param")
@mock.patch("commands.cluster_create.get_version_info")
@mock.patch("commands.cluster_create.config_wrangling.get_viewer_config_archive")
@mock.patch("commands.cluster_create.config_wrangling.get_capture_config_archive")
@mock.patch("commands.cluster_create.s3.put_file_to_bucket")
@mock.patch("commands.cluster_create.s3.ensure_bucket_exists")
@mock.patch("commands.cluster_create.config_wrangling.set_up_arkime_config_dir")
def test_WHEN_set_up_arkime_config_called_AND_happy_path_THEN_as_expected(mock_set_up_config_dir, mock_ensure_bucket, mock_put_file,
                                                                          mock_get_capture_archive, mock_get_viewer_archive,
                                                                          mock_get_version, mock_put_ssm_param, mock_get_ssm_param):
    # Set up our mock
    test_env = AwsEnvironment("XXXXXXXXXXX", "my-region-1", "profile")
    bucket_name = constants.get_config_bucket_name(test_env.aws_account, test_env.aws_region, "cluster-name")
    capture_s3_key = constants.get_capture_config_s3_key("1")
    viewer_s3_key = constants.get_viewer_config_s3_key("1")

    mock_provider = mock.Mock()
    mock_provider.get_aws_env.return_value = test_env

    test_capture_tarball = local_file.TarGzDirectory("/capture", "/capture.tgz")
    test_capture_tarball._exists = True
    mock_get_capture_archive.return_value = test_capture_tarball

    test_viewer_tarball = local_file.TarGzDirectory("/viewer", "/viewer.tgz")
    test_viewer_tarball._exists = True
    mock_get_viewer_archive.return_value = test_viewer_tarball

    capture_metadata = config_wrangling.ConfigDetails(
        s3=config_wrangling.S3Details(bucket_name, capture_s3_key),
        version=VersionInfo("1", "1", "abcd1234", "v1-1-12312", "2023-01-01 01:01:01")
    )
    viewer_metadata = config_wrangling.ConfigDetails(
        s3=config_wrangling.S3Details(bucket_name, viewer_s3_key),
        version=VersionInfo("2", "1", "2345bcde", "v1-1-12312", "2023-01-01 01:01:01")
    )
    mock_get_version.side_effect = [
        capture_metadata.version,
        viewer_metadata.version,
    ]

    mock_get_ssm_param.side_effect = ssm_ops.ParamDoesNotExist("param")

    # Run our test
    _set_up_arkime_config("cluster-name", mock_provider)

    # Check our results
    expected_set_up_config_dir_calls = [
        mock.call("cluster-name", test_env, constants.get_repo_root_dir())
    ]
    assert expected_set_up_config_dir_calls == mock_set_up_config_dir.call_args_list

    expected_mock_ensure_bucket_calls = [
        mock.call(bucket_name, mock_provider)
    ]
    assert expected_mock_ensure_bucket_calls == mock_ensure_bucket.call_args_list

    expected_put_file_calls = [
        mock.call(
            local_file.S3File(test_capture_tarball, metadata=capture_metadata.version.to_dict()),
            bucket_name,
            capture_s3_key,
            mock.ANY
        ),
        mock.call(
            local_file.S3File(test_viewer_tarball, metadata=viewer_metadata.version.to_dict()),
            bucket_name,
            viewer_s3_key,
            mock.ANY
        ),
    ]
    assert expected_put_file_calls == mock_put_file.call_args_list

    expected_put_ssm_param_calls = [
        mock.call(
            constants.get_capture_config_details_ssm_param_name("cluster-name"),
            json.dumps(capture_metadata.to_dict()),
            mock.ANY,
            description=mock.ANY,
            overwrite=True,
        ),
        mock.call(
            constants.get_viewer_config_details_ssm_param_name("cluster-name"),
            json.dumps(viewer_metadata.to_dict()),
            mock.ANY,
            description=mock.ANY,
            overwrite=True,
        ),
    ]
    assert expected_put_ssm_param_calls == mock_put_ssm_param.call_args_list

@mock.patch("commands.cluster_create.ssm_ops.get_ssm_param_value")
@mock.patch("commands.cluster_create.ssm_ops.put_ssm_param")
@mock.patch("commands.cluster_create.get_version_info")
@mock.patch("commands.cluster_create.config_wrangling.get_viewer_config_archive")
@mock.patch("commands.cluster_create.config_wrangling.get_capture_config_archive")
@mock.patch("commands.cluster_create.s3.put_file_to_bucket")
@mock.patch("commands.cluster_create.s3.ensure_bucket_exists")
@mock.patch("commands.cluster_create.config_wrangling.set_up_arkime_config_dir")
def test_WHEN_set_up_arkime_config_called_AND_config_exists_THEN_as_expected(mock_set_up_config_dir, mock_ensure_bucket, mock_put_file,
                                                                          mock_get_capture_archive, mock_get_viewer_archive,
                                                                          mock_get_version, mock_put_ssm_param, mock_get_ssm_param):
    # Set up our mock
    test_env = AwsEnvironment("XXXXXXXXXXX", "my-region-1", "profile")
    bucket_name = constants.get_config_bucket_name(test_env.aws_account, test_env.aws_region, "cluster-name")
    capture_s3_key = constants.get_capture_config_s3_key("1")
    viewer_s3_key = constants.get_viewer_config_s3_key("1")

    mock_provider = mock.Mock()
    mock_provider.get_aws_env.return_value = test_env

    test_capture_tarball = local_file.TarGzDirectory("/capture", "/capture.tgz")
    test_capture_tarball._exists = True
    mock_get_capture_archive.return_value = test_capture_tarball

    test_viewer_tarball = local_file.TarGzDirectory("/viewer", "/viewer.tgz")
    test_viewer_tarball._exists = True
    mock_get_viewer_archive.return_value = test_viewer_tarball

    capture_metadata = config_wrangling.ConfigDetails(
        s3=config_wrangling.S3Details(bucket_name, capture_s3_key),
        version=VersionInfo("1", "1", "abcd1234", "v1-1-12312", "2023-01-01 01:01:01")
    )
    viewer_metadata = config_wrangling.ConfigDetails(
        s3=config_wrangling.S3Details(bucket_name, viewer_s3_key),
        version=VersionInfo("2", "1", "2345bcde", "v1-1-12312", "2023-01-01 01:01:01")
    )
    mock_get_version.side_effect = [
        capture_metadata.version,
        viewer_metadata.version,
    ]

    mock_get_ssm_param.side_effect = ["blah", "bleh"] # Both configs exist

    # Run our test
    _set_up_arkime_config("cluster-name", mock_provider)

    # Check our results
    expected_set_up_config_dir_calls = [
        mock.call("cluster-name", test_env, constants.get_repo_root_dir())
    ]
    assert expected_set_up_config_dir_calls == mock_set_up_config_dir.call_args_list

    expected_mock_ensure_bucket_calls = [
        mock.call(bucket_name, mock_provider)
    ]
    assert expected_mock_ensure_bucket_calls == mock_ensure_bucket.call_args_list

    expected_put_file_calls = []
    assert expected_put_file_calls == mock_put_file.call_args_list

    expected_put_ssm_param_calls = []
    assert expected_put_ssm_param_calls == mock_put_ssm_param.call_args_list

class SysExitCalled(Exception):
    pass

@mock.patch("commands.cluster_create.sys.exit")
@mock.patch("commands.cluster_create.s3.ensure_bucket_exists")
@mock.patch("commands.cluster_create.config_wrangling.set_up_arkime_config_dir")
def test_WHEN_set_up_arkime_config_called_AND_couldnt_make_bucket_THEN_as_expected(mock_set_up_config_dir, mock_ensure_bucket, mock_exit):
    # Set up our mock
    test_env = AwsEnvironment("XXXXXXXXXXX", "my-region-1", "profile")

    mock_provider = mock.Mock()
    mock_provider.get_aws_env.return_value = test_env

    mock_ensure_bucket.side_effect = s3.CouldntEnsureBucketExists("")

    mock_exit.side_effect = SysExitCalled()

    # Run our test
    with pytest.raises(SysExitCalled):
        _set_up_arkime_config("cluster-name", mock_provider)

    # Check our results
    expected_mock_ensure_bucket_calls = [
        mock.call(constants.get_config_bucket_name("XXXXXXXXXXX", "my-region-1", "cluster-name"), mock_provider)
    ]
    assert expected_mock_ensure_bucket_calls == mock_ensure_bucket.call_args_list

    expected_exit_calls = [mock.call(1)]
    assert expected_exit_calls == mock_exit.call_args_list

@mock.patch("commands.cluster_create.ssm_ops.get_ssm_param_json_value")
def test_WHEN_tag_domain_called_THEN_as_expected(mock_get_ssm_json):
    # Set up our mock
    mock_os_client = mock.Mock()
    mock_provider = mock.Mock()
    mock_provider.get_opensearch.return_value = mock_os_client

    mock_get_ssm_json.return_value = "os-arn"

    # Run our test
    _tag_domain("MyCluster", mock_provider)

    # Check our results
    expected_get_ssm_json_calls = [
        mock.call(constants.get_opensearch_domain_ssm_param_name("MyCluster"), "domainArn", mock_provider)
    ]
    assert expected_get_ssm_json_calls == mock_get_ssm_json.call_args_list

    expected_add_tag_calls = [
        mock.call(
            ARN="os-arn",
            TagList=[
                {"Key": "arkime_cluster", "Value": "MyCluster"},
            ]
        )
    ]
    assert expected_add_tag_calls == mock_os_client.add_tags.call_args_list

@mock.patch("commands.cluster_create.ssm_ops.get_ssm_param_value")
def test_WHEN_is_initial_invocation_called_THEN_as_expected(mock_get_ssm):
    # Set up our mock
    mock_provider = mock.Mock()

    # TEST: This is the "initial" invocation of the command
    mock_get_ssm.side_effect = ssm_ops.ParamDoesNotExist("")

    actual_value = _is_initial_invocation("MyCluster", mock_provider)
    assert True == actual_value
    
    expected_get_ssm_calls = [
        mock.call(constants.get_cluster_ssm_param_name("MyCluster"), mock_provider)
    ]
    assert expected_get_ssm_calls == mock_get_ssm.call_args_list

    # TEST: This is not the "initial" invocation of the command
    mock_get_ssm.side_effect = ["blah"]

    actual_value = _is_initial_invocation("MyCluster", mock_provider)
    assert False == actual_value

def test_WHEN_get_stacks_to_deploy_called_THEN_as_expected():
    cluster_name = "MyCluster"
    user_config = UserConfig(1, 30, 365, 2, 30)   

    # TEST: No Viewer VPC
    cluster_plan = ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 1, 2, 1),
        VpcPlan(DEFAULT_VPC_CIDR, DEFAULT_NUM_AZS, DEFAULT_CAPTURE_PUBLIC_MASK),
        EcsSysResourcePlan(3584, 15360),
        OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search")),
        S3Plan(DEFAULT_S3_STORAGE_CLASS, DEFAULT_S3_STORAGE_DAYS),
        ViewerNodesPlan(4, 2),
        None
    )

    actual_value = _get_stacks_to_deploy(cluster_name, user_config, cluster_plan)

    expected_value = [
        constants.get_capture_bucket_stack_name(cluster_name),
        constants.get_capture_nodes_stack_name(cluster_name),
        constants.get_capture_vpc_stack_name(cluster_name),
        constants.get_opensearch_domain_stack_name(cluster_name),
        constants.get_viewer_nodes_stack_name(cluster_name)
    ]
    assert expected_value == actual_value

def test_WHEN_get_cdk_context_called_THEN_as_expected():
    cluster_name = "MyCluster"
    cert_arn = "arn:cert"
    aws_env = AwsEnvironment("XXXXXXXXXXX", "my-region-1", "profile")
    user_config = UserConfig(1, 30, 365, 2, 30)

    # TEST: No Viewer VPC
    cluster_plan = ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 1, 2, 1),
        VpcPlan(DEFAULT_VPC_CIDR, DEFAULT_NUM_AZS, DEFAULT_CAPTURE_PUBLIC_MASK),
        EcsSysResourcePlan(3584, 15360),
        OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search")),
        S3Plan(DEFAULT_S3_STORAGE_CLASS, DEFAULT_S3_STORAGE_DAYS),
        ViewerNodesPlan(4, 2),
        None
    )

    actual_value = _get_cdk_context(cluster_name, user_config, cluster_plan, cert_arn, aws_env)

    expected_value = {
        constants.CDK_CONTEXT_CMD_VAR: constants.CMD_cluster_create,
        constants.CDK_CONTEXT_PARAMS_VAR: shlex.quote(json.dumps({
            "nameCluster": cluster_name,
            "nameCaptureBucketStack": constants.get_capture_bucket_stack_name(cluster_name),
            "nameCaptureBucketSsmParam": constants.get_capture_bucket_ssm_param_name(cluster_name),
            "nameCaptureConfigSsmParam": constants.get_capture_config_details_ssm_param_name(cluster_name),
            "nameCaptureDetailsSsmParam": constants.get_capture_details_ssm_param_name(cluster_name),
            "nameCaptureNodesStack": constants.get_capture_nodes_stack_name(cluster_name),
            "nameCaptureVpcStack": constants.get_capture_vpc_stack_name(cluster_name),
            "nameClusterConfigBucket": constants.get_config_bucket_name(aws_env.aws_account, aws_env.aws_region, cluster_name),
            "nameClusterSsmParam": constants.get_cluster_ssm_param_name(cluster_name),
            "nameOSDomainStack": constants.get_opensearch_domain_stack_name(cluster_name),
            "nameOSDomainSsmParam": constants.get_opensearch_domain_ssm_param_name(cluster_name),
            "nameViewerCertArn": cert_arn,
            "nameViewerConfigSsmParam": constants.get_viewer_config_details_ssm_param_name(cluster_name),
            "nameViewerDetailsSsmParam": constants.get_viewer_details_ssm_param_name(cluster_name),
            "nameViewerNodesStack": constants.get_viewer_nodes_stack_name(cluster_name),
            "planCluster": json.dumps(cluster_plan.to_dict()),
            "userConfig": json.dumps(user_config.to_dict()),
        }))
    }

    assert expected_value == actual_value
    