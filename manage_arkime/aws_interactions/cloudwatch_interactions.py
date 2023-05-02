from abc import ABC, abstractmethod
from enum import Enum
import json
import logging
from typing import Dict, List

from aws_interactions.aws_client_provider import AwsClientProvider
import constants as constants


logger = logging.getLogger(__name__)

CW_ARKIME_EVENT_NAMESPACE="Arkime/Events"

class ArkimeEventMetric(ABC):
    def __init__(self):
        pass

    @property
    def namespace(self) -> str:
        return CW_ARKIME_EVENT_NAMESPACE

    @property
    def unit(self) -> str:
        return "None"

    @property
    @abstractmethod
    def metric_data(self) -> List[Dict[str, any]]:
        pass

    def __str__(self) -> str:
        metric = {
            "namespace": self.namespace,
            "metric_data": self.metric_data
        }
        return json.dumps(metric)

    def __eq__(self, other: object) -> bool:
        return self.namespace == other.namespace and self.metric_data == other.metric_data

class CreateEniMirrorEventOutcome(Enum):
    SUCCESS="Success"
    ABORTED_EXISTS="AbortedExists"
    ABORTED_ENI_TYPE="AbortedEniType"
    FAILURE="Failure"

class CreateEniMirrorEventMetrics(ArkimeEventMetric):
    def __init__(self, cluster_name: str, vpc_id: str, outcome: CreateEniMirrorEventOutcome):
        super().__init__()

        self.cluster_name = cluster_name
        self.vpc_id = vpc_id
        self.event_type = constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR

        self.value_success = 0
        self.value_abort_exists = 0
        self.value_abort_eni_type = 0
        self.value_failure = 0

        if outcome == CreateEniMirrorEventOutcome.SUCCESS:
            self.value_success = 1
        elif outcome == CreateEniMirrorEventOutcome.ABORTED_EXISTS:
            self.value_abort_exists = 1
        elif outcome == CreateEniMirrorEventOutcome.ABORTED_ENI_TYPE:
            self.value_abort_eni_type = 1
        elif outcome == CreateEniMirrorEventOutcome.FAILURE:
            self.value_failure = 1

    @property
    def metric_data(self) -> List[Dict[str, any]]:
        """
        We emit a metric value for each outcome of the operation, as it makes metric math and alarming easier.  Only one
        metric value should be 1; the rest should be 0.
        """

        shared_dimensions = {
            "Dimensions": [
                {"Name": "ClusterName", "Value": self.cluster_name},
                {"Name": "VpcId", "Value": self.vpc_id},
                {"Name": "EventType", "Value": self.event_type},
            ]
        }

        metric_success = {
            "MetricName": CreateEniMirrorEventOutcome.SUCCESS.value,
            "Value": self.value_success
        }
        metric_success.update(shared_dimensions)

        metric_abort_exists = {
            "MetricName": CreateEniMirrorEventOutcome.ABORTED_EXISTS.value,
            "Value": self.value_abort_exists
        }
        metric_abort_exists.update(shared_dimensions)

        metric_abort_eni_type = {
            "MetricName": CreateEniMirrorEventOutcome.ABORTED_ENI_TYPE.value,
            "Value": self.value_abort_eni_type
        }
        metric_abort_eni_type.update(shared_dimensions)

        metric_abort_failure = {
            "MetricName": CreateEniMirrorEventOutcome.FAILURE.value,
            "Value": self.value_failure
        }
        metric_abort_failure.update(shared_dimensions)
        
        return [metric_success, metric_abort_exists, metric_abort_eni_type, metric_abort_failure]

class DestroyEniMirrorEventOutcome(Enum):
    SUCCESS="Success"
    FAILURE="Failure"

class DestroyEniMirrorEventMetrics(ArkimeEventMetric):
    def __init__(self, cluster_name: str, vpc_id: str, outcome: DestroyEniMirrorEventOutcome):
        super().__init__()

        self.cluster_name = cluster_name
        self.vpc_id = vpc_id
        self.event_type = constants.EVENT_DETAIL_TYPE_DESTROY_ENI_MIRROR

        self.value_success = 0
        self.value_failure = 0

        if outcome == DestroyEniMirrorEventOutcome.SUCCESS:
            self.value_success = 1
        elif outcome == DestroyEniMirrorEventOutcome.FAILURE:
            self.value_failure = 1

    @property
    def metric_data(self) -> List[Dict[str, any]]:
        """
        We emit a metric value for each outcome of the operation, as it makes metric math and alarming easier.  Only one
        metric value should be 1; the rest should be 0.
        """

        shared_dimensions = {
            "Dimensions": [
                {"Name": "ClusterName", "Value": self.cluster_name},
                {"Name": "VpcId", "Value": self.vpc_id},
                {"Name": "EventType", "Value": self.event_type},
            ]
        }

        metric_success = {
            "MetricName": DestroyEniMirrorEventOutcome.SUCCESS.value,
            "Value": self.value_success
        }
        metric_success.update(shared_dimensions)

        metric_abort_failure = {
            "MetricName": DestroyEniMirrorEventOutcome.FAILURE.value,
            "Value": self.value_failure
        }
        metric_abort_failure.update(shared_dimensions)
        
        return [metric_success, metric_abort_failure]


def put_event_metrics(metrics: ArkimeEventMetric, aws_client_provider: AwsClientProvider):
    logger.debug(f"Putting Arkime Event metrics: {metrics}")

    cw_client = aws_client_provider.get_cloudwatch()
    cw_client.put_metric_data(
        Namespace=metrics.namespace,
        MetricData=metrics.metric_data
    )
