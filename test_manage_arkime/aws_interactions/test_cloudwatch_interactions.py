import json
import unittest.mock as mock

import aws_interactions.cloudwatch_interactions as cwi
import constants as constants


def test_WHEN_CreateEniMirrorEventMetrics_created_AND_success_THEN_correct_metrics():
    # Run our test
    actual_value = cwi.CreateEniMirrorEventMetrics("cluster-1", "vpc-1", cwi.CreateEniMirrorEventOutcome.SUCCESS)

    # Check our results
    expected_namespace = cwi.CW_ARKIME_EVENT_NAMESPACE
    assert expected_namespace == actual_value.namespace

    expected_metric_data = [
        {
            "MetricName": cwi.CreateEniMirrorEventOutcome.SUCCESS.value,
            "Value": 1,
            "Dimensions": [
                {"Name": "ClusterName", "Value": "cluster-1"},
                {"Name": "VpcId", "Value": "vpc-1"},
                {"Name": "EventType", "Value": constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR},
            ]
        },
        {
            "MetricName": cwi.CreateEniMirrorEventOutcome.ABORTED_EXISTS.value,
            "Value": 0,
            "Dimensions": [
                {"Name": "ClusterName", "Value": "cluster-1"},
                {"Name": "VpcId", "Value": "vpc-1"},
                {"Name": "EventType", "Value": constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR},
            ]
        },
        {
            "MetricName": cwi.CreateEniMirrorEventOutcome.ABORTED_ENI_TYPE.value,
            "Value": 0,
            "Dimensions": [
                {"Name": "ClusterName", "Value": "cluster-1"},
                {"Name": "VpcId", "Value": "vpc-1"},
                {"Name": "EventType", "Value": constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR},
            ]
        },
        {
            "MetricName": cwi.CreateEniMirrorEventOutcome.FAILURE.value,
            "Value": 0,
            "Dimensions": [
                {"Name": "ClusterName", "Value": "cluster-1"},
                {"Name": "VpcId", "Value": "vpc-1"},
                {"Name": "EventType", "Value": constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR},
            ]
        },
    ]
    assert expected_metric_data == actual_value.metric_data

def test_WHEN_CreateEniMirrorEventMetrics_created_AND_aborted_exists_THEN_correct_metrics():
    # Run our test
    actual_value = cwi.CreateEniMirrorEventMetrics("cluster-1", "vpc-1", cwi.CreateEniMirrorEventOutcome.ABORTED_EXISTS)

    # Check our results
    expected_namespace = cwi.CW_ARKIME_EVENT_NAMESPACE
    assert expected_namespace == actual_value.namespace

    expected_metric_data = [
        {
            "MetricName": cwi.CreateEniMirrorEventOutcome.SUCCESS.value,
            "Value": 0,
            "Dimensions": [
                {"Name": "ClusterName", "Value": "cluster-1"},
                {"Name": "VpcId", "Value": "vpc-1"},
                {"Name": "EventType", "Value": constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR},
            ]
        },
        {
            "MetricName": cwi.CreateEniMirrorEventOutcome.ABORTED_EXISTS.value,
            "Value": 1,
            "Dimensions": [
                {"Name": "ClusterName", "Value": "cluster-1"},
                {"Name": "VpcId", "Value": "vpc-1"},
                {"Name": "EventType", "Value": constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR},
            ]
        },
        {
            "MetricName": cwi.CreateEniMirrorEventOutcome.ABORTED_ENI_TYPE.value,
            "Value": 0,
            "Dimensions": [
                {"Name": "ClusterName", "Value": "cluster-1"},
                {"Name": "VpcId", "Value": "vpc-1"},
                {"Name": "EventType", "Value": constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR},
            ]
        },
        {
            "MetricName": cwi.CreateEniMirrorEventOutcome.FAILURE.value,
            "Value": 0,
            "Dimensions": [
                {"Name": "ClusterName", "Value": "cluster-1"},
                {"Name": "VpcId", "Value": "vpc-1"},
                {"Name": "EventType", "Value": constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR},
            ]
        },
    ]
    assert expected_metric_data == actual_value.metric_data

def test_WHEN_CreateEniMirrorEventMetrics_created_AND_aborted_eni_type_THEN_correct_metrics():
    # Run our test
    actual_value = cwi.CreateEniMirrorEventMetrics("cluster-1", "vpc-1", cwi.CreateEniMirrorEventOutcome.ABORTED_ENI_TYPE)

    # Check our results
    expected_namespace = cwi.CW_ARKIME_EVENT_NAMESPACE
    assert expected_namespace == actual_value.namespace

    expected_metric_data = [
        {
            "MetricName": cwi.CreateEniMirrorEventOutcome.SUCCESS.value,
            "Value": 0,
            "Dimensions": [
                {"Name": "ClusterName", "Value": "cluster-1"},
                {"Name": "VpcId", "Value": "vpc-1"},
                {"Name": "EventType", "Value": constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR},
            ]
        },
        {
            "MetricName": cwi.CreateEniMirrorEventOutcome.ABORTED_EXISTS.value,
            "Value": 0,
            "Dimensions": [
                {"Name": "ClusterName", "Value": "cluster-1"},
                {"Name": "VpcId", "Value": "vpc-1"},
                {"Name": "EventType", "Value": constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR},
            ]
        },
        {
            "MetricName": cwi.CreateEniMirrorEventOutcome.ABORTED_ENI_TYPE.value,
            "Value": 1,
            "Dimensions": [
                {"Name": "ClusterName", "Value": "cluster-1"},
                {"Name": "VpcId", "Value": "vpc-1"},
                {"Name": "EventType", "Value": constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR},
            ]
        },
        {
            "MetricName": cwi.CreateEniMirrorEventOutcome.FAILURE.value,
            "Value": 0,
            "Dimensions": [
                {"Name": "ClusterName", "Value": "cluster-1"},
                {"Name": "VpcId", "Value": "vpc-1"},
                {"Name": "EventType", "Value": constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR},
            ]
        },
    ]
    assert expected_metric_data == actual_value.metric_data

