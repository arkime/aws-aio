from dataclasses import dataclass, fields
import logging
from typing import Dict

from core.capacity_planning import (MINIMUM_TRAFFIC, DEFAULT_SPI_DAYS, DEFAULT_REPLICAS, DEFAULT_S3_STORAGE_DAYS, DEFAULT_HISTORY_DAYS)

logger = logging.getLogger(__name__)

@dataclass
class UserConfig:
    expectedTraffic: float
    spiDays: int
    historyDays: int
    replicas: int
    pcapDays: int
    viewerPrefixList: str = None

    def __init__(self, expectedTraffic: float, spiDays: int, historyDays: int, replicas: int, pcapDays: int, viewerPrefixList: str = None):
        if (expectedTraffic is None):
            expectedTraffic = MINIMUM_TRAFFIC

        if (spiDays is None):
            spiDays = DEFAULT_SPI_DAYS

        if (historyDays is None):
            historyDays = DEFAULT_HISTORY_DAYS

        if (replicas is None):
            replicas = DEFAULT_REPLICAS

        if (pcapDays is None):
            pcapDays = DEFAULT_S3_STORAGE_DAYS


        self.expectedTraffic = expectedTraffic
        self.spiDays = spiDays
        self.historyDays = historyDays
        self.replicas = replicas
        self.pcapDays = pcapDays
        self.viewerPrefixList = viewerPrefixList

    """ Only process fields we still need, this allows us to ignore config no longer used """
    @classmethod
    def from_dict(cls, d):
        valid_keys = {f.name for f in fields(cls)}
        valid_kwargs = {key: value for key, value in d.items() if key in valid_keys}
        return cls(**valid_kwargs)

    def __eq__(self, other):
        return (self.expectedTraffic == other.expectedTraffic and
                self.spiDays == other.spiDays and
                self.historyDays == other.historyDays and
                self.replicas == other.replicas and
                self.pcapDays == other.pcapDays and
                self.viewerPrefixList == other.viewerPrefixList)

    def to_dict(self) -> Dict[str, any]:
        return {
            'expectedTraffic': self.expectedTraffic,
            'spiDays': self.spiDays,
            'replicas': self.replicas,
            'pcapDays': self.pcapDays,
            'historyDays': self.historyDays,
            'viewerPrefixList': self.viewerPrefixList,
        }

