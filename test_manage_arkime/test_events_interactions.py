import json
import unittest.mock as mock

import aws_interactions.events_interactions as events


def test_WHEN_put_events_called_THEN_events_are_put():
    # Set up our mock
    mock_events_client = mock.Mock()

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_events.return_value = mock_events_client

    # Run our test
    create_eni_event = events.CreateEniMirrorEvent("cluster-1", "vpc-1", "subnet-1", "eni-1", "eni-type-1", "filter-1", 42)
    destroy_eni_event = events.DestroyEniMirrorEvent("cluster-1", "vpc-1", "subnet-1", "eni-2")

    test_events = [
        create_eni_event,
        destroy_eni_event
    ]
    events.put_events(test_events, "bus-1", mock_aws_provider)

    # Check our results
    expected_put_calls = [
        mock.call(Entries=[
            {
                'Source': create_eni_event.source,
                'DetailType': create_eni_event.detail_type,
                'Detail': json.dumps(create_eni_event.details),
                'EventBusName': "bus-1"
            },
            {
                'Source': destroy_eni_event.source,
                'DetailType': destroy_eni_event.detail_type,
                'Detail': json.dumps(destroy_eni_event.details),
                'EventBusName': "bus-1"
            },
        ])
    ]
    assert expected_put_calls == mock_events_client.put_events.call_args_list
