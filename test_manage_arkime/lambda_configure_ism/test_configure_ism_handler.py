import json
import unittest.mock as mock

from lambda_configure_ism.configure_ism_handler import ConfigureIsmHandler
import aws_interactions.cloudwatch_interactions as cwi
import constants as constants

@mock.patch("lambda_configure_ism.configure_ism_handler.os")
@mock.patch("lambda_configure_ism.configure_ism_handler.ism.setup_sessions_ism")
@mock.patch("lambda_configure_ism.configure_ism_handler.ism.setup_user_history_ism")
@mock.patch("lambda_configure_ism.configure_ism_handler.AwsClientProvider")
@mock.patch("lambda_configure_ism.configure_ism_handler.cwi")
def test_WHEN_ConfigureIsmHandler_handle_called_THEN_sets_up_mirroring(mock_cwi, mock_provider, mock_setup_history, mock_setup_sessions, mock_os):
    # Set up our mock
    mock_cwi.ConfigureIsmEventMetrics = cwi.ConfigureIsmEventMetrics
    mock_cwi.ConfigureIsmEventOutcome = cwi.ConfigureIsmEventOutcome

    mock_secrets_client = mock.Mock()
    mock_secrets_client.get_secret_value.return_value = {"SecretString": "password"}
    mock_provider_instance = mock.Mock()
    mock_provider_instance.get_secretsmanager.return_value = mock_secrets_client
    mock_provider.return_value = mock_provider_instance

    mock_os.environ = {"CLUSTER_NAME": "cluster_name", "OPENSEARCH_ENDPOINT": "endpoint", "OPENSEARCH_SECRET_ARN": "arn"}

    # Run our test
    test_event = {
        "detail-type": constants.EVENT_DETAIL_TYPE_CONFIGURE_ISM,
        "source": constants.EVENT_SOURCE,
        "detail": {
            "history_days": 365,
            "spi_days": 30,
            "replicas": 1,
        }
    }

    actual_return = ConfigureIsmHandler().handler(test_event, {})

    # Check our results
    expected_return = {"statusCode": 200}
    assert expected_return == actual_return

    expected_get_secret_calls = [
        mock.call(SecretId="arn"),
    ]
    assert expected_get_secret_calls == mock_secrets_client.get_secret_value.call_args_list

    expected_setup_history_calls = [
        mock.call(
            365,
            mock.ANY
        ),
    ]
    assert expected_setup_history_calls == mock_setup_history.call_args_list

    expected_setup_sessions_calls = [
        mock.call(
            30,
            1,
            mock.ANY
        ),
    ]
    assert expected_setup_sessions_calls == mock_setup_sessions.call_args_list

    expected_put_metrics_calls = [
        mock.call(            
            cwi.ConfigureIsmEventMetrics(
                "cluster_name",
                cwi.ConfigureIsmEventOutcome.SUCCESS
            ),
            mock.ANY
        ),
    ]
    assert expected_put_metrics_calls == mock_cwi.put_event_metrics.call_args_list

@mock.patch("lambda_configure_ism.configure_ism_handler.os")
@mock.patch("lambda_configure_ism.configure_ism_handler.ism.setup_sessions_ism")
@mock.patch("lambda_configure_ism.configure_ism_handler.ism.setup_user_history_ism")
@mock.patch("lambda_configure_ism.configure_ism_handler.AwsClientProvider")
@mock.patch("lambda_configure_ism.configure_ism_handler.cwi")
def test_WHEN_ConfigureIsmHandler_handle_called_AND_unhandled_ex_THEN_handles_gracefully(mock_cwi, mock_provider, mock_setup_history, mock_setup_sessions, mock_os):
    # Set up our mock
    mock_cwi.ConfigureIsmEventMetrics = cwi.ConfigureIsmEventMetrics
    mock_cwi.ConfigureIsmEventOutcome = cwi.ConfigureIsmEventOutcome

    mock_secrets_client = mock.Mock()
    mock_secrets_client.get_secret_value.side_effect = Exception("boom")
    mock_provider_instance = mock.Mock()
    mock_provider_instance.get_secretsmanager.return_value = mock_secrets_client
    mock_provider.return_value = mock_provider_instance

    mock_os.environ = {"CLUSTER_NAME": "cluster_name", "OPENSEARCH_ENDPOINT": "endpoint", "OPENSEARCH_SECRET_ARN": "arn"}

    # Run our test
    test_event = {
        "detail-type": constants.EVENT_DETAIL_TYPE_CONFIGURE_ISM,
        "source": constants.EVENT_SOURCE,
        "detail": {
            "history_days": 365,
            "spi_days": 30,
            "replicas": 1,
        }
    }

    actual_return = ConfigureIsmHandler().handler(test_event, {})

    # Check our results
    expected_return = {"statusCode": 500}
    assert expected_return == actual_return

    expected_get_secret_calls = [
        mock.call(SecretId="arn"),
    ]
    assert expected_get_secret_calls == mock_secrets_client.get_secret_value.call_args_list

    expected_setup_history_calls = []
    assert expected_setup_history_calls == mock_setup_history.call_args_list

    expected_setup_sessions_calls = []
    assert expected_setup_sessions_calls == mock_setup_sessions.call_args_list

    expected_put_metrics_calls = [
        mock.call(            
            cwi.ConfigureIsmEventMetrics(
                "cluster_name",
                cwi.ConfigureIsmEventOutcome.FAILURE
            ),
            mock.ANY
        ),
    ]
    assert expected_put_metrics_calls == mock_cwi.put_event_metrics.call_args_list