import json
import shlex
import unittest.mock as mock

from commands.vpc_add import cmd_vpc_add, _mirror_enis_in_subnet
from aws_interactions.aws_environment import AwsEnvironment
import aws_interactions.ec2_interactions as ec2i
import aws_interactions.events_interactions as events
from aws_interactions.ssm_operations import ParamDoesNotExist
import core.constants as constants
import core.vni_provider as vnis


@mock.patch("commands.vpc_add.events")
@mock.patch("commands.vpc_add.ec2i")
def test_WHEN_mirror_enis_in_subnet_called_THEN_sets_up_mirroring(mock_ec2i, mock_events):
    # Set up our mock
    eni_1 = ec2i.NetworkInterface("vpc-1", "subnet-1", "eni-1", "type-1")
    eni_2 = ec2i.NetworkInterface("vpc-1", "subnet-1", "eni-2", "type-2")

    mock_ec2i.get_enis_of_subnet.return_value = [eni_1, eni_2]

    event_1 = events.CreateEniMirrorEvent("cluster-1", "vpc-1", "subnet-1", "eni-1", "eni-type-1", "session-1", 1234)
    event_2 = events.CreateEniMirrorEvent("cluster-1", "vpc-1", "subnet-1", "eni-2", "eni-type-1", "session-2", 1234)
    mock_events.CreateEniMirrorEvent.side_effect = [event_1, event_2]

    mock_provider = mock.Mock()

    # Run our test
    _mirror_enis_in_subnet("bus-1", "cluster-1", "vpc-1", "subnet-1", "filter-1", 1234, mock_provider)

    # Check our results
    expected_put_events_calls = [
        mock.call([event_1], "bus-1", mock_provider),
        mock.call([event_2], "bus-1", mock_provider)
    ]
    assert expected_put_events_calls == mock_events.put_events.call_args_list


@mock.patch("commands.vpc_add.AwsClientProvider")
@mock.patch("commands.vpc_add.SsmVniProvider")
@mock.patch("commands.vpc_add._mirror_enis_in_subnet")
@mock.patch("commands.vpc_add.ssm_ops")
@mock.patch("commands.vpc_add.ec2i")
@mock.patch("commands.vpc_add.CdkClient")
def test_WHEN_cmd_vpc_add_called_AND_no_user_vni_THEN_sets_up_mirroring(mock_cdk_client_cls, mock_ec2i, mock_ssm, mock_mirror,
                                                                        mock_vni_provider_cls, mock_aws_provider_cls):
    # Set up our mock
    mock_vni_provider = mock.Mock()
    mock_vni_provider.get_next_vni.return_value = 42
    mock_vni_provider_cls.return_value = mock_vni_provider

    subnet_ids = ["subnet-1", "subnet-2"]
    mock_ec2i.get_subnets_of_vpc.return_value = ["subnet-1", "subnet-2"]
    mock_ec2i.get_vpc_details.return_value = ec2i.VpcDetails("vpc-1", "1234", ["192.168.0.0/24", "192.168.128.0/24"], "default")

    mock_ssm.get_ssm_param_value.return_value = "" # Doesn't matter what this is besides an exception
    mock_ssm.get_ssm_param_json_value.side_effect = ["service-1", "bus-1", "filter-1"]

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    aws_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")
    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_aws_env.return_value = aws_env
    mock_aws_provider_cls.return_value = mock_aws_provider

    # Run our test
    cmd_vpc_add("profile", "region", "cluster-1", "vpc-1", None)

    # Check our results
    expected_cdk_calls = [
        mock.call(
            [
                constants.get_vpc_mirror_setup_stack_name("cluster-1", "vpc-1")
            ],
            context={
                constants.CDK_CONTEXT_CMD_VAR: constants.CMD_vpc_add,
                constants.CDK_CONTEXT_PARAMS_VAR: shlex.quote(json.dumps({
                    "arnEventBus": "bus-1",
                    "nameCluster": "cluster-1",
                    "nameVpcMirrorStack": constants.get_vpc_mirror_setup_stack_name("cluster-1", "vpc-1"),
                    "nameVpcSsmParam": constants.get_vpc_ssm_param_name("cluster-1", "vpc-1"),
                    "idVni": str(42),
                    "idVpc": "vpc-1",
                    "idVpceService": "service-1",
                    "listSubnetIds": subnet_ids,
                    "listSubnetSsmParams": [constants.get_subnet_ssm_param_name("cluster-1", "vpc-1", subnet_id) for subnet_id in subnet_ids],
                    "vpcCidrs": ["192.168.0.0/24", "192.168.128.0/24"]
                }))
            }
        )
    ]
    assert expected_cdk_calls == mock_cdk.deploy.call_args_list

    expected_cdk_client_create_calls = [
        mock.call(aws_env)
    ]
    assert expected_cdk_client_create_calls == mock_cdk_client_cls.call_args_list

    expected_mirror_calls = [
        mock.call("bus-1", "cluster-1", "vpc-1", "subnet-1", "filter-1", 42, mock.ANY),
        mock.call("bus-1", "cluster-1", "vpc-1", "subnet-2", "filter-1", 42, mock.ANY)
    ]
    assert expected_mirror_calls == mock_mirror.call_args_list

    expected_vni_calls = [mock.call(42)]
    assert expected_vni_calls == mock_vni_provider.use_next_vni.call_args_list

