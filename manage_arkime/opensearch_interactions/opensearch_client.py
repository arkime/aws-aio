import json
import logging
from requests.auth import HTTPBasicAuth
from typing import Dict

import opensearch_interactions.rest_ops as ops

logger = logging.getLogger(__name__)


class OpenSearchClient:
    def __init__(self, endpoint: str, port: int, auth: HTTPBasicAuth):
        self.endpoint = endpoint
        self.port = port
        self.auth = auth

    def __eq__(self, other) -> bool:
        return self.endpoint == other.endpoint and self.port == other.port and self.auth == other.auth

    def get_ism_policy(self, policy_id: str) -> ops.RESTResponse:
        """
        Get an ISM Policy by its policy ID
        """
        logger.debug(f"Getting ISM policy:\n{policy_id}")
        rest_path = ops.RESTPath(prefix=self.endpoint, port=self.port, suffix=f"_plugins/_ism/policies/{policy_id}")
        return ops.perform_get(rest_path=rest_path, auth=self.auth)
    
    def create_ism_policy(self, policy_id: str, policy: Dict[str, any]) -> ops.RESTResponse:
        """
        Put a new ISM policy by ID
        """
        logger.debug(f"Creating ISM policy:\n{policy_id}\n{json.dumps(policy)}")
        rest_path = ops.RESTPath(prefix=self.endpoint, port=self.port, suffix=f"_plugins/_ism/policies/{policy_id}")
        headers = {"Content-Type": "application/json"}

        return ops.perform_put(rest_path=rest_path, data=json.dumps(policy), headers=headers, auth=self.auth)
    
    def update_ism_policy(self, policy_id: str, policy: Dict[str, any], seq_no: int, primary_term: int) -> ops.RESTResponse:
        """
        Update an existing ISM policy by ID
        """
        logger.debug(f"Updating ISM policy:\n{policy_id}\n{json.dumps(policy)}")
        rest_path = ops.RESTPath(prefix=self.endpoint, port=self.port, suffix=f"_plugins/_ism/policies/{policy_id}?if_seq_no={seq_no}&if_primary_term={primary_term}")
        headers = {"Content-Type": "application/json"}

        return ops.perform_put(rest_path=rest_path, data=json.dumps(policy), headers=headers, auth=self.auth)
    
    def add_ism_policy_to_index(self, policy_id: str, index_str: str) -> ops.RESTResponse:
        """
        Adds an ISM policy to an OpenSearch index or indices
        """
        logger.debug(f"Adding ISM policy to index:\n{policy_id}\n{index_str}")
        rest_path = ops.RESTPath(prefix=self.endpoint, port=self.port, suffix=f"_plugins/_ism/add/{index_str}")
        policy_identifier = {"policy_id": policy_id}
        headers = {"Content-Type": "application/json"}

        return ops.perform_post(rest_path=rest_path, data=json.dumps(policy_identifier), headers=headers, auth=self.auth)
    
    def set_ism_policy_of_index(self, policy_id: str, index_str: str) -> ops.RESTResponse:
        """
        Updates which ISM policy applies to an existing OpenSearch index or indices
        """
        logger.debug(f"Setting ISM policy of index:\n{policy_id}\n{index_str}")
        rest_path = ops.RESTPath(prefix=self.endpoint, port=self.port, suffix=f"_plugins/_ism/change_policy/{index_str}")
        policy_identifier = {"policy_id": policy_id}
        headers = {"Content-Type": "application/json"}

        return ops.perform_post(rest_path=rest_path, data=json.dumps(policy_identifier), headers=headers, auth=self.auth)
