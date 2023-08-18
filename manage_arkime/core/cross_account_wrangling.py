from dataclasses import dataclass
from typing import Dict

@dataclass
class CrossAccountAssociation:
    clusterAccount: str
    clusterName: str
    roleArn: str
    vpcAccount: str
    vpcId: str
    vpceServiceId: str

    def __equal__(self, other) -> bool:
        return (self.clusterAccount == other.clusterAccount
                and self.clusterName == other.clusterName
                and self.roleArn == other.roleArn
                and self.vpcAccount == other.vpcAccount
                and self.vpcId == other.vpcId
                and self.vpceServiceId == other.vpceServiceId)

    def to_dict(self) -> Dict[str, str]:
        return {
            'clusterAccount': self.clusterAccount,
            'clusterName': self.clusterName,
            'roleArn': self.roleArn,
            'vpcAccount': self.vpcAccount,
            'vpcId': self.vpcId,
            'vpceServiceId': self.vpceServiceId
        }