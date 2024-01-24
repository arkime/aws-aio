import json
import shlex
import unittest.mock as mock

from aws_interactions.aws_environment import AwsEnvironment
from aws_interactions.ssm_operations import ParamDoesNotExist
import cdk_interactions.cdk_context as context
from commands.cluster_destroy import (cmd_cluster_destroy, _destroy_viewer_cert, _delete_arkime_config_from_datastore, _get_stacks_to_destroy,
                                      _get_cdk_context)
import core.constants as constants
from core.capacity_planning import (CaptureNodesPlan, ViewerNodesPlan, EcsSysResourcePlan, OSDomainPlan, DataNodesPlan, MasterNodesPlan,
                                    ClusterPlan, VpcPlan, S3Plan, DEFAULT_S3_STORAGE_CLASS, DEFAULT_VPC_CIDR, DEFAULT_CAPTURE_PUBLIC_MASK,
                                    DEFAULT_NUM_AZS, DEFAULT_S3_STORAGE_DAYS)
from core.user_config import UserConfig
from core.versioning import CliClusterVersionMismatch, UnableToRetrieveClusterVersion

TEST_CLUSTER = "my-cluster"

@mock.patch("commands.cluster_destroy.ver.confirm_aws_aio_version_compatibility", mock.Mock())
@mock.patch("commands.cluster_destroy.get_ssm_param_json_value")
@mock.patch("commands.cluster_destroy._get_cdk_context")
@mock.patch("commands.cluster_destroy._get_stacks_to_destroy")
@mock.patch("commands.cluster_destroy.AwsClientProvider")
@mock.patch("commands.cluster_destroy._delete_arkime_config_from_datastore")
@mock.patch("commands.cluster_destroy._destroy_viewer_cert")
@mock.patch("commands.cluster_destroy.get_ssm_names_by_path")
@mock.patch("commands.cluster_destroy.destroy_os_domain_and_wait")
@mock.patch("commands.cluster_destroy.destroy_bucket")
@mock.patch("commands.cluster_destroy.CdkClient")
def test_WHEN_cmd_cluster_destroy_called_AND_dont_destroy_everything_THEN_expected_cmds(mock_cdk_client_cls, mock_destroy_bucket,
                                                                                        mock_destroy_domain, mock_ssm_get, mock_destroy_cert,
                                                                                        mock_delete_arkime, mock_aws_provider_cls,
                                                                                        mock_get_stacks, mock_get_context, mock_get_json):
    # Set up our mock
    mock_ssm_get.return_value = []

    mock_client = mock.Mock()
    mock_cdk_client_cls.return_value = mock_client

    aws_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")
    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_aws_env.return_value = aws_env
    mock_aws_provider_cls.return_value = mock_aws_provider

    mock_get_stacks.return_value = ["stack1", "stack2"]
    mock_get_context.return_value = {"key": "value"}

    test_plan = ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 1, 2, 1),
        VpcPlan(DEFAULT_VPC_CIDR, DEFAULT_NUM_AZS, DEFAULT_CAPTURE_PUBLIC_MASK),
        EcsSysResourcePlan(3584, 15360),
        OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search")),
        S3Plan(DEFAULT_S3_STORAGE_CLASS, DEFAULT_S3_STORAGE_DAYS),
        ViewerNodesPlan(4, 2),
        None
    )
    mock_get_json.return_value = test_plan.to_dict()

    # Run our test
    cmd_cluster_destroy("profile", "region", TEST_CLUSTER, False, True)

    # Check our results
    mock_destroy_bucket.assert_not_called()
    mock_destroy_domain.assert_not_called()

    expected_stacks_calls = [mock.call(TEST_CLUSTER, False, False)]
    assert expected_stacks_calls == mock_get_stacks.call_args_list

    expected_cdk_calls = [mock.call(TEST_CLUSTER, test_plan)]
    assert expected_cdk_calls == mock_get_context.call_args_list

    expected_calls = [
        mock.call(
            ["stack1", "stack2"],
            context={"key": "value"}
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

@mock.patch("commands.cluster_destroy.ver.confirm_aws_aio_version_compatibility", mock.Mock())
@mock.patch("commands.cluster_destroy._get_cdk_context")
@mock.patch("commands.cluster_destroy._get_stacks_to_destroy")
@mock.patch("commands.cluster_destroy.AwsClientProvider")
@mock.patch("commands.cluster_destroy._delete_arkime_config_from_datastore")
@mock.patch("commands.cluster_destroy._destroy_viewer_cert")
@mock.patch("commands.cluster_destroy.get_ssm_names_by_path")
@mock.patch("commands.cluster_destroy.destroy_os_domain_and_wait")
@mock.patch("commands.cluster_destroy.destroy_bucket")
@mock.patch("commands.cluster_destroy.get_ssm_param_json_value")
@mock.patch("commands.cluster_destroy.get_ssm_param_value")
@mock.patch("commands.cluster_destroy.CdkClient")
def test_WHEN_cmd_cluster_destroy_called_AND_destroy_everything_THEN_expected_cmds(mock_cdk_client_cls, mock_get_ssm, mock_get_ssm_json, 
                                                                                   mock_destroy_bucket,mock_destroy_domain, mock_ssm_names,
                                                                                   mock_destroy_cert, mock_delete_arkime, mock_aws_provider_cls,
                                                                                    mock_get_stacks, mock_get_context):
    # Set up our mock
    mock_ssm_names.return_value = []

    mock_client = mock.Mock()
    mock_cdk_client_cls.return_value = mock_client

    aws_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")
    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_aws_env.return_value = aws_env
    mock_aws_provider_cls.return_value = mock_aws_provider

    test_plan = ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 1, 2, 1),
        VpcPlan(DEFAULT_VPC_CIDR, DEFAULT_NUM_AZS, DEFAULT_CAPTURE_PUBLIC_MASK),
        EcsSysResourcePlan(3584, 15360),
        OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search")),
        S3Plan(DEFAULT_S3_STORAGE_CLASS, DEFAULT_S3_STORAGE_DAYS),
        ViewerNodesPlan(4, 2),
        VpcPlan(DEFAULT_VPC_CIDR, DEFAULT_NUM_AZS, DEFAULT_CAPTURE_PUBLIC_MASK),
    )
    mock_get_ssm_json.side_effect = [test_plan.to_dict(), "arkime-domain"]
    mock_get_ssm.return_value = "capture-bucket"

    mock_get_stacks.return_value = ["stack1", "stack2"]
    mock_get_context.return_value = {"key": "value"}

    # Run our test
    cmd_cluster_destroy("profile", "region", TEST_CLUSTER, True, False)

    # Check our results
    expected_destroy_domain_calls = [
        mock.call(
            domain_name="arkime-domain",
            aws_client_provider=mock.ANY
        )
    ]
    assert expected_destroy_domain_calls == mock_destroy_domain.call_args_list

    expected_destroy_bucket_calls = [
        mock.call(
            bucket_name="capture-bucket",
            aws_provider=mock.ANY
        )
    ]
    assert expected_destroy_bucket_calls == mock_destroy_bucket.call_args_list

    expected_stacks_calls = [mock.call(TEST_CLUSTER, True, True)]
    assert expected_stacks_calls == mock_get_stacks.call_args_list

    expected_cdk_calls = [mock.call(TEST_CLUSTER, test_plan)]
    assert expected_cdk_calls == mock_get_context.call_args_list

    expected_cdk_calls = [
        mock.call(
            ["stack1", "stack2"],
            context={"key": "value"}
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

@mock.patch("commands.cluster_destroy.ver.confirm_aws_aio_version_compatibility", mock.Mock())
@mock.patch("commands.cluster_destroy.AwsClientProvider", mock.Mock())
@mock.patch("commands.cluster_destroy.get_ssm_param_json_value")
@mock.patch("commands.cluster_destroy.get_ssm_names_by_path")
@mock.patch("commands.cluster_destroy.destroy_os_domain_and_wait")
@mock.patch("commands.cluster_destroy.destroy_bucket")
@mock.patch("commands.cluster_destroy.CdkClient")
def test_WHEN_cmd_cluster_destroy_called_AND_existing_captures_THEN_abort(mock_cdk_client_cls, mock_destroy_bucket, mock_destroy_domain,
                                                                          mock_ssm_names, mock_get_ssm_json):
    # Set up our mock
    mock_ssm_names.return_value = ["vpc-1", "vpc-2"]

    mock_client = mock.Mock()
    mock_cdk_client_cls.return_value = mock_client

    test_plan = ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 1, 2, 1),
        VpcPlan(DEFAULT_VPC_CIDR, DEFAULT_NUM_AZS, DEFAULT_CAPTURE_PUBLIC_MASK),
        EcsSysResourcePlan(3584, 15360),
        OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search")),
        S3Plan(DEFAULT_S3_STORAGE_CLASS, DEFAULT_S3_STORAGE_DAYS),
        ViewerNodesPlan(4, 2),
        None
    )
    mock_get_ssm_json.side_effect = [test_plan.to_dict(), "arkime-domain"]

    # Run our test
    cmd_cluster_destroy("profile", "region", TEST_CLUSTER, False, True)

    # Check our results
    mock_destroy_bucket.assert_not_called()
    mock_destroy_domain.assert_not_called()
    mock_client.destroy.assert_not_called()

