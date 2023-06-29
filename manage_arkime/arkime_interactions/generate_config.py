from dataclasses import dataclass
from typing import Dict

# ========== Magic Strings ==========
# Magic key strings we'll search for as targets for a sed find/replace on our Capture/Viewer hosts during their startup
# steps.  We only know their real values at CloudFormation deploy-time and embed those values into the containers.
AWS_REGION = "_AWS_REGION_"
HEALTH_PORT = "_HEALTH_PORT_"
OS_AUTH = "_OS_AUTH_"
OS_ENDPOINT = "_OS_ENDPOINT_"
PCAP_BUCKET = "_PCAP_BUCKET_"
VIEWER_PORT = "_VIEWER_PORT_"

# ========== Config File Generation ==========
@dataclass
class ArkimeFile:
    file_name: str # The Arkime Config's file name on-disk
    path_prefix: str # The path to where the config should live on-disk, excluding the filename
    contents: str # The contents of the config file

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

def get_capture_ini(s3_storage_class: str) -> ArkimeFile:
    contents = f"""
[default]
debug=1
dropUser=nobody
dropGroup=daemon

elasticsearch=https://{OS_ENDPOINT}
elasticsearchBasicAuth={OS_AUTH}
rotateIndex=daily
logESRequests=true

tcpHealthCheckPort={HEALTH_PORT}
pluginsDir=/opt/arkime/plugins
plugins=tcphealthcheck.so;writer-s3

### PCAP Reading
interface=eth0
pcapDir=/opt/arkime/raw
snapLen=32768
pcapReadMethod=afpacketv3
tpacketv3NumThreads=1

### PCAP Writing
pcapWriteMethod=s3
s3Compression=zstd
s3Region={AWS_REGION}
s3Bucket={PCAP_BUCKET}
s3StorageClass={s3_storage_class}
s3UseECSEnv=true
maxFileTimeM=1

### Processing
packetThreads=1
rulesFiles=/opt/arkime/etc/default.rules
rirFile=/opt/arkime/etc/ipv4-address-space.csv
ouiFile=/opt/arkime/etc/oui.txt
"""

    return ArkimeFile(
        "config.ini",
        "/opt/arkime/etc/",
        contents
    )

def get_capture_rules_default() -> ArkimeFile:
    contents = """
---
version: 1
rules:
  - name: "Truncate Encrypted PCAP"
    when: "fieldSet"
    fields:
      protocols:
        - tls
        - ssh
        - quic
    ops:
      _maxPacketsToSave: 20

  - name: "Drop syn scan"
    when: "beforeFinalSave"
    fields:
      packets.src: 1
      packets.dst: 0
      tcpflags.syn: 1
    ops:
      _dontSaveSPI: 1
"""

    return ArkimeFile(
        "default.rules",
        "/opt/arkime/etc/",
        contents
    )

def get_viewer_ini() -> ArkimeFile:
    contents = f"""
[default]
debug=1
dropUser=nobody
dropGroup=daemon

elasticsearch=https://{OS_ENDPOINT}
elasticsearchBasicAuth={OS_AUTH}
rotateIndex=daily

passwordSecret=ignore

cronQueries=auto

spiDataMaxIndices=7
pluginsDir=/opt/arkime/plugins
viewerPlugins=writer-s3
viewPort={VIEWER_PORT}

### PCAP Config
pcapDir=/opt/arkime/raw
pcapWriteMethod=s3
"""

    return ArkimeFile(
        "config.ini",
        "/opt/arkime/etc/",
        contents
    )