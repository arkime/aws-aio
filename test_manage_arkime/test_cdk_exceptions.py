import pytest
import unittest.mock as mock

import manage_arkime.cdk_exceptions as exceptions


def test_WHEN_expired_credentials_THEN_raises():
    # Set up our mock
    exit_code = 1
    stdout = [
        "There are expired AWS credentials in your environment. The CDK app will synth without current account information.",
        "",
        "Unable to resolve AWS account to use. It must be either configured when you define your CDK Stack, or through the environment"
    ]

    # Run our test
    with pytest.raises(exceptions.CommonExpiredAWSCredentials):
        exceptions.raise_common_exceptions(exit_code, stdout)

def test_WHEN_expired_credentials_THEN_raises_2():
    # Set up our mock
    exit_code = 1
    stdout = [
        "MyStack: building assets...",
        "",
        "",
        " ❌ Building assets failed: Error: Building Assets Failed: ExpiredToken: The security token included in the request is expired",
        "    at buildAllStackAssets (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:374:115279)",
        "    at process.processTicksAndRejections (node:internal/process/task_queues:95:5)",
        "    at async CdkToolkit.deploy (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:374:143496)",
        "    at async exec4 (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:429:51795)"
    ]

    # Run our test
    with pytest.raises(exceptions.CommonExpiredAWSCredentials):
        exceptions.raise_common_exceptions(exit_code, stdout)

def test_WHEN_invalid_token_THEN_raises():
    # Set up our mock
    exit_code = 1
    raw_stdout = """
    ⏳  Bootstrapping environment aws://XXXXXXXXXXXX/us-east-2...
    ❌  Environment aws://XXXXXXXXXXXX/us-east-2 failed bootstrapping: InvalidClientTokenId: The security token included in the request is invalid
        at Request.extractError (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:266:46127)
        at Request.callListeners (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:266:88989)
        at Request.emit (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:266:88437)
        at Request.emit (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:266:194844)
        at Request.transition (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:266:188396)
        at AcceptorStateMachine.runTo (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:266:153268)
        at /Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:266:153598
        at Request.<anonymous> (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:266:188688)
        at Request.<anonymous> (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:266:194919)
        at Request.callListeners (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:266:89157) {
    code: 'InvalidClientTokenId',
    time: 2023-03-22T20:45:07.284Z,
    requestId: '010836c7-51ef-4f41-bb50-b6799af00b55',
    statusCode: 403,
    retryable: false,
    retryDelay: 61.18240384871556
    }

    The security token included in the request is invalid
    """

    stdout = raw_stdout.split("\n")

    # Run our test
    with pytest.raises(exceptions.CommonInvalidAWSToken):
        exceptions.raise_common_exceptions(exit_code, stdout)

def test_WHEN_signature_mismatch_THEN_raises():
    # Set up our mock
    exit_code = 1
    raw_stdout = """
    ❌  Environment aws://XXXXXXXXXXXX/us-east-2 failed bootstrapping: SignatureDoesNotMatch: The request signature we calculated does not match the signature you provided. Check your AWS Secret Access Key and signing method. Consult the service documentation for details.
        at Request.extractError (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:266:46127)
        at Request.callListeners (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:266:88989)
        at Request.emit (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:266:88437)
        at Request.emit (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:266:194844)
        at Request.transition (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:266:188396)
        at AcceptorStateMachine.runTo (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:266:153268)
        at /Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:266:153598
        at Request.<anonymous> (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:266:188688)
        at Request.<anonymous> (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:266:194919)
        at Request.callListeners (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:266:89157) {
    code: 'SignatureDoesNotMatch',
    time: 2023-03-22T20:42:06.356Z,
    requestId: 'ce1c2f4e-aa40-4d39-a6c0-52f034ba39c4',
    statusCode: 403,
    retryable: false,
    retryDelay: 9.526405429290662
    }

    The request signature we calculated does not match the signature you provided. Check your AWS Secret Access Key and signing method. Consult the service documentation for details.
    """

    stdout = raw_stdout.split("\n")

    # Run our test
    with pytest.raises(exceptions.CommonAWSCredentialsSigMismatch):
        exceptions.raise_common_exceptions(exit_code, stdout)

