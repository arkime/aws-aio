import json
import shlex
import unittest.mock as mock

from aws_interactions.aws_environment import AwsEnvironment
from aws_interactions.ssm_operations import ParamDoesNotExist
from commands.destroy_cluster import cmd_destroy_cluster, _destroy_viewer_cert, _delete_arkime_config_from_datastore
import core.constants as constants
from core.capacity_planning import (CaptureNodesPlan, EcsSysResourcePlan, OSDomainPlan, DataNodesPlan, MasterNodesPlan,
                                    ClusterPlan, CaptureVpcPlan, S3Plan, DEFAULT_S3_STORAGE_CLASS)
from core.user_config import UserConfig

TEST_CLUSTER = "my-cluster"

@mock.patch("commands.destroy_cluster.AwsClientProvider")
@mock.patch("commands.destroy_cluster._delete_arkime_config_from_datastore")
@mock.patch("commands.destroy_cluster._destroy_viewer_cert")
@mock.patch("commands.destroy_cluster.get_ssm_names_by_path")
@mock.patch("commands.destroy_cluster.destroy_os_domain_and_wait")
@mock.patch("commands.destroy_cluster.destroy_bucket")
@mock.patch("commands.destroy_cluster.CdkClient")
def test_WHEN_cmd_destroy_cluster_called_AND_dont_destroy_everything_THEN_expected_cmds(mock_cdk_client_cls, mock_destroy_bucket,
                                                                                        mock_destroy_domain, mock_ssm_get, mock_destroy_cert,
                                                                                        mock_delete_arkime, mock_aws_provider_cls):
    # Set up our mock
    mock_ssm_get.return_value = []

    mock_client = mock.Mock()
    mock_cdk_client_cls.return_value = mock_client

    aws_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")
    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_aws_env.return_value = aws_env
    mock_aws_provider_cls.return_value = mock_aws_provider

    cluster_plan = ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 1, 2, 1),
        CaptureVpcPlan(2),
        EcsSysResourcePlan(1, 1),
        OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search")),
        S3Plan(DEFAULT_S3_STORAGE_CLASS, 1)
    )

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
            context={
                constants.CDK_CONTEXT_CMD_VAR: constants.CMD_DESTROY_CLUSTER,
                constants.CDK_CONTEXT_PARAMS_VAR: shlex.quote(json.dumps({
                    "nameCluster": TEST_CLUSTER,
                    "nameCaptureBucketStack": constants.get_capture_bucket_stack_name(TEST_CLUSTER),
                    "nameCaptureBucketSsmParam": constants.get_capture_bucket_ssm_param_name(TEST_CLUSTER),
                    "nameCaptureConfigSsmParam": constants.get_capture_config_details_ssm_param_name(TEST_CLUSTER),
                    "nameCaptureNodesStack": constants.get_capture_nodes_stack_name(TEST_CLUSTER),
                    "nameCaptureVpcStack": constants.get_capture_vpc_stack_name(TEST_CLUSTER),
                    "nameClusterConfigBucket": "",
                    "nameClusterSsmParam": constants.get_cluster_ssm_param_name(TEST_CLUSTER),
                    "nameOSDomainStack": constants.get_opensearch_domain_stack_name(TEST_CLUSTER),
                    "nameOSDomainSsmParam": constants.get_opensearch_domain_ssm_param_name(TEST_CLUSTER),
                    "nameViewerCertArn": "N/A",
                    "nameViewerConfigSsmParam": constants.get_viewer_config_details_ssm_param_name(TEST_CLUSTER),
                    "nameViewerDnsSsmParam": constants.get_viewer_dns_ssm_param_name(TEST_CLUSTER),
                    "nameViewerPassSsmParam": constants.get_viewer_password_ssm_param_name(TEST_CLUSTER),
                    "nameViewerUserSsmParam": constants.get_viewer_user_ssm_param_name(TEST_CLUSTER),
                    "nameViewerNodesStack": constants.get_viewer_nodes_stack_name(TEST_CLUSTER),
                    "planCluster": json.dumps(cluster_plan.to_dict()),
                    "userConfig": json.dumps(UserConfig(1, 1, 1, 1, 1).to_dict()),
                }))
            }
        )
    ]
    assert expected_calls == mock_client.destroy.call_args_list

    expected_cdk_client_create_calls = [
        mock.call(aws_env)
    ]
    assert expected_cdk_client_create_calls == mock_cdk_client_cls.call_args_list

    expected_destroy_calls = [
        mock.call(TEST_CLUSTER, mock.ANY)
    ]
    assert expected_destroy_calls == mock_destroy_cert.call_args_list

    expected_delete_arkime_calls = [
        mock.call(TEST_CLUSTER, mock.ANY)
    ]
    assert expected_delete_arkime_calls == mock_delete_arkime.call_args_list

