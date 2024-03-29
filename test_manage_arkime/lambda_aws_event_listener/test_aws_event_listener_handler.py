import json
import unittest.mock as mock

from lambda_aws_event_listener.aws_event_listener_handler import AwsEventListenerHandler
import aws_interactions.ec2_interactions as ec2i
import aws_interactions.events_interactions as events
import core.constants as constants

@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.os")
def test_WHEN_AwsEventListenerHandler_handle_called_AND_ec2_running_THEN_invokes_correct_subhandler(mock_os):
    # Set up our mock
    mock_os.environ = {
        "EVENT_BUS_ARN": "bus-1",
        "CLUSTER_NAME": "cluster-1",
        "VPC_ID": "vpc-1",
        "TRAFFIC_FILTER_ID": "filter-1",
        "MIRROR_VNI": "1234",
    }

    mock_subhandler = mock.Mock()
    mock_subhandler.return_value = {"statusCode": 200}
    test_handler = AwsEventListenerHandler()
    test_handler._handle_ec2_running = mock_subhandler

    # Run our test
    actual_return = test_handler.handler(TEST_EVENT_EC2_RUNNING, {})

    # Check our results
    expected_return = {"statusCode": 200}
    assert expected_return == actual_return

    expected_subhandler_calls = [
        mock.call(TEST_EVENT_EC2_RUNNING, "bus-1", "cluster-1", "vpc-1", "filter-1", 1234),
    ]
    assert expected_subhandler_calls == mock_subhandler.call_args_list

@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.os")
def test_WHEN_AwsEventListenerHandler_handle_called_AND_ec2_shutting_down_THEN_invokes_correct_subhandler(mock_os):
    # Set up our mock
    mock_os.environ = {
        "EVENT_BUS_ARN": "bus-1",
        "CLUSTER_NAME": "cluster-1",
        "VPC_ID": "vpc-1",
        "TRAFFIC_FILTER_ID": "filter-1",
        "MIRROR_VNI": "1234",
    }

    mock_subhandler = mock.Mock()
    mock_subhandler.return_value = {"statusCode": 200}
    test_handler = AwsEventListenerHandler()
    test_handler._handle_ec2_shutting_down = mock_subhandler

    # Run our test
    actual_return = test_handler.handler(TEST_EVENT_EC2_SHUTTING_DOWN, {})

    # Check our results
    expected_return = {"statusCode": 200}
    assert expected_return == actual_return

    expected_subhandler_calls = [
        mock.call(TEST_EVENT_EC2_SHUTTING_DOWN, "bus-1", "cluster-1", "vpc-1"),
    ]
    assert expected_subhandler_calls == mock_subhandler.call_args_list

@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.os")
def test_WHEN_AwsEventListenerHandler_handle_called_AND_fargate_running_THEN_invokes_correct_subhandler(mock_os):
    # Set up our mock
    mock_os.environ = {
        "EVENT_BUS_ARN": "bus-1",
        "CLUSTER_NAME": "cluster-1",
        "VPC_ID": "vpc-1",
        "TRAFFIC_FILTER_ID": "filter-1",
        "MIRROR_VNI": "1234",
    }

    mock_subhandler = mock.Mock()
    mock_subhandler.return_value = {"statusCode": 200}
    test_handler = AwsEventListenerHandler()
    test_handler._handle_fargate_running = mock_subhandler

    # Run our test
    actual_return = test_handler.handler(TEST_EVENT_FARGATE_RUNNING, {})

    # Check our results
    expected_return = {"statusCode": 200}
    assert expected_return == actual_return

    expected_subhandler_calls = [
        mock.call(TEST_EVENT_FARGATE_RUNNING, "bus-1", "cluster-1", "vpc-1", "filter-1", 1234),
    ]
    assert expected_subhandler_calls == mock_subhandler.call_args_list

@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.os")
def test_WHEN_AwsEventListenerHandler_handle_called_AND_fargate_stopped_THEN_invokes_correct_subhandler(mock_os):
    # Set up our mock
    mock_os.environ = {
        "EVENT_BUS_ARN": "bus-1",
        "CLUSTER_NAME": "cluster-1",
        "VPC_ID": "vpc-1",
        "TRAFFIC_FILTER_ID": "filter-1",
        "MIRROR_VNI": "1234",
    }

    mock_subhandler = mock.Mock()
    mock_subhandler.return_value = {"statusCode": 200}
    test_handler = AwsEventListenerHandler()
    test_handler._handle_fargate_stopped = mock_subhandler

    # Run our test
    actual_return = test_handler.handler(TEST_EVENT_FARGATE_STOPPED, {})

    # Check our results
    expected_return = {"statusCode": 200}
    assert expected_return == actual_return

    expected_subhandler_calls = [
        mock.call(TEST_EVENT_FARGATE_STOPPED, "bus-1", "cluster-1", "vpc-1"),
    ]
    assert expected_subhandler_calls == mock_subhandler.call_args_list

