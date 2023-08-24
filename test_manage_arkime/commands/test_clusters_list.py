import unittest.mock as mock

from aws_interactions.aws_environment import AwsEnvironment
from commands.clusters_list import cmd_clusters_list
import core.constants as constants
import core.cross_account_wrangling as caw


@mock.patch("commands.clusters_list.get_cross_account_vpc_details")
@mock.patch("commands.clusters_list.ssm_ops")
@mock.patch("commands.clusters_list.AwsClientProvider")
def test_WHEN_cmd_clusters_list_called_THEN_lists_them(mock_provider_cls, mock_ssm_ops, mock_get_cross):
    # Set up our mock
    test_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")
    mock_provider = mock.Mock()
    mock_provider.get_aws_env.return_value = test_env
    mock_provider_cls.return_value = mock_provider

    mock_ssm_ops.get_ssm_param_json_value.side_effect = [
        "os-domain-1",
        "os-domain-2"
    ]

    mock_ssm_ops.get_ssm_names_by_path.side_effect = [
        ["MyCluster", "MyCluster3"]
    ]

    mock_ssm_ops.get_ssm_params_by_path.side_effect = [
        [],
        [
            {
                'Name': '/arkime/clusters/MyCluster3/vpcs/vpc-08d5c92356da0ccb4/cross-account',
                'Value': '{"clusterAccount": "XXXXXXXXXXXX", "clusterName": "MyCluster3", "roleName": "arkime_MyCluster3_vpc-08d5c92356da0ccb4", "vpcAccount": "YYYYYYYYYYYY", "vpcId": "vpc-08d5c92356da0ccb4", "vpceServiceId": "vpce-svc-0bf7f421d6596c8cb"}',
            },
            {
                'Name': '/arkime/clusters/MyCluster3/vpcs/vpc-0f08710cdbc32d58a',
                'Value': '{"busArn":"arn:aws:events:us-east-2:XXXXXXXXXXXX:event-bus/MyCluster3vpc0f08710cdbc32d58aMirrorVpcBusAC2AE73F","mirrorFilterId":"tmf-0f84cdfef3cd62b09","mirrorVni":"24","vpcId":"vpc-0f08710cdbc32d58a"}',
            },
            {
                'Name': '/arkime/clusters/MyCluster3/vpcs/vpc-0f08710cdbc32d58a/subnets/subnet-04bc404a6e4ef39e3',
                'Value': '{"mirrorTargetId":"tmt-031fd480afeb2cd7b","subnetId":"subnet-04bc404a6e4ef39e3","vpcEndpointId":"vpce-090ba993602e313e6"}',
            },
            {
                'Name': '/arkime/clusters/MyCluster3/vpcs/vpc-0f08710cdbc32d58a/subnets/subnet-04bc404a6e4ef39e3/enis/eni-02be669dc1f946dbc',
                'Value': '{"eniId": "eni-02be669dc1f946dbc", "trafficSessionId": "tms-0c987245d763cdc12"}',
            },
        ]
    ]

    mock_get_cross.side_effect = [
        [],
        [caw.CrossAccountVpcDetail("bus_arn", "filter_id", "26", "YYYYYYYYYYYY", "vpc-08d5c92356da0ccb4")]
    ]

    mock_ssm_ops.get_ssm_param_value.side_effect = [
        '{"s3": {"bucket": "bucket-name","key": "v1/archive.zip"},"version": {"aws_aio_version": "1","config_version": "1","md5_version": "1111","source_version": "v1","time_utc": "now"},"previous": "None"}',
        '{"s3": {"bucket": "bucket-name","key": "v2/archive.zip"},"version": {"aws_aio_version": "1","config_version": "2","md5_version": "2222","source_version": "v1","time_utc": "now"},"previous": "None"}',
        '{"s3": {"bucket": "bucket-name","key": "v3/archive.zip"},"version": {"aws_aio_version": "1","config_version": "3","md5_version": "3333","source_version": "v1","time_utc": "now"},"previous": "None"}',
        '{"s3": {"bucket": "bucket-name","key": "v4/archive.zip"},"version": {"aws_aio_version": "1","config_version": "4","md5_version": "4444","source_version": "v1","time_utc": "now"},"previous": "None"}',
    ]

    # Run our test
    result = cmd_clusters_list("profile", "region")

    # Check our results
    expected_get_names_calls = [
        mock.call(constants.SSM_CLUSTERS_PREFIX, mock_provider),
    ]
    assert expected_get_names_calls == mock_ssm_ops.get_ssm_names_by_path.call_args_list

    expected_get_params_path_calls = [
        mock.call(f"{constants.get_cluster_ssm_param_name('MyCluster')}/vpcs", mock_provider, recursive=True),
        mock.call(f"{constants.get_cluster_ssm_param_name('MyCluster3')}/vpcs", mock_provider, recursive=True),
    ]
    assert expected_get_params_path_calls == mock_ssm_ops.get_ssm_params_by_path.call_args_list

    expected_result = [
        {
            "cluster_name": "MyCluster",
            "opensearch_domain": "os-domain-1",
            "configuration_capture": {
                "aws_aio_version": "1",
                "config_version": "1",
                "md5_version": "1111",
                "source_version": "v1",
                "time_utc": "now"
            },
            "configuration_viewer": {
                "aws_aio_version": "1",
                "config_version": "2",
                "md5_version": "2222",
                "source_version": "v1",
                "time_utc": "now"
            },
            "monitored_vpcs": []
        },
        {
            "cluster_name": "MyCluster3", 
            "opensearch_domain": "os-domain-2",
            "configuration_capture": {
                "aws_aio_version": "1",
                "config_version": "3",
                "md5_version": "3333",
                "source_version": "v1",
                "time_utc": "now"
            },
            "configuration_viewer": {
                "aws_aio_version": "1",
                "config_version": "4",
                "md5_version": "4444",
                "source_version": "v1",
                "time_utc": "now"
            },
            "monitored_vpcs": [
                {"vpc_account": "XXXXXXXXXXXX", "vpc_id": "vpc-0f08710cdbc32d58a", "vni": "24"},
                {"vpc_account": "YYYYYYYYYYYY", "vpc_id": "vpc-08d5c92356da0ccb4", "vni": "26"}
            ]
        }
    ]
    assert expected_result == result

