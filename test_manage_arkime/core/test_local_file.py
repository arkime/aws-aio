import os
import pytest
import unittest.mock as mock

import core.local_file as lf


@mock.patch("core.local_file.tarfile")
def test_WHEN_TarGzDirectory_THEN_lifecycle_as_expected(mock_tarfile):
    # Set up our tests
    source = "/my/source/dir"
    tarball = "/test/file.tgz"
    tgz_dir = lf.TarGzDirectory(source, tarball)

    # TEST: Raises when you try to get the path before generating
    with pytest.raises(lf.FileNotGenerated):
        tgz_dir.local_path

    # TEST: When generate called, then file is created
    tar_obj = mock.MagicMock()
    mock_tarfile.open.return_value.__enter__.return_value = tar_obj

    tgz_dir.generate()

    assert [mock.call(tarball, "w:gz")] == mock_tarfile.open.call_args_list
    assert [mock.call(source, arcname=os.path.basename(source))] == tar_obj.add.call_args_list

    # TEST: After generate is called, you can get the path
    actual_value = tgz_dir.local_path
    assert tarball == actual_value

@mock.patch("core.local_file.tarfile", mock.MagicMock())
def test_WHEN_S3File_THEN_lifecycle_as_expected():
    # Set up our tests
    source = "/my/source/dir"
    tarball = "/test/file.tgz"
    tgz_dir = lf.TarGzDirectory(source, tarball)

    metadata = {"aws_aio_version": "1.1"}

    # TEST: Members as expected (1)
    s3_file_1 = lf.S3File(tgz_dir)

    with pytest.raises(lf.FileNotGenerated):
        s3_file_1.local_path

    # TEST: Members as expected (2)
    tgz_dir.generate()
    s3_file_2 = lf.S3File(tgz_dir, metadata)

    assert tarball == s3_file_2.local_path
    assert metadata == s3_file_2.metadata