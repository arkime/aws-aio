import os
import pytest
import unittest.mock as mock

from aws_interactions.aws_environment import AwsEnvironment
import cdk_interactions.cfn_wrangling as cfn
import core.constants as constants


TEST_ENV = AwsEnvironment("account", "region", "profile")

def test_WHEN_get_cfn_dir_name_called_THEN_as_expected():
    # TEST: Valid name should give right answer
    actual_value = cfn.get_cfn_dir_name("MyCluster01", TEST_ENV)
    assert f"cfn-MyCluster01-{TEST_ENV.aws_account}-{TEST_ENV.aws_region}" == actual_value

    # TEST: Invalid name should raise
    with pytest.raises(constants.InvalidClusterName):
        cfn.get_cfn_dir_name("My Cluster 01", TEST_ENV)

@mock.patch("cdk_interactions.cfn_wrangling.os.path.isdir")
@mock.patch("cdk_interactions.cfn_wrangling.get_repo_root_dir")
def test_WHEN_get_cdk_out_path_called_AND_happy_path_THEN_as_expected(mock_get_repo_root, mock_isdir):
    # Set up our mock
    mock_get_repo_root.return_value = "/my/path"
    mock_isdir.return_value = True

    # Run the test
    actual_value = cfn.get_cdk_out_dir_path()

    # Check the result
    assert "/my/path/cdk.out" == actual_value

@mock.patch("cdk_interactions.cfn_wrangling.os.path.isdir")
@mock.patch("cdk_interactions.cfn_wrangling.get_repo_root_dir")
def test_WHEN_get_cdk_out_path_called_AND_doesnt_exist_THEN_raises(mock_get_repo_root, mock_isdir):
    # Set up our mock
    mock_get_repo_root.return_value = "/my/path"
    mock_isdir.return_value = False

    # Run the test
    with pytest.raises(cfn.CdkOutNotPresent):
        cfn.get_cdk_out_dir_path()

@mock.patch("cdk_interactions.cfn_wrangling.shutil.copyfile")
@mock.patch("cdk_interactions.cfn_wrangling.os.path.isfile")
@mock.patch("cdk_interactions.cfn_wrangling.os.listdir")
def test_WHEN_copy_templates_to_cfn_dir_called_THEN_as_expected(mock_listdir, mock_isfile, mock_copyfile):
    # Set up our mock
    mock_listdir.return_value = [
        "MyCluster-CaptureBucket.assets.json",
        "MyCluster-CaptureBucket.template.json",
        "MyCluster3-CaptureBucket.assets.json",
        "MyCluster3-CaptureBucket.template.json",
        "MyCluster3-CaptureNodes.assets.json",
        "MyCluster3-CaptureNodes.template.json",
        "asset.13fd643b69301bb29b4aea4ad8a3b85f158c70674d7081b9af08eaea02188af5",
        "cdk.out",
        "unexpected_directory"
    ]
    mock_isfile.return_value = True

    # Run the test
    actual_value = cfn._copy_templates_to_cfn_dir("MyCluster3", "/path/cfn", "path/cdk.out")

    # Check the result
    expected_copy_calls = [
        mock.call("path/cdk.out/MyCluster3-CaptureBucket.template.json", "/path/cfn/MyCluster3-CaptureBucket.template.json"),
        mock.call("path/cdk.out/MyCluster3-CaptureNodes.template.json", "/path/cfn/MyCluster3-CaptureNodes.template.json")
    ]
    assert expected_copy_calls == mock_copyfile.call_args_list


@mock.patch("cdk_interactions.cfn_wrangling._copy_templates_to_cfn_dir")
@mock.patch("cdk_interactions.cfn_wrangling.get_cdk_out_dir_path")
@mock.patch("cdk_interactions.cfn_wrangling.os.makedirs")
@mock.patch("cdk_interactions.cfn_wrangling.shutil.rmtree")
@mock.patch("cdk_interactions.cfn_wrangling.os.path.exists")
def test_WHEN_set_up_cloudformation_template_dir_called_THEN_as_expected(mock_exists, mock_rmtree, mock_mkdirs, mock_get_cdk_path, mock_copy):
    # Set up our mock
    test_env = AwsEnvironment("account", "region", "profile")
    cluster_name = "MyCluster01"
    parent_dir = "/my/path"
    
    mock_exists.return_value = True
    mock_get_cdk_path.return_value = "/path/cdk.out"

    # Run the test
    cfn.set_up_cloudformation_template_dir(cluster_name, test_env, parent_dir)

    # Check the result
    expected_rmtree_calls = [
        mock.call(cfn.get_cfn_dir_path(cluster_name, test_env, parent_dir))
    ]
    assert expected_rmtree_calls == mock_rmtree.call_args_list

    expected_mkdirs_calls = [
        mock.call(cfn.get_cfn_dir_path(cluster_name, test_env, parent_dir))
    ]
    assert expected_mkdirs_calls == mock_mkdirs.call_args_list

    expected_copy_calls = [
        mock.call(
            cluster_name,
            cfn.get_cfn_dir_path(cluster_name, test_env, parent_dir),
            "/path/cdk.out"
        )
    ]
    assert expected_copy_calls == mock_copy.call_args_list