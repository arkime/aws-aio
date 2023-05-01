import json
import unittest.mock as mock

from lambda_destroy_eni_mirror.destroy_eni_mirror_handler import DestroyEniMirrorHandler
import aws_interactions.cloudwatch_interactions as cwi
import aws_interactions.ec2_interactions as ec2i
import constants as constants

@mock.patch("lambda_destroy_eni_mirror.destroy_eni_mirror_handler.AwsClientProvider", mock.Mock())
@mock.patch("lambda_destroy_eni_mirror.destroy_eni_mirror_handler.cwi")
@mock.patch("lambda_destroy_eni_mirror.destroy_eni_mirror_handler.ssm_ops")
@mock.patch("lambda_destroy_eni_mirror.destroy_eni_mirror_handler.ec2i")
def test_WHEN_DestroyEniMirrorHandler_handle_called_THEN_destroys_mirroring(mock_ec2i, mock_ssm_ops, mock_cwi):
    # Set up our mock
    mock_cwi.DestroyEniMirrorEventMetrics = cwi.DestroyEniMirrorEventMetrics
    mock_cwi.DestroyEniMirrorEventOutcome = cwi.DestroyEniMirrorEventOutcome

    mock_ssm_ops.get_ssm_param_json_value.return_value = "session-1"

    # Run our test
    test_event = {
        "detail-type": constants.EVENT_DETAIL_TYPE_DESTROY_ENI_MIRROR,
        "source": constants.EVENT_SOURCE,
        "detail": {
            "cluster_name": "cluster-1",
            "vpc_id": "vpc-1",
            "subnet_id": "subnet-1",
            "eni_id": "eni-1",
        }
    }

    actual_return = DestroyEniMirrorHandler().handler(test_event, {})

    # Check our results
    expected_return = {"statusCode": 200}
    assert expected_return == actual_return

    expected_mirror_calls = [
        mock.call(
            "session-1",
            mock.ANY
        ),
    ]
    assert expected_mirror_calls == mock_ec2i.delete_eni_mirroring.call_args_list

    expected_delete_calls = [
        mock.call(
            constants.get_eni_ssm_param_name("cluster-1", "vpc-1", "subnet-1", "eni-1"), 
            mock.ANY,
        ),
    ]
    assert expected_delete_calls == mock_ssm_ops.delete_ssm_param.call_args_list

    expected_put_metrics_calls = [
        mock.call(            
            cwi.DestroyEniMirrorEventMetrics(
                "cluster-1", 
                "vpc-1",
                cwi.DestroyEniMirrorEventOutcome.SUCCESS
            ),
            mock.ANY
        ),
    ]
    assert expected_put_metrics_calls == mock_cwi.put_event_metrics.call_args_list

@mock.patch("lambda_destroy_eni_mirror.destroy_eni_mirror_handler.AwsClientProvider", mock.Mock())
@mock.patch("lambda_destroy_eni_mirror.destroy_eni_mirror_handler.cwi")
@mock.patch("lambda_destroy_eni_mirror.destroy_eni_mirror_handler.ssm_ops")
@mock.patch("lambda_destroy_eni_mirror.destroy_eni_mirror_handler.ec2i")
def test_WHEN_DestroyEniMirrorHandler_handle_called_AND_session_doesnt_exist_THEN_handles_gracefully(mock_ec2i, mock_ssm_ops, mock_cwi):
    # Set up our mock
    mock_cwi.DestroyEniMirrorEventMetrics = cwi.DestroyEniMirrorEventMetrics
    mock_cwi.DestroyEniMirrorEventOutcome = cwi.DestroyEniMirrorEventOutcome

    mock_ec2i.MirrorDoesntExist = ec2i.MirrorDoesntExist
    mock_ec2i.delete_eni_mirroring.side_effect = ec2i.MirrorDoesntExist("session-1")

    mock_ssm_ops.get_ssm_param_json_value.return_value = "session-1"

    # Run our test
    test_event = {
        "detail-type": constants.EVENT_DETAIL_TYPE_DESTROY_ENI_MIRROR,
        "source": constants.EVENT_SOURCE,
        "detail": {
            "cluster_name": "cluster-1",
            "vpc_id": "vpc-1",
            "subnet_id": "subnet-1",
            "eni_id": "eni-1",
        }
    }

    actual_return = DestroyEniMirrorHandler().handler(test_event, {})

    # Check our results
    expected_return = {"statusCode": 200}
    assert expected_return == actual_return

    expected_mirror_calls = [
        mock.call(
            "session-1",
            mock.ANY
        ),
    ]
    assert expected_mirror_calls == mock_ec2i.delete_eni_mirroring.call_args_list

    expected_delete_calls = [
        mock.call(
            constants.get_eni_ssm_param_name("cluster-1", "vpc-1", "subnet-1", "eni-1"), 
            mock.ANY,
        ),
    ]
    assert expected_delete_calls == mock_ssm_ops.delete_ssm_param.call_args_list

    expected_put_metrics_calls = [
        mock.call(            
            cwi.DestroyEniMirrorEventMetrics(
                "cluster-1", 
                "vpc-1",
                cwi.DestroyEniMirrorEventOutcome.SUCCESS
            ),
            mock.ANY
        ),
    ]
    assert expected_put_metrics_calls == mock_cwi.put_event_metrics.call_args_list

@mock.patch("lambda_destroy_eni_mirror.destroy_eni_mirror_handler.AwsClientProvider", mock.Mock())
@mock.patch("lambda_destroy_eni_mirror.destroy_eni_mirror_handler.cwi")
@mock.patch("lambda_destroy_eni_mirror.destroy_eni_mirror_handler.ssm_ops")
@mock.patch("lambda_destroy_eni_mirror.destroy_eni_mirror_handler.ec2i")
def test_WHEN_DestroyEniMirrorHandler_handle_called_AND_unhandled_ex_THEN_handles_gracefully(mock_ec2i, mock_ssm_ops, mock_cwi):
    # Set up our mock
    mock_cwi.DestroyEniMirrorEventMetrics = cwi.DestroyEniMirrorEventMetrics
    mock_cwi.DestroyEniMirrorEventOutcome = cwi.DestroyEniMirrorEventOutcome

    mock_ssm_ops.get_ssm_param_json_value.side_effect = Exception("boom")

    # Run our test
    test_event = {
        "detail-type": constants.EVENT_DETAIL_TYPE_DESTROY_ENI_MIRROR,
        "source": constants.EVENT_SOURCE,
        "detail": {
            "cluster_name": "cluster-1",
            "vpc_id": "vpc-1",
            "subnet_id": "subnet-1",
            "eni_id": "eni-1",
        }
    }

    actual_return = DestroyEniMirrorHandler().handler(test_event, {})

    # Check our results
    expected_return = {"statusCode": 500}
    assert expected_return == actual_return

    expected_mirror_calls = []
    assert expected_mirror_calls == mock_ec2i.delete_eni_mirroring.call_args_list

    expected_delete_calls = []
    assert expected_delete_calls == mock_ssm_ops.delete_ssm_param.call_args_list

    expected_put_metrics_calls = [
        mock.call(            
            cwi.DestroyEniMirrorEventMetrics(
                "cluster-1", 
                "vpc-1",
                cwi.DestroyEniMirrorEventOutcome.FAILURE
            ),
            mock.ANY
        ),
    ]
    assert expected_put_metrics_calls == mock_cwi.put_event_metrics.call_args_list