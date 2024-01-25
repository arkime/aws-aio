import json
import shlex
import unittest.mock as mock

from commands.vpc_remove import cmd_vpc_remove
from aws_interactions.aws_environment import AwsEnvironment
import aws_interactions.events_interactions as events
from aws_interactions.ssm_operations import ParamDoesNotExist
import core.compatibility as compat
import core.constants as constants


@mock.patch("commands.vpc_remove.compat.confirm_aws_aio_version_compatibility", mock.Mock())
@mock.patch("commands.vpc_remove.AwsClientProvider")
@mock.patch("commands.vpc_remove.SsmVniProvider")
@mock.patch("commands.vpc_remove.ssm_ops")
@mock.patch("commands.vpc_remove.events")
@mock.patch("commands.vpc_remove.CdkClient")
def test_WHEN_cmd_vpc_remove_called_THEN_removes_mirroring(mock_cdk_client_cls, mock_events, mock_ssm,
                                                           mock_vni_provider_cls, mock_aws_provider_cls):
    # Set up our mock
    mock_vni_provider = mock.Mock()
    mock_vni_provider_cls.return_value = mock_vni_provider

    aws_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")
    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_aws_env.return_value = aws_env
    mock_aws_provider_cls.return_value = mock_aws_provider

    mock_events.DestroyEniMirrorEvent = events.DestroyEniMirrorEvent

    mock_ssm.ParamDoesNotExist = ParamDoesNotExist
    mock_ssm.get_ssm_param_value.side_effect = ParamDoesNotExist("")
    mock_ssm.get_ssm_param_json_value.side_effect = ["service-1", "bus-1", 1337]
    mock_ssm.get_ssm_params_by_path.return_value = [
        {"Name": "param-1", "Value": json.dumps({"subnetId": "subnet-1"})},
        {"Name": "param-2", "Value": json.dumps({"subnetId": "subnet-2"})},
    ]
    mock_ssm.get_ssm_names_by_path.side_effect = [["eni-1"], ["eni-2"]]

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    # Run our test
    cmd_vpc_remove("profile", "region", "cluster-1", "vpc-1")

    # Check our results
    expected_cdk_calls = [
        mock.call(
            [
                constants.get_vpc_mirror_setup_stack_name("cluster-1", "vpc-1")
            ],
            context={
                constants.CDK_CONTEXT_CMD_VAR: constants.CMD_vpc_remove,
                constants.CDK_CONTEXT_PARAMS_VAR: shlex.quote(json.dumps({
                    "nameCluster": "cluster-1",
                    "nameVpcMirrorStack": constants.get_vpc_mirror_setup_stack_name("cluster-1", "vpc-1"),
                    "nameVpcSsmParam": constants.get_vpc_ssm_param_name("cluster-1", "vpc-1"),
                    "idVni": str(constants.VNI_DEFAULT),
                    "idVpc": "vpc-1",
                    "idVpceService": "service-1",
                    "listSubnetIds": ["subnet-1", "subnet-2"],
                    "listSubnetSsmParams": [constants.get_subnet_ssm_param_name("cluster-1", "vpc-1", subnet_id) for subnet_id in ["subnet-1", "subnet-2"]],
                    "vpcCidrs": ["0.0.0.0/0"]
                }))
            }
        )
    ]
    assert expected_cdk_calls == mock_cdk.destroy.call_args_list

    expected_cdk_client_create_calls = [
        mock.call(aws_env)
    ]
    assert expected_cdk_client_create_calls == mock_cdk_client_cls.call_args_list

    expected_put_event_calls = [
        mock.call([events.DestroyEniMirrorEvent("cluster-1", "vpc-1", "subnet-1", "eni-1")], "bus-1", mock.ANY),
        mock.call([events.DestroyEniMirrorEvent("cluster-1", "vpc-1", "subnet-2", "eni-2")], "bus-1", mock.ANY),
    ]
    assert expected_put_event_calls == mock_events.put_events.call_args_list

    expected_vni_calls = [mock.call(1337, "vpc-1")]
    assert expected_vni_calls == mock_vni_provider.relinquish_vni.call_args_list

