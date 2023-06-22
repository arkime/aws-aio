import opensearch_interactions.ism_policies as policies
from opensearch_interactions.opensearch_client import OpenSearchClient



def setup_user_history_ism(history_days: int, client: OpenSearchClient):
    # Create the new policy template
    policy = policies.get_user_history_ism_policy(history_days)

    # Get the existing policy, if it exists
    get_policy_raw = client.get_ism_policy(policies.ISM_ID_HISTORY)

    # If it exists
    if get_policy_raw.succeeded:
        # Update the existing policy
        sequence_number = get_policy_raw.response_json["_seq_no"]
        primary_term = get_policy_raw.response_json["_primary_term"]
        client.update_ism_policy(policies.ISM_ID_HISTORY, policy, sequence_number, primary_term)

        # Ensure existing indices with that policy use the updated version
        client.set_ism_policy_of_index(policies.ISM_ID_HISTORY, policies.INDEX_PATTERN_HISTORY)

        # Add the policy to any new indices
        client.add_ism_policy_to_index(policies.ISM_ID_HISTORY, policies.INDEX_PATTERN_HISTORY)
    else:
        # Create the policy
        client.create_ism_policy(policies.ISM_ID_HISTORY, policy)

        # Add the policy to the indices
        client.add_ism_policy_to_index(policies.ISM_ID_HISTORY, policies.INDEX_PATTERN_HISTORY)

def setup_sessions_ism(spi_days: int, replicas: int, client: OpenSearchClient):
    # Create the new policy template
    policy = policies.get_sessions_ism_policy(spi_days, 0, replicas, policies.ISM_DEFAULT_MERGE_SEGMENTS)

    # Get the existing policy, if it exists
    get_policy_raw = client.get_ism_policy(policies.ISM_ID_SESSIONS)

    # If it exists
    if get_policy_raw.succeeded:
        # Update the existing policy
        sequence_number = get_policy_raw.response_json["_seq_no"]
        primary_term = get_policy_raw.response_json["_primary_term"]
        client.update_ism_policy(policies.ISM_ID_SESSIONS, policy, sequence_number, primary_term)

        # Ensure existing indices with that policy use the updated version
        client.set_ism_policy_of_index(policies.ISM_ID_SESSIONS, policies.INDEX_PATTERN_SESSIONS)

        # Add the policy to any new indices
        client.add_ism_policy_to_index(policies.ISM_ID_SESSIONS, policies.INDEX_PATTERN_SESSIONS)
    else:
        # Create the policy
        client.create_ism_policy(policies.ISM_ID_SESSIONS, policy)

        # Add the policy to the indices
        client.add_ism_policy_to_index(policies.ISM_ID_SESSIONS, policies.INDEX_PATTERN_SESSIONS)