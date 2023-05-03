import pytest
import unittest.mock as mock

from botocore.exceptions import ClientError

import aws_interactions.ec2_interactions as ec2i

def test_WHEN_get_subnets_of_vpc_called_THEN_returns_them():
    # Set up our mock
    mock_ec2_client = mock.Mock()
    mock_ec2_client.describe_subnets.side_effect = [
        {
            "Subnets": [{"SubnetId": "subnet-1"}, {"SubnetId": "subnet-2"}],
            "NextToken": "next-1",
        },
        {
            "Subnets": [{"SubnetId": "subnet-3"}, {"SubnetId": "subnet-4"}],
        }
    ]

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_ec2.return_value = mock_ec2_client

    # Run our test
    result = ec2i.get_subnets_of_vpc("my-vpc", mock_aws_provider)

    # Check our results
    expected_describe_calls = [
        mock.call(Filters=[{"Name": "vpc-id", "Values": ["my-vpc"]}]),
        mock.call(Filters=[{"Name": "vpc-id", "Values": ["my-vpc"]}], NextToken="next-1"),
    ]
    assert expected_describe_calls == mock_ec2_client.describe_subnets.call_args_list

    expected_result = ["subnet-1", "subnet-2", "subnet-3", "subnet-4"]
    assert expected_result == result

def test_WHEN_get_subnets_of_vpc_called_AND_doesnt_exist_THEN_raises():
    # Set up our mock
    mock_ec2_client = mock.Mock()
    mock_ec2_client.describe_subnets.side_effect = [
        {
            "Subnets": []
        }
    ]

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_ec2.return_value = mock_ec2_client

    # Run our test
    with pytest.raises(ec2i.VpcDoesNotExist):
        result = ec2i.get_subnets_of_vpc("my-vpc", mock_aws_provider)

def test_WHEN_get_enis_of_instance_called_THEN_returns_them():
    # Set up our mock
    mock_ec2_client = mock.Mock()
    mock_ec2_client.describe_instances.return_value = {
        'Reservations': [{
            'Instances': [{
                'NetworkInterfaces': [
                    {
                        'NetworkInterfaceId': 'eni-1',
                        'SubnetId': 'subnet-1',
                        'VpcId': 'vpc-1',
                        'InterfaceType': 'type-1'
                    },
                    {
                        'NetworkInterfaceId': 'eni-2',
                        'SubnetId': 'subnet-1',
                        'VpcId': 'vpc-1',
                        'InterfaceType': 'type-2'
                    }
                ]
            }],
        }]
    }

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_ec2.return_value = mock_ec2_client

    # Run our test
    result = ec2i.get_enis_of_instance("i-1", mock_aws_provider)

    # Check our results
    expected_describe_calls = [
        mock.call(InstanceIds=["i-1"]),
    ]
    assert expected_describe_calls == mock_ec2_client.describe_instances.call_args_list

    expected_result = [
        ec2i.NetworkInterface("vpc-1", "subnet-1", "eni-1", "type-1"),
        ec2i.NetworkInterface("vpc-1", "subnet-1", "eni-2", "type-2"),
    ]
    assert expected_result == result

def test_WHEN_get_enis_of_subnet_called_THEN_returns_them():
    # Set up our mock
    mock_ec2_client = mock.Mock()
    mock_ec2_client.describe_network_interfaces.side_effect = [
        {
            "NetworkInterfaces": [
                {"NetworkInterfaceId": "eni-1", "InterfaceType": "type-1", "VpcId": "vpc-1", "SubnetId": "subnet-1"},
                {"NetworkInterfaceId": "eni-2", "InterfaceType": "type-2", "VpcId": "vpc-1", "SubnetId": "subnet-1"},
            ],
            "NextToken": "next-1",
        },
        {
            "NetworkInterfaces": [
                {"NetworkInterfaceId": "eni-3", "InterfaceType": "type-3", "VpcId": "vpc-1", "SubnetId": "subnet-1"},
                {"NetworkInterfaceId": "eni-4", "InterfaceType": "type-4", "VpcId": "vpc-1", "SubnetId": "subnet-1"},
            ],
        }
    ]

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_ec2.return_value = mock_ec2_client

    # Run our test
    result = ec2i.get_enis_of_subnet("subnet-1", mock_aws_provider)

    # Check our results
    expected_describe_calls = [
        mock.call(Filters=[{"Name": "subnet-id", "Values": ["subnet-1"]}]),
        mock.call(Filters=[{"Name": "subnet-id", "Values": ["subnet-1"]}], NextToken="next-1"),
    ]
    assert expected_describe_calls == mock_ec2_client.describe_network_interfaces.call_args_list

    expected_result = [
        ec2i.NetworkInterface("vpc-1", "subnet-1", "eni-1", "type-1"),
        ec2i.NetworkInterface("vpc-1", "subnet-1", "eni-2", "type-2"),
        ec2i.NetworkInterface("vpc-1", "subnet-1", "eni-3", "type-3"),
        ec2i.NetworkInterface("vpc-1", "subnet-1", "eni-4", "type-4"),
    ]
    assert expected_result == result

