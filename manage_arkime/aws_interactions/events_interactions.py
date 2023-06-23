from abc import ABC, abstractmethod
import json
import logging
from typing import Dict, List

from aws_interactions.aws_client_provider import AwsClientProvider
import constants as constants


logger = logging.getLogger(__name__)

class ArkimeEvent(ABC):
    @classmethod
    def from_event_dict(cls, raw_event: Dict[str, any]):
        detail_dict = raw_event["detail"]
        return cls(**detail_dict)

    def __init__(self):
        pass

    @property
    def source(self) -> str:
        return constants.EVENT_SOURCE

    @property
    @abstractmethod
    def detail_type(self) -> str:
        pass

    @property
    @abstractmethod
    def details(self) -> Dict[str, any]:
        pass

    def __str__(self) -> str:
        event = {
            "source": self.source,
            "detail_type": self.detail_type,
            "details": self.details
        }
        return json.dumps(event)

    def __eq__(self, other: object) -> bool:
        return self.source == other.source and self.detail_type == other.detail_type and self.details == other.details
    
class ConfigureIsmEvent(ArkimeEvent):
    def __init__(self, history_days: int, spi_days: int, replicas: int):
        super().__init__()

        self.history_days = history_days
        self.spi_days = spi_days
        self.replicas = replicas

    @property
    def details(self) -> Dict[str, any]:
        return {
            "history_days": self.history_days,
            "spi_days": self.spi_days,
            "replicas": self.replicas,
        }

    @property
    def detail_type(self) -> str:
        return constants.EVENT_DETAIL_TYPE_CONFIGURE_ISM

class CreateEniMirrorEvent(ArkimeEvent):
    def __init__(self, cluster_name: str, vpc_id: str, subnet_id: str, eni_id: str, eni_type: str, traffic_filter_id: str, vni: int):
        super().__init__()

        self.cluster_name = cluster_name
        self.vpc_id = vpc_id
        self.subnet_id = subnet_id
        self.eni_id = eni_id
        self.eni_type = eni_type
        self.traffic_filter_id = traffic_filter_id
        self.vni = vni

    @property
    def details(self) -> Dict[str, any]:
        return {
            "cluster_name": self.cluster_name,
            "vpc_id": self.vpc_id,
            "subnet_id": self.subnet_id,
            "eni_id": self.eni_id,
            "eni_type": self.eni_type,
            "traffic_filter_id": self.traffic_filter_id,
            "vni": self.vni,
        }

    @property
    def detail_type(self) -> str:
        return constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR

class DestroyEniMirrorEvent(ArkimeEvent):
    def __init__(self, cluster_name: str, vpc_id: str, subnet_id: str, eni_id: str):
        super().__init__()

        self.cluster_name = cluster_name
        self.vpc_id = vpc_id
        self.subnet_id = subnet_id
        self.eni_id = eni_id

    @property
    def details(self) -> Dict[str, any]:
        return {
            "cluster_name": self.cluster_name,
            "vpc_id": self.vpc_id,
            "subnet_id": self.subnet_id,
            "eni_id": self.eni_id
        }
    
    @property
    def detail_type(self) -> str:
        return constants.EVENT_DETAIL_TYPE_DESTROY_ENI_MIRROR


def put_events(events: List[ArkimeEvent], event_bus_arn: str, aws_client_provider: AwsClientProvider):
    logger.debug(f"Putting {len(events)} events to Event Bus {event_bus_arn}...")
    for event in events:
        logger.debug(f"Putting Event: {str(event)}")

    event_entries = [
        {
            'Source': event.source,
            'DetailType': event.detail_type,
            'Detail': json.dumps(event.details),
            'EventBusName': event_bus_arn
        }
        for event in events
    ]

    events_client = aws_client_provider.get_events()
    events_client.put_events(
        Entries=event_entries
    )