@mock.patch("commands.cluster_destroy.AwsClientProvider", mock.Mock())
@mock.patch("commands.cluster_destroy.ver.confirm_aws_aio_version_compatibility")
@mock.patch("commands.cluster_destroy.destroy_os_domain_and_wait")
@mock.patch("commands.cluster_destroy.destroy_bucket")
@mock.patch("commands.cluster_destroy.CdkClient")
def test_WHEN_cmd_cluster_destroy_called_AND_doesnt_exist_THEN_abort(mock_cdk_client_cls, mock_destroy_bucket, mock_destroy_domain,
                                                                          mock_confirm_ver):
    # Set up our mock
    mock_client = mock.Mock()
    mock_cdk_client_cls.return_value = mock_client

    mock_confirm_ver.side_effect = UnableToRetrieveClusterVersion("cluster", 1)

    # Run our test
    cmd_cluster_destroy("profile", "region", TEST_CLUSTER, False, True)

    # Check our results
    mock_destroy_bucket.assert_not_called()
    mock_destroy_domain.assert_not_called()
    mock_client.destroy.assert_not_called()
    
@mock.patch("commands.cluster_destroy.AwsClientProvider", mock.Mock())
@mock.patch("commands.cluster_destroy.ver.confirm_aws_aio_version_compatibility")
@mock.patch("commands.cluster_destroy.destroy_os_domain_and_wait")
@mock.patch("commands.cluster_destroy.destroy_bucket")
@mock.patch("commands.cluster_destroy.CdkClient")
def test_WHEN_cmd_cluster_destroy_called_AND_cli_version_THEN_abort(mock_cdk_client_cls, mock_destroy_bucket, mock_destroy_domain,
                                                                          mock_confirm_ver):
    # Set up our mock
    mock_client = mock.Mock()
    mock_cdk_client_cls.return_value = mock_client

    mock_confirm_ver.side_effect = CliClusterVersionMismatch(2, 1)

    # Run our test
    cmd_cluster_destroy("profile", "region", TEST_CLUSTER, False, True)

    # Check our results
    mock_destroy_bucket.assert_not_called()
    mock_destroy_domain.assert_not_called()
    mock_client.destroy.assert_not_called()

