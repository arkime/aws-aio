import json
import unittest.mock as mock

from lambda_configure_ism.configure_ism_handler import ConfigureIsmHandler
from opensearch_interactions.opensearch_client import OpenSearchClient
import aws_interactions.cloudwatch_interactions as cwi
import constants as constants

@mock.patch("lambda_configure_ism.configure_ism_handler.os")
@mock.patch("lambda_configure_ism.configure_ism_handler.ism.setup_user_history_ism")
@mock.patch("lambda_configure_ism.configure_ism_handler.AwsClientProvider")
@mock.patch("lambda_configure_ism.configure_ism_handler.cwi")
def test_WHEN_CreateEniMirrorHandler_handle_called_THEN_sets_up_mirroring(mock_cwi, mock_provider, mock_setup_history, mock_os):
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

# @mock.patch("lambda_create_eni_mirror.create_eni_mirror_handler.AwsClientProvider", mock.Mock())
# @mock.patch("lambda_create_eni_mirror.create_eni_mirror_handler.cwi")
# @mock.patch("lambda_create_eni_mirror.create_eni_mirror_handler.ssm_ops")
# @mock.patch("lambda_create_eni_mirror.create_eni_mirror_handler.ec2i")
# def test_WHEN_CreateEniMirrorHandler_handle_called_AND_unhandled_ex_THEN_handles_gracefully(mock_ec2i, mock_ssm_ops, mock_cwi):
#     # Set up our mock
#     mock_cwi.CreateEniMirrorEventMetrics = cwi.CreateEniMirrorEventMetrics
#     mock_cwi.CreateEniMirrorEventOutcome = cwi.CreateEniMirrorEventOutcome

#     mock_ec2i.NetworkInterface = ec2i.NetworkInterface
#     mock_ec2i.mirror_eni.return_value = "session-1"

#     mock_ssm_ops.get_ssm_param_value.side_effect = Exception("boom")
#     mock_ssm_ops.get_ssm_param_json_value.return_value = "target-1"

#     # Run our test
#     test_event = {
#         "detail-type": constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR,
#         "source": constants.EVENT_SOURCE,
#         "detail": {
#             "cluster_name": "cluster-1",
#             "vpc_id": "vpc-1",
#             "subnet_id": "subnet-1",
#             "eni_id": "eni-1",
#             "eni_type": "eni-type-1",
#             "traffic_filter_id": "filter-1",
#             "vni": 1234
#         }
#     }

#     actual_return = CreateEniMirrorHandler().handler(test_event, {})

#     # Check our results
#     expected_return = {"statusCode": 500}
#     assert expected_return == actual_return

#     expected_mirror_calls = []
#     assert expected_mirror_calls == mock_ec2i.mirror_eni.call_args_list

#     expected_put_calls = []
#     assert expected_put_calls == mock_ssm_ops.put_ssm_param.call_args_list

#     expected_put_metrics_calls = [
#         mock.call(            
#             cwi.CreateEniMirrorEventMetrics(
#                 "cluster-1", 
#                 "vpc-1",
#                 cwi.CreateEniMirrorEventOutcome.FAILURE
#             ),
#             mock.ANY
#         ),
#     ]
#     assert expected_put_metrics_calls == mock_cwi.put_event_metrics.call_args_list