@mock.patch("commands.vpc_remove.AwsClientProvider", mock.Mock())
@mock.patch("commands.vpc_remove.compat.confirm_aws_aio_version_compatibility")
@mock.patch("commands.vpc_remove.SsmVniProvider")
@mock.patch("commands.vpc_remove.ssm_ops")
@mock.patch("commands.vpc_remove.events")
@mock.patch("commands.vpc_remove.CdkClient")
def test_WHEN_cmd_vpc_remove_called_AND_cluster_doesnt_exist_THEN_aborts(mock_cdk_client_cls, mock_events, mock_ssm,
                                                                         mock_vni_provider_cls, mock_confirm_ver):
    # Set up our mock
    mock_vni_provider = mock.Mock()
    mock_vni_provider_cls.return_value = mock_vni_provider

    mock_ssm.ParamDoesNotExist = ParamDoesNotExist
    mock_ssm.get_ssm_param_value.side_effect = ParamDoesNotExist("")

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    mock_confirm_ver.side_effect = compat.UnableToRetrieveClusterVersion("cluster-1", 1)

    # Run our test
    cmd_vpc_remove("profile", "region", "cluster-1", "vpc-1")

    # Check our results
    expected_cdk_calls = []
    assert expected_cdk_calls == mock_cdk.destroy.call_args_list

    expected_put_event_calls = []
    assert expected_put_event_calls == mock_events.put_events.call_args_list

    expected_vni_calls = []
    assert expected_vni_calls == mock_vni_provider.relinquish_vni.call_args_list

@mock.patch("commands.vpc_remove.AwsClientProvider", mock.Mock())
@mock.patch("commands.vpc_remove.compat.confirm_aws_aio_version_compatibility")
@mock.patch("commands.vpc_remove.SsmVniProvider")
@mock.patch("commands.vpc_remove.ssm_ops")
@mock.patch("commands.vpc_remove.events")
@mock.patch("commands.vpc_remove.CdkClient")
def test_WHEN_cmd_vpc_remove_called_AND_cli_version_THEN_aborts(mock_cdk_client_cls, mock_events, mock_ssm,
                                                                         mock_vni_provider_cls, mock_confirm_ver):
    # Set up our mock
    mock_vni_provider = mock.Mock()
    mock_vni_provider_cls.return_value = mock_vni_provider

    mock_ssm.ParamDoesNotExist = ParamDoesNotExist
    mock_ssm.get_ssm_param_value.side_effect = ParamDoesNotExist("")

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    mock_confirm_ver.side_effect = compat.CliClusterVersionMismatch(2, 1)

    # Run our test
    cmd_vpc_remove("profile", "region", "cluster-1", "vpc-1")

    # Check our results
    expected_cdk_calls = []
    assert expected_cdk_calls == mock_cdk.destroy.call_args_list

    expected_put_event_calls = []
    assert expected_put_event_calls == mock_events.put_events.call_args_list

    expected_vni_calls = []
    assert expected_vni_calls == mock_vni_provider.relinquish_vni.call_args_list