def test_WHEN_not_bootstrapped_stack_THEN_raises_1():
    # Set up our mock
    exit_code = 1
    stdout = [
        "MyStack: building assets...",
        "",
        "current credentials could not be used to assume 'arn:aws:iam::XXXXXXXXXXXX:role/rolename', but are for the right account. Proceeding anyway.",
        "",
        " ❌ Building assets failed: Error: Building Assets Failed: Error: MyStack: SSM parameter /cdk-bootstrap/blah/version not found. Has the environment been bootstrapped? Please run 'cdk bootstrap' (see https://docs.aws.amazon.com/cdk/latest/guide/bootstrapping.html)",
        "    at buildAllStackAssets (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:374:115279)",
        "    at process.processTicksAndRejections (node:internal/process/task_queues:95:5)",
        "    at async CdkToolkit.deploy (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:374:143496)",
        "    at async exec4 (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:429:51795)",
        "",
        "Building Assets Failed: Error: MyStack: SSM parameter /cdk-bootstrap/blah/version not found. Has the environment been bootstrapped? Please run 'cdk bootstrap' (see https://docs.aws.amazon.com/cdk/latest/guide/bootstrapping.html)"
    ]

    # Run our test
    with pytest.raises(exceptions.CommonCdkNotBootstrapped):
        exceptions.raise_common_exceptions(exit_code, stdout)

def test_WHEN_not_bootstrapped_stack_THEN_raises_2():
    # Set up our mock
    exit_code = 1
    raw_stdout = """
    [0%] start: Building da93f9fd3c42d618a322361a988afe52bdd76e6b284c1b2dbfadd7e063fe24df:XXXXXXXXXXXX-us-east-2
    [0%] start: Building ed75578691729c241bb3f8fb32c6e68b317241e63c3ab33684c92f69ab66c9fc:XXXXXXXXXXXX-us-east-2
    [50%] success: Built da93f9fd3c42d618a322361a988afe52bdd76e6b284c1b2dbfadd7e063fe24df:XXXXXXXXXXXX-us-east-2
    [100%] fail: No ECR repository named 'cdk-hnb659fds-container-assets-XXXXXXXXXXXX-us-east-2' in account XXXXXXXXXXXX. Is this account bootstrapped?
    """

    stdout = raw_stdout.split("\n")

    # Run our test
    with pytest.raises(exceptions.CommonCdkNotBootstrapped):
        exceptions.raise_common_exceptions(exit_code, stdout)


# =================================================================================================
# Errors to handle later
# =================================================================================================
"""
DemoTrafficGen01: building assets...

[0%] start: Building c16765d316b0a0e32a95dcb3a7df3944f77b34b648c79674da3745e676b10aec:968674222892-us-east-2
[0%] start: Building 7b0b50bef7003cc0426593d21af569fed652d3a5b1a759cac8c3a74eea1365a1:968674222892-us-east-2
[50%] success: Built c16765d316b0a0e32a95dcb3a7df3944f77b34b648c79674da3745e676b10aec:968674222892-us-east-2
[100%] fail: docker login --username AWS --password-stdin https://968674222892.dkr.ecr.us-east-2.amazonaws.com exited with error code 1: Error saving credentials: error storing credentials - err: exit status 1, out: `Post "http://ipc/registry/credstore-updated": dial unix backend.sock: connect: no such file or directory`
DemoTrafficGen02: building assets...

[0%] start: Building 3badb358a7479c1ec6ee2fda786ccba4d8e6523674fc9bfe52720a7302d3d58a:968674222892-us-east-2
[0%] start: Building 7b0b50bef7003cc0426593d21af569fed652d3a5b1a759cac8c3a74eea1365a1:968674222892-us-east-2
[50%] success: Built 3badb358a7479c1ec6ee2fda786ccba4d8e6523674fc9bfe52720a7302d3d58a:968674222892-us-east-2
[100%] fail: docker login --username AWS --password-stdin https://968674222892.dkr.ecr.us-east-2.amazonaws.com exited with error code 1: Error saving credentials: error storing credentials - err: exit status 1, out: `Post "http://ipc/registry/credstore-updated": dial unix backend.sock: connect: no such file or directory`

 ❌ Building assets failed: Error: Building Assets Failed: Error: Failed to build one or more assets. See the error messages above for more information., Error: Failed to build one or more assets. See the error messages above for more information.
    at buildAllStackAssets (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:374:115279)
    at async CdkToolkit.deploy (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:374:143496)
    at async exec4 (/Users/username/.nvm/versions/node/v19.0.0/lib/node_modules/aws-cdk/lib/index.js:429:51795)

Building Assets Failed: Error: Failed to build one or more assets. See the error messages above for more information., Error: Failed to build one or more assets. See the error messages above for more information.
"""




