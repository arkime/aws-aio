from dataclasses import dataclass, fields
import logging
from typing import Dict, List

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
    extraTags: List[Dict[str, str]] = None

    def __init__(self, expectedTraffic: float, spiDays: int, historyDays: int, replicas: int, pcapDays: int, viewerPrefixList: str = None, extraTags: List[Dict[str, str]] = []):
        self.expectedTraffic = expectedTraffic
        self.spiDays = spiDays
        self.historyDays = historyDays
        self.replicas = replicas
        self.pcapDays = pcapDays
        self.viewerPrefixList = viewerPrefixList
        self.extraTags = extraTags

        if (expectedTraffic is None):
            self.expectedTraffic = MINIMUM_TRAFFIC

        if (spiDays is None):
            self.spiDays = DEFAULT_SPI_DAYS

        if (historyDays is None):
            self.historyDays = DEFAULT_HISTORY_DAYS

        if (replicas is None):
            self.replicas = DEFAULT_REPLICAS

        if (pcapDays is None):
            self.pcapDays = DEFAULT_S3_STORAGE_DAYS

    """ Only process fields we still need, this allows us to ignore config no longer used """
    @classmethod
    def from_dict(cls, d):
        valid_keys = {f.name for f in fields(cls)}
        valid_kwargs = {key: value for key, value in d.items() if key in valid_keys}
        return cls(**valid_kwargs)

    def __eq__(self, other):
        set1 = None
        if self.extraTags is not None:
            set1 = {frozenset(d.items()) for d in self.extraTags}

        set2 = None
        if other.extraTags is not None:
            set2 = {frozenset(d.items()) for d in other.extraTags}

        return (self.expectedTraffic == other.expectedTraffic and
                self.spiDays == other.spiDays and
                self.historyDays == other.historyDays and
                self.replicas == other.replicas and
                self.pcapDays == other.pcapDays and
                self.viewerPrefixList == other.viewerPrefixList and
                set1 == set2)

    def to_dict(self) -> Dict[str, any]:
        return {
            'expectedTraffic': self.expectedTraffic,
            'spiDays': self.spiDays,
            'replicas': self.replicas,
            'pcapDays': self.pcapDays,
            'historyDays': self.historyDays,
            'viewerPrefixList': self.viewerPrefixList,
            'extraTags': self.extraTags,
        }