@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.os")
def test_WHEN_AwsEventListenerHandler_handle_called_AND_unknown_THEN_invokes_correct_subhandler(mock_os):
    # Set up our mock
    mock_os.environ = {
        "EVENT_BUS_ARN": "bus-1",
        "CLUSTER_NAME": "cluster-1",
        "VPC_ID": "vpc-1",
        "TRAFFIC_FILTER_ID": "filter-1",
        "MIRROR_VNI": "1234",
    }

    mock_subhandler = mock.Mock()
    mock_subhandler.return_value = {"statusCode": 200}
    test_handler = AwsEventListenerHandler()
    test_handler._handle_unknown = mock_subhandler

    # Run our test
    actual_return = test_handler.handler(TEST_EVENT_UNKNOWN, {})

    # Check our results
    expected_return = {"statusCode": 200}
    assert expected_return == actual_return

    expected_subhandler_calls = [
        mock.call(TEST_EVENT_UNKNOWN),
    ]
    assert expected_subhandler_calls == mock_subhandler.call_args_list

@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.os")
def test_WHEN_AwsEventListenerHandler_handle_called_AND_wacky_error_THEN_handles_gracefully(mock_os):
    # Set up our mock
    mock_os.environ = {}

    test_handler = AwsEventListenerHandler()

    # Run our test
    actual_return = test_handler.handler(TEST_EVENT_UNKNOWN, {})

    # Check our results
    expected_return = {"statusCode": 500}
    assert expected_return == actual_return

@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.AwsClientProvider", mock.Mock())
@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.ec2i")
@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.events")
def test_WHEN_handle_ec2_running_called_THEN_as_expected(mock_events, mock_ec2i):
    # Set up our mock
    mock_ec2i.get_enis_of_instance.return_value = [
        ec2i.NetworkInterface("vpc-1", "subnet-1", "eni-1", "type-1"),
        ec2i.NetworkInterface("vpc-1", "subnet-1", "eni-2", "type-1"),
    ]

    mock_events.CreateEniMirrorEvent = events.CreateEniMirrorEvent

    # Run our test
    actual_return = AwsEventListenerHandler()._handle_ec2_running(
        TEST_EVENT_EC2_RUNNING,
        "bus-1",
        "cluster-1",
        "vpc-1",
        "filter-1",
        1234
    )

    # Check our results
    expected_return = {"statusCode": 200}
    assert expected_return == actual_return

    expected_get_enis_calls = [
        mock.call(TEST_EVENT_EC2_RUNNING["detail"]["instance-id"], mock.ANY),
    ]
    assert expected_get_enis_calls == mock_ec2i.get_enis_of_instance.call_args_list

    expected_put_events_calls = [
        mock.call(
            [
                events.CreateEniMirrorEvent("cluster-1", "vpc-1", "subnet-1", "eni-1", "type-1", "filter-1", 1234),
                events.CreateEniMirrorEvent("cluster-1", "vpc-1", "subnet-1", "eni-2", "type-1", "filter-1", 1234),
            ],
            "bus-1",
            mock.ANY
        ),
    ]
    assert expected_put_events_calls == mock_events.put_events.call_args_list

@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.AwsClientProvider", mock.Mock())
@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.ec2i")
@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.events")
def test_WHEN_handle_ec2_running_called_AND_wrong_vpc_THEN_handles_gracefully(mock_events, mock_ec2i):
    # Set up our mock
    mock_ec2i.get_enis_of_instance.return_value = [
        ec2i.NetworkInterface("vpc-2", "subnet-1", "eni-1", "type-1")
    ]

    mock_events.CreateEniMirrorEvent = events.CreateEniMirrorEvent

    # Run our test
    actual_return = AwsEventListenerHandler()._handle_ec2_running(
        TEST_EVENT_EC2_RUNNING,
        "bus-1",
        "cluster-1",
        "vpc-1",
        "filter-1",
        1234
    )

    # Check our results
    expected_return = {"statusCode": 200}
    assert expected_return == actual_return

    expected_get_enis_calls = [
        mock.call(TEST_EVENT_EC2_RUNNING["detail"]["instance-id"], mock.ANY),
    ]
    assert expected_get_enis_calls == mock_ec2i.get_enis_of_instance.call_args_list

    expected_put_events_calls = []
    assert expected_put_events_calls == mock_events.put_events.call_args_list

