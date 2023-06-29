from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ArkimeFile:
    """
    Class to encapsulate a file to be written to disk on the Arkime Capture/Viewer nodes.
    """

    file_name: str # The file name on-disk
    path_prefix: str # The path to where the file should live on-disk, excluding the filename
    contents: str # The contents of the file

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ArkimeFile):
            return False
        return self.file_name == other.file_name and self.path_prefix == other.path_prefix and self.contents == other.contents

    def to_dict(self) -> Dict[str, str]:
        return {
            "file_name": self.file_name,
            "path_prefix": self.path_prefix,
            "contents": self.contents
        }

@dataclass
class ArkimeFilesMap:
    """
    Class to provide a map to the in-datastore location of files needed on Arkime Capture/Viewer Nodes
    """
    captureIniPath: str # The Capture Nodes' .INI file for the Capture process
    captureAddFilePaths: List[str] # Paths to any additional Capture Node files
    viewerIniPath: str # The Viewer Nodes' .INI file for the Viewer process
    viewerAddFilePaths: List[str] # Paths to any additional Viewer Node files

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ArkimeFilesMap):
            return False
        return (self.captureIniPath == other.captureIniPath and self.captureAddFilePaths == other.captureAddFilePaths
                and self.viewerIniPath == other.viewerIniPath and self.viewerAddFilePaths == other.viewerAddFilePaths)

    def to_dict(self) -> Dict[str, any]:
        return {
            "captureIniPath": self.captureIniPath,
            "captureAddFilePaths": self.captureAddFilePaths,
            "viewerIniPath": self.viewerIniPath,
            "viewerAddFilePaths": self.viewerAddFilePaths
        }