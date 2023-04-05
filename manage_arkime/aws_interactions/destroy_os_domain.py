import logging
import time

from botocore.exceptions import ClientError

from manage_arkime.aws_interactions.aws_client_provider import AwsClientProvider

logger = logging.getLogger(__name__)

def destroy_os_domain_and_wait(domain_name: str, aws_client_provider: AwsClientProvider):
    os_client = aws_client_provider.get_opensearch()

    logger.info(f"Confirming OS Domain {domain_name} currently exists...")
    try:
        describe_response = os_client.describe_domain(DomainName=domain_name)
        logger.debug(describe_response)
    except ClientError as exc:
        if exc.response['Error']['Code'] == 'ResourceNotFoundException':
            logger.info(f"OS Domain {domain_name} does not exist; no need to delete")
            return
        raise
    logger.info(f"OS Domain {domain_name} exists")

    logger.info(f"Destroying OS Domain {domain_name}...")
    delete_response = os_client.delete_domain(DomainName=domain_name)
    logger.debug(delete_response)
    logger.info(f"Destruction in progress.  Beginning wait; this could be a while (15-20 min)...")

    # Keep periodically checking the status of the domain until the check throws a ResourceNotFound
    while True:
        time.sleep(10)

        try:
            describe_response = os_client.describe_domain(DomainName=domain_name)
            logger.debug(describe_response)
        except ClientError as exc:
            if exc.response['Error']['Code'] == 'ResourceNotFoundException':
                break
            raise

        logger.info("Waiting a bit more...")

    logger.info(f"OS Domain {domain_name} has been destroyed")