import json
import pytest
from requests.auth import HTTPBasicAuth
import unittest.mock as mock

import opensearch_interactions.rest_ops as ops
import opensearch_interactions.ism_policies as policies
import opensearch_interactions.opensearch_client as client
import opensearch_interactions.ism_interactions as ism


POLICY_ID = "policy"
POLICY = {"rotation": "yes"}
HISTORY_DAYS = 365
SPI_DAYS = 30
REPLICAS = 2
SEQ_NO = 1
PRIMARY_TERM = 1

def test_WHEN_setup_user_history_ism_AND_exists_THEN_as_expected():
    # Set up our mock
    mock_client = mock.Mock()

    policy_resp = mock.Mock()
    policy_resp.response_json = {"_seq_no": SEQ_NO, "_primary_term": PRIMARY_TERM}
    policy_resp.succeeded = True
    mock_client.get_ism_policy.return_value = policy_resp

    # Run our test
    ism.setup_user_history_ism(HISTORY_DAYS, mock_client)

    # Check the results
    expected_get_ism_calls = [
        mock.call(policies.ISM_ID_HISTORY)
    ]
    assert expected_get_ism_calls == mock_client.get_ism_policy.call_args_list

    expected_update_ism_calls = [
        mock.call(
            policies.ISM_ID_HISTORY,
            policies.get_user_history_ism_policy(HISTORY_DAYS),
            SEQ_NO,
            PRIMARY_TERM
        )
    ]
    assert expected_update_ism_calls == mock_client.update_ism_policy.call_args_list

    expected_set_ism_calls = [
        mock.call(
            policies.ISM_ID_HISTORY,
            policies.INDEX_PATTERN_HISTORY,
        )
    ]
    assert expected_set_ism_calls == mock_client.set_ism_policy_of_index.call_args_list

    expected_add_ism_calls = [
        mock.call(
            policies.ISM_ID_HISTORY,
            policies.INDEX_PATTERN_HISTORY,
        )
    ]
    assert expected_add_ism_calls == mock_client.add_ism_policy_to_index.call_args_list

def test_WHEN_setup_user_history_ism_AND_doesnt_exists_THEN_as_expected():
    # Set up our mock
    mock_client = mock.Mock()

    policy_resp = mock.Mock()
    policy_resp.succeeded = False
    mock_client.get_ism_policy.return_value = policy_resp

    # Run our test
    ism.setup_user_history_ism(HISTORY_DAYS, mock_client)

    # Check the results
    expected_get_ism_calls = [
        mock.call(policies.ISM_ID_HISTORY)
    ]
    assert expected_get_ism_calls == mock_client.get_ism_policy.call_args_list

    expected_update_ism_calls = []
    assert expected_update_ism_calls == mock_client.update_ism_policy.call_args_list

    expected_set_ism_calls = []
    assert expected_set_ism_calls == mock_client.set_ism_policy_of_index.call_args_list

    expected_create_ism_calls = [
        mock.call(
            policies.ISM_ID_HISTORY,
            policies.get_user_history_ism_policy(HISTORY_DAYS),
        )
    ]
    assert expected_create_ism_calls == mock_client.create_ism_policy.call_args_list

    expected_add_ism_calls = [
        mock.call(
            policies.ISM_ID_HISTORY,
            policies.INDEX_PATTERN_HISTORY,
        )
    ]
    assert expected_add_ism_calls == mock_client.add_ism_policy_to_index.call_args_list

def test_WHEN_setup_sessions_ism_AND_exists_THEN_as_expected():
    # Set up our mock
    mock_client = mock.Mock()

    policy_resp = mock.Mock()
    policy_resp.response_json = {"_seq_no": SEQ_NO, "_primary_term": PRIMARY_TERM}
    policy_resp.succeeded = True
    mock_client.get_ism_policy.return_value = policy_resp

    # Run our test
    ism.setup_sessions_ism(SPI_DAYS, REPLICAS, mock_client)

    # Check the results
    expected_get_ism_calls = [
        mock.call(policies.ISM_ID_SESSIONS)
    ]
    assert expected_get_ism_calls == mock_client.get_ism_policy.call_args_list

    expected_update_ism_calls = [
        mock.call(
            policies.ISM_ID_SESSIONS,
            policies.get_sessions_ism_policy(SPI_DAYS, 0, REPLICAS, 1),
            SEQ_NO,
            PRIMARY_TERM
        )
    ]
    assert expected_update_ism_calls == mock_client.update_ism_policy.call_args_list

    expected_set_ism_calls = [
        mock.call(
            policies.ISM_ID_SESSIONS,
            policies.INDEX_PATTERN_SESSIONS,
        )
    ]
    assert expected_set_ism_calls == mock_client.set_ism_policy_of_index.call_args_list

    expected_add_ism_calls = [
        mock.call(
            policies.ISM_ID_SESSIONS,
            policies.INDEX_PATTERN_SESSIONS,
        )
    ]
    assert expected_add_ism_calls == mock_client.add_ism_policy_to_index.call_args_list

def test_WHEN_setup_sessions_ism_AND_doesnt_exists_THEN_as_expected():
    # Set up our mock
    mock_client = mock.Mock()

    policy_resp = mock.Mock()
    policy_resp.succeeded = False
    mock_client.get_ism_policy.return_value = policy_resp

    # Run our test
    ism.setup_sessions_ism(SPI_DAYS, REPLICAS, mock_client)

    # Check the results
    expected_get_ism_calls = [
        mock.call(policies.ISM_ID_SESSIONS)
    ]
    assert expected_get_ism_calls == mock_client.get_ism_policy.call_args_list

    expected_update_ism_calls = []
    assert expected_update_ism_calls == mock_client.update_ism_policy.call_args_list

    expected_set_ism_calls = []
    assert expected_set_ism_calls == mock_client.set_ism_policy_of_index.call_args_list

    expected_create_ism_calls = [
        mock.call(
            policies.ISM_ID_SESSIONS,
            policies.get_sessions_ism_policy(SPI_DAYS, 0, REPLICAS, 1),
        )
    ]
    assert expected_create_ism_calls == mock_client.create_ism_policy.call_args_list

    expected_add_ism_calls = [
        mock.call(
            policies.ISM_ID_SESSIONS,
            policies.INDEX_PATTERN_SESSIONS,
        )
    ]
    assert expected_add_ism_calls == mock_client.add_ism_policy_to_index.call_args_list