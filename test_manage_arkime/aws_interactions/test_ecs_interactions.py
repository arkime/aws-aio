import pytest
import unittest.mock as mock

from botocore.exceptions import ClientError

import aws_interactions.ecs_interactions as ecsi


def test_WHEN_force_ecs_deployment_called_THEN_as_expected():
    # Set up our mock
    mock_ecs_client = mock.Mock()
    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_ecs.return_value = mock_ecs_client

    # Run our test
    ecsi.force_ecs_deployment("cluster", "service", mock_aws_provider)

    # Check the results
    expected_update_calls = [
        mock.call(cluster="cluster", service="service", forceNewDeployment=True)
    ]
    assert expected_update_calls == mock_ecs_client.update_service.call_args_list

def test_WHEN_is_deployment_in_progress_called_THEN_as_expected():
    # Set up our mock
    mock_ecs_client = mock.Mock()
    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_ecs.return_value = mock_ecs_client

    # TEST: Deployment is in progress
    mock_ecs_client.describe_services.return_value = {
        "services": [
            {
                "deployments": [
                    {"rolloutState": "IN_PROGRESS"},
                    {"rolloutState": "COMPLETED"},
                ]
            }
        ]
    }
    
    result = ecsi.is_deployment_in_progress("cluster", "service", mock_aws_provider)
    assert True == result

    expected_describe_calls = [
        mock.call(cluster="cluster", services=["service"])
    ]
    assert expected_describe_calls == mock_ecs_client.describe_services.call_args_list

    # TEST: Deployment is not in progress
    mock_ecs_client.describe_services.return_value = {
        "services": [
            {
                "deployments": [
                    {"rolloutState": "FAILED"},
                    {"rolloutState": "COMPLETED"},
                ]
            }
        ]
    }
    result = ecsi.is_deployment_in_progress("cluster", "service", mock_aws_provider)
    assert False == result

def test_WHEN_get_failed_task_count_called_THEN_as_expected():
    # Set up our mock
    mock_ecs_client = mock.Mock()
    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_ecs.return_value = mock_ecs_client

    # TEST: Scenario 1
    mock_ecs_client.describe_services.return_value = {
        "services": [
            {
                "deployments": [
                    {"failedTasks": 0},
                    {"failedTasks": 7},
                ]
            }
        ]
    }
    result = ecsi.get_failed_task_count("cluster", "service", mock_aws_provider)
    assert 7 == result

    expected_describe_calls = [
        mock.call(cluster="cluster", services=["service"])
    ]
    assert expected_describe_calls == mock_ecs_client.describe_services.call_args_list

    # TEST: Scenario 2
    mock_ecs_client.describe_services.return_value = {
        "services": [
            {
                "deployments": [
                    {"failedTasks": 0},
                ]
            }
        ]
    }
    result = ecsi.get_failed_task_count("cluster", "service", mock_aws_provider)
    assert 0 == result
