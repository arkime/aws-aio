import json
import shlex
import unittest.mock as mock

from manage_arkime.commands.create_cluster import cmd_create_cluster
import manage_arkime.constants as constants

@mock.patch("manage_arkime.commands.create_cluster.CdkClient")
def test_WHEN_cmd_create_cluster_called_THEN_cdk_command_correct(mock_cdk_client_cls):
    # Set up our mock
    mock_client = mock.Mock()
    mock_cdk_client_cls.return_value = mock_client

    # Run our test
    cmd_create_cluster("profile", "region", "my-cluster")

    # Check our results
    expected_calls = [
        mock.call(
            [
                constants.get_capture_bucket_stack_name("my-cluster"),
                constants.get_capture_nodes_stack_name("my-cluster"),
                constants.get_capture_vpc_stack_name("my-cluster"),
                constants.get_opensearch_domain_stack_name("my-cluster")
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
                }))
            }
        )
    ]
    assert expected_calls == mock_client.deploy.call_args_list