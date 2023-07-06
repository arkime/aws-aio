from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ArkimeFile:
    """
    Class to encapsulate a file to be written to disk on the Arkime Capture/Viewer nodes.
    """

    system_path: str # Absolute path where the file should live on-disk (prefix + filename)
    contents: str # The contents of the file

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ArkimeFile):
            return False
        return self.system_path == other.system_path and self.contents == other.contents

    def to_dict(self) -> Dict[str, str]:
        return {
            "system_path": self.system_path,
            "contents": self.contents
        }

@dataclass
class ArkimeFilesMap:
    """
    Class to provide a map to the in-datastore location of files needed on Arkime Capture/Viewer Nodes
    """
    captureIniLoc: str # The in-datastore location of Capture Nodes' .INI file for the Capture process
    captureAddFileLocs: List[str] # The in-datastore locations of to any additional Capture Node files
    viewerIniLoc: str # The Viewer Nodes' .INI file for the Viewer process
    viewerAddFileLocs: List[str] # Paths to any additional Viewer Node files

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ArkimeFilesMap):
            return False
        return (self.captureIniLoc == other.captureIniLoc and self.captureAddFileLocs == other.captureAddFileLocs
                and self.viewerIniLoc == other.viewerIniLoc and self.viewerAddFileLocs == other.viewerAddFileLocs)

    def to_dict(self) -> Dict[str, any]:
        return {
            "captureIniLoc": self.captureIniLoc,
            "captureAddFileLocs": self.captureAddFileLocs,
            "viewerIniLoc": self.viewerIniLoc,
            "viewerAddFileLocs": self.viewerAddFileLocs
        }