@mock.patch("commands.vpc_add.AwsClientProvider", mock.Mock())
@mock.patch("commands.vpc_add.SsmVniProvider")
@mock.patch("commands.vpc_add._mirror_enis_in_subnet")
@mock.patch("commands.vpc_add.CdkClient")
def test_WHEN_cmd_vpc_add_called_AND_no_available_vnis_THEN_aborts(mock_cdk_client_cls, mock_mirror, mock_vni_provider_cls):
    # Set up our mock
    mock_vni_provider = mock.Mock()
    mock_vni_provider.get_next_vni.side_effect = vnis.VniPoolExhausted()
    mock_vni_provider_cls.return_value = mock_vni_provider

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    # Run our test
    cmd_vpc_add("profile", "region", "cluster-1", "vpc-1", None)

    # Check our results
    expected_cdk_calls = []
    assert expected_cdk_calls == mock_cdk.deploy.call_args_list

    expected_mirror_calls = []
    assert expected_mirror_calls == mock_mirror.call_args_list

    expected_vni_calls = []
    assert expected_vni_calls == mock_vni_provider.use_next_vni.call_args_list

@mock.patch("commands.vpc_add.AwsClientProvider")
@mock.patch("commands.vpc_add.SsmVniProvider")
@mock.patch("commands.vpc_add._mirror_enis_in_subnet")
@mock.patch("commands.vpc_add.ssm_ops")
@mock.patch("commands.vpc_add.ec2i")
@mock.patch("commands.vpc_add.CdkClient")
def test_WHEN_cmd_vpc_add_called_AND_is_available_user_vni_THEN_sets_up_mirroring(mock_cdk_client_cls, mock_ec2i, mock_ssm, mock_mirror,
                                                                                  mock_vni_provider_cls, mock_aws_provider_cls):
    # Set up our mock
    mock_vni_provider = mock.Mock()
    mock_vni_provider.is_vni_available.return_value = True
    mock_vni_provider_cls.return_value = mock_vni_provider

    subnet_ids = ["subnet-1", "subnet-2"]
    mock_ec2i.get_subnets_of_vpc.return_value = ["subnet-1", "subnet-2"]
    mock_ec2i.get_vpc_details.return_value = ec2i.VpcDetails("vpc-1", "1234", ["192.168.0.0/24", "192.168.128.0/24"], "default")

    mock_ssm.get_ssm_param_value.return_value = "" # Doesn't matter what this is besides an exception
    mock_ssm.get_ssm_param_json_value.side_effect = ["service-1", "bus-1", "filter-1"]

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    aws_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")
    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_aws_env.return_value = aws_env
    mock_aws_provider_cls.return_value = mock_aws_provider

    # Run our test
    cmd_vpc_add("profile", "region", "cluster-1", "vpc-1", 1234)

    # Check our results
    expected_cdk_calls = [
        mock.call(
            [
                constants.get_vpc_mirror_setup_stack_name("cluster-1", "vpc-1")
            ],
            context={
                constants.CDK_CONTEXT_CMD_VAR: constants.CMD_vpc_add,
                constants.CDK_CONTEXT_PARAMS_VAR: shlex.quote(json.dumps({
                    "arnEventBus": "bus-1",
                    "nameCluster": "cluster-1",
                    "nameVpcMirrorStack": constants.get_vpc_mirror_setup_stack_name("cluster-1", "vpc-1"),
                    "nameVpcSsmParam": constants.get_vpc_ssm_param_name("cluster-1", "vpc-1"),
                    "idVni": str(1234),
                    "idVpc": "vpc-1",
                    "idVpceService": "service-1",
                    "listSubnetIds": subnet_ids,
                    "listSubnetSsmParams": [constants.get_subnet_ssm_param_name("cluster-1", "vpc-1", subnet_id) for subnet_id in subnet_ids],
                    "vpcCidrs": ["192.168.0.0/24", "192.168.128.0/24"]
                }))
            }
        )
    ]
    assert expected_cdk_calls == mock_cdk.deploy.call_args_list

    expected_cdk_client_create_calls = [
        mock.call(aws_env)
    ]
    assert expected_cdk_client_create_calls == mock_cdk_client_cls.call_args_list

    expected_mirror_calls = [
        mock.call("bus-1", "cluster-1", "vpc-1", "subnet-1", "filter-1", 1234, mock.ANY),
        mock.call("bus-1", "cluster-1", "vpc-1", "subnet-2", "filter-1", 1234, mock.ANY)
    ]
    assert expected_mirror_calls == mock_mirror.call_args_list

    expected_vni_calls = [mock.call(1234, "vpc-1")]
    assert expected_vni_calls == mock_vni_provider.register_user_vni.call_args_list

