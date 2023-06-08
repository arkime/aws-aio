import json
import pytest
import shlex
import unittest.mock as mock

import aws_interactions.ssm_operations as ssm_ops
from commands.create_cluster import cmd_create_cluster, _set_up_viewer_cert, _get_capacity_plan, _get_user_config
import constants as constants
from core.capacity_planning import (CaptureNodesPlan, EcsSysResourcePlan, MINIMUM_TRAFFIC, OSDomainPlan, DataNodesPlan, MasterNodesPlan,
                                    CaptureVpcPlan, ClusterPlan, DEFAULT_SPI_DAYS, DEFAULT_REPLICAS, DEFAULT_NUM_AZS, S3Plan,
                                    DEFAULT_S3_STORAGE_CLASS, DEFAULT_S3_STORAGE_DAYS, DEFAULT_HISTORY_DAYS)
from core.user_config import UserConfig

@mock.patch("commands.create_cluster.AwsClientProvider", mock.Mock())
@mock.patch("commands.create_cluster._get_user_config")
@mock.patch("commands.create_cluster._get_capacity_plan")
@mock.patch("commands.create_cluster._set_up_viewer_cert")
@mock.patch("commands.create_cluster.CdkClient")
def test_WHEN_cmd_create_cluster_called_THEN_cdk_command_correct(mock_cdk_client_cls, mock_set_up, mock_get_plans, mock_get_config):
    # Set up our mock
    mock_set_up.return_value = "arn"

    mock_client = mock.Mock()
    mock_cdk_client_cls.return_value = mock_client

    user_config = UserConfig(1, 30, 365, 2, 30)
    mock_get_config.return_value = user_config

    cluster_plan = ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 20, 25, 1),
        CaptureVpcPlan(DEFAULT_NUM_AZS),
        EcsSysResourcePlan(3584, 15360),
        OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search")),
        S3Plan(DEFAULT_S3_STORAGE_CLASS, DEFAULT_S3_STORAGE_DAYS)
    )
    mock_get_plans.return_value = cluster_plan

    # Run our test
    cmd_create_cluster("profile", "region", "my-cluster", None, None, None, None, None)

    # Check our results
    expected_calls = [
        mock.call(
            [
                constants.get_capture_bucket_stack_name("my-cluster"),
                constants.get_capture_nodes_stack_name("my-cluster"),
                constants.get_capture_vpc_stack_name("my-cluster"),
                constants.get_opensearch_domain_stack_name("my-cluster"),
                constants.get_viewer_nodes_stack_name("my-cluster"),
            ],
            aws_profile="profile",
            aws_region="region",
            context={
                constants.CDK_CONTEXT_CMD_VAR: constants.CMD_CREATE_CLUSTER,
                constants.CDK_CONTEXT_PARAMS_VAR: shlex.quote(json.dumps({
                    "nameCluster": "my-cluster",
                    "nameCaptureBucketStack": constants.get_capture_bucket_stack_name("my-cluster"),
                    "nameCaptureBucketSsmParam": constants.get_capture_bucket_ssm_param_name("my-cluster"),
                    "nameCaptureNodesStack": constants.get_capture_nodes_stack_name("my-cluster"),
                    "nameCaptureVpcStack": constants.get_capture_vpc_stack_name("my-cluster"),
                    "nameClusterSsmParam": constants.get_cluster_ssm_param_name("my-cluster"),
                    "nameOSDomainStack": constants.get_opensearch_domain_stack_name("my-cluster"),
                    "nameOSDomainSsmParam": constants.get_opensearch_domain_ssm_param_name("my-cluster"),
                    "nameViewerCertArn": "arn",
                    "nameViewerDnsSsmParam": constants.get_viewer_dns_ssm_param_name("my-cluster"),
                    "nameViewerPassSsmParam": constants.get_viewer_password_ssm_param_name("my-cluster"),
                    "nameViewerUserSsmParam": constants.get_viewer_user_ssm_param_name("my-cluster"),
                    "nameViewerNodesStack": constants.get_viewer_nodes_stack_name("my-cluster"),
                    "planCluster": json.dumps(cluster_plan.to_dict()),
                    "userConfig": json.dumps(user_config.to_dict()),
                }))
            }
        )
    ]
    assert expected_calls == mock_client.deploy.call_args_list

    expected_set_up_calls = [
        mock.call("my-cluster", mock.ANY)
    ]
    assert expected_set_up_calls == mock_set_up.call_args_list

