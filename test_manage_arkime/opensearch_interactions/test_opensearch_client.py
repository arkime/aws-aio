import json
from requests.auth import HTTPBasicAuth
import unittest.mock as mock

import opensearch_interactions.rest_ops as ops
import opensearch_interactions.opensearch_client as client


ENDPOINT = "https://menegroth"
PORT = 443
AUTH = HTTPBasicAuth("beren", "fate")
POLICY_ID = "policy"
POLICY = {"rotation": "yes"}
SEQ_NO = 1
PRIMARY_TERM = 1
INDEX_STR = "atanatári_*"

@mock.patch("opensearch_interactions.opensearch_client.ops.perform_get")
def test_WHEN_get_ism_policy_THEN_as_expected(mock_get):
    # Set up our mock
    return_val = mock.Mock()
    mock_get.return_value = return_val

    # Run our test
    test_client = client.OpenSearchClient(ENDPOINT, PORT, AUTH)
    actual_value = test_client.get_ism_policy(POLICY_ID)

    # Check the results
    assert actual_value == return_val

    expected_calls = [
        mock.call(
            rest_path=ops.RESTPath(prefix=ENDPOINT, port=PORT, suffix=f"_plugins/_ism/policies/{POLICY_ID}"),
            auth=AUTH
        )
    ]
    assert expected_calls == mock_get.call_args_list

@mock.patch("opensearch_interactions.opensearch_client.ops.perform_put")
def test_WHEN_create_ism_policy_THEN_as_expected(mock_put):
    # Set up our mock
    return_val = mock.Mock()
    mock_put.return_value = return_val

    # Run our test
    test_client = client.OpenSearchClient(ENDPOINT, PORT, AUTH)
    actual_value = test_client.create_ism_policy(POLICY_ID, POLICY)

    # Check the results
    assert actual_value == return_val

    expected_calls = [
        mock.call(
            rest_path=ops.RESTPath(prefix=ENDPOINT, port=PORT, suffix=f"_plugins/_ism/policies/{POLICY_ID}"),
            data=json.dumps(POLICY),
            headers={"Content-Type": "application/json"},
            auth=AUTH
        )
    ]
    assert expected_calls == mock_put.call_args_list

@mock.patch("opensearch_interactions.opensearch_client.ops.perform_put")
def test_WHEN_update_ism_policy_THEN_as_expected(mock_put):
    # Set up our mock
    return_val = mock.Mock()
    mock_put.return_value = return_val

    # Run our test
    test_client = client.OpenSearchClient(ENDPOINT, PORT, AUTH)
    actual_value = test_client.update_ism_policy(POLICY_ID, POLICY, SEQ_NO, PRIMARY_TERM)

    # Check the results
    assert actual_value == return_val

    expected_calls = [
        mock.call(
            rest_path=ops.RESTPath(prefix=ENDPOINT, port=PORT, suffix=f"_plugins/_ism/policies/{POLICY_ID}?if_seq_no={SEQ_NO}&if_primary_term={PRIMARY_TERM}"),
            data=json.dumps(POLICY),
            headers={"Content-Type": "application/json"},
            auth=AUTH
        )
    ]
    assert expected_calls == mock_put.call_args_list

@mock.patch("opensearch_interactions.opensearch_client.ops.perform_post")
def test_WHEN_add_ism_policy_to_index_THEN_as_expected(mock_post):
    # Set up our mock
    return_val = mock.Mock()
    mock_post.return_value = return_val

    # Run our test
    test_client = client.OpenSearchClient(ENDPOINT, PORT, AUTH)
    actual_value = test_client.add_ism_policy_to_index(POLICY_ID, INDEX_STR)

    # Check the results
    assert actual_value == return_val

    expected_calls = [
        mock.call(
            rest_path=ops.RESTPath(prefix=ENDPOINT, port=PORT, suffix=f"_plugins/_ism/add/{INDEX_STR}"),
            data=json.dumps({"policy_id": POLICY_ID}),
            headers={"Content-Type": "application/json"},
            auth=AUTH
        )
    ]
    assert expected_calls == mock_post.call_args_list

@mock.patch("opensearch_interactions.opensearch_client.ops.perform_post")
def test_WHEN_update_ism_policy_of_index_THEN_as_expected(mock_post):
    # Set up our mock
    return_val = mock.Mock()
    mock_post.return_value = return_val

    # Run our test
    test_client = client.OpenSearchClient(ENDPOINT, PORT, AUTH)
    actual_value = test_client.set_ism_policy_of_index(POLICY_ID, INDEX_STR)

    # Check the results
    assert actual_value == return_val

    expected_calls = [
        mock.call(
            rest_path=ops.RESTPath(prefix=ENDPOINT, port=PORT, suffix=f"_plugins/_ism/change_policy/{INDEX_STR}"),
            data=json.dumps({"policy_id": POLICY_ID}),
            headers={"Content-Type": "application/json"},
            auth=AUTH
        )
    ]
    assert expected_calls == mock_post.call_args_list


