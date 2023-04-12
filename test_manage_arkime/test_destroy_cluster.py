import json
import shlex
import unittest.mock as mock

from manage_arkime.commands.destroy_cluster import cmd_destroy_cluster
import manage_arkime.constants as constants

TEST_CLUSTER = "my-cluster"

@mock.patch("manage_arkime.commands.destroy_cluster.destroy_os_domain_and_wait")
@mock.patch("manage_arkime.commands.destroy_cluster.destroy_s3_bucket")
@mock.patch("manage_arkime.commands.destroy_cluster.CdkClient")
def test_WHEN_cmd_destroy_cluster_called_AND_dont_destroy_everything_THEN_expected_cmds(mock_cdk_client_cls, mock_destroy_bucket, mock_destroy_domain):
    # Set up our mock
    mock_client = mock.Mock()
    mock_cdk_client_cls.return_value = mock_client

    # Run our test
    cmd_destroy_cluster("profile", "region", TEST_CLUSTER, False)

    # Check our results
    mock_destroy_bucket.assert_not_called()
    mock_destroy_domain.assert_not_called()

    expected_calls = [
        mock.call(
            [
                constants.get_capture_nodes_stack_name(TEST_CLUSTER),
                constants.get_viewer_nodes_stack_name(TEST_CLUSTER),
            ],
            aws_profile="profile",
            aws_region="region",
            context={
                constants.CDK_CONTEXT_CMD_VAR: constants.CMD_DESTROY_CLUSTER,
                constants.CDK_CONTEXT_PARAMS_VAR: shlex.quote(json.dumps({
                    "nameCluster": TEST_CLUSTER,
                    "nameCaptureBucketStack": constants.get_capture_bucket_stack_name(TEST_CLUSTER),
                    "nameCaptureBucketSsmParam": constants.get_capture_bucket_ssm_param_name(TEST_CLUSTER),
                    "nameCaptureNodesStack": constants.get_capture_nodes_stack_name(TEST_CLUSTER),
                    "nameCaptureVpcStack": constants.get_capture_vpc_stack_name(TEST_CLUSTER),
                    "nameClusterSsmParam": constants.get_cluster_ssm_param_name(TEST_CLUSTER),
                    "nameOSDomainStack": constants.get_opensearch_domain_stack_name(TEST_CLUSTER),
                    "nameOSDomainSsmParam": constants.get_opensearch_domain_ssm_param_name(TEST_CLUSTER),
                    "nameViewerNodesStack": constants.get_viewer_nodes_stack_name(TEST_CLUSTER),
                }))
            }
        )
    ]
    assert expected_calls == mock_client.destroy.call_args_list

@mock.patch("manage_arkime.commands.destroy_cluster.AwsClientProvider", mock.Mock())
@mock.patch("manage_arkime.commands.destroy_cluster.destroy_os_domain_and_wait")
@mock.patch("manage_arkime.commands.destroy_cluster.destroy_s3_bucket")
@mock.patch("manage_arkime.commands.destroy_cluster.get_ssm_param_value")
@mock.patch("manage_arkime.commands.destroy_cluster.CdkClient")
def test_WHEN_cmd_destroy_cluster_called_AND_destroy_everything_THEN_expected_cmds(mock_cdk_client_cls, mock_get_ssm, mock_destroy_bucket, mock_destroy_domain):
    # Set up our mock
    mock_client = mock.Mock()
    mock_cdk_client_cls.return_value = mock_client

    mock_get_ssm.side_effect = [
        constants.get_opensearch_domain_ssm_param_name(TEST_CLUSTER),
        constants.get_capture_bucket_ssm_param_name(TEST_CLUSTER),
    ]

    # Run our test
    cmd_destroy_cluster("profile", "region", TEST_CLUSTER, True)

    # Check our results
    expected_destroy_domain_calls = [
        mock.call(
            domain_name=constants.get_opensearch_domain_ssm_param_name(TEST_CLUSTER),
            aws_client_provider=mock.ANY
        )
    ]
    assert expected_destroy_domain_calls == mock_destroy_domain.call_args_list


    expected_destroy_bucket_calls = [
        mock.call(
            bucket_name=constants.get_capture_bucket_ssm_param_name(TEST_CLUSTER),
            aws_client_provider=mock.ANY
        )
    ]
    assert expected_destroy_bucket_calls == mock_destroy_bucket.call_args_list

    expected_cdk_calls = [
        mock.call(
            [
                constants.get_capture_bucket_stack_name(TEST_CLUSTER),
                constants.get_capture_nodes_stack_name(TEST_CLUSTER),
                constants.get_capture_vpc_stack_name(TEST_CLUSTER),
                constants.get_opensearch_domain_stack_name(TEST_CLUSTER),
                constants.get_viewer_nodes_stack_name(TEST_CLUSTER)
            ],
            aws_profile="profile",
            aws_region="region",
            context={
                constants.CDK_CONTEXT_CMD_VAR: constants.CMD_DESTROY_CLUSTER,
                constants.CDK_CONTEXT_PARAMS_VAR: shlex.quote(json.dumps({
                    "nameCluster": TEST_CLUSTER,
                    "nameCaptureBucketStack": constants.get_capture_bucket_stack_name(TEST_CLUSTER),
                    "nameCaptureBucketSsmParam": constants.get_capture_bucket_ssm_param_name(TEST_CLUSTER),
                    "nameCaptureNodesStack": constants.get_capture_nodes_stack_name(TEST_CLUSTER),
                    "nameCaptureVpcStack": constants.get_capture_vpc_stack_name(TEST_CLUSTER),
                    "nameClusterSsmParam": constants.get_cluster_ssm_param_name(TEST_CLUSTER),
                    "nameOSDomainStack": constants.get_opensearch_domain_stack_name(TEST_CLUSTER),
                    "nameOSDomainSsmParam": constants.get_opensearch_domain_ssm_param_name(TEST_CLUSTER),
                    "nameViewerNodesStack": constants.get_viewer_nodes_stack_name(TEST_CLUSTER),
                }))
            }
        )
    ]
    assert expected_cdk_calls == mock_client.destroy.call_args_list