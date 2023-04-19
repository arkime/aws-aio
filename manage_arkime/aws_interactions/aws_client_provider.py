import boto3

from manage_arkime.logging_wrangler import set_boto_log_level

class AwsClientProvider:
    def __init__(self, aws_profile: str = None, aws_region: str = None):
        """
        Wrapper around creation of Boto AWS Clients.
        aws_profile: if not provided, will use "default"
        aws_region: if not provided, will use the default region in your local AWS Config
        """
        self._aws_profile = aws_profile if aws_profile else "default"
        self._aws_region = aws_region

    def get_ec2(self):
        with set_boto_log_level("WARNING"):
            session = boto3.Session(profile_name=self._aws_profile, region_name=self._aws_region)
            client = session.client("ec2")
        return client

    def get_opensearch(self):
        with set_boto_log_level("WARNING"):
            session = boto3.Session(profile_name=self._aws_profile, region_name=self._aws_region)
            client = session.client("opensearch")
        return client

    def get_s3(self):
        with set_boto_log_level("WARNING"):
            session = boto3.Session(profile_name=self._aws_profile, region_name=self._aws_region)
            client = session.client("s3")
        return client

    def get_s3_resource(self):
        with set_boto_log_level("WARNING"):
            boto3.setup_default_session(profile_name=self._aws_profile)
            resource = boto3.resource("s3", region_name=self._aws_region)
        return resource

    def get_secretsmanager(self):
        with set_boto_log_level("WARNING"):
            session = boto3.Session(profile_name=self._aws_profile, region_name=self._aws_region)
            client = session.client("secretsmanager")
        return client

    def get_ssm(self):
        with set_boto_log_level("WARNING"):
            session = boto3.Session(profile_name=self._aws_profile, region_name=self._aws_region)
            client = session.client("ssm")
        return client

    def get_sts(self):
        with set_boto_log_level("WARNING"):
            session = boto3.Session(profile_name=self._aws_profile, region_name=self._aws_region)
            client = session.client("sts")
        return client