@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.AwsClientProvider", mock.Mock())
@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.ec2i")
@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.events")
def test_WHEN_handle_ec2_shutting_down_called_THEN_as_expected(mock_events, mock_ec2i):
    # Set up our mock
    mock_ec2i.get_enis_of_instance.return_value = [
        ec2i.NetworkInterface("vpc-1", "subnet-1", "eni-1", "type-1"),
        ec2i.NetworkInterface("vpc-1", "subnet-1", "eni-2", "type-1"),
    ]

    mock_events.DestroyEniMirrorEvent = events.CreateEniMirrorEvent

    # Run our test
    actual_return = AwsEventListenerHandler()._handle_ec2_shutting_down(
        TEST_EVENT_EC2_RUNNING,
        "bus-1",
        "cluster-1",
        "vpc-1"
    )

    # Check our results
    expected_return = {"statusCode": 200}
    assert expected_return == actual_return

    expected_get_enis_calls = [
        mock.call(TEST_EVENT_EC2_RUNNING["detail"]["instance-id"], mock.ANY),
    ]
    assert expected_get_enis_calls == mock_ec2i.get_enis_of_instance.call_args_list

    expected_put_events_calls = [
        mock.call(
            [
                events.DestroyEniMirrorEvent("cluster-1", "vpc-1", "subnet-1", "eni-1"),
                events.DestroyEniMirrorEvent("cluster-1", "vpc-1", "subnet-1", "eni-2"),
            ],
            "bus-1",
            mock.ANY
        ),
    ]
    assert expected_put_events_calls == mock_events.put_events.call_args_list

@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.AwsClientProvider", mock.Mock())
@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.ec2i")
@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.events")
def test_WHEN_handle_ec2_shutting_down_called_THEN_as_expected(mock_events, mock_ec2i):
    # Set up our mock
    mock_ec2i.get_enis_of_instance.return_value = [
        ec2i.NetworkInterface("vpc-1", "subnet-1", "eni-1", "type-1"),
        ec2i.NetworkInterface("vpc-1", "subnet-1", "eni-2", "type-1"),
    ]

    mock_events.DestroyEniMirrorEvent = events.DestroyEniMirrorEvent

    # Run our test
    actual_return = AwsEventListenerHandler()._handle_ec2_shutting_down(
        TEST_EVENT_EC2_SHUTTING_DOWN,
        "bus-1",
        "cluster-1",
        "vpc-1"
    )

    # Check our results
    expected_return = {"statusCode": 200}
    assert expected_return == actual_return

    expected_get_enis_calls = [
        mock.call(TEST_EVENT_EC2_SHUTTING_DOWN["detail"]["instance-id"], mock.ANY),
    ]
    assert expected_get_enis_calls == mock_ec2i.get_enis_of_instance.call_args_list

    expected_put_events_calls = [
        mock.call(
            [
                events.DestroyEniMirrorEvent("cluster-1", "vpc-1", "subnet-1", "eni-1"),
                events.DestroyEniMirrorEvent("cluster-1", "vpc-1", "subnet-1", "eni-2"),
            ],
            "bus-1",
            mock.ANY
        ),
    ]
    assert expected_put_events_calls == mock_events.put_events.call_args_list

@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.AwsClientProvider", mock.Mock())
@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.ec2i")
@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.events")
def test_WHEN_handle_ec2_shutting_down_called_AND_wrong_vpc_THEN_handles_gracefully(mock_events, mock_ec2i):
    # Set up our mock
    mock_ec2i.get_enis_of_instance.return_value = [
        ec2i.NetworkInterface("vpc-2", "subnet-1", "eni-1", "type-1"),
    ]

    mock_events.DestroyEniMirrorEvent = events.DestroyEniMirrorEvent

    # Run our test
    actual_return = AwsEventListenerHandler()._handle_ec2_shutting_down(
        TEST_EVENT_EC2_SHUTTING_DOWN,
        "bus-1",
        "cluster-1",
        "vpc-1"
    )

    # Check our results
    expected_return = {"statusCode": 200}
    assert expected_return == actual_return

    expected_get_enis_calls = [
        mock.call(TEST_EVENT_EC2_SHUTTING_DOWN["detail"]["instance-id"], mock.ANY),
    ]
    assert expected_get_enis_calls == mock_ec2i.get_enis_of_instance.call_args_list

    expected_put_events_calls = []
    assert expected_put_events_calls == mock_events.put_events.call_args_list

