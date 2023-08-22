import pytest
import unittest.mock as mock

from botocore.exceptions import ClientError

import aws_interactions.iam_interactions as iami

class ExpectedException(Exception):
    def __init__(self):
        super().__init__(f"This was expected")

def test_WHEN_does_iam_role_exist_called_THEN_as_expected():
    # Set up our mock
    mock_iam_client = mock.Mock()
    mock_iam_client.get_role.side_effect = [
        {"response": []},
        ClientError(error_response={"Error": {"Code": "NoSuchEntity"}}, operation_name=""),
        ExpectedException()
    ]

    mock_provider = mock.Mock()
    mock_provider.get_iam.return_value = mock_iam_client

    # TEST: Role does exist
    actual_value = iami.does_iam_role_exist("role", mock_provider)
    assert True == actual_value

    # TEST: Role does not exist
    actual_value = iami.does_iam_role_exist("role", mock_provider)    
    assert False == actual_value

    # TEST: Unexpected error
    with pytest.raises(ExpectedException):
        iami.does_iam_role_exist("role", mock_provider)

@mock.patch("aws_interactions.iam_interactions.does_iam_role_exist")
def test_WHEN_delete_iam_role_called_THEN_as_expected(mock_exists):
    # Set up our mock
    mock_exists.return_value = True

    mock_iam_client = mock.Mock()
    mock_iam_client.list_instance_profiles_for_role.return_value = {
        "InstanceProfiles": [
            {"InstanceProfileName": "ip-1"},
            {"InstanceProfileName": "ip-2"},
        ]
    }
    mock_iam_client.list_role_policies.return_value = {
        "PolicyNames": [
            "inline-1",
            "inline-2",
        ]
    }
    mock_iam_client.list_attached_role_policies.return_value = {
        "AttachedPolicies": [
            {"PolicyArn": "arn-1"},
            {"PolicyArn": "arn-2"},
        ]
    }

    mock_provider = mock.Mock()
    mock_provider.get_iam.return_value = mock_iam_client

    # Run the test
    iami.delete_iam_role("role", mock_provider)
    
    # Check the results
    expected_remove_profile_calls = [
        mock.call(InstanceProfileName="ip-1", RoleName="role"),
        mock.call(InstanceProfileName="ip-2", RoleName="role"),
    ]
    assert expected_remove_profile_calls == mock_iam_client.remove_role_from_instance_profile.call_args_list

    expected_delete_policy_calls = [
        mock.call(PolicyName="inline-1", RoleName="role"),
        mock.call(PolicyName="inline-2", RoleName="role"),
    ]
    assert expected_delete_policy_calls == mock_iam_client.delete_role_policy.call_args_list

    expected_detach_policy_calls = [
        mock.call(PolicyArn="arn-1", RoleName="role"),
        mock.call(PolicyArn="arn-2", RoleName="role"),
    ]
    assert expected_detach_policy_calls == mock_iam_client.detach_role_policy.call_args_list

    expected_delete_role_calls = [
        mock.call(RoleName="role"),
    ]
    assert expected_delete_role_calls == mock_iam_client.delete_role.call_args_list

@mock.patch("aws_interactions.iam_interactions.does_iam_role_exist")
def test_WHEN_delete_iam_role_called_AND_doesnt_exist_THEN_aborts(mock_exists):
    # Set up our mock
    mock_exists.return_value = False

    mock_iam_client = mock.Mock()
    mock_provider = mock.Mock()
    mock_provider.get_iam.return_value = mock_iam_client

    # Run the test
    iami.delete_iam_role("role", mock_provider)
    
    # Check the results
    expected_remove_profile_calls = []
    assert expected_remove_profile_calls == mock_iam_client.remove_role_from_instance_profile.call_args_list

    expected_delete_policy_calls = []
    assert expected_delete_policy_calls == mock_iam_client.delete_role_policy.call_args_list

    expected_detach_policy_calls = []
    assert expected_detach_policy_calls == mock_iam_client.detach_role_policy.call_args_list

    expected_delete_role_calls = []
    assert expected_delete_role_calls == mock_iam_client.delete_role.call_args_list