import json
import shlex
import unittest.mock as mock

from manage_arkime.commands.remove_vpc import cmd_remove_vpc, _remove_mirroring_for_eni
import manage_arkime.aws_interactions.ec2_interactions as ec2i
from manage_arkime.aws_interactions.ssm_operations import ParamDoesNotExist
import manage_arkime.constants as constants


@mock.patch("manage_arkime.commands.remove_vpc.ssm_ops")
@mock.patch("manage_arkime.commands.remove_vpc.ec2i")
def test_WHEN_remove_mirroring_for_eni_called_THEN_removes_it(mock_ec2i, mock_ssm_ops):
    # Set up our mock
    mock_ssm_ops.get_ssm_param_json_value.return_value = "session-1"

    mock_provider = mock.Mock()

    # Run our test
    _remove_mirroring_for_eni("cluster-1", "vpc-1", "subnet-1", "eni-1", mock_provider)

    # Check our results
    expected_delete_calls = [
        mock.call("session-1", mock.ANY)
    ]
    assert expected_delete_calls == mock_ec2i.delete_eni_mirroring.call_args_list

    expected_delete_ssm_calls = [
        mock.call(
            constants.get_eni_ssm_param_name("cluster-1", "vpc-1", "subnet-1", "eni-1"), 
            mock.ANY
        )
    ]
    assert expected_delete_ssm_calls == mock_ssm_ops.delete_ssm_param.call_args_list

@mock.patch("manage_arkime.commands.remove_vpc.ssm_ops")
@mock.patch("manage_arkime.commands.remove_vpc.ec2i")
def test_WHEN_remove_mirroring_for_eni_called_AND_session_doesnt_exist_THEN_handles_gracefully(mock_ec2i, mock_ssm_ops):
    # Set up our mock
    mock_ssm_ops.get_ssm_param_json_value.return_value = "session-1"

    mock_ec2i.MirrorDoesntExist = ec2i.MirrorDoesntExist
    mock_ec2i.delete_eni_mirroring.side_effect = ec2i.MirrorDoesntExist("session-1")

    mock_provider = mock.Mock()

    # Run our test
    _remove_mirroring_for_eni("cluster-1", "vpc-1", "subnet-1", "eni-1", mock_provider)

    # Check our results
    expected_delete_calls = [
        mock.call("session-1", mock.ANY)
    ]
    assert expected_delete_calls == mock_ec2i.delete_eni_mirroring.call_args_list

    expected_delete_ssm_calls = [
        mock.call(
            constants.get_eni_ssm_param_name("cluster-1", "vpc-1", "subnet-1", "eni-1"), 
            mock.ANY
        )
    ]
    assert expected_delete_ssm_calls == mock_ssm_ops.delete_ssm_param.call_args_list

@mock.patch("manage_arkime.commands.remove_vpc.AwsClientProvider", mock.Mock())
@mock.patch("manage_arkime.commands.remove_vpc._remove_mirroring_for_eni")
@mock.patch("manage_arkime.commands.remove_vpc.ssm_ops")
@mock.patch("manage_arkime.commands.remove_vpc.ec2i")
@mock.patch("manage_arkime.commands.remove_vpc.CdkClient")
def test_WHEN_cmd_remove_vpc_called_THEN_sets_up_mirroring(mock_cdk_client_cls, mock_ec2i, mock_ssm, mock_remove):
    # Set up our mock
    mock_ssm.get_ssm_param_json_value.return_value = "service-1"
    mock_ssm.get_ssm_params_by_path.return_value = [
        {"Name": "param-1", "Value": json.dumps({"subnetId": "subnet-1"})},
        {"Name": "param-2", "Value": json.dumps({"subnetId": "subnet-2"})},
    ]
    mock_ssm.get_ssm_names_by_path.side_effect = [["eni-1"], ["eni-2"]]

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    # Run our test
    cmd_remove_vpc("profile", "region", "cluster-1", "vpc-1")

    # Check our results
    expected_cdk_calls = [
        mock.call(
            [
                constants.get_vpc_mirror_setup_stack_name("cluster-1", "vpc-1")
            ],
            aws_profile="profile",
            aws_region="region",
            context={
                constants.CDK_CONTEXT_CMD_VAR: constants.CMD_REMOVE_VPC,
                constants.CDK_CONTEXT_PARAMS_VAR: shlex.quote(json.dumps({
                    "nameVpcMirrorStack": constants.get_vpc_mirror_setup_stack_name("cluster-1", "vpc-1"),
                    "nameVpcSsmParam": constants.get_vpc_ssm_param_name("cluster-1", "vpc-1"),
                    "idVni": str(constants.VNI_DEFAULT),
                    "idVpc": "vpc-1",
                    "idVpceService": "service-1",
                    "listSubnetIds": ["subnet-1", "subnet-2"],
                    "listSubnetSsmParams": [constants.get_subnet_ssm_param_name("cluster-1", "vpc-1", subnet_id) for subnet_id in ["subnet-1", "subnet-2"]]
                }))
            }
        )
    ]
    assert expected_cdk_calls == mock_cdk.destroy.call_args_list

    expected_remove_calls = [
        mock.call("cluster-1", "vpc-1", "subnet-1", "eni-1", mock.ANY),
        mock.call("cluster-1", "vpc-1", "subnet-2", "eni-2", mock.ANY)
    ]
    assert expected_remove_calls == mock_remove.call_args_list

@mock.patch("manage_arkime.commands.remove_vpc.AwsClientProvider", mock.Mock())
@mock.patch("manage_arkime.commands.remove_vpc._remove_mirroring_for_eni")
@mock.patch("manage_arkime.commands.remove_vpc.ssm_ops")
@mock.patch("manage_arkime.commands.remove_vpc.ec2i")
@mock.patch("manage_arkime.commands.remove_vpc.CdkClient")
def test_WHEN_cmd_remove_vpc_called_AND_cluster_doesnt_exist_THEN_aborts(mock_cdk_client_cls, mock_ec2i, mock_ssm, mock_remove):
    # Set up our mock
    mock_ssm.ParamDoesNotExist = ParamDoesNotExist
    mock_ssm.get_ssm_param_json_value.side_effect = ParamDoesNotExist("param-1")

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    # Run our test
    cmd_remove_vpc("profile", "region", "cluster-1", "vpc-1")

    # Check our results
    expected_cdk_calls = []
    assert expected_cdk_calls == mock_cdk.destroy.call_args_list

    expected_remove_calls = []
    assert expected_remove_calls == mock_remove.call_args_list