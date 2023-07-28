import unittest.mock as mock

from commands.clusters_list import cmd_clusters_list
import core.constants as constants

@mock.patch("commands.clusters_list.AwsClientProvider", mock.Mock())
@mock.patch("commands.clusters_list.ssm_ops")
def test_WHEN_cmd_clusters_list_called_THEN_lists_them(mock_ssm_ops):
    # Set up our mock
    mock_ssm_ops.get_ssm_param_json_value.side_effect = [
        "vni-1", "vni-2",
        "os-domain-1",
        "vni-3",
        "os-domain-2"
    ]

    mock_ssm_ops.get_ssm_names_by_path.side_effect = [
        ["cluster-1", "cluster-2"],
        ["vpc-1", "vpc-2"],
        ["vpc-3"],
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
        mock.call(constants.SSM_CLUSTERS_PREFIX, mock.ANY),
        mock.call(f"{constants.get_cluster_ssm_param_name('cluster-1')}/vpcs", mock.ANY),
        mock.call(f"{constants.get_cluster_ssm_param_name('cluster-2')}/vpcs", mock.ANY),
    ]
    assert expected_get_names_calls == mock_ssm_ops.get_ssm_names_by_path.call_args_list

    expected_result = [
        {
            "cluster_name": "cluster-1",
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
            "monitored_vpcs": [
                {"vpc_id": "vpc-1", "vni": "vni-1"},
                {"vpc_id": "vpc-2", "vni": "vni-2"}
            ]
        },
        {
            "cluster_name": "cluster-2", 
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
                {"vpc_id": "vpc-3", "vni": "vni-3"}
            ]
        }
    ]
    assert expected_result == result

