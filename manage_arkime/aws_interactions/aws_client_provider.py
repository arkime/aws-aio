import boto3

class AwsClientProvider:
    def __init__(self, aws_profile: str = "default", aws_region: str = None):
        """
        Wrapper around creation of Boto AWS Clients.
        aws_profile: if not provided, will use "default"
        aws_region: if not provided, will use the default region in your local AWS Config
        """
        self._aws_profile = aws_profile
        self._aws_region = aws_region

    def get_ec2(self):
        session = boto3.Session(profile_name=self._aws_profile, region_name=self._aws_region)
        client = session.client("ec2")
        return client    

    def get_events(self):
        session = boto3.Session(profile_name=self._aws_profile, region_name=self._aws_region)
        client = session.client("events")
        return client

    def get_opensearch(self):
        session = boto3.Session(profile_name=self._aws_profile, region_name=self._aws_region)
        client = session.client("opensearch")
        return client

    def get_s3(self):
        session = boto3.Session(profile_name=self._aws_profile, region_name=self._aws_region)
        client = session.client("s3")
        return client

    def get_s3_resource(self):
        boto3.setup_default_session(profile_name=self._aws_profile)
        resource = boto3.resource("s3", region_name=self._aws_region)
        return resource

    def get_secretsmanager(self):
        session = boto3.Session(profile_name=self._aws_profile, region_name=self._aws_region)
        client = session.client("secretsmanager")
        return client

    def get_ssm(self):
        session = boto3.Session(profile_name=self._aws_profile, region_name=self._aws_region)
        client = session.client("ssm")
        return client

    def get_sts(self):
        session = boto3.Session(profile_name=self._aws_profile, region_name=self._aws_region)
        client = session.client("sts")
        return client
