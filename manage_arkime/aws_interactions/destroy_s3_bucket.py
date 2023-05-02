import logging

from aws_interactions.aws_client_provider import AwsClientProvider

logger = logging.getLogger(__name__)

def destroy_s3_bucket(bucket_name: str, aws_client_provider: AwsClientProvider):
    s3_resource = aws_client_provider.get_s3_resource()
    bucket = s3_resource.Bucket(bucket_name)

    logger.info(f"Ensuring S3 Bucket {bucket_name} currently exists...")
    if not bucket.creation_date:
        logger.info(f"S3 Bucket {bucket_name} does not exist; no need to destroy")
        return
    logger.info(f"S3 Bucket {bucket_name} exists")

    logger.info(f"Ensuring s3 Bucket {bucket_name} is empty by deleting all objects in it...")
    bucket.objects.all().delete()
    logger.info(f"All objects in S3 Bucket {bucket_name} have been deleted")

    logger.info(f"Deleting S3 Bucket {bucket_name}...")
    bucket.delete()
    logger.info(f"S3 Bucket {bucket_name} has been deleted")

