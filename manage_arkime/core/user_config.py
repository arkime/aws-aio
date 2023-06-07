from dataclasses import dataclass
import logging
from typing import Dict

logger = logging.getLogger(__name__)

@dataclass
class UserConfig:
    expectedTraffic: float
    spiDays: int
    replicas: int
    pcapDays: int

    def __equal__(self, other):
        return (self.expectedTraffic == other.expectedTraffic and self.spiDays == other.spiDays 
                and self.replicas == other.replicas and self.pcapDays == other.pcapDays)

    def to_dict(self) -> Dict[str, any]:
        return {
            'expectedTraffic': self.expectedTraffic,
            'spiDays': self.spiDays,
            'replicas': self.replicas,
            'pcapDays': self.pcapDays,
        }

