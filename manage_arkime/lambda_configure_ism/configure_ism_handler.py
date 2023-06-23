import json
import logging
import os
from requests.auth import HTTPBasicAuth
from typing import Dict

from aws_interactions.aws_client_provider import AwsClientProvider
import aws_interactions.cloudwatch_interactions as cwi
import aws_interactions.events_interactions as events
import constants as constants
import opensearch_interactions.ism_interactions as ism
import opensearch_interactions.opensearch_client as client

class ConfigureIsmHandler:
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

        cluster_name = os.environ['CLUSTER_NAME']
        self.logger.info(f"Cluster Name: {cluster_name}")
        opensearch_endpoint = os.environ['OPENSEARCH_ENDPOINT']
        self.logger.info(f"OpenSearch Endpoint: {opensearch_endpoint}")
        opensearch_secret_arn = os.environ['OPENSEARCH_SECRET_ARN']
        self.logger.info(f"OpenSearch Secret Arn: {opensearch_secret_arn}")

        # Ensure our Lambda will always return a status code
        try:
            self.logger.info(f"Configuring ISM for OpenSearch Domain at {opensearch_endpoint}")
            ism_event = events.ConfigureIsmEvent.from_event_dict(event)

            aws_provider = AwsClientProvider(aws_compute=True)

            secrets_client = aws_provider.get_secretsmanager()
            opensearch_pass = secrets_client.get_secret_value(SecretId=opensearch_secret_arn)["SecretString"]
            auth = HTTPBasicAuth("admin", opensearch_pass)
            opensearch_client = client.OpenSearchClient(f"https://{opensearch_endpoint}", 443, auth)

            ism.setup_user_history_ism(ism_event.history_days, opensearch_client)
            ism.setup_sessions_ism(ism_event.spi_days, ism_event.replicas, opensearch_client)
            
            cwi.put_event_metrics(
                cwi.ConfigureIsmEventMetrics(
                    cluster_name, 
                    cwi.ConfigureIsmEventOutcome.SUCCESS
                ),
                aws_provider
            )
            return {"statusCode": 200}

        except Exception as ex:
            # This should only handle completely unexpected exceptions, not "expected failures" (which should 
            # be handled and return a 200)
            self.logger.error(ex, exc_info=True)

            cwi.put_event_metrics(
                cwi.ConfigureIsmEventMetrics(
                    cluster_name,
                    cwi.ConfigureIsmEventOutcome.FAILURE
                ),
                aws_provider
            )
            return {"statusCode": 500}

