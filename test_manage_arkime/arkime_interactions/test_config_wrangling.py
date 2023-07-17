import os
import pytest
import unittest.mock as mock

import arkime_interactions.config_wrangling as config
import core.constants as constants


def test_WHEN_get_cluster_dir_name_called_THEN_as_expected():
    # TEST: Valid name should give right answer
    actual_value = config.get_cluster_dir_name("MyCluster01")
    assert "config-MyCluster01" == actual_value

    # TEST: Invalid name should raise
    with pytest.raises(constants.InvalidClusterName):
        config.get_cluster_dir_name("My Cluster 01")

@mock.patch("arkime_interactions.config_wrangling.os.makedirs")
@mock.patch("arkime_interactions.config_wrangling.os.path.exists")
def test_WHEN_create_config_dir_called_AND_doesnt_exist_THEN_as_expected(mock_exists, mock_makedirs):
    # Set up our mock
    cluster_name = "MyCluster01"
    parent_dir = "/my/path"
    dir_name = config.get_cluster_dir_name(cluster_name)
    mock_exists.return_value = False

    # Run the test
    actual_value = config._create_config_dir(cluster_name, parent_dir)

    # Check the results
    assert config.get_cluster_dir_path(cluster_name, parent_dir) == actual_value
    assert [mock.call(f"{parent_dir}/{dir_name}")] == mock_makedirs.call_args_list

@mock.patch("arkime_interactions.config_wrangling.os.makedirs")
@mock.patch("arkime_interactions.config_wrangling.os.path.exists")
def test_WHEN_create_config_dir_called_AND_does_exist_THEN_as_expected(mock_exists, mock_makedirs):
    # Set up our mock
    cluster_name = "MyCluster01"
    parent_dir = "/my/path"
    mock_exists.return_value = True

    # Run the test
    actual_value = config._create_config_dir(cluster_name, parent_dir)

    # Check the results
    assert config.get_cluster_dir_path(cluster_name, parent_dir) == actual_value
    assert False == mock_makedirs.called

@mock.patch("arkime_interactions.config_wrangling.shutil.copytree")
@mock.patch("arkime_interactions.config_wrangling.os.listdir")
def test_WHEN_copy_default_config_to_cluster_dir_called_AND_empty_THEN_as_expected(mock_listdir, mock_copy):
    # Set up our mock
    cluster_name = "MyCluster01"
    parent_dir = "/my/path"
    cluster_dir_path = config.get_cluster_dir_path(cluster_name, parent_dir)

    mock_listdir.return_value = []

    # Run the test
    config._copy_default_config_to_cluster_dir(cluster_name, parent_dir)

    # Check the results
    expected_copy_calls = [
        mock.call(
            config._get_default_capture_config_dir_path(),
            os.path.join(cluster_dir_path, "capture")
        ),
        mock.call(
            config._get_default_viewer_config_dir_path(),
            os.path.join(cluster_dir_path, "viewer")
        )
    ]
    assert expected_copy_calls == mock_copy.call_args_list

@mock.patch("arkime_interactions.config_wrangling.shutil.copytree")
@mock.patch("arkime_interactions.config_wrangling.os.listdir")
def test_WHEN_copy_default_config_to_cluster_dir_called_AND_not_empty_THEN_raises(mock_listdir, mock_copy):
    # Set up our mock
    cluster_name = "MyCluster01"
    parent_dir = "/my/path"

    mock_listdir.return_value = ["blah"]

    # Run the test
    with pytest.raises(config.ConfigDirNotEmpty):
        config._copy_default_config_to_cluster_dir(cluster_name, parent_dir)

    # Check the results
    expected_copy_calls = []
    assert expected_copy_calls == mock_copy.call_args_list


@mock.patch("arkime_interactions.config_wrangling._copy_default_config_to_cluster_dir")
@mock.patch("arkime_interactions.config_wrangling._create_config_dir")
def test_WHEN_set_up_arkime_config_dir_called_THEN_as_expected(mock_create, mock_copy):
    # Set up our mock
    cluster_name = "MyCluster01"
    parent_dir = "/my/path"

    # Run the test
    config.set_up_arkime_config_dir(cluster_name, parent_dir)

    # Check the results
    expected_create_calls = [
        mock.call(cluster_name, parent_dir)
    ]
    assert expected_create_calls == mock_create.call_args_list

    expected_copy_calls = [
        mock.call(cluster_name, parent_dir)
    ]
    assert expected_copy_calls == mock_copy.call_args_list