@mock.patch("commands.vpc_remove.compat.confirm_aws_aio_version_compatibility", mock.Mock())
@mock.patch("commands.vpc_remove.AwsClientProvider")
@mock.patch("commands.vpc_remove.SsmVniProvider")
@mock.patch("commands.vpc_remove.ssm_ops")
@mock.patch("commands.vpc_remove.events")
@mock.patch("commands.vpc_remove.CdkClient")
def test_WHEN_cmd_vpc_remove_called_AND_cross_account_THEN_uses_correct_clients(mock_cdk_client_cls, mock_events, mock_ssm,
                                                           mock_vni_provider_cls, mock_aws_provider_cls):
    # Set up our mock
    mock_vni_provider = mock.Mock()
    mock_vni_provider_cls.return_value = mock_vni_provider

    vpc_aws_env = AwsEnvironment("YYYYYYYYYYYY", "region", "profile")
    mock_vpc_aws_provider = mock.Mock()
    mock_vpc_aws_provider.get_aws_env.return_value = vpc_aws_env
    mock_cluster_aws_provider = mock.Mock()
    mock_aws_provider_cls.side_effect = [mock_vpc_aws_provider, mock_cluster_aws_provider]

    mock_events.DestroyEniMirrorEvent = events.DestroyEniMirrorEvent

    mock_ssm.ParamDoesNotExist = ParamDoesNotExist
    mock_ssm.get_ssm_param_value.return_value = json.dumps({
            "clusterAccount": "XXXXXXXXXXXX",
            "clusterName": "my_cluster",
            "roleName": "role_name",
            "vpcAccount": "YYYYYYYYYYYY",
            "vpcId": "vpc",
            "vpceServiceId": "vpce_id",
    })
    mock_ssm.get_ssm_param_json_value.side_effect = ["service-1", "bus-1", 1337]
    mock_ssm.get_ssm_params_by_path.return_value = [
        {"Name": "param-1", "Value": json.dumps({"subnetId": "subnet-1"})},
        {"Name": "param-2", "Value": json.dumps({"subnetId": "subnet-2"})},
    ]
    mock_ssm.get_ssm_names_by_path.side_effect = [["eni-1"], ["eni-2"]]

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    # Run our test
    cmd_vpc_remove("profile", "region", "cluster-1", "vpc-1")

    # Check our results
    expected_cdk_client_create_calls = [
        mock.call(vpc_aws_env)
    ]
    assert expected_cdk_client_create_calls == mock_cdk_client_cls.call_args_list

    expected_ssm_get_param_val_calls = [
        mock.call(mock.ANY, mock_vpc_aws_provider), # Cross-account link check
    ]
    assert expected_ssm_get_param_val_calls == mock_ssm.get_ssm_param_value.call_args_list

    expected_ssm_get_param_json_calls = [
        mock.call(mock.ANY, mock.ANY, mock_cluster_aws_provider), # Get VPCE ID from Cluster Param
        mock.call(mock.ANY, mock.ANY, mock_vpc_aws_provider), # Get Event Bus from VPC Param
        mock.call(mock.ANY, mock.ANY, mock_vpc_aws_provider), # Get VNI from VPC Param
    ]
    assert expected_ssm_get_param_json_calls == mock_ssm.get_ssm_param_json_value.call_args_list

    expected_get_ssm_params_by_path_calls = [
        mock.call(mock.ANY, mock_vpc_aws_provider), # Get Subnet IDs from VPC Path
    ]
    assert expected_get_ssm_params_by_path_calls == mock_ssm.get_ssm_params_by_path.call_args_list

    expected_get_ssm_names_by_path_calls = [
        mock.call(mock.ANY, mock_vpc_aws_provider), # Get ENIs from Subnet Path
        mock.call(mock.ANY, mock_vpc_aws_provider), # Get ENIs from Subnet Path
    ]
    assert expected_get_ssm_names_by_path_calls == mock_ssm.get_ssm_names_by_path.call_args_list

    expected_put_event_calls = [
        mock.call(mock.ANY, mock.ANY, mock_vpc_aws_provider),
        mock.call(mock.ANY, mock.ANY, mock_vpc_aws_provider),
    ]
    assert expected_put_event_calls == mock_events.put_events.call_args_list

    expected_vni_provider_create_calls = [
        mock.call("cluster-1", mock_cluster_aws_provider)
    ]
    assert expected_vni_provider_create_calls == mock_vni_provider_cls.call_args_list

@mock.patch("commands.vpc_remove.AwsClientProvider")
@mock.patch("commands.vpc_remove.SsmVniProvider")
@mock.patch("commands.vpc_remove.ssm_ops")
@mock.patch("commands.vpc_remove.events")
@mock.patch("commands.vpc_remove.CdkClient")
def test_WHEN_cmd_vpc_remove_called_AND_wrong_account_THEN_aborts(mock_cdk_client_cls, mock_events, mock_ssm,
                                                           mock_vni_provider_cls, mock_aws_provider_cls):
    # Set up our mock
    mock_vni_provider = mock.Mock()
    mock_vni_provider_cls.return_value = mock_vni_provider

    aws_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")
    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_aws_env.return_value = aws_env
    mock_aws_provider_cls.return_value = mock_aws_provider

    mock_events.DestroyEniMirrorEvent = events.DestroyEniMirrorEvent

    mock_ssm.ParamDoesNotExist = ParamDoesNotExist
    mock_ssm.get_ssm_param_value.return_value = json.dumps({
            "clusterAccount": "XXXXXXXXXXXX",
            "clusterName": "my_cluster",
            "roleName": "role_name",
            "vpcAccount": "YYYYYYYYYYYY",
            "vpcId": "vpc",
            "vpceServiceId": "vpce_id",
    })
    mock_ssm.get_ssm_param_json_value.side_effect = ["service-1", "bus-1", 1337]
    mock_ssm.get_ssm_params_by_path.return_value = [
        {"Name": "param-1", "Value": json.dumps({"subnetId": "subnet-1"})},
        {"Name": "param-2", "Value": json.dumps({"subnetId": "subnet-2"})},
    ]
    mock_ssm.get_ssm_names_by_path.side_effect = [["eni-1"], ["eni-2"]]

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    # Run our test
    cmd_vpc_remove("profile", "region", "cluster-1", "vpc-1")

    # Check our results
    expected_cdk_calls = []
    assert expected_cdk_calls == mock_cdk.destroy.call_args_list

    expected_cdk_client_create_calls = [
        mock.call(aws_env)
    ]
    assert expected_cdk_client_create_calls == mock_cdk_client_cls.call_args_list

    expected_put_event_calls = []
    assert expected_put_event_calls == mock_events.put_events.call_args_list

    expected_vni_calls = []
    assert expected_vni_calls == mock_vni_provider.relinquish_vni.call_args_list