@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.AwsClientProvider", mock.Mock())
@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.events")
def test_WHEN_handle_fargate_running_called_THEN_as_expected(mock_events):
    # Set up our mock
    mock_events.CreateEniMirrorEvent = events.CreateEniMirrorEvent

    # Run our test
    actual_return = AwsEventListenerHandler()._handle_fargate_running(
        TEST_EVENT_FARGATE_SIMPLIFIED,
        "bus-1",
        "cluster-1",
        "vpc-1",
        "filter-1",
        1234
    )

    # Check our results
    expected_return = {"statusCode": 200}
    assert expected_return == actual_return

    expected_put_events_calls = [
        mock.call(
            [
                events.CreateEniMirrorEvent("cluster-1", "vpc-1", "subnet-1", "eni-1", "interface", "filter-1", 1234),
                events.CreateEniMirrorEvent("cluster-1", "vpc-1", "subnet-1", "eni-2", "interface", "filter-1", 1234),
            ],
            "bus-1",
            mock.ANY
        ),
    ]
    assert expected_put_events_calls == mock_events.put_events.call_args_list

@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.AwsClientProvider", mock.Mock())
@mock.patch("lambda_aws_event_listener.aws_event_listener_handler.events")
def test_WHEN_handle_fargate_stopped_called_THEN_as_expected(mock_events):
    # Set up our mock
    mock_events.DestroyEniMirrorEvent = events.DestroyEniMirrorEvent

    # Run our test
    actual_return = AwsEventListenerHandler()._handle_fargate_stopped(
        TEST_EVENT_FARGATE_SIMPLIFIED,
        "bus-1",
        "cluster-1",
        "vpc-1"
    )

    # Check our results
    expected_return = {"statusCode": 200}
    assert expected_return == actual_return

    expected_put_events_calls = [
        mock.call(
            [
                events.DestroyEniMirrorEvent("cluster-1", "vpc-1", "subnet-1", "eni-1"),
                events.DestroyEniMirrorEvent("cluster-1", "vpc-1", "subnet-1", "eni-2"),
            ],
            "bus-1",
            mock.ANY
        ),
    ]
    assert expected_put_events_calls == mock_events.put_events.call_args_list


# =================================
# Test Events
# =================================

TEST_EVENT_UNKNOWN = {
    "version": "0",
    "id": "12345678-1234-1234-1234-111122223333",
    "detail-type": "Chime VoiceConnector Streaming Status",
    "source": "aws.chime",
    "account": "111122223333",
    "time": "yyyy-mm-ddThh:mm:ssZ",
    "region": "us-east-1",
    "resources": [],
    "detail": {
        "callId": "1112-2222-4333",
        "direction": "Outbound",
        "fromNumber": "+12065550100",
        "inviteHeaders": {
            "from": "\"John\" <sip:+12065550100@10.24.34.0>;tag=abcdefg",
            "to": "<sip:+13605550199@abcdef1ghij2klmno3pqr4.voiceconnector.chime.aws:5060>",
            "call-id": "1112-2222-4333",
            "cseq": "101 INVITE",
            "contact": "<sip:user@10.24.34.0:6090>;",
            "content-type": "application/sdp",
            "content-length": "246"
        },
        "isCaller": False,
        "mediaType": "audio/L16",
        "sdp": {
            "mediaIndex": 0,
            "mediaLabel": "1"
        },
        "siprecMetadata": "<&xml version=\"1.0\" encoding=\"UTF-8\"&>;\r\n<recording xmlns='urn:ietf:params:xml:ns:recording:1'>",
        "startFragmentNumber": "1234567899444",
        "startTime": "yyyy-mm-ddThh:mm:ssZ",
        "streamArn": "arn:aws:kinesisvideo:us-east-1:123456:stream/ChimeVoiceConnector-abcdef1ghij2klmno3pqr4-111aaa-22bb-33cc-44dd-111222/111122223333",
        "toNumber": "+13605550199",
        "transactionId": "12345678-1234-1234",
        "voiceConnectorId": "abcdef1ghij2klmno3pqr4",
        "streamingStatus": "STARTED",
        "version": "0"
    }
}

TEST_EVENT_FARGATE_SIMPLIFIED = {
    "detail": {
        "attachments": [
            {
                "type": "eni",
                "status": "ATTACHED",
                "details": [
                    {
                        "name": "subnetId",
                        "value": "subnet-1"
                    },
                    {
                        "name": "networkInterfaceId",
                        "value": "eni-1"
                    },
                    {
                        "name": "macAddress",
                        "value": "blah"
                    }
                ]
            },
            {
                "type": "eni",
                "status": "ATTACHED",
                "details": [
                    {
                        "name": "subnetId",
                        "value": "subnet-1"
                    },
                    {
                        "name": "networkInterfaceId",
                        "value": "eni-2"
                    },
                    {
                        "name": "macAddress",
                        "value": "blah"
                    }
                ]
            }
        ],
    }
}