@mock.patch("commands.destroy_cluster.AwsClientProvider")
@mock.patch("commands.destroy_cluster._delete_arkime_config_from_datastore")
@mock.patch("commands.destroy_cluster._destroy_viewer_cert")
@mock.patch("commands.destroy_cluster.get_ssm_names_by_path")
@mock.patch("commands.destroy_cluster.destroy_os_domain_and_wait")
@mock.patch("commands.destroy_cluster.destroy_bucket")
@mock.patch("commands.destroy_cluster.get_ssm_param_value")
@mock.patch("commands.destroy_cluster.CdkClient")
def test_WHEN_cmd_destroy_cluster_called_AND_destroy_everything_THEN_expected_cmds(mock_cdk_client_cls, mock_get_ssm, mock_destroy_bucket,
                                                                                   mock_destroy_domain, mock_ssm_names, mock_destroy_cert,
                                                                                   mock_delete_arkime, mock_aws_provider_cls):
    # Set up our mock
    mock_ssm_names.return_value = []

    mock_client = mock.Mock()
    mock_cdk_client_cls.return_value = mock_client

    aws_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")
    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_aws_env.return_value = aws_env
    mock_aws_provider_cls.return_value = mock_aws_provider

    mock_get_ssm.side_effect = [
        constants.get_opensearch_domain_ssm_param_name(TEST_CLUSTER),
        constants.get_capture_bucket_ssm_param_name(TEST_CLUSTER),
    ]

    cluster_plan = ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 1, 2, 1),
        CaptureVpcPlan(2),
        EcsSysResourcePlan(1, 1),
        OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search")),
        S3Plan(DEFAULT_S3_STORAGE_CLASS, 1)
    )

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
            aws_provider=mock.ANY
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
            context={
                constants.CDK_CONTEXT_CMD_VAR: constants.CMD_DESTROY_CLUSTER,
                constants.CDK_CONTEXT_PARAMS_VAR: shlex.quote(json.dumps({
                    "nameCluster": TEST_CLUSTER,
                    "nameCaptureBucketStack": constants.get_capture_bucket_stack_name(TEST_CLUSTER),
                    "nameCaptureBucketSsmParam": constants.get_capture_bucket_ssm_param_name(TEST_CLUSTER),
                    "nameCaptureConfigSsmParam": constants.get_capture_config_details_ssm_param_name(TEST_CLUSTER),
                    "nameCaptureNodesStack": constants.get_capture_nodes_stack_name(TEST_CLUSTER),
                    "nameCaptureVpcStack": constants.get_capture_vpc_stack_name(TEST_CLUSTER),
                    "nameClusterConfigBucket": "",
                    "nameClusterSsmParam": constants.get_cluster_ssm_param_name(TEST_CLUSTER),
                    "nameOSDomainStack": constants.get_opensearch_domain_stack_name(TEST_CLUSTER),
                    "nameOSDomainSsmParam": constants.get_opensearch_domain_ssm_param_name(TEST_CLUSTER),
                    "nameViewerCertArn": "N/A",
                    "nameViewerConfigSsmParam": constants.get_viewer_config_details_ssm_param_name(TEST_CLUSTER),
                    "nameViewerDnsSsmParam": constants.get_viewer_dns_ssm_param_name(TEST_CLUSTER),
                    "nameViewerPassSsmParam": constants.get_viewer_password_ssm_param_name(TEST_CLUSTER),
                    "nameViewerUserSsmParam": constants.get_viewer_user_ssm_param_name(TEST_CLUSTER),
                    "nameViewerNodesStack": constants.get_viewer_nodes_stack_name(TEST_CLUSTER),
                    "planCluster": json.dumps(cluster_plan.to_dict()),
                    "userConfig": json.dumps(UserConfig(1, 1, 1, 1, 1).to_dict()),
                }))
            }
        )
    ]
    assert expected_cdk_calls == mock_client.destroy.call_args_list

    expected_cdk_client_create_calls = [
        mock.call(aws_env)
    ]
    assert expected_cdk_client_create_calls == mock_cdk_client_cls.call_args_list

    expected_destroy_calls = [
        mock.call(TEST_CLUSTER, mock.ANY)
    ]
    assert expected_destroy_calls == mock_destroy_cert.call_args_list

    expected_delete_arkime_calls = [
        mock.call(TEST_CLUSTER, mock.ANY)
    ]
    assert expected_delete_arkime_calls == mock_delete_arkime.call_args_list

