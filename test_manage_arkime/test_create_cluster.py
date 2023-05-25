import json
import shlex
import unittest.mock as mock

import aws_interactions.ssm_operations as ssm_ops
from commands.create_cluster import cmd_create_cluster, _set_up_viewer_cert, _get_capacity_plans
import constants as constants
from core.capacity_planning import CaptureNodesPlan, EcsSysResourcePlan, MINIMUM_TRAFFIC

@mock.patch("commands.create_cluster.AwsClientProvider", mock.Mock())
@mock.patch("commands.create_cluster._get_capacity_plans")
@mock.patch("commands.create_cluster._set_up_viewer_cert")
@mock.patch("commands.create_cluster.CdkClient")
def test_WHEN_cmd_create_cluster_called_THEN_cdk_command_correct(mock_cdk_client_cls, mock_set_up, mock_get_plans):
    # Set up our mock
    mock_set_up.return_value = "arn"

    mock_client = mock.Mock()
    mock_cdk_client_cls.return_value = mock_client

    cap_plan = CaptureNodesPlan("m5.xlarge", 20, 25, 1)
    ecs_plan = EcsSysResourcePlan(3584, 15360)
    mock_get_plans.return_value = (cap_plan, ecs_plan)

    # Run our test
    cmd_create_cluster("profile", "region", "my-cluster", None)

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
                    "planCaptureNodes": json.dumps(cap_plan.to_dict()),
                    "planEcsResources": json.dumps(ecs_plan.to_dict())
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
def test_WHEN_get_capacity_plans_called_AND_use_existing_THEN_as_expected(mock_ssm_ops):
    # Set up our mock
    mock_ssm_ops.get_ssm_param_json_value.return_value = {"instanceType":"m5.xlarge","desiredCount":10,"maxCount":12,"minCount":1}

    mock_provider = mock.Mock()

    # Run our test
    actual_cap, actual_resources = _get_capacity_plans("my-cluster", None, mock_provider)

    # Check our results
    assert CaptureNodesPlan("m5.xlarge", 10, 12, 1) == actual_cap
    assert EcsSysResourcePlan(3584, 15360) == actual_resources

    expected_get_ssm_calls = [
        mock.call(constants.get_cluster_ssm_param_name("my-cluster"), "captureNodesPlan", mock.ANY)
    ]
    assert expected_get_ssm_calls == mock_ssm_ops.get_ssm_param_json_value.call_args_list

@mock.patch("commands.create_cluster.get_capture_node_capacity_plan")
@mock.patch("commands.create_cluster.ssm_ops")
def test_WHEN_get_capacity_plans_called_AND_use_default_THEN_as_expected(mock_ssm_ops, mock_get_cap):
    # Set up our mock
    mock_ssm_ops.ParamDoesNotExist = ssm_ops.ParamDoesNotExist
    mock_ssm_ops.get_ssm_param_json_value.side_effect = ssm_ops.ParamDoesNotExist("")

    mock_get_cap.return_value = CaptureNodesPlan("m5.xlarge", 1, 2, 1)

    mock_provider = mock.Mock()

    # Run our test
    actual_cap, actual_resources = _get_capacity_plans("my-cluster", None, mock_provider)

    # Check our results
    assert mock_get_cap.return_value == actual_cap
    assert EcsSysResourcePlan(3584, 15360) == actual_resources

    expected_get_cap_calls = [
        mock.call(MINIMUM_TRAFFIC)
    ]
    assert expected_get_cap_calls == mock_get_cap.call_args_list

    expected_get_ssm_calls = [
        mock.call(constants.get_cluster_ssm_param_name("my-cluster"), "captureNodesPlan", mock.ANY)
    ]
    assert expected_get_ssm_calls == mock_ssm_ops.get_ssm_param_json_value.call_args_list

@mock.patch("commands.create_cluster.get_capture_node_capacity_plan")
@mock.patch("commands.create_cluster.ssm_ops")
def test_WHEN_get_capacity_plans_called_AND_gen_plan_THEN_as_expected(mock_ssm_ops, mock_get_cap):
    # Set up our mock
    mock_ssm_ops.ParamDoesNotExist = ssm_ops.ParamDoesNotExist
    mock_ssm_ops.get_ssm_param_json_value.side_effect = ssm_ops.ParamDoesNotExist("")

    mock_get_cap.return_value = CaptureNodesPlan("m5.xlarge", 10, 12, 1)

    mock_provider = mock.Mock()

    # Run our test
    actual_cap, actual_resources = _get_capacity_plans("my-cluster", 20, mock_provider)

    # Check our results
    assert mock_get_cap.return_value == actual_cap
    assert EcsSysResourcePlan(3584, 15360) == actual_resources

    expected_get_cap_calls = [
        mock.call(20)
    ]
    assert expected_get_cap_calls == mock_get_cap.call_args_list

    expected_get_ssm_calls = []
    assert expected_get_ssm_calls == mock_ssm_ops.get_ssm_param_json_value.call_args_list


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