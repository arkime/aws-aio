from enum import Enum
import logging
import os
from typing import Dict, List

from botocore.exceptions import ClientError

from aws_interactions.aws_client_provider import AwsClientProvider
from core.local_file import PlainFile, S3File

logger = logging.getLogger(__name__)

class BucketStatus(Enum):
    DOES_NOT_EXIST="does not exist"
    EXISTS_HAVE_ACCESS="exists have access"
    EXISTS_NO_ACCESS="exists no access"

class BucketAccessDenied(Exception):
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        super().__init__(f"You do not have access to S3 bucket {bucket_name}")

class BucketDoesntExist(Exception):
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        super().__init__(f"The S3 bucket {bucket_name} does not exist")

class BucketNameNotAvailable(Exception):
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        super().__init__(f"The S3 bucket name {bucket_name} is already owned by another account")

class CouldntEnsureBucketExists(Exception):
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        super().__init__(f"Could not ensure that the S3 bucket name {bucket_name} exists and is accessible")

class CantWriteFileDirDoesntExist(Exception):
    def __init__(self, local_path: str):
        self.local_path = local_path
        super().__init__(f"Could not write to the location {local_path} because its directory doesn't exist")

class CantWriteFileAlreadyExists(Exception):
    def __init__(self, local_path: str):
        self.local_path = local_path
        super().__init__(f"Could not write to the location {local_path} because a file already exists there")

class CantWriteFileLackPermission(Exception):
    def __init__(self, local_path: str):
        self.local_path = local_path
        super().__init__(f"Could not write to the location {local_path} because you lack permission to do so")

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
        create_args = {
            "ACL": "private",
            "Bucket": bucket_name,
            "ObjectOwnership": "BucketOwnerPreferred"
        }

        if aws_env.aws_region != "us-east-1":
            create_args["CreateBucketConfiguration"] = {
                "LocationConstraint": aws_env.aws_region
            }
        s3_client.create_bucket(**create_args)
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

def put_file_to_bucket(file: S3File, bucket_name: str, s3_key: str, aws_provider: AwsClientProvider):
    s3_client = aws_provider.get_s3()

    try:
        with open(file.local_path, "rb") as data:    
            s3_client.put_object(
                ACL="bucket-owner-full-control",
                Body=data,
                Bucket=bucket_name,
                Key=s3_key,
                Metadata=file.metadata,
                ServerSideEncryption='aws:kms',
                StorageClass='STANDARD'
            )
    except ClientError as ex:
        if "NoSuchBucket" in str(ex):
            raise BucketDoesntExist(bucket_name)
        elif "AccessDenied" in str(ex):
            raise BucketAccessDenied(bucket_name)
        else:
            raise ex

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

def list_bucket_objects(bucket_name: str, aws_provider: AwsClientProvider, prefix: str = None) -> List[Dict[str, str]]:
    """
    Gets the keys and last modified date of all objects in an S3 bucket.  Returned in the format: [{"key", "date_modified"}]
    """
    s3_client = aws_provider.get_s3()
    
    paginator = s3_client.get_paginator('list_objects_v2')
    all_objects = []

    # Adding the prefix parameter to the pagination call if it's provided
    page_iterator = (
        paginator.paginate(Bucket=bucket_name, Prefix=prefix)
        if prefix
        else paginator.paginate(Bucket=bucket_name)
    )

    for page in page_iterator:
        contents = page.get('Contents', [])
        for obj in contents:
            all_objects.append({
                "key": obj["Key"],
                "date_modified": obj["LastModified"],
            })
    
    return all_objects

def get_object_user_metadata(bucket_name: str, s3_key: str, aws_provider: AwsClientProvider) -> Dict[str, str]:
    """
    Gets the user-defined object metadata for a specified S3 Key
    """
    s3_client = aws_provider.get_s3()

    response = s3_client.head_object(
        Bucket=bucket_name,
        Key=s3_key,
    )
    object_metadata = response.get("Metadata", None)
    return object_metadata

def get_object(bucket_name: str, s3_key: str, local_path: str, aws_provider: AwsClientProvider) -> S3File:
    """
    Gets the object from S3 and places it at the defined local_path, raising an error if a file already exists at that
    location on disk.
    """
    s3_client = aws_provider.get_s3()

    if os.path.exists(local_path):
        raise CantWriteFileAlreadyExists(local_path)
    
    if not os.path.exists(os.path.dirname(local_path)):
        raise CantWriteFileDirDoesntExist(local_path)
    
    response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)

    try:
        with open(local_path, 'wb') as file:
            file.write(response['Body'].read())
    except PermissionError:
        raise CantWriteFileLackPermission(local_path)

    return S3File(
        PlainFile(local_path),
        metadata=response.get("Metadata", None)
    )