@mock.patch("commands.destroy_cluster.AwsClientProvider", mock.Mock())
@mock.patch("commands.destroy_cluster.get_ssm_names_by_path")
@mock.patch("commands.destroy_cluster.destroy_os_domain_and_wait")
@mock.patch("commands.destroy_cluster.destroy_bucket")
@mock.patch("commands.destroy_cluster.CdkClient")
def test_WHEN_cmd_destroy_cluster_called_AND_existing_captures_THEN_abort(mock_cdk_client_cls, mock_destroy_bucket, mock_destroy_domain,
                                                                          mock_ssm_names):
    # Set up our mock
    mock_ssm_names.return_value = ["vpc-1", "vpc-2"]

    mock_client = mock.Mock()
    mock_cdk_client_cls.return_value = mock_client

    # Run our test
    cmd_destroy_cluster("profile", "region", TEST_CLUSTER, False)

    # Check our results
    mock_destroy_bucket.assert_not_called()
    mock_destroy_domain.assert_not_called()
    mock_client.destroy.assert_not_called()

@mock.patch("commands.destroy_cluster.delete_ssm_param")
@mock.patch("commands.destroy_cluster.destroy_cert")
@mock.patch("commands.destroy_cluster.get_ssm_param_value")
def test_WHEN_destroy_viewer_cert_called_THEN_as_expected(mock_ssm_get, mock_destroy_cert, mock_ssm_delete):
    # Set up our mock
    mock_ssm_get.return_value = "arn"

    mock_provider = mock.Mock()

    # Run our test
    _destroy_viewer_cert(TEST_CLUSTER, mock_provider)

    # Check our results
    expected_get_ssm_calls = [
        mock.call(
            constants.get_viewer_cert_ssm_param_name(TEST_CLUSTER),
            mock_provider
        )
    ]
    assert expected_get_ssm_calls == mock_ssm_get.call_args_list

    expected_destroy_cert_calls = [
        mock.call("arn", mock_provider)
    ]
    assert expected_destroy_cert_calls == mock_destroy_cert.call_args_list

    expected_delete_ssm_calls = [
        mock.call(
            constants.get_viewer_cert_ssm_param_name(TEST_CLUSTER),
            mock_provider
        )
    ]
    assert expected_delete_ssm_calls == mock_ssm_delete.call_args_list

@mock.patch("commands.destroy_cluster.delete_ssm_param")
@mock.patch("commands.destroy_cluster.destroy_cert")
@mock.patch("commands.destroy_cluster.get_ssm_param_value")
def test_WHEN_destroy_viewer_cert_called_AND_doesnt_exist_THEN_skip(mock_ssm_get, mock_destroy_cert, mock_ssm_delete):
    # Set up our mock
    mock_ssm_get.side_effect = ParamDoesNotExist("")

    mock_provider = mock.Mock()

    # Run our test
    _destroy_viewer_cert(TEST_CLUSTER, mock_provider)

    # Check our results
    expected_get_ssm_calls = [
        mock.call(
            constants.get_viewer_cert_ssm_param_name(TEST_CLUSTER),
            mock_provider
        )
    ]
    assert expected_get_ssm_calls == mock_ssm_get.call_args_list

    expected_destroy_cert_calls = []
    assert expected_destroy_cert_calls == mock_destroy_cert.call_args_list

    expected_delete_ssm_calls = []
    assert expected_delete_ssm_calls == mock_ssm_delete.call_args_list

@mock.patch("commands.destroy_cluster.destroy_bucket")
@mock.patch("commands.destroy_cluster.delete_ssm_param")
def test_WHEN_delete_arkime_config_from_datastore_called_THEN_as_expected(mock_ssm_delete, mock_destroy_bucket):
    # Set up our mock
    test_env = AwsEnvironment("XXXXXXXXXXX", "my-region-1", "profile")
    mock_provider = mock.Mock()
    mock_provider.get_aws_env.return_value = test_env

    # Run our test
    _delete_arkime_config_from_datastore(TEST_CLUSTER, mock_provider)

    # Check our results
    expected_delete_ssm_calls = [
        mock.call(
            constants.get_capture_config_details_ssm_param_name(TEST_CLUSTER),
            mock_provider
        ),
        mock.call(
            constants.get_viewer_config_details_ssm_param_name(TEST_CLUSTER),
            mock_provider
        ),
    ]
    assert expected_delete_ssm_calls == mock_ssm_delete.call_args_list

    expected_destroy_bucket_calls = [
        mock.call(
            bucket_name=constants.get_config_bucket_name(
                test_env.aws_account,
                test_env.aws_region,
                TEST_CLUSTER
            ),
        aws_provider=mock_provider
        )
    ]
    assert expected_destroy_bucket_calls == mock_destroy_bucket.call_args_list