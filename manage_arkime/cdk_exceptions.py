import re
from typing import List

"""
Exceptions and exception handling code for our CDK Client
"""

# =============================================================================
# Broadly-applicable exceptions that should apply to all CDK CLI commands
# =============================================================================

class CommonCdkNotBootstrapped(Exception):
    def __init__(self):
        super().__init__("The CDK Environment has not been bootstrapped")

class CommonAWSCredentialsSigMismatch(Exception):
    def __init__(self):
        super().__init__("The AWS Credential signature does not match what was expected")

class CommonExpiredAWSCredentials(Exception):
    def __init__(self):
        super().__init__("The AWS Credentials used for the operation have expired")

class CommonInvalidAWSToken(Exception):
    def __init__(self):
        super().__init__("The AWS Security Token is invalid")

# These are pulled from actual, observed errors during usage/testing
EXPIRED_CREDS_1: str = "There are expired AWS credentials in your environment"
EXPIRED_CREDS_2: str = "ExpiredToken: The security token included in the request is expired"
INVALID_TOKEN: str = "The security token included in the request is invalid"
SIG_MISMATCH: str = "The request signature we calculated does not match the signature you provided"
NOT_BOOTSTRAPPED: str = "Please run 'cdk bootstrap'"

def raise_common_exceptions(exit_code: int, stdout: List[str]) -> None:
    """
    Scan through the returned stdout lines and raise exceptions for generic errors.  We'll probably want to handle
    at least some of these in a "better", more proactive way than letting the CDK CLI let us know something is off.

    TODO: Handle the following
    * Non-existent region
    * Profile doesn't exist
    * Stack name not in app
    * Oddball Cfn deployment failures
    """
    for line in stdout:
        if re.search(EXPIRED_CREDS_1, line):
            raise CommonExpiredAWSCredentials()
        if re.search(EXPIRED_CREDS_2, line):
            raise CommonExpiredAWSCredentials()
        if re.search(INVALID_TOKEN, line):
            raise CommonInvalidAWSToken()
        if re.search(SIG_MISMATCH, line):
            raise CommonAWSCredentialsSigMismatch()
        if re.search(NOT_BOOTSTRAPPED, line):
            raise CommonCdkNotBootstrapped()

# =============================================================================
# Command-specific exceptions
# =============================================================================

class CdkBootstrapFailedUnknown(Exception):
    def __init__(self):
        super().__init__("The CDK Bootstrap operation failed for unknown reasons, please check the logs and stdout.")

class CdkDeployFailedUnknown(Exception):
    def __init__(self):
        super().__init__("The CDK Deploy operation failed for unknown reasons, please check the logs and stdout.")
