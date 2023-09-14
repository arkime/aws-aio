from abc import ABC, abstractmethod
import os
import shutil
import tarfile
from typing import Dict


class FileNotGenerated(Exception):
    def __init__(self, file_path: str):
        self.file_path = file_path
        super().__init__(f"The file {file_path} does not yet exist.  Have you generated it yet?")

class LocalFile(ABC):
    """
    Encapsulates a file on the local disk and a way to get a path to it
    """
    @property
    @abstractmethod
    def local_path(self) -> str:
        pass

class TarGzDirectory(LocalFile):
    """
    Encapsulates the ability to take a directory on disk, turn it into a gzip-compressed tarball, and provide a
    reference to the final file afterwards.
    """

    def __init__(self, source_dir_path: str, tarball_path: str):
        self._source_dir_path = source_dir_path
        self._tarball_path = tarball_path
        self._exists = False

    def __eq__(self, other):
        return (self._source_dir_path == other._source_dir_path 
                and self._tarball_path == other._tarball_path
                and self._exists == other._exists)

    def generate(self):
        """
        Turns the source_dir_path into a tarball at tarball_path.  Overwrites tarball_path if it already exists.
        """
        with tarfile.open(self._tarball_path, "w:gz") as tar:
            tar.add(self._source_dir_path, arcname=os.path.basename(self._source_dir_path))

        self._exists = True

    @property
    def local_path(self) -> str:
        if not self._exists:
            raise FileNotGenerated(self._tarball_path)

        return self._tarball_path
    
class S3File(LocalFile):
    """
    Provides an abstraction for a file on disk that either will be sent to S3 or was pulled from S3.  Provides a
    reference to the raw file while also providing S3 metadata.
    """
    def __init__(self, file: LocalFile, metadata: Dict[str, str] = None):
        self._file = file
        self._metadata = metadata if metadata else dict()

    def __eq__(self, other):
        return self._file == other._file and self._metadata == other._metadata

    @property
    def local_path(self) -> str:
        return self._file.local_path

    @property
    def metadata(self) -> Dict[str, str]:
        return self._metadata
    
class ZipDirectory(LocalFile):
    """
    Encapsulates the ability to take a directory on disk, turn it into a zip archive, and provide a reference to the
    final file afterwards.
    """

    def __init__(self, source_dir_path: str, archive_path: str):
        self._source_dir_path = source_dir_path
        self._archive_path = archive_path
        self._exists = False

    def __eq__(self, other):
        return (self._source_dir_path == other._source_dir_path 
                and self._archive_path == other._tarball_path
                and self._exists == other._exists)

    def generate(self):
        """
        Turns the source_dir_path into a archive at archive_path.  Overwrites archive_path if it already exists.
        """
        suffixless_path = self._archive_path[:-4] if self._archive_path.endswith(".zip") else self._archive_path
        shutil.make_archive(suffixless_path, 'zip', self._source_dir_path)

        self._exists = True

    @property
    def local_path(self) -> str:
        if not self._exists:
            raise FileNotGenerated(self._archive_path)

        return self._archive_path

    

    