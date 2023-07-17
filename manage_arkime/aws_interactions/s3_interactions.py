from enum import Enum
import logging

from botocore.exceptions import ClientError

from aws_interactions.aws_client_provider import AwsClientProvider
import core.constants as constants

logger = logging.getLogger(__name__)

class BucketStatus(Enum):
    DOES_NOT_EXIST="does not exist"
    EXISTS_HAVE_ACCESS="exists have access"
    EXISTS_NO_ACCESS="exists no access"

class BucketNameNotAvailable(Exception):
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        super().__init__(f"The S3 bucket name {bucket_name} is already owned by another account")

class CouldntEnsureBucketExists(Exception):
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        super().__init__(f"We could not ensure that the S3 bucket name {bucket_name} exists and is accessible")

def get_bucket_status(bucket_name: str, aws_provider: AwsClientProvider) -> BucketStatus:
    s3_client = aws_provider.get_s3()
    try:
        s3_client.head_bucket(
            Bucket=bucket_name
        )
        return BucketStatus.EXISTS_HAVE_ACCESS
    except ClientError as ex:
        if ex.response["Error"]["Code"] == "403":
            return BucketStatus.EXISTS_NO_ACCESS
        elif ex.response["Error"]["Code"] == "404":
            return BucketStatus.DOES_NOT_EXIST
        else:
            raise ex

def create_bucket(bucket_name: str, aws_provider: AwsClientProvider):
    s3_client = aws_provider.get_s3()

    # This S3 API is complex.  In this particular case, we must pass in the region the bucket should exist in; the
    # API hosts won't infer from which regional endpoint we're hitting.  Therefore, we find the actual region we're
    # operating in so we can supply that as the location of the bucket.  
    aws_env = aws_provider.get_aws_env()

    try:
        s3_client.create_bucket(
            ACL="private",
            Bucket=bucket_name,
            CreateBucketConfiguration={
                "LocationConstraint": aws_env.aws_region
            },
            ObjectOwnership="BucketOwnerPreferred"
        )
    except ClientError as ex:
        if "BucketAlreadyOwnedByYou" in str(ex):
            logger.debug(f"Bucket {bucket_name} already exists and is owned by this account")
        elif "BucketAlreadyExists" in str(ex):
            raise BucketNameNotAvailable(bucket_name)
        else:
            raise ex

def destroy_bucket(bucket_name: str, aws_provider: AwsClientProvider):
    s3_resource = aws_provider.get_s3_resource()
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

def ensure_bucket_exists(bucket_name: str, aws_provider: AwsClientProvider):
    logger.info(f"Determining the status of S3 bucket: {bucket_name}")
    bucket_status = get_bucket_status(bucket_name, aws_provider)
    if bucket_status is BucketStatus.DOES_NOT_EXIST:
        try:
            logger.info(f"S3 Bucket {bucket_name} does not exist; creating it to hold Arkime Configuration")
            create_bucket(bucket_name, aws_provider)
        except BucketNameNotAvailable:
            # Very unlikely to happen, but let's handle the edge case simply.
            logger.error(f"We ran into an unexpected situation with creating the S3 bucket {bucket_name};"
                            + " its ownership status changed unexpectedly. Please try re-running the same CLI"
                            + " command you just ran and it should (hopefully) work.")
            raise CouldntEnsureBucketExists(bucket_name)
    elif bucket_status is BucketStatus.EXISTS_HAVE_ACCESS:
        logger.info(f"S3 Bucket {bucket_name} already exists; no work needed")
    elif bucket_status is BucketStatus.EXISTS_NO_ACCESS:
        logger.error(f"S3 Bucket {bucket_name} already exists, but this account does not have access to it.  This is"
                     + " unexpected, but possible if the bucket was created manually.  Try to ensure your account"
                     +  f" has access to the bucket, then retry the CLI command.")
        raise CouldntEnsureBucketExists(bucket_name)
    else:
        # If we got here, it means we have an enum we're not handling
        raise RuntimeError("We didn't expect to get here; please cut a bug report to the Arkime AWS-AIO team")