TEST_EVENT_FARGATE_RUNNING = {
        "version": "0",
        "id": "1925f534-3191-33f1-bbd9-108405eadf3d",
        "detail-type": "ECS Task State Change",
        "source": "aws.ecs",
        "account": "XXXXXXXXXXXX",
        "time": "2023-05-02T14:19:34Z",
        "region": "us-east-2",
        "resources": [
            "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:task/DemoTrafficGen01-ClusterEB0386A7-sCRgDrfn5BP9/c50e321c974248dbaf4ae2cfa1662986"
        ],
        "detail": {
            "attachments": [
                {
                    "id": "17a62b05-62f5-4c9b-99f6-56f4b0e13813",
                    "type": "eni",
                    "status": "ATTACHED",
                    "details": [
                        {
                            "name": "subnetId",
                            "value": "subnet-0aeeeea40ba9b0406"
                        },
                        {
                            "name": "networkInterfaceId",
                            "value": "eni-067c2d19a5fe6ecf3"
                        },
                        {
                            "name": "macAddress",
                            "value": "02:75:1e:d0:70:59"
                        },
                        {
                            "name": "privateDnsName",
                            "value": "ip-10-0-215-105.us-east-2.compute.internal"
                        },
                        {
                            "name": "privateIPv4Address",
                            "value": "10.0.215.105"
                        }
                    ]
                }
            ],
            "attributes": [
                {
                    "name": "ecs.cpu-architecture",
                    "value": "x86_64"
                }
            ],
            "availabilityZone": "us-east-2a",
            "clusterArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:cluster/DemoTrafficGen01-ClusterEB0386A7-sCRgDrfn5BP9",
            "connectivity": "CONNECTED",
            "connectivityAt": "2023-05-02T14:19:19.928Z",
            "containers": [
                {
                    "containerArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:container/DemoTrafficGen01-ClusterEB0386A7-sCRgDrfn5BP9/c50e321c974248dbaf4ae2cfa1662986/faced4af-762e-4b2f-97a6-f4e4816aceaa",
                    "lastStatus": "RUNNING",
                    "name": "FargateContainer",
                    "image": "XXXXXXXXXXXX.dkr.ecr.us-east-2.amazonaws.com/cdk-hnb659fds-container-assets-XXXXXXXXXXXX-us-east-2:4fccb469d9b434f1e2ef0fca061c015f1fafdd35ed4cbe1783c419c4905da49a",
                    "imageDigest": "sha256:4c8a9049915f437fcf5e8ef339e4109140cb92039dc0d3a78460623532c7c0cb",
                    "runtimeId": "c50e321c974248dbaf4ae2cfa1662986-766747396",
                    "taskArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:task/DemoTrafficGen01-ClusterEB0386A7-sCRgDrfn5BP9/c50e321c974248dbaf4ae2cfa1662986",
                    "networkInterfaces": [
                        {
                            "attachmentId": "17a62b05-62f5-4c9b-99f6-56f4b0e13813",
                            "privateIpv4Address": "10.0.215.105"
                        }
                    ],
                    "cpu": "0",
                    "memory": "512",
                    "managedAgents": [
                        {
                            "name": "ExecuteCommandAgent",
                            "status": "PENDING"
                        }
                    ]
                }
            ],
            "cpu": "256",
            "createdAt": "2023-05-02T14:19:14.98Z",
            "desiredStatus": "RUNNING",
            "enableExecuteCommand": True,
            "ephemeralStorage": {
                "sizeInGiB": 20
            },
            "group": "service:DemoTrafficGen01-ServiceD69D759B-EfyMIBhdCKVk",
            "launchType": "FARGATE",
            "lastStatus": "RUNNING",
            "memory": "512",
            "overrides": {
                "containerOverrides": [
                    {
                        "name": "FargateContainer"
                    }
                ]
            },
            "platformVersion": "1.4.0",
            "pullStartedAt": "2023-05-02T14:19:27.907Z",
            "pullStoppedAt": "2023-05-02T14:19:32.427Z",
            "startedAt": "2023-05-02T14:19:34.52Z",
            "startedBy": "ecs-svc/8646900195280463695",
            "taskArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:task/DemoTrafficGen01-ClusterEB0386A7-sCRgDrfn5BP9/c50e321c974248dbaf4ae2cfa1662986",
            "taskDefinitionArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:task-definition/DemoTrafficGen01TaskDef59B414B2:10",
            "updatedAt": "2023-05-02T14:19:34.52Z",
            "version": 3
        }
    }