def test_WHEN_CreateEniMirrorEventMetrics_created_AND_failure_THEN_correct_metrics():
    # Run our test
    actual_value = cwi.CreateEniMirrorEventMetrics("cluster-1", "vpc-1", cwi.CreateEniMirrorEventOutcome.FAILURE)

    # Check our results
    expected_namespace = cwi.CW_ARKIME_EVENT_NAMESPACE
    assert expected_namespace == actual_value.namespace

    expected_metric_data = [
        {
            "MetricName": cwi.CreateEniMirrorEventOutcome.SUCCESS.value,
            "Value": 0,
            "Dimensions": [
                {"Name": "ClusterName", "Value": "cluster-1"},
                {"Name": "VpcId", "Value": "vpc-1"},
                {"Name": "EventType", "Value": constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR},
            ]
        },
        {
            "MetricName": cwi.CreateEniMirrorEventOutcome.ABORTED_EXISTS.value,
            "Value": 0,
            "Dimensions": [
                {"Name": "ClusterName", "Value": "cluster-1"},
                {"Name": "VpcId", "Value": "vpc-1"},
                {"Name": "EventType", "Value": constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR},
            ]
        },
        {
            "MetricName": cwi.CreateEniMirrorEventOutcome.ABORTED_ENI_TYPE.value,
            "Value": 0,
            "Dimensions": [
                {"Name": "ClusterName", "Value": "cluster-1"},
                {"Name": "VpcId", "Value": "vpc-1"},
                {"Name": "EventType", "Value": constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR},
            ]
        },
        {
            "MetricName": cwi.CreateEniMirrorEventOutcome.FAILURE.value,
            "Value": 1,
            "Dimensions": [
                {"Name": "ClusterName", "Value": "cluster-1"},
                {"Name": "VpcId", "Value": "vpc-1"},
                {"Name": "EventType", "Value": constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR},
            ]
        },
    ]
    assert expected_metric_data == actual_value.metric_data

def test_WHEN_DestroyEniMirrorEventMetrics_created_AND_success_THEN_correct_metrics():
    # Run our test
    actual_value = cwi.DestroyEniMirrorEventMetrics("cluster-1", "vpc-1", cwi.DestroyEniMirrorEventOutcome.SUCCESS)

    # Check our results
    expected_namespace = cwi.CW_ARKIME_EVENT_NAMESPACE
    assert expected_namespace == actual_value.namespace

    expected_metric_data = [
        {
            "MetricName": cwi.DestroyEniMirrorEventOutcome.SUCCESS.value,
            "Value": 1,
            "Dimensions": [
                {"Name": "ClusterName", "Value": "cluster-1"},
                {"Name": "VpcId", "Value": "vpc-1"},
                {"Name": "EventType", "Value": constants.EVENT_DETAIL_TYPE_DESTROY_ENI_MIRROR},
            ]
        },
        {
            "MetricName": cwi.DestroyEniMirrorEventOutcome.FAILURE.value,
            "Value": 0,
            "Dimensions": [
                {"Name": "ClusterName", "Value": "cluster-1"},
                {"Name": "VpcId", "Value": "vpc-1"},
                {"Name": "EventType", "Value": constants.EVENT_DETAIL_TYPE_DESTROY_ENI_MIRROR},
            ]
        },
    ]
    assert expected_metric_data == actual_value.metric_data

def test_WHEN_DestroyEniMirrorEventMetrics_created_AND_failure_THEN_correct_metrics():
    # Run our test
    actual_value = cwi.DestroyEniMirrorEventMetrics("cluster-1", "vpc-1", cwi.DestroyEniMirrorEventOutcome.FAILURE)

    # Check our results
    expected_namespace = cwi.CW_ARKIME_EVENT_NAMESPACE
    assert expected_namespace == actual_value.namespace

    expected_metric_data = [
        {
            "MetricName": cwi.DestroyEniMirrorEventOutcome.SUCCESS.value,
            "Value": 0,
            "Dimensions": [
                {"Name": "ClusterName", "Value": "cluster-1"},
                {"Name": "VpcId", "Value": "vpc-1"},
                {"Name": "EventType", "Value": constants.EVENT_DETAIL_TYPE_DESTROY_ENI_MIRROR},
            ]
        },
        {
            "MetricName": cwi.DestroyEniMirrorEventOutcome.FAILURE.value,
            "Value": 1,
            "Dimensions": [
                {"Name": "ClusterName", "Value": "cluster-1"},
                {"Name": "VpcId", "Value": "vpc-1"},
                {"Name": "EventType", "Value": constants.EVENT_DETAIL_TYPE_DESTROY_ENI_MIRROR},
            ]
        },
    ]
    assert expected_metric_data == actual_value.metric_data


def test_WHEN_put_event_metrics_called_THEN_metrics_are_put():
    # Set up our mock
    mock_metrics = mock.Mock()
    mock_metrics.namespace = "name-1"
    mock_metrics.metric_data = [{"blah": "blah"}]

    mock_cw_client = mock.Mock()
    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_cloudwatch.return_value = mock_cw_client

    # Run our test
    cwi.put_event_metrics(mock_metrics, mock_aws_provider)

    # Check our results
    expected_put_calls = [
        mock.call(            
            Namespace=mock_metrics.namespace,
            MetricData=mock_metrics.metric_data
        )
    ]
    assert expected_put_calls == mock_cw_client.put_metric_data.call_args_list
