import logging

import boto3

from aws_interactions.aws_environment import AwsEnvironment

logger = logging.getLogger(__name__)

class AwsClientProvider:
    def __init__(self, aws_profile: str = "default", aws_region: str = None, aws_compute=False):
        """
        Wrapper around creation of Boto AWS Clients.
        aws_profile: if not provided, will use "default"
        aws_region: if not provided, will use the default region in your local AWS Config
        """
        self._aws_profile = aws_profile
        self._aws_region = aws_region
        self._aws_compute = aws_compute

    def get_aws_env(self) -> AwsEnvironment:
        logger.debug(f"Getting AWS Environment for profile '{self._aws_profile}' and region '{self._aws_region}'")

        sts_client = self.get_sts()

        # Determine the region first.  If it's known, use that.  Otherwise, we attempt to pull the default region from
        # the user's on-box AWS Config which we can access through a boto client object
        env_region = self._aws_region if self._aws_region else sts_client.meta.region_name

        # Next is the AWS Account.  This can be determined via the STS API "GetCallerIdentity", which tells you about the
        # credentials used to make the call.
        env_account = sts_client.get_caller_identity()["Account"]

        return AwsEnvironment(env_account, env_region, self._aws_profile)

    def _get_session(self) -> boto3.Session:
        if self._aws_compute:
            return boto3.Session()
        else:
            return boto3.Session(profile_name=self._aws_profile, region_name=self._aws_region)

    def get_acm(self):
        session = self._get_session()
        client = session.client("acm")
        return client

    def get_cloudwatch(self):
        session = self._get_session()
        client = session.client("cloudwatch")
        return client    

    def get_ec2(self):
        session = self._get_session()
        client = session.client("ec2")
        return client    

    def get_events(self):
        session = self._get_session()
        client = session.client("events")
        return client

    def get_opensearch(self):
        session = self._get_session()
        client = session.client("opensearch")
        return client

    def get_s3(self):
        session = self._get_session()
        client = session.client("s3")
        return client

    def get_s3_resource(self):
        boto3.setup_default_session(profile_name=self._aws_profile)
        resource = boto3.resource("s3", region_name=self._aws_region)
        return resource

    def get_secretsmanager(self):
        session = self._get_session()
        client = session.client("secretsmanager")
        return client

    def get_ssm(self):
        session = self._get_session()
        client = session.client("ssm")
        return client

    def get_sts(self):
        session = self._get_session()
        client = session.client("sts")
        return client