@mock.patch("commands.cluster_destroy.ver.confirm_aws_aio_version_compatibility", mock.Mock())
@mock.patch("commands.cluster_destroy.AwsClientProvider", mock.Mock())
@mock.patch("commands.cluster_destroy.get_ssm_param_json_value")
@mock.patch("commands.cluster_destroy.get_ssm_names_by_path")
@mock.patch("commands.cluster_destroy.destroy_os_domain_and_wait")
@mock.patch("commands.cluster_destroy.destroy_bucket")
@mock.patch("commands.cluster_destroy.CdkClient")
def test_WHEN_cmd_cluster_destroy_called_AND_dont_supply_tags_THEN_abort(mock_cdk_client_cls, mock_destroy_bucket, mock_destroy_domain,
                                                                          mock_ssm_names, mock_get_ssm_json):
    # Set up our mock
    mock_client = mock.Mock()
    mock_cdk_client_cls.return_value = mock_client

    # Run our test
    cmd_cluster_destroy("profile", "region", TEST_CLUSTER, False, False)

    # Check our results
    mock_ssm_names.assert_not_called()
    mock_get_ssm_json.assert_not_called()
    mock_destroy_bucket.assert_not_called()
    mock_destroy_domain.assert_not_called()
    mock_client.destroy.assert_not_called()

