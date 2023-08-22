import logging
from typing import Dict

import boto3

from aws_interactions.aws_environment import AwsEnvironment

logger = logging.getLogger(__name__)

class AssumeRoleNotSupported(Exception):
    def __init__(self):
        super().__init__("We don't currently support role assumption on AWS Compute platforms")

class AwsClientProvider:
    def __init__(self, aws_profile: str = "default", aws_region: str = None, aws_compute=False, assume_role_arn: str=None):
        """
        Wrapper around creation of Boto AWS Clients.
        aws_profile: if not provided, will use "default"
        aws_region: if not provided, will use the default region in your local AWS Config
        """
        self._aws_profile = aws_profile
        self._aws_region = aws_region
        self._aws_compute = aws_compute
        self._assume_role_arn = assume_role_arn

    def get_aws_env(self) -> AwsEnvironment:
        """
        Get an encapsulation of the AWS Account/Region context using the specific AWS Profile.
        """

        logger.debug(f"Getting AWS Environment for profile '{self._aws_profile}' and region '{self._aws_region}'")

        sts_client = self.get_sts()

        # Determine the region first.  If it's known, use that.  Otherwise, we attempt to pull the default region from
        # the user's on-box AWS Config which we can access through a boto client object
        env_region = self._aws_region if self._aws_region else sts_client.meta.region_name

        # Next is the AWS Account.  This can be determined via the STS API "GetCallerIdentity", which tells you about the
        # credentials used to make the call.
        env_account = sts_client.get_caller_identity()["Account"]

        return AwsEnvironment(env_account, env_region, self._aws_profile)
    
    def _get_assumed_credentials(self, current_session: boto3.Session) -> Dict[str, str]:
        sts_client = current_session.client("sts")

        # Assume the role in the target account
        assumed_role_object = sts_client.assume_role(
            RoleArn=self._assume_role_arn,
            RoleSessionName="ArkimeAwsAioCLI"
        )

        return assumed_role_object["Credentials"]

    def _get_session(self) -> boto3.Session:
        if self._aws_compute:
            current_account_session = boto3.Session()
        else:
            current_account_session = boto3.Session(profile_name=self._aws_profile, region_name=self._aws_region)

        if self._assume_role_arn and not self._aws_compute:
            creds = self._get_assumed_credentials(current_account_session)
            session_to_use = boto3.Session(
                aws_access_key_id = creds["AccessKeyId"],
                aws_secret_access_key = creds["SecretAccessKey"],
                aws_session_token = creds["SessionToken"],
                region_name = self._aws_region
            )
        elif self._assume_role_arn and self._aws_compute:
            # There's additional considerations for this scenario, and there isn't currently a need for it.  We can
            # revist later if necessary.
            raise AssumeRoleNotSupported()
        else:
            session_to_use = current_account_session

        return session_to_use

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

    def get_ecs(self):
        session = self._get_session()
        client = session.client("ecs")
        return client

    def get_events(self):
        session = self._get_session()
        client = session.client("events")
        return client

    def get_iam(self):
        session = self._get_session()
        client = session.client("iam")
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
