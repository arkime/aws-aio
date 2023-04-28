import json
import logging

from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.ec2_interactions as ec2i
import aws_interactions.events_interactions as events
import aws_interactions.ssm_operations as ssm_ops
import constants as constants

class CreateEniMirrorHandler:
    def __init__(self):
        self.logger = logging.getLogger()
        self.logger.handlers = []  # Make sure we're starting with a clean slate
        self.logger.setLevel(logging.INFO)

        console_handler = logging.StreamHandler()
        self.logger.addHandler(console_handler)

    def handler(self, event, context):
        # Log the triggering event; first thing every Lambda should do
        self.logger.info("Event:")
        self.logger.info(json.dumps(event, indent=2))

        # Ensure our Lambda will always return a status code
        try:
            create_event = events.CreateEniMirrorEvent.from_event_dict(event)

            self.logger.info(f"Starting Traffic Mirroring Session creation process for ENI {create_event.eni_id}")

            eni_param_name = constants.get_eni_ssm_param_name(
                create_event.cluster_name, 
                create_event.vpc_id, 
                create_event.subnet_id, 
                create_event.eni_id
            )

            aws_provider = AwsClientProvider(aws_profile=None)

            # If the SSM parameter exists for this ENI, we assume the Mirroring Session already exists
            try:
                ssm_ops.get_ssm_param_value(eni_param_name, aws_provider)
                self.logger.info(f"Mirroring already configured for ENI {create_event.eni_id}; aborting...")
                return {"statusCode": 200}
            except ssm_ops.ParamDoesNotExist:
                self.logger.info(f"Confirmed SSM Param does not exist for ENI {create_event.eni_id}")
                pass 

            subnet_param_name = constants.get_subnet_ssm_param_name(create_event.cluster_name, create_event.vpc_id, create_event.subnet_id)
            traffic_target_id = ssm_ops.get_ssm_param_json_value(subnet_param_name, "mirrorTargetId", aws_provider)

            self.logger.info(f"Creating Mirroring Session...")
            eni = ec2i.NetworkInterface(create_event.eni_id, create_event.eni_type)
            try:
                traffic_session_id = ec2i.mirror_eni(
                    eni,
                    traffic_target_id,
                    create_event.traffic_filter_id,
                    create_event.vpc_id,
                    aws_provider,
                    virtual_network=create_event.vni
                )
            except ec2i.NonMirrorableEniType as ex:
                self.logger.warning(f"Eni {eni.id} is of unsupported type {eni.type}; aborting...")
                return {"statusCode": 200}

            self.logger.info(f"Creating SSM Parameter: {eni_param_name}")
            ssm_ops.put_ssm_param(
                eni_param_name, 
                json.dumps({"eniId": eni.id, "trafficSessionId": traffic_session_id}),
                aws_provider,
                description=f"Mirroring details for {eni.id}",
                pattern=".*"
            )

            return {"statusCode": 200}

        except Exception as ex:
            # This should only handle completely unexpected exceptions, not "expected" failures
            self.logger.error(str(ex))
            return {"statusCode": 500}

        

            



        