@mock.patch("commands.cluster_destroy.delete_ssm_param")
@mock.patch("commands.cluster_destroy.destroy_cert")
@mock.patch("commands.cluster_destroy.get_ssm_param_value")
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

@mock.patch("commands.cluster_destroy.delete_ssm_param")
@mock.patch("commands.cluster_destroy.destroy_cert")
@mock.patch("commands.cluster_destroy.get_ssm_param_value")
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

@mock.patch("commands.cluster_destroy.destroy_bucket")
@mock.patch("commands.cluster_destroy.delete_ssm_param")
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

def test_WHEN_get_stacks_to_destroy_called_THEN_as_expected():
    cluster_name = "MyCluster"

    # TEST: Don't destroy everything, no Viewer VPC
    actual_value = _get_stacks_to_destroy(cluster_name, False, False)

    expected_value = [
        constants.get_capture_nodes_stack_name(cluster_name),
        constants.get_viewer_nodes_stack_name(cluster_name),
    ]
    assert expected_value == actual_value

    # TEST: Don't destroy everything, has Viewer VPC
    actual_value = _get_stacks_to_destroy(cluster_name, False, True)

    expected_value = [
        constants.get_capture_nodes_stack_name(cluster_name),
        constants.get_viewer_nodes_stack_name(cluster_name),
        constants.get_capture_tgw_stack_name(cluster_name),
        constants.get_viewer_vpc_stack_name(cluster_name),
    ]
    assert expected_value == actual_value

    # TEST: Destroy everything, no Viewer VPC
    actual_value = _get_stacks_to_destroy(cluster_name, True, False)

    expected_value = [
        constants.get_capture_bucket_stack_name(cluster_name),
        constants.get_capture_nodes_stack_name(cluster_name),
        constants.get_capture_vpc_stack_name(cluster_name),
        constants.get_opensearch_domain_stack_name(cluster_name),
        constants.get_viewer_nodes_stack_name(cluster_name)
    ]
    assert expected_value == actual_value

    # TEST: Destroy everything, has Viewer VPC
    actual_value = _get_stacks_to_destroy(cluster_name, True, True)

    expected_value = [
        constants.get_capture_bucket_stack_name(cluster_name),
        constants.get_capture_nodes_stack_name(cluster_name),
        constants.get_capture_vpc_stack_name(cluster_name),
        constants.get_opensearch_domain_stack_name(cluster_name),
        constants.get_viewer_nodes_stack_name(cluster_name),
        constants.get_capture_tgw_stack_name(cluster_name),
        constants.get_viewer_vpc_stack_name(cluster_name),
    ]
    assert expected_value == actual_value