TEST_EVENT_FARGATE_STOPPED = {
    "version": "0",
    "id": "47cc72d7-e8dd-320c-cba3-a8d73d1f8d0d",
    "detail-type": "ECS Task State Change",
    "source": "aws.ecs",
    "account": "XXXXXXXXXXXX",
    "time": "2023-05-02T15:29:11Z",
    "region": "us-east-2",
    "resources": [
        "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:task/DemoTrafficGen01-ClusterEB0386A7-sCRgDrfn5BP9/c50e321c974248dbaf4ae2cfa1662986"
    ],
    "detail": {
        "attachments": [
            {
                "id": "17a62b05-62f5-4c9b-99f6-56f4b0e13813",
                "type": "eni",
                "status": "DELETED",
                "details": [
                    {
                        "name": "subnetId",
                        "value": "subnet-0aeeeea40ba9b0406"
                    },
                    {
                        "name": "networkInterfaceId",
                        "value": "eni-067c2d19a5fe6ecf3"
                    },
                    {
                        "name": "macAddress",
                        "value": "02:75:1e:d0:70:59"
                    },
                    {
                        "name": "privateDnsName",
                        "value": "ip-10-0-215-105.us-east-2.compute.internal"
                    },
                    {
                        "name": "privateIPv4Address",
                        "value": "10.0.215.105"
                    }
                ]
            }
        ],
        "attributes": [
            {
                "name": "ecs.cpu-architecture",
                "value": "x86_64"
            }
        ],
        "availabilityZone": "us-east-2a",
        "clusterArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:cluster/DemoTrafficGen01-ClusterEB0386A7-sCRgDrfn5BP9",
        "connectivity": "CONNECTED",
        "connectivityAt": "2023-05-02T14:19:19.928Z",
        "containers": [
            {
                "containerArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:container/DemoTrafficGen01-ClusterEB0386A7-sCRgDrfn5BP9/c50e321c974248dbaf4ae2cfa1662986/faced4af-762e-4b2f-97a6-f4e4816aceaa",
                "exitCode": 137,
                "lastStatus": "STOPPED",
                "name": "FargateContainer",
                "image": "XXXXXXXXXXXX.dkr.ecr.us-east-2.amazonaws.com/cdk-hnb659fds-container-assets-XXXXXXXXXXXX-us-east-2:4fccb469d9b434f1e2ef0fca061c015f1fafdd35ed4cbe1783c419c4905da49a",
                "imageDigest": "sha256:4c8a9049915f437fcf5e8ef339e4109140cb92039dc0d3a78460623532c7c0cb",
                "runtimeId": "c50e321c974248dbaf4ae2cfa1662986-766747396",
                "taskArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:task/DemoTrafficGen01-ClusterEB0386A7-sCRgDrfn5BP9/c50e321c974248dbaf4ae2cfa1662986",
                "networkInterfaces": [
                    {
                        "attachmentId": "17a62b05-62f5-4c9b-99f6-56f4b0e13813",
                        "privateIpv4Address": "10.0.215.105"
                    }
                ],
                "cpu": "0",
                "memory": "512",
                "managedAgents": [
                    {
                        "name": "ExecuteCommandAgent",
                        "status": "STOPPED"
                    }
                ]
            }
        ],
        "cpu": "256",
        "createdAt": "2023-05-02T14:19:14.98Z",
        "desiredStatus": "STOPPED",
        "enableExecuteCommand": True,
        "ephemeralStorage": {
            "sizeInGiB": 20
        },
        "executionStoppedAt": "2023-05-02T15:28:48.391Z",
        "group": "service:DemoTrafficGen01-ServiceD69D759B-EfyMIBhdCKVk",
        "launchType": "FARGATE",
        "lastStatus": "STOPPED",
        "memory": "512",
        "overrides": {
            "containerOverrides": [
                {
                    "name": "FargateContainer"
                }
            ]
        },
        "platformVersion": "1.4.0",
        "pullStartedAt": "2023-05-02T14:19:27.907Z",
        "pullStoppedAt": "2023-05-02T14:19:32.427Z",
        "startedAt": "2023-05-02T14:19:34.52Z",
        "startedBy": "ecs-svc/8646900195280463695",
        "stoppingAt": "2023-05-02T15:28:04.974Z",
        "stoppedAt": "2023-05-02T15:29:11.177Z",
        "stoppedReason": "Scaling activity initiated by (deployment ecs-svc/8646900195280463695)",
        "stopCode": "ServiceSchedulerInitiated",
        "taskArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:task/DemoTrafficGen01-ClusterEB0386A7-sCRgDrfn5BP9/c50e321c974248dbaf4ae2cfa1662986",
        "taskDefinitionArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:task-definition/DemoTrafficGen01TaskDef59B414B2:10",
        "updatedAt": "2023-05-02T15:29:11.177Z",
        "version": 6
    }
}

