import json
import unittest.mock as mock

from lambda_create_eni_mirror.create_eni_mirror_handler import CreateEniMirrorHandler
import aws_interactions.cloudwatch_interactions as cwi
import aws_interactions.ec2_interactions as ec2i
from aws_interactions.ssm_operations import ParamDoesNotExist
import core.constants as constants

@mock.patch("lambda_create_eni_mirror.create_eni_mirror_handler.AwsClientProvider", mock.Mock())
@mock.patch("lambda_create_eni_mirror.create_eni_mirror_handler.cwi")
@mock.patch("lambda_create_eni_mirror.create_eni_mirror_handler.ssm_ops")
@mock.patch("lambda_create_eni_mirror.create_eni_mirror_handler.ec2i")
def test_WHEN_CreateEniMirrorHandler_handle_called_THEN_sets_up_mirroring(mock_ec2i, mock_ssm_ops, mock_cwi):
    # Set up our mock
    mock_cwi.CreateEniMirrorEventMetrics = cwi.CreateEniMirrorEventMetrics
    mock_cwi.CreateEniMirrorEventOutcome = cwi.CreateEniMirrorEventOutcome

    mock_ec2i.NetworkInterface = ec2i.NetworkInterface
    mock_ec2i.mirror_eni.return_value = "session-1"

    mock_ssm_ops.ParamDoesNotExist = ParamDoesNotExist
    mock_ssm_ops.get_ssm_param_value.side_effect = ParamDoesNotExist("")
    mock_ssm_ops.get_ssm_param_json_value.return_value = "target-1"

    # Run our test
    test_event = {
        "detail-type": constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR,
        "source": constants.EVENT_SOURCE,
        "detail": {
            "cluster_name": "cluster-1",
            "vpc_id": "vpc-1",
            "subnet_id": "subnet-1",
            "eni_id": "eni-1",
            "eni_type": "eni-type-1",
            "traffic_filter_id": "filter-1",
            "vni": 1234
        }
    }

    actual_return = CreateEniMirrorHandler().handler(test_event, {})

    # Check our results
    expected_return = {"statusCode": 200}
    assert expected_return == actual_return

    expected_mirror_calls = [
        mock.call(
            ec2i.NetworkInterface("vpc-1", "subnet-1", "eni-1", "eni-type-1"),
            "target-1",
            "filter-1",
            "vpc-1",
            mock.ANY,
            virtual_network=1234
        ),
    ]
    assert expected_mirror_calls == mock_ec2i.mirror_eni.call_args_list

    expected_put_calls = [
        mock.call(
            constants.get_eni_ssm_param_name("cluster-1", "vpc-1", "subnet-1", "eni-1"), 
            json.dumps({"eniId": "eni-1", "trafficSessionId": "session-1"}),
            mock.ANY,
            description=mock.ANY,
            pattern=".*"
        ),
    ]
    assert expected_put_calls == mock_ssm_ops.put_ssm_param.call_args_list

    expected_put_metrics_calls = [
        mock.call(            
            cwi.CreateEniMirrorEventMetrics(
                "cluster-1", 
                "vpc-1",
                cwi.CreateEniMirrorEventOutcome.SUCCESS
            ),
            mock.ANY
        ),
    ]
    assert expected_put_metrics_calls == mock_cwi.put_event_metrics.call_args_list

@mock.patch("lambda_create_eni_mirror.create_eni_mirror_handler.AwsClientProvider", mock.Mock())
@mock.patch("lambda_create_eni_mirror.create_eni_mirror_handler.cwi")
@mock.patch("lambda_create_eni_mirror.create_eni_mirror_handler.ssm_ops")
@mock.patch("lambda_create_eni_mirror.create_eni_mirror_handler.ec2i")
def test_WHEN_CreateEniMirrorHandler_handle_called_AND_already_mirrored_THEN_aborts(mock_ec2i, mock_ssm_ops, mock_cwi):
    # Set up our mock
    mock_cwi.CreateEniMirrorEventMetrics = cwi.CreateEniMirrorEventMetrics
    mock_cwi.CreateEniMirrorEventOutcome = cwi.CreateEniMirrorEventOutcome

    mock_ec2i.NetworkInterface = ec2i.NetworkInterface
    mock_ec2i.mirror_eni.return_value = "session-1"

    mock_ssm_ops.get_ssm_param_value.return_value = "blah"
    mock_ssm_ops.get_ssm_param_json_value.return_value = "target-1"

    # Run our test
    test_event = {
        "detail-type": constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR,
        "source": constants.EVENT_SOURCE,
        "detail": {
            "cluster_name": "cluster-1",
            "vpc_id": "vpc-1",
            "subnet_id": "subnet-1",
            "eni_id": "eni-1",
            "eni_type": "eni-type-1",
            "traffic_filter_id": "filter-1",
            "vni": 1234
        }
    }

    actual_return = CreateEniMirrorHandler().handler(test_event, {})

    # Check our results
    expected_return = {"statusCode": 200}
    assert expected_return == actual_return

    expected_mirror_calls = []
    assert expected_mirror_calls == mock_ec2i.mirror_eni.call_args_list

    expected_put_calls = []
    assert expected_put_calls == mock_ssm_ops.put_ssm_param.call_args_list

    expected_put_metrics_calls = [
        mock.call(            
            cwi.CreateEniMirrorEventMetrics(
                "cluster-1", 
                "vpc-1",
                cwi.CreateEniMirrorEventOutcome.ABORTED_EXISTS
            ),
            mock.ANY
        ),
    ]
    assert expected_put_metrics_calls == mock_cwi.put_event_metrics.call_args_list
    