@mock.patch("commands.vpc_add.AwsClientProvider", mock.Mock())
@mock.patch("commands.vpc_add.SsmVniProvider")
@mock.patch("commands.vpc_add._mirror_enis_in_subnet")
@mock.patch("commands.vpc_add.CdkClient")
def test_WHEN_cmd_vpc_add_called_AND_is_unavailable_user_vni_THEN_aborts(mock_cdk_client_cls, mock_mirror, mock_vni_provider_cls):
    # Set up our mock
    mock_vni_provider = mock.Mock()
    mock_vni_provider.is_vni_available.return_value = False
    mock_vni_provider_cls.return_value = mock_vni_provider

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    # Run our test
    cmd_vpc_add("profile", "region", "cluster-1", "vpc-1", 1234)

    # Check our results
    expected_cdk_calls = []
    assert expected_cdk_calls == mock_cdk.deploy.call_args_list

    expected_mirror_calls = []
    assert expected_mirror_calls == mock_mirror.call_args_list

    expected_vni_calls = []
    assert expected_vni_calls == mock_vni_provider.register_user_vni.call_args_list

@mock.patch("commands.vpc_add.AwsClientProvider", mock.Mock())
@mock.patch("commands.vpc_add.SsmVniProvider")
@mock.patch("commands.vpc_add._mirror_enis_in_subnet")
@mock.patch("commands.vpc_add.CdkClient")
def test_WHEN_cmd_vpc_add_called_AND_is_outrange_user_vni_THEN_aborts(mock_cdk_client_cls, mock_mirror, mock_vni_provider_cls):
    # Set up our mock
    mock_vni_provider = mock.Mock()
    mock_vni_provider.is_vni_available.side_effect = vnis.VniOutsideRange(1234)
    mock_vni_provider_cls.return_value = mock_vni_provider

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    # Run our test
    cmd_vpc_add("profile", "region", "cluster-1", "vpc-1", 1234)

    # Check our results
    expected_cdk_calls = []
    assert expected_cdk_calls == mock_cdk.deploy.call_args_list

    expected_mirror_calls = []
    assert expected_mirror_calls == mock_mirror.call_args_list

    expected_vni_calls = []
    assert expected_vni_calls == mock_vni_provider.register_user_vni.call_args_list