TEST_EVENT_ECS_RUNNING = {
    "version": "0",
    "id": "2c1f6fff-4d45-93c6-1448-839865057404",
    "detail-type": "ECS Task State Change",
    "source": "aws.ecs",
    "account": "XXXXXXXXXXXX",
    "time": "2023-05-03T15:18:04Z",
    "region": "us-east-2",
    "resources": [
        "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:task/DemoTrafficGen01-EcsCluster97242B84-u8PnqOAmk1tO/5f9900fd646345e9ab339c0e66e305a0"
    ],
    "detail": {
        "attachments": [],
        "attributes": [
            {
                "name": "ecs.cpu-architecture",
                "value": "x86_64"
            }
        ],
        "availabilityZone": "us-east-2a",
        "clusterArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:cluster/DemoTrafficGen01-EcsCluster97242B84-u8PnqOAmk1tO",
        "connectivity": "CONNECTED",
        "connectivityAt": "2023-05-03T15:18:01.844Z",
        "containerInstanceArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:container-instance/DemoTrafficGen01-EcsCluster97242B84-u8PnqOAmk1tO/c2df6e33804b4e12aab6ec6496fdef5d",
        "containers": [
            {
                "containerArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:container/DemoTrafficGen01-EcsCluster97242B84-u8PnqOAmk1tO/5f9900fd646345e9ab339c0e66e305a0/e5be832e-643b-45a1-be93-b73313d8e0f5",
                "lastStatus": "RUNNING",
                "name": "EcsContainer",
                "image": "XXXXXXXXXXXX.dkr.ecr.us-east-2.amazonaws.com/cdk-hnb659fds-container-assets-XXXXXXXXXXXX-us-east-2:4fccb469d9b434f1e2ef0fca061c015f1fafdd35ed4cbe1783c419c4905da49a",
                "imageDigest": "sha256:4c8a9049915f437fcf5e8ef339e4109140cb92039dc0d3a78460623532c7c0cb",
                "runtimeId": "3e549d9bf699aeb93c13aa0d95b9f4498010d57c1cbd2785a3caccffac675c41",
                "taskArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:task/DemoTrafficGen01-EcsCluster97242B84-u8PnqOAmk1tO/5f9900fd646345e9ab339c0e66e305a0",
                "networkInterfaces": [],
                "cpu": "1536",
                "memory": "768",
                "managedAgents": [
                    {
                        "name": "ExecuteCommandAgent",
                        "status": "PENDING"
                    }
                ]
            }
        ],
        "cpu": "1536",
        "createdAt": "2023-05-03T15:18:01.844Z",
        "desiredStatus": "RUNNING",
        "enableExecuteCommand": True,
        "group": "service:DemoTrafficGen01-EcsService81FC6EF6-1MxpQy4jk934",
        "launchType": "EC2",
        "lastStatus": "RUNNING",
        "memory": "768",
        "overrides": {
            "containerOverrides": [
                {
                    "name": "EcsContainer"
                }
            ]
        },
        "pullStartedAt": "2023-05-03T15:18:02.807Z",
        "pullStoppedAt": "2023-05-03T15:18:02.93Z",
        "startedAt": "2023-05-03T15:18:04.11Z",
        "startedBy": "ecs-svc/9909299324976484585",
        "taskArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:task/DemoTrafficGen01-EcsCluster97242B84-u8PnqOAmk1tO/5f9900fd646345e9ab339c0e66e305a0",
        "taskDefinitionArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:task-definition/DemoTrafficGen01EcsTaskDef7C0694E4:1",
        "updatedAt": "2023-05-03T15:18:04.11Z",
        "version": 2
    }
}

