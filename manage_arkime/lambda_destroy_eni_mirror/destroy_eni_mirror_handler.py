import json
import logging
from typing import Dict

from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.ec2_interactions as ec2i
import aws_interactions.events_interactions as events
import aws_interactions.ssm_operations as ssm_ops
import constants as constants

class DestroyEniMirrorHandler:
    def __init__(self):
        self.logger = logging.getLogger()
        self.logger.handlers = []  # Make sure we're starting with a clean slate
        self.logger.setLevel(logging.INFO)

        console_handler = logging.StreamHandler()
        self.logger.addHandler(console_handler)

    def handler(self, event: Dict[str, any], context):
        # Log the triggering event; first thing every Lambda should do
        self.logger.info("Event:")
        self.logger.info(json.dumps(event, indent=2))

        # Ensure our Lambda will always return a status code
        try:
            destroy_event = events.DestroyEniMirrorEvent.from_event_dict(event)

            eni_param = constants.get_eni_ssm_param_name(
                destroy_event.cluster_name, 
                destroy_event.vpc_id, 
                destroy_event.subnet_id, 
                destroy_event.eni_id
            )

            aws_provider = AwsClientProvider(aws_profile=None)
            traffic_session_id = ssm_ops.get_ssm_param_json_value(eni_param, "trafficSessionId", aws_provider)

            self.logger.info(f"Removing mirroring session for eni {destroy_event.eni_id}: {traffic_session_id}...")
            try:
                ec2i.delete_eni_mirroring(traffic_session_id, aws_provider)
            except ec2i.MirrorDoesntExist as ex:
                self.logger.info(f"Traffic mirroring session {traffic_session_id} not found; something else must have deleted it. Skipping...")

            self.logger.info(f"Deleting SSM parameter for ENI {destroy_event.eni_id}: {eni_param}")
            ssm_ops.delete_ssm_param(eni_param, aws_provider)

            return {"statusCode": 200}

        except Exception as ex:
            # This should only handle completely unexpected exceptions, not "expected" failures (which should 
            # be handled and return a 200)
            self.logger.error(ex, exc_info=True)
            return {"statusCode": 500}