@mock.patch("lambda_create_eni_mirror.create_eni_mirror_handler.AwsClientProvider", mock.Mock())
@mock.patch("lambda_create_eni_mirror.create_eni_mirror_handler.cwi")
@mock.patch("lambda_create_eni_mirror.create_eni_mirror_handler.ssm_ops")
@mock.patch("lambda_create_eni_mirror.create_eni_mirror_handler.ec2i")
def test_WHEN_CreateEniMirrorHandler_handle_called_AND_wrong_type_THEN_aborts(mock_ec2i, mock_ssm_ops, mock_cwi):
    # Set up our mock
    mock_cwi.CreateEniMirrorEventMetrics = cwi.CreateEniMirrorEventMetrics
    mock_cwi.CreateEniMirrorEventOutcome = cwi.CreateEniMirrorEventOutcome

    mock_ec2i.NetworkInterface = ec2i.NetworkInterface
    mock_ec2i.NonMirrorableEniType = ec2i.NonMirrorableEniType
    mock_ec2i.mirror_eni.side_effect = ec2i.NonMirrorableEniType(ec2i.NetworkInterface("vpc-1", "subnet-1", "eni-1", "eni-type-1"))

    mock_ssm_ops.ParamDoesNotExist = ParamDoesNotExist
    mock_ssm_ops.get_ssm_param_value.side_effect = ParamDoesNotExist("")
    mock_ssm_ops.get_ssm_param_json_value.return_value = "target-1"

    # Run our test
    test_event = {
        "detail-type": constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR,
        "source": constants.EVENT_SOURCE,
        "detail": {
            "cluster_name": "cluster-1",
            "vpc_id": "vpc-1",
            "subnet_id": "subnet-1",
            "eni_id": "eni-1",
            "eni_type": "eni-type-1",
            "traffic_filter_id": "filter-1",
            "vni": 1234
        }
    }

    actual_return = CreateEniMirrorHandler().handler(test_event, {})

    # Check our results
    expected_return = {"statusCode": 200}
    assert expected_return == actual_return

    expected_mirror_calls = [
        mock.call(
            ec2i.NetworkInterface("vpc-1", "subnet-1", "eni-1", "eni-type-1"),
            "target-1",
            "filter-1",
            "vpc-1",
            mock.ANY,
            virtual_network=1234
        ),
    ]
    assert expected_mirror_calls == mock_ec2i.mirror_eni.call_args_list

    expected_put_calls = []
    assert expected_put_calls == mock_ssm_ops.put_ssm_param.call_args_list

    expected_put_metrics_calls = [
        mock.call(            
            cwi.CreateEniMirrorEventMetrics(
                "cluster-1", 
                "vpc-1",
                cwi.CreateEniMirrorEventOutcome.ABORTED_ENI_TYPE
            ),
            mock.ANY
        ),
    ]
    assert expected_put_metrics_calls == mock_cwi.put_event_metrics.call_args_list

@mock.patch("lambda_create_eni_mirror.create_eni_mirror_handler.AwsClientProvider", mock.Mock())
@mock.patch("lambda_create_eni_mirror.create_eni_mirror_handler.cwi")
@mock.patch("lambda_create_eni_mirror.create_eni_mirror_handler.ssm_ops")
@mock.patch("lambda_create_eni_mirror.create_eni_mirror_handler.ec2i")
def test_WHEN_CreateEniMirrorHandler_handle_called_AND_unhandled_ex_THEN_handles_gracefully(mock_ec2i, mock_ssm_ops, mock_cwi):
    # Set up our mock
    mock_cwi.CreateEniMirrorEventMetrics = cwi.CreateEniMirrorEventMetrics
    mock_cwi.CreateEniMirrorEventOutcome = cwi.CreateEniMirrorEventOutcome

    mock_ec2i.NetworkInterface = ec2i.NetworkInterface
    mock_ec2i.mirror_eni.return_value = "session-1"

    mock_ssm_ops.get_ssm_param_value.side_effect = Exception("boom")
    mock_ssm_ops.get_ssm_param_json_value.return_value = "target-1"

    # Run our test
    test_event = {
        "detail-type": constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR,
        "source": constants.EVENT_SOURCE,
        "detail": {
            "cluster_name": "cluster-1",
            "vpc_id": "vpc-1",
            "subnet_id": "subnet-1",
            "eni_id": "eni-1",
            "eni_type": "eni-type-1",
            "traffic_filter_id": "filter-1",
            "vni": 1234
        }
    }

    actual_return = CreateEniMirrorHandler().handler(test_event, {})

    # Check our results
    expected_return = {"statusCode": 500}
    assert expected_return == actual_return

    expected_mirror_calls = []
    assert expected_mirror_calls == mock_ec2i.mirror_eni.call_args_list

    expected_put_calls = []
    assert expected_put_calls == mock_ssm_ops.put_ssm_param.call_args_list

    expected_put_metrics_calls = [
        mock.call(            
            cwi.CreateEniMirrorEventMetrics(
                "cluster-1", 
                "vpc-1",
                cwi.CreateEniMirrorEventOutcome.FAILURE
            ),
            mock.ANY
        ),
    ]
    assert expected_put_metrics_calls == mock_cwi.put_event_metrics.call_args_list