TEST_EVENT_ECS_STOPPED = {
    "version": "0",
    "id": "10b56661-1a84-1b7f-d86c-3ccc32eccc78",
    "detail-type": "ECS Task State Change",
    "source": "aws.ecs",
    "account": "XXXXXXXXXXXX",
    "time": "2023-05-03T15:28:41Z",
    "region": "us-east-2",
    "resources": [
        "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:task/DemoTrafficGen01-EcsCluster97242B84-u8PnqOAmk1tO/5f9900fd646345e9ab339c0e66e305a0"
    ],
    "detail": {
        "attachments": [],
        "attributes": [
            {
                "name": "ecs.cpu-architecture",
                "value": "x86_64"
            }
        ],
        "availabilityZone": "us-east-2a",
        "clusterArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:cluster/DemoTrafficGen01-EcsCluster97242B84-u8PnqOAmk1tO",
        "connectivity": "CONNECTED",
        "connectivityAt": "2023-05-03T15:18:01.844Z",
        "containerInstanceArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:container-instance/DemoTrafficGen01-EcsCluster97242B84-u8PnqOAmk1tO/c2df6e33804b4e12aab6ec6496fdef5d",
        "containers": [
            {
                "containerArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:container/DemoTrafficGen01-EcsCluster97242B84-u8PnqOAmk1tO/5f9900fd646345e9ab339c0e66e305a0/e5be832e-643b-45a1-be93-b73313d8e0f5",
                "exitCode": 137,
                "lastStatus": "STOPPED",
                "name": "EcsContainer",
                "image": "XXXXXXXXXXXX.dkr.ecr.us-east-2.amazonaws.com/cdk-hnb659fds-container-assets-XXXXXXXXXXXX-us-east-2:4fccb469d9b434f1e2ef0fca061c015f1fafdd35ed4cbe1783c419c4905da49a",
                "imageDigest": "sha256:4c8a9049915f437fcf5e8ef339e4109140cb92039dc0d3a78460623532c7c0cb",
                "runtimeId": "3e549d9bf699aeb93c13aa0d95b9f4498010d57c1cbd2785a3caccffac675c41",
                "taskArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:task/DemoTrafficGen01-EcsCluster97242B84-u8PnqOAmk1tO/5f9900fd646345e9ab339c0e66e305a0",
                "networkInterfaces": [],
                "cpu": "1536",
                "memory": "768",
                "managedAgents": [
                    {
                        "name": "ExecuteCommandAgent",
                        "status": "STOPPED",
                        "reason": "Received Container Stopped event"
                    }
                ]
            }
        ],
        "cpu": "1536",
        "createdAt": "2023-05-03T15:18:01.844Z",
        "desiredStatus": "STOPPED",
        "enableExecuteCommand": True,
        "executionStoppedAt": "2023-05-03T15:28:41.023Z",
        "group": "service:DemoTrafficGen01-EcsService81FC6EF6-1MxpQy4jk934",
        "launchType": "EC2",
        "lastStatus": "STOPPED",
        "memory": "768",
        "overrides": {
            "containerOverrides": [
                {
                    "name": "EcsContainer"
                }
            ]
        },
        "pullStartedAt": "2023-05-03T15:18:02.807Z",
        "pullStoppedAt": "2023-05-03T15:18:02.93Z",
        "startedAt": "2023-05-03T15:18:04.11Z",
        "startedBy": "ecs-svc/9909299324976484585",
        "stoppingAt": "2023-05-03T15:28:09.697Z",
        "stoppedAt": "2023-05-03T15:28:41.041Z",
        "stoppedReason": "Scaling activity initiated by (deployment ecs-svc/9909299324976484585)",
        "stopCode": "ServiceSchedulerInitiated",
        "taskArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:task/DemoTrafficGen01-EcsCluster97242B84-u8PnqOAmk1tO/5f9900fd646345e9ab339c0e66e305a0",
        "taskDefinitionArn": "arn:aws:ecs:us-east-2:XXXXXXXXXXXX:task-definition/DemoTrafficGen01EcsTaskDef7C0694E4:1",
        "updatedAt": "2023-05-03T15:28:41.041Z",
        "version": 4
    }
}

TEST_EVENT_EC2_RUNNING = {
    "version": "0",
    "id": "59444e21-1551-617e-42f7-4ada553d3463",
    "detail-type": "EC2 Instance State-change Notification",
    "source": "aws.ec2",
    "account": "XXXXXXXXXXXX",
    "time": "2023-05-03T15:14:39Z",
    "region": "us-east-2",
    "resources": [
        "arn:aws:ec2:us-east-2:XXXXXXXXXXXX:instance/i-0336e8c207d9eb69a"
    ],
    "detail": {
        "instance-id": "i-0336e8c207d9eb69a",
        "state": "running"
    }
}

TEST_EVENT_EC2_SHUTTING_DOWN = {
    "version": "0",
    "id": "84b3f070-eb70-a8b3-bbfe-6e874f0d3acb",
    "detail-type": "EC2 Instance State-change Notification",
    "source": "aws.ec2",
    "account": "XXXXXXXXXXXX",
    "time": "2023-05-03T15:20:34Z",
    "region": "us-east-2",
    "resources": [
        "arn:aws:ec2:us-east-2:XXXXXXXXXXXX:instance/i-0d917354353e9f7e8"
    ],
    "detail": {
        "instance-id": "i-0d917354353e9f7e8",
        "state": "shutting-down"
    }
}