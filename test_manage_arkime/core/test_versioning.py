import py
import pytest
import unittest.mock as mock

import core.constants as constants
import core.local_file as lf
import core.versioning as ver


@pytest.fixture
def local_test_file_path(tmpdir):
    temp_file_path = tmpdir.join("test.txt")
    with open(temp_file_path, "w") as file_handle:
        file_handle.write("Aure entuluva!" * 1000) # larger than 4096 bytes
    return str(temp_file_path)

def test_WHEN_get_md5_of_file_called_THEN_as_expected(local_test_file_path):
    # Set up our mock
    mock_file = mock.Mock()
    mock_file.local_path = local_test_file_path

    # Run our test
    actual_md5 = ver.get_md5_of_file(mock_file)

    # Check the results
    assert "ffc2c982c7363a318de4b18ee1357402" == actual_md5

@mock.patch("core.versioning.call_shell_command")
def test_WHEN_get_source_version_called_THEN_as_expected(mock_shell):
    # TEST: Happy Path
    mock_shell.return_value = [0, ["v0.1.1-1-gd8e1200"]]
    actual_version = ver.get_source_version()
    assert "v0.1.1-1-gd8e1200" == actual_version

    expected_shell_call = [mock.call("git describe --tags")]
    assert expected_shell_call == mock_shell.call_args_list

    # TEST: Problem with command then raises
    mock_shell.return_value = [1, ["ERROR"]]
    with pytest.raises(ver.CouldntReadSourceVersion):
        ver.get_source_version()

@mock.patch("core.versioning.datetime")
@mock.patch("core.versioning.get_source_version")
@mock.patch("core.versioning.get_md5_of_file")
def test_WHEN_get_version_info_called_THEN_as_expected(mock_get_md5, mock_get_source_v, mock_datetime):
    # Set up our mock
    mock_file = mock.Mock()
    mock_get_md5.return_value = "86d3f3a95c324c9479bd8986968f4327"
    mock_get_source_v.return_value = "v0.1.1-1-gd8e1200"
    mock_datetime.now.return_value.strftime.return_value = "2023-05-11 07:13:42"

    # TEST: Config version default is 1
    actual_versions = ver.get_version_info(mock_file)

    expected_versions = ver.VersionInfo(
        "1",
        "1",
        "86d3f3a95c324c9479bd8986968f4327",
        "v0.1.1-1-gd8e1200",
        "2023-05-11 07:13:42",
    )
    assert expected_versions == actual_versions

    # TEST: Config version is non-default
    actual_versions = ver.get_version_info(mock_file, config_version="3")

    expected_versions = ver.VersionInfo(
        "1",
        "3",
        "86d3f3a95c324c9479bd8986968f4327",
        "v0.1.1-1-gd8e1200",
        "2023-05-11 07:13:42",
    )
    assert expected_versions == actual_versions