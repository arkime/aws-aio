import json
import shlex
import unittest.mock as mock

import aws_interactions.ssm_operations as ssm_ops
from commands.create_cluster import cmd_create_cluster, _set_up_viewer_cert
import constants as constants
from core.capacity_planning import CaptureNodesPlan

@mock.patch("commands.create_cluster._set_up_viewer_cert")
@mock.patch("commands.create_cluster.CdkClient")
def test_WHEN_cmd_create_cluster_called_THEN_cdk_command_correct(mock_cdk_client_cls, mock_set_up):
    # Set up our mock
    mock_set_up.return_value = "arn"

    mock_client = mock.Mock()
    mock_cdk_client_cls.return_value = mock_client

    # Run our test
    cmd_create_cluster("profile", "region", "my-cluster", 40)

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
                    "planCaptureNodes": json.dumps(CaptureNodesPlan("m5.xlarge", 20, 25).to_dict())
                }))
            }
        )
    ]
    assert expected_calls == mock_client.deploy.call_args_list

    expected_set_up_calls = [
        mock.call("profile", "region", "my-cluster")
    ]
    assert expected_set_up_calls == mock_set_up.call_args_list

@mock.patch("commands.create_cluster.AwsClientProvider", mock.Mock())
@mock.patch("commands.create_cluster.upload_default_elb_cert")
@mock.patch("commands.create_cluster.ssm_ops")
def test_WHEN_set_up_viewer_cert_called_THEN_set_up_correctly(mock_ssm_ops, mock_upload):
    # Set up our mock
    mock_ssm_ops.ParamDoesNotExist = ssm_ops.ParamDoesNotExist
    mock_ssm_ops.get_ssm_param_value.side_effect = ssm_ops.ParamDoesNotExist("")

    mock_upload.return_value = "arn"

    # Run our test
    actual_value = _set_up_viewer_cert("profile", "region", "my-cluster")

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

    # Run our test
    actual_value = _set_up_viewer_cert("profile", "region", "my-cluster")

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