def test_WHEN_get_cdk_context_called_AND_viewer_vpc_THEN_as_expected():
    azs = ["us-fake-1"]
    cluster_name = "MyCluster"

    default_plan = ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 1, 2, 1),
        VpcPlan(DEFAULT_VPC_CIDR, azs, DEFAULT_CAPTURE_PUBLIC_MASK),
        EcsSysResourcePlan(1, 1),
        OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search")),
        S3Plan(DEFAULT_S3_STORAGE_CLASS, 1),
        ViewerNodesPlan(4, 2),
        VpcPlan(DEFAULT_VPC_CIDR, azs, DEFAULT_CAPTURE_PUBLIC_MASK),
    )

    stack_names = context.ClusterStackNames(
        captureBucket=constants.get_capture_bucket_stack_name(cluster_name),
        captureNodes=constants.get_capture_nodes_stack_name(cluster_name),
        captureTgw=constants.get_capture_tgw_stack_name(cluster_name),
        captureVpc=constants.get_capture_vpc_stack_name(cluster_name),
        osDomain=constants.get_opensearch_domain_stack_name(cluster_name),
        viewerNodes=constants.get_viewer_nodes_stack_name(cluster_name),
        viewerVpc=constants.get_viewer_vpc_stack_name(cluster_name),
    )

    actual_value = _get_cdk_context(cluster_name, default_plan)

    expected_value = {
        constants.CDK_CONTEXT_CMD_VAR: constants.CMD_cluster_destroy,
        constants.CDK_CONTEXT_PARAMS_VAR: shlex.quote(json.dumps({
            "nameCluster": cluster_name,
            "nameCaptureBucketSsmParam": constants.get_capture_bucket_ssm_param_name(cluster_name),
            "nameCaptureConfigSsmParam": constants.get_capture_config_details_ssm_param_name(cluster_name),
            "nameCaptureDetailsSsmParam": constants.get_capture_details_ssm_param_name(cluster_name),
            "nameClusterConfigBucket": "",
            "nameClusterSsmParam": constants.get_cluster_ssm_param_name(cluster_name),
            "nameOSDomainSsmParam": constants.get_opensearch_domain_ssm_param_name(cluster_name),
            "nameViewerCertArn": "N/A",
            "nameViewerConfigSsmParam": constants.get_viewer_config_details_ssm_param_name(cluster_name),
            "nameViewerDetailsSsmParam": constants.get_viewer_details_ssm_param_name(cluster_name),
            "planCluster": json.dumps(default_plan.to_dict()),
            "stackNames": json.dumps(stack_names.to_dict()),
            "userConfig": json.dumps(UserConfig(1, 1, 1, 1, 1).to_dict()),
        }))
    }

    assert expected_value == actual_value

def test_WHEN_get_cdk_context_called_AND_no_viewer_vpc_THEN_as_expected():
    azs = ["us-fake-1"]
    cluster_name = "MyCluster"

    default_plan = ClusterPlan(
        CaptureNodesPlan("m5.xlarge", 1, 2, 1),
        VpcPlan(DEFAULT_VPC_CIDR, azs, DEFAULT_CAPTURE_PUBLIC_MASK),
        EcsSysResourcePlan(1, 1),
        OSDomainPlan(DataNodesPlan(2, "t3.small.search", 100), MasterNodesPlan(3, "m6g.large.search")),
        S3Plan(DEFAULT_S3_STORAGE_CLASS, 1),
        ViewerNodesPlan(4, 2),
        None,
    )

    stack_names = context.ClusterStackNames(
        captureBucket=constants.get_capture_bucket_stack_name(cluster_name),
        captureNodes=constants.get_capture_nodes_stack_name(cluster_name),
        captureTgw=constants.get_capture_tgw_stack_name(cluster_name),
        captureVpc=constants.get_capture_vpc_stack_name(cluster_name),
        osDomain=constants.get_opensearch_domain_stack_name(cluster_name),
        viewerNodes=constants.get_viewer_nodes_stack_name(cluster_name),
        viewerVpc=constants.get_viewer_vpc_stack_name(cluster_name),
    )

    actual_value = _get_cdk_context(cluster_name, default_plan)

    expected_value = {
        constants.CDK_CONTEXT_CMD_VAR: constants.CMD_cluster_destroy,
        constants.CDK_CONTEXT_PARAMS_VAR: shlex.quote(json.dumps({
            "nameCluster": cluster_name,
            "nameCaptureBucketSsmParam": constants.get_capture_bucket_ssm_param_name(cluster_name),
            "nameCaptureConfigSsmParam": constants.get_capture_config_details_ssm_param_name(cluster_name),
            "nameCaptureDetailsSsmParam": constants.get_capture_details_ssm_param_name(cluster_name),
            "nameClusterConfigBucket": "",
            "nameClusterSsmParam": constants.get_cluster_ssm_param_name(cluster_name),
            "nameOSDomainSsmParam": constants.get_opensearch_domain_ssm_param_name(cluster_name),
            "nameViewerCertArn": "N/A",
            "nameViewerConfigSsmParam": constants.get_viewer_config_details_ssm_param_name(cluster_name),
            "nameViewerDetailsSsmParam": constants.get_viewer_details_ssm_param_name(cluster_name),
            "planCluster": json.dumps(default_plan.to_dict()),
            "stackNames": json.dumps(stack_names.to_dict()),
            "userConfig": json.dumps(UserConfig(1, 1, 1, 1, 1).to_dict()),
        }))
    }

    assert expected_value == actual_value