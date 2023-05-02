import boto3

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

    def _get_session(self) -> boto3.Session:
        if self._aws_compute:
            return boto3.Session()
        else:
            return boto3.Session(profile_name=self._aws_profile, region_name=self._aws_region)

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
