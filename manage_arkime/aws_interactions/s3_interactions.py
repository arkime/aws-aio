from enum import Enum
import logging

from botocore.exceptions import ClientError

from aws_interactions.aws_client_provider import AwsClientProvider

logger = logging.getLogger(__name__)

class BucketStatus(Enum):
    DOES_NOT_EXIST="does not exist"
    EXISTS_HAVE_ACCESS="exists have access"
    EXISTS_NO_ACCESS="exists no access"

def get_bucket_status(bucket_name: str, aws_client_provider: AwsClientProvider) -> BucketStatus:
    s3_client = aws_client_provider.get_s3()
    try:
        s3_client.head_bucket(
            Bucket=bucket_name
        )
        return BucketStatus.EXISTS_HAVE_ACCESS
    except ClientError as ex:
        print(ex.response)
        if ex.response["Error"]["Code"] == "403":
            return BucketStatus.EXISTS_NO_ACCESS
        elif ex.response["Error"]["Code"] == "404":
            return BucketStatus.DOES_NOT_EXIST
        else:
            raise ex

"""
{'ResponseMetadata': {'RequestId': 'XB5Y296BMGYAQSEM', 'HostId': 'V8ZhbWDrrEhdvpoCONpj1wPRN8/zhi9DGQ4WTcr8w6RDpPak9NilGNepXU1BXN/V/z5W1tqUaFI=', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amz-id-2': 'V8ZhbWDrrEhdvpoCONpj1wPRN8/zhi9DGQ4WTcr8w6RDpPak9NilGNepXU1BXN/V/z5W1tqUaFI=', 'x-amz-request-id': 'XB5Y296BMGYAQSEM', 'date': 'Mon, 10 Jul 2023 19:48:11 GMT', 'x-amz-bucket-region': 'us-east-1', 'x-amz-access-point-alias': 'false', 'content-type': 'application/xml', 'server': 'AmazonS3'}, 'RetryAttempts': 1}}

{'Error': {'Code': '403', 'Message': 'Forbidden'}, 'ResponseMetadata': {'RequestId': '7Z0WXQ83E5G0PNV2', 'HostId': 'RJsxGguZLp1PKh6JRqgDrRd/4QRTO/cFHpgZ6u0bRtnP0XqNwUdKaOPcUtHl4EFygjlR/PWpHPg=', 'HTTPStatusCode': 403, 'HTTPHeaders': {'x-amz-bucket-region': 'us-west-2', 'x-amz-request-id': '7Z0WXQ83E5G0PNV2', 'x-amz-id-2': 'RJsxGguZLp1PKh6JRqgDrRd/4QRTO/cFHpgZ6u0bRtnP0XqNwUdKaOPcUtHl4EFygjlR/PWpHPg=', 'content-type': 'application/xml', 'date': 'Mon, 10 Jul 2023 20:05:45 GMT', 'server': 'AmazonS3'}, 'RetryAttempts': 1}}
"""

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

