import boto3

class AwsClientProvider:
    def __init__(self, aws_profile: str = None, aws_region: str = None):
        """
        Wrapper around creation of Boto AWS Clients.
        aws_profile: if not provided, will use "default"
        aws_region: if not provided, will use the default region in your local AWS Config
        """
        self._aws_profile = aws_profile if aws_profile else "default"
        self._aws_region = aws_region

    def get_opensearch(self):
        session = boto3.Session(profile_name=self._aws_profile, region_name=self._aws_region)
        return session.client("opensearch")

    def get_s3(self):
        session = boto3.Session(profile_name=self._aws_profile, region_name=self._aws_region)
        return session.client("s3")

    def get_s3_resource(self):
        boto3.setup_default_session(profile_name=self._aws_profile)
        resource = boto3.resource("s3", region_name=self._aws_region)
        return resource

    def get_ssm(self):
        session = boto3.Session(profile_name=self._aws_profile, region_name=self._aws_region)
        return session.client("ssm")

    def get_sts(self):
        session = boto3.Session(profile_name=self._aws_profile, region_name=self._aws_region)
        return session.client("sts")