from dataclasses import dataclass
import logging

from aws_interactions.aws_client_provider import AwsClientProvider


"""
CDK Environments are the combination of an AWS Account and AWS Region.  Every AWS User can slightly different
in a given account/region, as things like Availability Zone IDs (e.g. us-east-2a) map to different physical data
centers depending on AWS Account.  Additionally, some users might have certain AZs enabled/disabled.  For that reason,
the combination of AWS Account and AWS Region is the unique key here.

See: https://docs.aws.amazon.com/cdk/v2/guide/environments.html
"""

logger = logging.getLogger(__name__)

@dataclass
class CdkEnvironment:
    aws_account: str
    aws_region: str

    def __str__(self) -> str:
        return f"aws://{self.aws_account}/{self.aws_region}"

def get_cdk_env(aws_profile: str = None, aws_region: str = None) -> CdkEnvironment:
    logger.debug(f"Getting CDK Environment for profile '{aws_profile}' and region '{aws_region}'")

    sts_client = AwsClientProvider(aws_profile=aws_profile, aws_region=aws_region).get_sts()

    # Determine the region first.  If it's passed in, use that.  Otherwise, we attempt to pull the default region from
    # the user's on-box AWS Config which we can access through a boto client object
    env_region = aws_region if aws_region else sts_client.meta.region_name

    # Next is the AWS Account.  This can be determined via the STS API "GetCallerIdentity", which tells you about the
    # credentials used to make the call.
    env_account = sts_client.get_caller_identity()["Account"]

    return CdkEnvironment(aws_account=env_account, aws_region=env_region)