@mock.patch("commands.create_cluster.ssm_ops")
def test_WHEN_get_user_config_called_AND_use_existing_THEN_as_expected(mock_ssm_ops):
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
    actual_value = _get_user_config("my-cluster", None, None, None, None, None, mock_provider)

    # Check our results
    assert UserConfig(1.2, 40, 120, 2, 35) == actual_value

    expected_get_ssm_calls = [
        mock.call(constants.get_cluster_ssm_param_name("my-cluster"), "userConfig", mock.ANY)
    ]
    assert expected_get_ssm_calls == mock_ssm_ops.get_ssm_param_json_value.call_args_list

@mock.patch("commands.create_cluster.ssm_ops")
def test_WHEN_get_user_config_called_AND_partial_update_THEN_as_expected(mock_ssm_ops):
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
    actual_value = _get_user_config("my-cluster", None, 30, None, None, None, mock_provider)

    # Check our results
    assert UserConfig(1.2, 30, 120, 2, 35) == actual_value

    expected_get_ssm_calls = [
        mock.call(constants.get_cluster_ssm_param_name("my-cluster"), "userConfig", mock.ANY)
    ]
    assert expected_get_ssm_calls == mock_ssm_ops.get_ssm_param_json_value.call_args_list

@mock.patch("commands.create_cluster.ssm_ops")
def test_WHEN_get_user_config_called_AND_use_default_THEN_as_expected(mock_ssm_ops):
    # Set up our mock
    mock_ssm_ops.ParamDoesNotExist = ssm_ops.ParamDoesNotExist
    mock_ssm_ops.get_ssm_param_json_value.side_effect = ssm_ops.ParamDoesNotExist("")

    mock_provider = mock.Mock()

    # Run our test
    actual_value = _get_user_config("my-cluster", None, None, None, None, None, mock_provider)

    # Check our results
    assert UserConfig(MINIMUM_TRAFFIC, DEFAULT_SPI_DAYS, DEFAULT_HISTORY_DAYS, DEFAULT_REPLICAS, DEFAULT_S3_STORAGE_DAYS) == actual_value

    expected_get_ssm_calls = [
        mock.call(constants.get_cluster_ssm_param_name("my-cluster"), "userConfig", mock.ANY)
    ]
    assert expected_get_ssm_calls == mock_ssm_ops.get_ssm_param_json_value.call_args_list

@mock.patch("commands.create_cluster.ssm_ops")
def test_WHEN_get_user_config_called_AND_specify_all_THEN_as_expected(mock_ssm_ops):
    # Set up our mock
    mock_ssm_ops.ParamDoesNotExist = ssm_ops.ParamDoesNotExist

    mock_provider = mock.Mock()

    # Run our test
    actual_value = _get_user_config("my-cluster", 10, 40, 120, 2, 35, mock_provider)

    # Check our results
    assert UserConfig(10, 40, 120, 2, 35) == actual_value

    expected_get_ssm_calls = []
    assert expected_get_ssm_calls == mock_ssm_ops.get_ssm_param_json_value.call_args_list


@mock.patch("commands.create_cluster.get_os_domain_plan")
@mock.patch("commands.create_cluster.get_capture_node_capacity_plan")
@mock.patch("commands.create_cluster.ssm_ops")
def test_WHEN_get_capacity_plan_called_THEN_as_expected(mock_ssm_ops, mock_get_cap, mock_get_os):
    # Set up our mock
    mock_ssm_ops.ParamDoesNotExist = ssm_ops.ParamDoesNotExist
    mock_ssm_ops.get_ssm_param_json_value.side_effect = ssm_ops.ParamDoesNotExist("")

    mock_get_cap.return_value = CaptureNodesPlan("m5.xlarge", 1, 2, 1)
    mock_get_os.return_value = OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search"))

    mock_provider = mock.Mock()

    # Run our test
    actual_value = _get_capacity_plan(UserConfig(1, 40, 120, 2, 35))

    # Check our results
    assert mock_get_cap.return_value == actual_value.captureNodes
    assert CaptureVpcPlan(DEFAULT_NUM_AZS) == actual_value.captureVpc
    assert mock_get_os.return_value == actual_value.osDomain
    assert EcsSysResourcePlan(3584, 15360) == actual_value.ecsResources
    assert S3Plan(DEFAULT_S3_STORAGE_CLASS, 35) == actual_value.s3

    expected_get_cap_calls = [
        mock.call(1)
    ]
    assert expected_get_cap_calls == mock_get_cap.call_args_list

    expected_get_os_calls = [
        mock.call(1, 40, 2, DEFAULT_NUM_AZS)
    ]
    assert expected_get_os_calls == mock_get_os.call_args_list

@mock.patch("commands.create_cluster.upload_default_elb_cert")
@mock.patch("commands.create_cluster.ssm_ops")
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

@mock.patch("commands.create_cluster.AwsClientProvider", mock.Mock())
@mock.patch("commands.create_cluster.upload_default_elb_cert")
@mock.patch("commands.create_cluster.ssm_ops")
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