def test_WHEN_get_enis_of_subnet_called_AND_no_enis_THEN_empty_list():
    # Set up our mock
    mock_ec2_client = mock.Mock()
    mock_ec2_client.describe_network_interfaces.side_effect = [
        {
            "NetworkInterfaces": []
        }
    ]

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_ec2.return_value = mock_ec2_client

    # Run our test
    result = ec2i.get_enis_of_subnet("subnet-1", mock_aws_provider)

    # Check our results
    assert [] == result


def test_WHEN_mirror_eni_called_THEN_sets_up_session():
    # Set up our mock
    mock_ec2_client = mock.Mock()
    mock_ec2_client.create_traffic_mirror_session.return_value = {
        "TrafficMirrorSession": {
            "TrafficMirrorSessionId": "session-1"
        }
    }

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_ec2.return_value = mock_ec2_client

    # Run our test
    test_eni = ec2i.NetworkInterface("vpc-1", "subnet-1", "eni-1", "type-1")
    result = ec2i.mirror_eni(test_eni, "target-1", "filter-1", "vpc-1", mock_aws_provider, virtual_network=1234)

    # Check our results
    expected_create_calls = [
        mock.call(
            NetworkInterfaceId="eni-1",
            TrafficMirrorTargetId="target-1",
            TrafficMirrorFilterId="filter-1",
            SessionNumber=1,
            VirtualNetworkId=1234,
            TagSpecifications=[
                {
                    "ResourceType": "traffic-mirror-session",
                    "Tags": [
                        {
                            "Key": "Name",
                            "Value": "vpc-1-eni-1"
                        },
                    ]
                },
            ],
        )
    ]
    assert expected_create_calls == mock_ec2_client.create_traffic_mirror_session.call_args_list

    expected_result = "session-1"
    assert expected_result == result

def test_WHEN_mirror_eni_called_AND_excluded_type_THEN_raises():
    # Set up our mock
    mock_ec2_client = mock.Mock()
    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_ec2.return_value = mock_ec2_client

    # Run our test
    test_eni = ec2i.NetworkInterface("vpc-1", "subnet-1", "eni-1", ec2i.NON_MIRRORABLE_ENI_TYPES[0])
    with pytest.raises(ec2i.NonMirrorableEniType):
        ec2i.mirror_eni(test_eni, "target-1", "filter-1", "vpc-1", mock_aws_provider, virtual_network=1234)

    # Check our results
    expected_create_calls = []
    assert expected_create_calls == mock_ec2_client.create_traffic_mirror_session.call_args_list


def test_WHEN_remove_eni_mirroring_called_THEN_removes_it():
    # Set up our mock
    mock_ec2_client = mock.Mock()
    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_ec2.return_value = mock_ec2_client

    # Run our test
    ec2i.delete_eni_mirroring("session-1", mock_aws_provider)

    # Check our results
    expected_delete_calls = [
        mock.call(TrafficMirrorSessionId="session-1")
    ]
    assert expected_delete_calls == mock_ec2_client.delete_traffic_mirror_session.call_args_list


def test_WHEN_remove_eni_mirroring_called_AND_doesnt_exist_THEN_raises():
    # Set up our mock
    mock_ec2_client = mock.Mock()
    mock_ec2_client.delete_traffic_mirror_session.side_effect = [
        ClientError(error_response={"Error": {"Code": "InvalidTrafficMirrorSessionId.NotFound"}}, operation_name="")
    ]

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_ec2.return_value = mock_ec2_client

    # Run our test
    with pytest.raises(ec2i.MirrorDoesntExist):
        ec2i.delete_eni_mirroring("session-1", mock_aws_provider)