from dataclasses import dataclass


"""
AWS Environments are the combination of an AWS Account and AWS Region.  Every AWS User can slightly different
in a given account/region, as things like Availability Zone IDs (e.g. us-east-2a) map to different physical data
centers depending on AWS Account.  Additionally, some users might have certain AZs enabled/disabled.  For that reason,
the combination of AWS Account and AWS Region is the unique key here.

See: https://docs.aws.amazon.com/cdk/v2/guide/environments.html
"""

@dataclass
class AwsEnvironment:
    aws_account: str
    aws_region: str
    aws_profile: str

    def __str__(self) -> str:
        return f"aws://{self.aws_account}/{self.aws_region}"