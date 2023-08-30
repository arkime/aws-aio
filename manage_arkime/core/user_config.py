from dataclasses import dataclass, fields
import logging
from typing import Dict

logger = logging.getLogger(__name__)

@dataclass
class UserConfig:
    expectedTraffic: float
    spiDays: int
    historyDays: int
    replicas: int
    pcapDays: int

    """ Only process fields we still need, this allows us to ignore config no longer used """
    @classmethod
    def from_dict(cls, d):
        valid_keys = {f.name for f in fields(cls)}
        valid_kwargs = {key: value for key, value in d.items() if key in valid_keys}
        return cls(**valid_kwargs)

    def __eq__(self, other):
        return (self.expectedTraffic == other.expectedTraffic and self.spiDays == other.spiDays
                and self.replicas == other.replicas and self.pcapDays == other.pcapDays and self.historyDays == other.historyDays)

    def to_dict(self) -> Dict[str, any]:
        return {
            'expectedTraffic': self.expectedTraffic,
            'spiDays': self.spiDays,
            'replicas': self.replicas,
            'pcapDays': self.pcapDays,
            'historyDays': self.historyDays
        }

