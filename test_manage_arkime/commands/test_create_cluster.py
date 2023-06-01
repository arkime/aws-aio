import json
import pytest
import shlex
import unittest.mock as mock

import aws_interactions.ssm_operations as ssm_ops
from commands.create_cluster import cmd_create_cluster, _set_up_viewer_cert, _get_capacity_plan, MustProvideAllParams
import constants as constants
from core.capacity_planning import (CaptureNodesPlan, EcsSysResourcePlan, MINIMUM_TRAFFIC, OSDomainPlan, DataNodesPlan, MasterNodesPlan,
                                    CaptureVpcPlan, ClusterPlan, DEFAULT_SPI_DAYS, DEFAULT_SPI_REPLICAS, DEFAULT_NUM_AZS)

@mock.patch("commands.create_cluster.AwsClientProvider", mock.Mock())
@mock.patch("commands.create_cluster._get_capacity_plan")
@mock.patch("commands.create_cluster._set_up_viewer_cert")
@mock.patch("commands.create_cluster.CdkClient")
def test_WHEN_cmd_create_cluster_called_THEN_cdk_command_correct(mock_cdk_client_cls, mock_set_up, mock_get_plans):
    # Set up our mock
    mock_set_up.return_value = "arn"

    mock_client = mock.Mock()
    mock_cdk_client_cls.return_value = mock_client

    cluster_plan = ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 20, 25, 1),
        CaptureVpcPlan(DEFAULT_NUM_AZS),
        EcsSysResourcePlan(3584, 15360),
        OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search"))
    )
    mock_get_plans.return_value = cluster_plan

    # Run our test
    cmd_create_cluster("profile", "region", "my-cluster", None, None, None)

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
def test_WHEN_get_capacity_plan_called_AND_use_existing_THEN_as_expected(mock_ssm_ops):
    # Set up our mock
    mock_ssm_ops.ParamDoesNotExist = ssm_ops.ParamDoesNotExist

    mock_ssm_ops.get_ssm_param_json_value.return_value = {
        "captureNodes": {
            "instanceType":"m5.xlarge","desiredCount":10,"maxCount":12,"minCount":1
        },
        "captureVpc": {
            "numAzs": 3
        },
        "ecsResources": {
            "cpu": 3584, "memory": 15360
        },
        "osDomain": {
            "dataNodes": {
                "count": 6, "instanceType": "t3.small.search", "volumeSize": 100
            },
            "masterNodes": {
                "count": 3, "instanceType": "c6g.2xlarge.search",
            }
        }
    }

    mock_provider = mock.Mock()

    # Run our test
    actual_value = _get_capacity_plan("my-cluster", None, None, None, mock_provider)

    # Check our results
    assert CaptureNodesPlan("m5.xlarge", 10, 12, 1) == actual_value.captureNodes
    assert CaptureVpcPlan(3) == actual_value.captureVpc
    assert EcsSysResourcePlan(3584, 15360) == actual_value.ecsResources
    assert OSDomainPlan(DataNodesPlan(6, "t3.small.search", 100), MasterNodesPlan(3, "c6g.2xlarge.search")) == actual_value.osDomain

    expected_get_ssm_calls = [
        mock.call(constants.get_cluster_ssm_param_name("my-cluster"), "capacityPlan", mock.ANY)
    ]
    assert expected_get_ssm_calls == mock_ssm_ops.get_ssm_param_json_value.call_args_list

@mock.patch("commands.create_cluster.get_os_domain_plan")
@mock.patch("commands.create_cluster.get_capture_node_capacity_plan")
@mock.patch("commands.create_cluster.ssm_ops")
def test_WHEN_get_capacity_plan_called_AND_use_default_THEN_as_expected(mock_ssm_ops, mock_get_cap, mock_get_os):
    # Set up our mock
    mock_ssm_ops.ParamDoesNotExist = ssm_ops.ParamDoesNotExist
    mock_ssm_ops.get_ssm_param_json_value.side_effect = ssm_ops.ParamDoesNotExist("")

    mock_get_cap.return_value = CaptureNodesPlan("m5.xlarge", 1, 2, 1)
    mock_get_os.return_value = OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search"))

    mock_provider = mock.Mock()

    # Run our test
    actual_value = _get_capacity_plan("my-cluster", None, None, None, mock_provider)

    # Check our results
    assert mock_get_cap.return_value == actual_value.captureNodes
    assert CaptureVpcPlan(DEFAULT_NUM_AZS) == actual_value.captureVpc
    assert mock_get_os.return_value == actual_value.osDomain
    assert EcsSysResourcePlan(3584, 15360) == actual_value.ecsResources

    expected_get_cap_calls = [
        mock.call(MINIMUM_TRAFFIC)
    ]
    assert expected_get_cap_calls == mock_get_cap.call_args_list

    expected_get_os_calls = [
        mock.call(MINIMUM_TRAFFIC, DEFAULT_SPI_DAYS, DEFAULT_SPI_REPLICAS, DEFAULT_NUM_AZS)
    ]
    assert expected_get_os_calls == mock_get_os.call_args_list

    expected_get_ssm_calls = [
        mock.call(constants.get_cluster_ssm_param_name("my-cluster"), "capacityPlan", mock.ANY)
    ]
    assert expected_get_ssm_calls == mock_ssm_ops.get_ssm_param_json_value.call_args_list

@mock.patch("commands.create_cluster.get_os_domain_plan")
@mock.patch("commands.create_cluster.get_capture_node_capacity_plan")
@mock.patch("commands.create_cluster.ssm_ops")
def test_WHEN_get_capacity_plan_called_AND_gen_plan_THEN_as_expected(mock_ssm_ops, mock_get_cap, mock_get_os):
    # Set up our mock
    mock_ssm_ops.ParamDoesNotExist = ssm_ops.ParamDoesNotExist
    mock_ssm_ops.get_ssm_param_json_value.side_effect = ssm_ops.ParamDoesNotExist("")

    mock_get_cap.return_value = CaptureNodesPlan("m5.xlarge", 10, 12, 1)
    mock_get_os.return_value = OSDomainPlan(DataNodesPlan(20, "r6g.large.search", 100), MasterNodesPlan(3, "m6g.large.search"))

    mock_provider = mock.Mock()

    # Run our test
    actual_value = _get_capacity_plan("my-cluster", 10, 40, 2, mock_provider)

    # Check our results
    assert mock_get_cap.return_value == actual_value.captureNodes
    assert CaptureVpcPlan(DEFAULT_NUM_AZS) == actual_value.captureVpc
    assert mock_get_os.return_value == actual_value.osDomain
    assert EcsSysResourcePlan(3584, 15360) == actual_value.ecsResources

    expected_get_cap_calls = [
        mock.call(10)
    ]
    assert expected_get_cap_calls == mock_get_cap.call_args_list

    expected_get_os_calls = [
        mock.call(10, 40, 2, DEFAULT_NUM_AZS)
    ]
    assert expected_get_os_calls == mock_get_os.call_args_list

    expected_get_ssm_calls = []
    assert expected_get_ssm_calls == mock_ssm_ops.get_ssm_param_json_value.call_args_list

def test_WHEN_get_capacity_plan_called_AND_not_all_params_THEN_as_expected():
    # Set up our mock
    mock_provider = mock.Mock()

    # Run our test
    with pytest.raises(MustProvideAllParams):
        _get_capacity_plan("my-cluster", 10, None, None, mock_provider)

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