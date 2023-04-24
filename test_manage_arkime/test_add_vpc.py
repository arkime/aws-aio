import json
import shlex
import unittest.mock as mock

from manage_arkime.commands.add_vpc import cmd_add_vpc, _mirror_enis_in_subnet
import manage_arkime.aws_interactions.ec2_interactions as ec2i
from manage_arkime.aws_interactions.ssm_operations import ParamDoesNotExist
import manage_arkime.constants as constants
import manage_arkime.vni_provider as vnis


@mock.patch("manage_arkime.commands.add_vpc.ssm_ops")
@mock.patch("manage_arkime.commands.add_vpc.ec2i")
def test_WHEN_mirror_enis_in_subnet_called_THEN_sets_up_mirroring(mock_ec2i, mock_ssm_ops):
    # Set up our mock
    eni_1 = ec2i.NetworkInterface("eni-1", "type-1")
    eni_2 = ec2i.NetworkInterface("eni-2", "type-2")

    mock_ec2i.get_enis_of_subnet.return_value = [eni_1, eni_2]
    mock_ec2i.mirror_eni.side_effect = ["session-1", "session-2"]

    mock_ssm_ops.ParamDoesNotExist = ParamDoesNotExist
    mock_ssm_ops.get_ssm_param_value.side_effect = ParamDoesNotExist("")
    mock_ssm_ops.get_ssm_param_json_value.return_value = "target-1"

    mock_provider = mock.Mock()

    # Run our test
    _mirror_enis_in_subnet("cluster-1", "vpc-1", "subnet-1", "filter-1", 1234, mock_provider)

    # Check our results
    expected_mirror_calls = [
        mock.call(
            eni_1,
            "target-1",
            "filter-1",
            "vpc-1",
            mock.ANY,
            virtual_network=1234
        ),
        mock.call(
            eni_2,
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
        mock.call(
            constants.get_eni_ssm_param_name("cluster-1", "vpc-1", "subnet-1", "eni-2"), 
            json.dumps({"eniId": "eni-2", "trafficSessionId": "session-2"}),
            mock.ANY,
            description=mock.ANY,
            pattern=".*"
        ),

    ]
    assert expected_put_calls == mock_ssm_ops.put_ssm_param.call_args_list

@mock.patch("manage_arkime.commands.add_vpc.ssm_ops")
@mock.patch("manage_arkime.commands.add_vpc.ec2i")
def test_WHEN_mirror_enis_in_subnet_called_AND_already_mirrored_THEN_skips(mock_ec2i, mock_ssm_ops):
    # Set up our mock
    eni_1 = ec2i.NetworkInterface("eni-1", "type-1")
    eni_2 = ec2i.NetworkInterface("eni-2", "type-2")

    mock_ec2i.get_enis_of_subnet.return_value = [eni_1, eni_2]
    mock_ec2i.mirror_eni.side_effect = ["session-1", "session-2"]

    mock_ssm_ops.ParamDoesNotExist = ParamDoesNotExist
    mock_ssm_ops.get_ssm_param_value.side_effect = [
        ParamDoesNotExist(""),
        ""
    ]
    mock_ssm_ops.get_ssm_param_json_value.return_value = "target-1"

    mock_provider = mock.Mock()

    # Run our test
    _mirror_enis_in_subnet("cluster-1", "vpc-1", "subnet-1", "filter-1", 1234, mock_provider)

    # Check our results
    expected_mirror_calls = [
        mock.call(
            eni_1,
            "target-1",
            "filter-1",
            "vpc-1",
            mock.ANY,
            virtual_network=1234
        )
    ]
    assert expected_mirror_calls == mock_ec2i.mirror_eni.call_args_list


    expected_put_calls = [
        mock.call(
            constants.get_eni_ssm_param_name("cluster-1", "vpc-1", "subnet-1", "eni-1"), 
            json.dumps({"eniId": "eni-1", "trafficSessionId": "session-1"}),
            mock.ANY,
            description=mock.ANY,
            pattern=".*"
        )

    ]
    assert expected_put_calls == mock_ssm_ops.put_ssm_param.call_args_list


@mock.patch("manage_arkime.commands.add_vpc.AwsClientProvider", mock.Mock())
@mock.patch("manage_arkime.commands.add_vpc.SsmVniProvider")
@mock.patch("manage_arkime.commands.add_vpc._mirror_enis_in_subnet")
@mock.patch("manage_arkime.commands.add_vpc.ssm_ops")
@mock.patch("manage_arkime.commands.add_vpc.ec2i")
@mock.patch("manage_arkime.commands.add_vpc.CdkClient")
def test_WHEN_cmd_add_vpc_called_AND_no_user_vni_THEN_sets_up_mirroring(mock_cdk_client_cls, mock_ec2i, mock_ssm, mock_mirror, mock_vni_provider_cls):
    # Set up our mock
    mock_vni_provider = mock.Mock()
    mock_vni_provider.get_next_vni.return_value = 42
    mock_vni_provider_cls.return_value = mock_vni_provider

    subnet_ids = ["subnet-1", "subnet-2"]
    mock_ec2i.get_subnets_of_vpc.return_value = ["subnet-1", "subnet-2"]

    mock_ssm.get_ssm_param_value.return_value = "" # Doesn't matter what this is besides an exception
    mock_ssm.get_ssm_param_json_value.side_effect = ["service-1", "filter-1"]

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    # Run our test
    cmd_add_vpc("profile", "region", "cluster-1", "vpc-1", None)

    # Check our results
    expected_cdk_calls = [
        mock.call(
            [
                constants.get_vpc_mirror_setup_stack_name("cluster-1", "vpc-1")
            ],
            aws_profile="profile",
            aws_region="region",
            context={
                constants.CDK_CONTEXT_CMD_VAR: constants.CMD_ADD_VPC,
                constants.CDK_CONTEXT_PARAMS_VAR: shlex.quote(json.dumps({
                    "nameVpcMirrorStack": constants.get_vpc_mirror_setup_stack_name("cluster-1", "vpc-1"),
                    "nameVpcSsmParam": constants.get_vpc_ssm_param_name("cluster-1", "vpc-1"),
                    "idVni": str(42),
                    "idVpc": "vpc-1",
                    "idVpceService": "service-1",
                    "listSubnetIds": subnet_ids,
                    "listSubnetSsmParams": [constants.get_subnet_ssm_param_name("cluster-1", "vpc-1", subnet_id) for subnet_id in subnet_ids]
                }))
            }
        )
    ]

    print(expected_cdk_calls)
    print(mock_cdk.deploy.call_args_list)

    assert expected_cdk_calls == mock_cdk.deploy.call_args_list

    expected_mirror_calls = [
        mock.call("cluster-1", "vpc-1", "subnet-1", "filter-1", 42, mock.ANY),
        mock.call("cluster-1", "vpc-1", "subnet-2", "filter-1", 42, mock.ANY)
    ]
    assert expected_mirror_calls == mock_mirror.call_args_list

    expected_vni_calls = [mock.call(42)]
    assert expected_vni_calls == mock_vni_provider.use_next_vni.call_args_list

@mock.patch("manage_arkime.commands.add_vpc.AwsClientProvider", mock.Mock())
@mock.patch("manage_arkime.commands.add_vpc.SsmVniProvider")
@mock.patch("manage_arkime.commands.add_vpc._mirror_enis_in_subnet")
@mock.patch("manage_arkime.commands.add_vpc.CdkClient")
def test_WHEN_cmd_add_vpc_called_AND_no_available_vnis_THEN_aborts(mock_cdk_client_cls, mock_mirror, mock_vni_provider_cls):
    # Set up our mock
    mock_vni_provider = mock.Mock()
    mock_vni_provider.get_next_vni.side_effect = vnis.VniPoolExhausted()
    mock_vni_provider_cls.return_value = mock_vni_provider

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    # Run our test
    cmd_add_vpc("profile", "region", "cluster-1", "vpc-1", None)

    # Check our results
    expected_cdk_calls = []
    assert expected_cdk_calls == mock_cdk.deploy.call_args_list

    expected_mirror_calls = []
    assert expected_mirror_calls == mock_mirror.call_args_list

    expected_vni_calls = []
    assert expected_vni_calls == mock_vni_provider.use_next_vni.call_args_list

@mock.patch("manage_arkime.commands.add_vpc.AwsClientProvider", mock.Mock())
@mock.patch("manage_arkime.commands.add_vpc.SsmVniProvider")
@mock.patch("manage_arkime.commands.add_vpc._mirror_enis_in_subnet")
@mock.patch("manage_arkime.commands.add_vpc.ssm_ops")
@mock.patch("manage_arkime.commands.add_vpc.ec2i")
@mock.patch("manage_arkime.commands.add_vpc.CdkClient")
def test_WHEN_cmd_add_vpc_called_AND_is_available_user_vni_THEN_sets_up_mirroring(mock_cdk_client_cls, mock_ec2i, mock_ssm, mock_mirror, mock_vni_provider_cls):
    # Set up our mock
    mock_vni_provider = mock.Mock()
    mock_vni_provider.is_vni_available.return_value = True
    mock_vni_provider_cls.return_value = mock_vni_provider

    subnet_ids = ["subnet-1", "subnet-2"]
    mock_ec2i.get_subnets_of_vpc.return_value = ["subnet-1", "subnet-2"]

    mock_ssm.get_ssm_param_value.return_value = "" # Doesn't matter what this is besides an exception
    mock_ssm.get_ssm_param_json_value.side_effect = ["service-1", "filter-1"]

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    # Run our test
    cmd_add_vpc("profile", "region", "cluster-1", "vpc-1", 1234)

    # Check our results
    expected_cdk_calls = [
        mock.call(
            [
                constants.get_vpc_mirror_setup_stack_name("cluster-1", "vpc-1")
            ],
            aws_profile="profile",
            aws_region="region",
            context={
                constants.CDK_CONTEXT_CMD_VAR: constants.CMD_ADD_VPC,
                constants.CDK_CONTEXT_PARAMS_VAR: shlex.quote(json.dumps({
                    "nameVpcMirrorStack": constants.get_vpc_mirror_setup_stack_name("cluster-1", "vpc-1"),
                    "nameVpcSsmParam": constants.get_vpc_ssm_param_name("cluster-1", "vpc-1"),
                    "idVni": str(1234),
                    "idVpc": "vpc-1",
                    "idVpceService": "service-1",
                    "listSubnetIds": subnet_ids,
                    "listSubnetSsmParams": [constants.get_subnet_ssm_param_name("cluster-1", "vpc-1", subnet_id) for subnet_id in subnet_ids]
                }))
            }
        )
    ]

    assert expected_cdk_calls == mock_cdk.deploy.call_args_list

    expected_mirror_calls = [
        mock.call("cluster-1", "vpc-1", "subnet-1", "filter-1", 1234, mock.ANY),
        mock.call("cluster-1", "vpc-1", "subnet-2", "filter-1", 1234, mock.ANY)
    ]
    assert expected_mirror_calls == mock_mirror.call_args_list

    expected_vni_calls = [mock.call(1234)]
    assert expected_vni_calls == mock_vni_provider.register_user_vni.call_args_list

@mock.patch("manage_arkime.commands.add_vpc.AwsClientProvider", mock.Mock())
@mock.patch("manage_arkime.commands.add_vpc.SsmVniProvider")
@mock.patch("manage_arkime.commands.add_vpc._mirror_enis_in_subnet")
@mock.patch("manage_arkime.commands.add_vpc.CdkClient")
def test_WHEN_cmd_add_vpc_called_AND_is_unavailable_user_vni_THEN_aborts(mock_cdk_client_cls, mock_mirror, mock_vni_provider_cls):
    # Set up our mock
    mock_vni_provider = mock.Mock()
    mock_vni_provider.is_vni_available.return_value = False
    mock_vni_provider_cls.return_value = mock_vni_provider

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    # Run our test
    cmd_add_vpc("profile", "region", "cluster-1", "vpc-1", 1234)

    # Check our results
    expected_cdk_calls = []
    assert expected_cdk_calls == mock_cdk.deploy.call_args_list

    expected_mirror_calls = []
    assert expected_mirror_calls == mock_mirror.call_args_list

    expected_vni_calls = []
    assert expected_vni_calls == mock_vni_provider.register_user_vni.call_args_list

@mock.patch("manage_arkime.commands.add_vpc.AwsClientProvider", mock.Mock())
@mock.patch("manage_arkime.commands.add_vpc.SsmVniProvider")
@mock.patch("manage_arkime.commands.add_vpc._mirror_enis_in_subnet")
@mock.patch("manage_arkime.commands.add_vpc.CdkClient")
def test_WHEN_cmd_add_vpc_called_AND_is_outrange_user_vni_THEN_aborts(mock_cdk_client_cls, mock_mirror, mock_vni_provider_cls):
    # Set up our mock
    mock_vni_provider = mock.Mock()
    mock_vni_provider.is_vni_available.side_effect = vnis.VniOutsideRange(1234)
    mock_vni_provider_cls.return_value = mock_vni_provider

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    # Run our test
    cmd_add_vpc("profile", "region", "cluster-1", "vpc-1", 1234)

    # Check our results
    expected_cdk_calls = []
    assert expected_cdk_calls == mock_cdk.deploy.call_args_list

    expected_mirror_calls = []
    assert expected_mirror_calls == mock_mirror.call_args_list

    expected_vni_calls = []
    assert expected_vni_calls == mock_vni_provider.register_user_vni.call_args_list

@mock.patch("manage_arkime.commands.add_vpc.AwsClientProvider", mock.Mock())
@mock.patch("manage_arkime.commands.add_vpc.SsmVniProvider")
@mock.patch("manage_arkime.commands.add_vpc._mirror_enis_in_subnet")
@mock.patch("manage_arkime.commands.add_vpc.CdkClient")
def test_WHEN_cmd_add_vpc_called_AND_is_used_user_vni_THEN_aborts(mock_cdk_client_cls, mock_mirror, mock_vni_provider_cls):
    # Set up our mock
    mock_vni_provider = mock.Mock()
    mock_vni_provider.is_vni_available.side_effect = vnis.VniAlreadyUsed(1234)
    mock_vni_provider_cls.return_value = mock_vni_provider

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    # Run our test
    cmd_add_vpc("profile", "region", "cluster-1", "vpc-1", 1234)

    # Check our results
    expected_cdk_calls = []
    assert expected_cdk_calls == mock_cdk.deploy.call_args_list

    expected_mirror_calls = []
    assert expected_mirror_calls == mock_mirror.call_args_list

    expected_vni_calls = []
    assert expected_vni_calls == mock_vni_provider.register_user_vni.call_args_list

@mock.patch("manage_arkime.commands.add_vpc.AwsClientProvider", mock.Mock())
@mock.patch("manage_arkime.commands.add_vpc.SsmVniProvider")
@mock.patch("manage_arkime.commands.add_vpc._mirror_enis_in_subnet")
@mock.patch("manage_arkime.commands.add_vpc.ssm_ops")
@mock.patch("manage_arkime.commands.add_vpc.CdkClient")
def test_WHEN_cmd_add_vpc_called_AND_cluster_doesnt_exist_THEN_aborts(mock_cdk_client_cls, mock_ssm, mock_mirror, mock_vni_provider_cls):
    # Set up our mock
    mock_vni_provider = mock.Mock()
    mock_vni_provider.is_vni_available.return_value = True
    mock_vni_provider_cls.return_value = mock_vni_provider

    mock_ssm.ParamDoesNotExist = ParamDoesNotExist
    mock_ssm.get_ssm_param_value.side_effect = ParamDoesNotExist("")

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    # Run our test
    cmd_add_vpc("profile", "region", "cluster-1", "vpc-1", 1234)

    # Check our results
    expected_cdk_calls = []
    assert expected_cdk_calls == mock_cdk.deploy.call_args_list

    expected_mirror_calls = []
    assert expected_mirror_calls == mock_mirror.call_args_list

    expected_vni_calls = []
    assert expected_vni_calls == mock_vni_provider.register_user_vni.call_args_list
    assert expected_vni_calls == mock_vni_provider.use_next_vni.call_args_list

@mock.patch("manage_arkime.commands.add_vpc.AwsClientProvider", mock.Mock())
@mock.patch("manage_arkime.commands.add_vpc.SsmVniProvider")
@mock.patch("manage_arkime.commands.add_vpc._mirror_enis_in_subnet")
@mock.patch("manage_arkime.commands.add_vpc.ssm_ops")
@mock.patch("manage_arkime.commands.add_vpc.ec2i")
@mock.patch("manage_arkime.commands.add_vpc.CdkClient")
def test_WHEN_cmd_add_vpc_called_AND_vpc_doesnt_exist_THEN_skips(mock_cdk_client_cls, mock_ec2i, mock_ssm, mock_mirror, mock_vni_provider_cls):
    # Set up our mock
    mock_vni_provider = mock.Mock()
    mock_vni_provider.is_vni_available.return_value = True
    mock_vni_provider_cls.return_value = mock_vni_provider

    mock_ec2i.VpcDoesNotExist = ec2i.VpcDoesNotExist
    mock_ec2i.get_subnets_of_vpc.side_effect = ec2i.VpcDoesNotExist("vpc-1")

    mock_ssm.get_ssm_param_value.return_value = "" # Doesn't matter what this is besides an exception

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    # Run our test
    cmd_add_vpc("profile", "region", "cluster-1", "vpc-1", 1234)

    # Check our results
    expected_cdk_calls = []
    assert expected_cdk_calls == mock_cdk.deploy.call_args_list

    expected_mirror_calls = []
    assert expected_mirror_calls == mock_mirror.call_args_list

    expected_vni_calls = []
    assert expected_vni_calls == mock_vni_provider.register_user_vni.call_args_list
    assert expected_vni_calls == mock_vni_provider.use_next_vni.call_args_list