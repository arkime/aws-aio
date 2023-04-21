import unittest.mock as mock

from manage_arkime.commands.list_clusters import cmd_list_clusters
import manage_arkime.constants as constants

@mock.patch("manage_arkime.commands.list_clusters.AwsClientProvider", mock.Mock())
@mock.patch("manage_arkime.commands.list_clusters.ssm_ops")
def test_WHEN_cmd_list_clusters_called_THEN_lists_them(mock_ssm_ops):
    # Set up our mock
    mock_ssm_ops.get_ssm_param_json_value.side_effect = ["vni-1", "vni-2", "vni-3"]

    mock_ssm_ops.get_ssm_names_by_path.side_effect = [
        ["cluster-1", "cluster-2"],
        ["vpc-1", "vpc-2"],
        ["vpc-3"],
    ]

    # Run our test
    result = cmd_list_clusters("profile", "region")

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
            "monitored_vpcs": [
                {"vpc_id": "vpc-1", "vni": "vni-1"},
                {"vpc_id": "vpc-2", "vni": "vni-2"}
            ]
        },
        {
            "cluster_name": "cluster-2", 
            "monitored_vpcs": [
                {"vpc_id": "vpc-3", "vni": "vni-3"}
            ]
        }
    ]
    assert expected_result == result

