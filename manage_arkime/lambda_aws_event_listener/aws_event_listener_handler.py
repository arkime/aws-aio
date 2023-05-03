from enum import Enum
import json
import logging
import os
from typing import Dict, List

from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.events_interactions as events
import constants as constants

class AwsEventType(Enum):
    FARGATE_RUNNING="FargateRunning"
    FARGATE_STOPPED="FargateStopped"
    UNKNOWN="Unknown"

class AwsEventListenerHandler:
    def __init__(self):
        self.logger = logging.getLogger()
        self.logger.handlers = []  # Make sure we're starting with a clean slate
        self.logger.setLevel(logging.INFO)

        console_handler = logging.StreamHandler()
        self.logger.addHandler(console_handler)

    def handler(self, event: Dict[str, any], context):
        # Log the triggering event; first thing every Lambda should do
        self.logger.info("Event:")
        self.logger.info(json.dumps(event))

        # Ensure our Lambda will always return a status code
        try:
            self.logger.info(f"Pulling context from Lambda Environment Variables...")
            event_bus_arn = os.environ["EVENT_BUS_ARN"]
            cluster_name = os.environ["CLUSTER_NAME"]
            vpc_id = os.environ["VPC_ID"]
            traffic_filter_id = os.environ["TRAFFIC_FILTER_ID"]
            mirror_vni = int(os.environ["MIRROR_VNI"])

            self.logger.info(f"Event Bus ARN: {event_bus_arn}")
            self.logger.info(f"Cluster Name: {cluster_name}")
            self.logger.info(f"VPC ID: {vpc_id}")
            self.logger.info(f"Traffic Filter ID: {traffic_filter_id}")
            self.logger.info(f"Mirror VNI: {mirror_vni}")

            self.logger.info(f"Parsing AWS Service Event...")
            event_type = self._get_event_type(event)

            if event_type == AwsEventType.FARGATE_RUNNING:
                self.logger.info(f"Event Type: Fargate Task Running")
                return self._handle_fargate_running(event, event_bus_arn, cluster_name, vpc_id, traffic_filter_id, mirror_vni)
            elif event_type == AwsEventType.FARGATE_STOPPED:
                self.logger.info(f"Event Type: Fargate Task Stopped")
                return self._handle_fargate_stopped(event, event_bus_arn, cluster_name, vpc_id)
            elif event_type == AwsEventType.UNKNOWN:
                self.logger.info(f"Event Type: Unknown")
                return self._handle_unknown(event)

            raise Exception("If we've gotten here, something has gone very wrong")

        except Exception as ex:
            # This should only handle completely unexpected exceptions, not "expected failures" (which should 
            # be handled and return a 200)
            self.logger.error(ex, exc_info=True)

            return {"statusCode": 500}

    def _handle_fargate_running(self, raw_event: Dict[str, any], event_bus_arn: str, cluster_name: str, vpc_id: str, 
            traffic_filter_id: str, mirror_vni: int) -> Dict[str, int]:
        
        eni_details = self._get_fargate_eni_details(raw_event)
        aws_provider = AwsClientProvider(aws_compute=True)
        
        create_events = []
        for eni_detail in eni_details:
            eni_id = eni_detail["eni_id"]
            subnet_id = eni_detail["subnet_id"]

            # The set ENI type for Fargate Containers is "interface"
            create_event = events.CreateEniMirrorEvent(cluster_name, vpc_id, subnet_id, eni_id, "interface", traffic_filter_id, mirror_vni)
            self.logger.info(f"Preparing CreateEniMirrorEvent: {create_event}")
            create_events.append(create_event)

        self.logger.info(f"Initiating creation of mirroring session(s) for {len(create_events)} ENI(s)")
        events.put_events(create_events, event_bus_arn, aws_provider)

        return {"statusCode": 200}        

    def _handle_fargate_stopped(self, raw_event: Dict[str, any], event_bus_arn: str, cluster_name: str, vpc_id: str) -> Dict[str, int]:        
        eni_details = self._get_fargate_eni_details(raw_event)
        aws_provider = AwsClientProvider(aws_compute=True)
        
        destroy_events = []
        for eni_detail in eni_details:
            eni_id = eni_detail["eni_id"]
            subnet_id = eni_detail["subnet_id"]

            # The set ENI type for Fargate Containers is "interface"
            destroy_event = events.DestroyEniMirrorEvent(cluster_name, vpc_id, subnet_id, eni_id)
            self.logger.info(f"Preparing DestroyEniMirrorEvent: {destroy_event}")
            destroy_events.append(destroy_event)

        self.logger.info(f"Initiating destruction of mirroring session(s) for {len(destroy_events)} ENI(s)")
        events.put_events(destroy_events, event_bus_arn, aws_provider)

        return {"statusCode": 200}

    def _get_fargate_eni_details(self, raw_event: Dict[str, any]) -> List[Dict[str, str]]:
        # A single Fargate Task can comprise multiple containers, and I think each can have their own ENI.  The stuff
        # we care about is buried pretty far in the JSON, unfortunately.
        attachments = raw_event["detail"]["attachments"]
        raw_eni_attachment_details = [a["details"] for a in attachments if a.get("type") == "eni"]
        eni_details = []
        for raw_detail in raw_eni_attachment_details:
            eni_detail = {}
            for name_val_pair in raw_detail:
                if name_val_pair["name"] == "subnetId":
                    eni_detail["subnet_id"] = name_val_pair["value"]
                elif name_val_pair["name"] == "networkInterfaceId":
                    eni_detail["eni_id"] = name_val_pair["value"]

            eni_details.append(eni_detail)

        return eni_details


    def _handle_unknown(self, raw_event: Dict[str, any]) -> Dict[str, int]:
        pass

    def _get_event_type(self, raw_event: Dict[str, any]) -> AwsEventType:
        if self._is_ecs_event(raw_event):
            if self._is_fargate_event(raw_event):
                last_status = raw_event["detail"]["lastStatus"]

                if last_status == "RUNNING":
                    return AwsEventType.FARGATE_RUNNING
                elif last_status == "STOPPED":
                    return AwsEventType.FARGATE_STOPPED
                else:
                    return AwsEventType.UNKNOWN

        return AwsEventType.UNKNOWN

    def _is_ecs_event(self, raw_event: Dict[str, any]) -> bool:
        return raw_event["source"] == "aws.ecs"

    def _is_fargate_event(self, raw_event: Dict[str, any]) -> bool:
        is_right_detail_type = raw_event["detail-type"] == "ECS Task State Change"
        is_right_launch_type = raw_event["detail"].get("launchType") == "FARGATE"
        return is_right_detail_type and is_right_launch_type

    