@mock.patch("commands.vpc_add.AwsClientProvider", mock.Mock())
@mock.patch("commands.vpc_add.SsmVniProvider")
@mock.patch("commands.vpc_add._mirror_enis_in_subnet")
@mock.patch("commands.vpc_add.CdkClient")
def test_WHEN_cmd_vpc_add_called_AND_is_used_user_vni_THEN_aborts(mock_cdk_client_cls, mock_mirror, mock_vni_provider_cls):
    # Set up our mock
    mock_vni_provider = mock.Mock()
    mock_vni_provider.is_vni_available.side_effect = vnis.VniAlreadyUsed(1234)
    mock_vni_provider_cls.return_value = mock_vni_provider

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    # Run our test
    cmd_vpc_add("profile", "region", "cluster-1", "vpc-1", 1234)

    # Check our results
    expected_cdk_calls = []
    assert expected_cdk_calls == mock_cdk.deploy.call_args_list

    expected_mirror_calls = []
    assert expected_mirror_calls == mock_mirror.call_args_list

    expected_vni_calls = []
    assert expected_vni_calls == mock_vni_provider.register_user_vni.call_args_list

@mock.patch("commands.vpc_add.AwsClientProvider", mock.Mock())
@mock.patch("commands.vpc_add.SsmVniProvider")
@mock.patch("commands.vpc_add._mirror_enis_in_subnet")
@mock.patch("commands.vpc_add.ssm_ops")
@mock.patch("commands.vpc_add.CdkClient")
def test_WHEN_cmd_vpc_add_called_AND_cluster_doesnt_exist_THEN_aborts(mock_cdk_client_cls, mock_ssm, mock_mirror, mock_vni_provider_cls):
    # Set up our mock
    mock_vni_provider = mock.Mock()
    mock_vni_provider.is_vni_available.return_value = True
    mock_vni_provider_cls.return_value = mock_vni_provider

    mock_ssm.ParamDoesNotExist = ParamDoesNotExist
    mock_ssm.get_ssm_param_value.side_effect = ParamDoesNotExist("")

    mock_cdk = mock.Mock()
    mock_cdk_client_cls.return_value = mock_cdk

    # Run our test
    cmd_vpc_add("profile", "region", "cluster-1", "vpc-1", 1234)

    # Check our results
    expected_cdk_calls = []
    assert expected_cdk_calls == mock_cdk.deploy.call_args_list

    expected_mirror_calls = []
    assert expected_mirror_calls == mock_mirror.call_args_list

    expected_vni_calls = []
    assert expected_vni_calls == mock_vni_provider.register_user_vni.call_args_list
    assert expected_vni_calls == mock_vni_provider.use_next_vni.call_args_list

@mock.patch("commands.vpc_add.AwsClientProvider", mock.Mock())
@mock.patch("commands.vpc_add.SsmVniProvider")
@mock.patch("commands.vpc_add._mirror_enis_in_subnet")
@mock.patch("commands.vpc_add.ssm_ops")
@mock.patch("commands.vpc_add.ec2i")
@mock.patch("commands.vpc_add.CdkClient")
def test_WHEN_cmd_vpc_add_called_AND_vpc_doesnt_exist_THEN_skips(mock_cdk_client_cls, mock_ec2i, mock_ssm, mock_mirror, mock_vni_provider_cls):
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
    cmd_vpc_add("profile", "region", "cluster-1", "vpc-1", 1234)

    # Check our results
    expected_cdk_calls = []
    assert expected_cdk_calls == mock_cdk.deploy.call_args_list

    expected_mirror_calls = []
    assert expected_mirror_calls == mock_mirror.call_args_list

    expected_vni_calls = []
    assert expected_vni_calls == mock_vni_provider.register_user_vni.call_args_list
    assert expected_vni_calls == mock_vni_provider.use_next_vni.call_args_list