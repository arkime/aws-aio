import json
import unittest.mock as mock

from aws_interactions.aws_environment import AwsEnvironment
import core.constants as constants
import core.cross_account_wrangling as caw

def test_WHEN_get_iam_role_name_called_THEN_as_expected():
    # TEST: Cluster Name is nice and short
    result = caw.get_iam_role_name("ThisIsMyRoleName", "vpc-12345678901234567")
    assert "arkime_ThisIsMyRoleName_vpc-12345678901234567" == result

    # TEST: Cluster Name is longer than will fit naturally
    result = caw.get_iam_role_name("ThisIsAVeryLongClusterNameThatHopefulyWontHappenForReal", "vpc-12345678901234567")
    assert "arkime_ThisIsAVeryLongClusterNameThatHopef_vpc-12345678901234567" == result

@mock.patch("core.cross_account_wrangling.does_iam_role_exist")
@mock.patch("core.cross_account_wrangling.get_iam_role_name")
def test_WHEN_ensure_cross_account_role_exists_called_AND_doesnt_exist_THEN_as_expected(mock_get_name, mock_does_exist):
    # Set up our mock
    mock_iam_client = mock.Mock()

    mock_provider = mock.Mock()
    mock_provider.get_iam.return_value = mock_iam_client
    test_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")

    mock_get_name.return_value = "role_name"
    mock_does_exist.return_value = False

    # Run our test
    result = caw.ensure_cross_account_role_exists("my_cluster", "XXXXXXXXXXXX", "vpc", mock_provider, test_env)

    # Check our results
    assert "role_name" == result

    expected_trust = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": f"arn:aws:iam::XXXXXXXXXXXX:root"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    expected_update_calls = []
    assert expected_update_calls == mock_iam_client.update_assume_role_policy.call_args_list

    expected_create_calls = [
        mock.call(            
            RoleName="role_name",
            AssumeRolePolicyDocument=json.dumps(expected_trust),
            Description=mock.ANY,
        )
    ]
    assert expected_create_calls == mock_iam_client.create_role.call_args_list

    expected_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ssm:DeleteParameter",
                    "ssm:GetParameter",
                    "ssm:GetParameters",
                    "ssm:PutParameter",
                ],
                "Resource": f"arn:aws:ssm:region:XXXXXXXXXXXX:parameter/arkime/clusters/my_cluster*"
            }
        ]
    }
    expected_put_calls = [
        mock.call(
            RoleName="role_name",
            PolicyName='CrossAcctSSMAccessPolicy',
            PolicyDocument=json.dumps(expected_policy)
        )
    ]
    assert expected_put_calls == mock_iam_client.put_role_policy.call_args_list

@mock.patch("core.cross_account_wrangling.does_iam_role_exist")
@mock.patch("core.cross_account_wrangling.get_iam_role_name")
def test_WHEN_ensure_cross_account_role_exists_called_AND_does_exist_THEN_as_expected(mock_get_name, mock_does_exist):
    # Set up our mock
    mock_iam_client = mock.Mock()

    mock_provider = mock.Mock()
    mock_provider.get_iam.return_value = mock_iam_client
    test_env = AwsEnvironment("XXXXXXXXXXXX", "region", "profile")

    mock_get_name.return_value = "role_name"
    mock_does_exist.return_value = True

    # Run our test
    result = caw.ensure_cross_account_role_exists("my_cluster", "XXXXXXXXXXXX", "vpc", mock_provider, test_env)

    # Check our results
    assert "role_name" == result

    expected_trust = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": f"arn:aws:iam::XXXXXXXXXXXX:root"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    expected_update_calls = [
        mock.call(            
            RoleName="role_name",
            PolicyDocument=json.dumps(expected_trust)
        )
    ]
    assert expected_update_calls == mock_iam_client.update_assume_role_policy.call_args_list

    expected_create_calls = []
    assert expected_create_calls == mock_iam_client.create_role.call_args_list

    expected_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ssm:DeleteParameter",
                    "ssm:GetParameter",
                    "ssm:GetParameters",
                    "ssm:PutParameter",
                ],
                "Resource": f"arn:aws:ssm:region:XXXXXXXXXXXX:parameter/arkime/clusters/my_cluster*"
            }
        ]
    }
    expected_put_calls = [
        mock.call(
            RoleName="role_name",
            PolicyName='CrossAcctSSMAccessPolicy',
            PolicyDocument=json.dumps(expected_policy)
        )
    ]
    assert expected_put_calls == mock_iam_client.put_role_policy.call_args_list

def test_WHEN_add_vpce_permissions_called_THEN_as_expected():
    # Set up our mock
    mock_ec2_client = mock.Mock()

    mock_provider = mock.Mock()
    mock_provider.get_ec2.return_value = mock_ec2_client

    # Run our test
    caw.add_vpce_permissions("vpce_id", "YYYYYYYYYYYY", mock_provider)

    # Check our results
    expected_modify_calls = [
        mock.call(
            ServiceId="vpce_id",
            AddAllowedPrincipals=[
                f"arn:aws:iam::YYYYYYYYYYYY:root"
            ]
        )
    ]
    assert expected_modify_calls == mock_ec2_client.modify_vpc_endpoint_service_permissions.call_args_list

@mock.patch("core.cross_account_wrangling.get_cross_account_associations")
def test_WHEN_remove_vpce_permissions_called_THEN_as_expected(mock_get_associations):
    # Set up our mock
    mock_ec2_client = mock.Mock()

    mock_provider = mock.Mock()
    mock_provider.get_ec2.return_value = mock_ec2_client

    raw_association_1 = {"clusterAccount": "XXXXXXXXXXXX", "clusterName": "MyCluster", "roleName": "arkime_MyCluster_vpc-08d5c92356da0ccb4", "vpcAccount": "YYYYYYYYYYYY", "vpcId": "vpc-08d5c92356da0ccb4", "vpceServiceId": "vpce-svc-0bf7f421d6596c8cb"}
    association_1 = caw.CrossAccountAssociation(**raw_association_1)
    raw_association_2 = {"clusterAccount": "XXXXXXXXXXXX", "clusterName": "MyCluster", "roleName": "arkime_MyCluster_vpc-0eadcf1a9ad8b3e26", "vpcAccount": "ZZZZZZZZZZZZ", "vpcId": "vpc-0eadcf1a9ad8b3e26", "vpceServiceId": "vpce-svc-0bf7f421d6596c8cb"}
    association_2 = caw.CrossAccountAssociation(**raw_association_2)
    mock_get_associations.return_value = [association_1, association_2]

    # Run our test
    caw.remove_vpce_permissions("MyCluster", "vpc-08d5c92356da0ccb4", mock_provider)

    # Check the results
    expected_modify_calls = [
        mock.call(
            ServiceId="vpce-svc-0bf7f421d6596c8cb",
            RemoveAllowedPrincipals=[
                f"arn:aws:iam::YYYYYYYYYYYY:root"
            ]
        )
    ]
    assert expected_modify_calls == mock_ec2_client.modify_vpc_endpoint_service_permissions.call_args_list

@mock.patch("core.cross_account_wrangling.get_cross_account_associations")
def test_WHEN_remove_vpce_permissions_called_AND_not_associated_THEN_skips(mock_get_associations):
    # Set up our mock
    mock_ec2_client = mock.Mock()

    mock_provider = mock.Mock()
    mock_provider.get_ec2.return_value = mock_ec2_client

    mock_get_associations.return_value = []

    # Run our test
    caw.remove_vpce_permissions("MyCluster", "vpc-08d5c92356da0ccb4", mock_provider)

    # Check the results
    expected_modify_calls = []
    assert expected_modify_calls == mock_ec2_client.modify_vpc_endpoint_service_permissions.call_args_list

@mock.patch("core.cross_account_wrangling.get_cross_account_associations")
def test_WHEN_remove_vpce_permissions_called_AND_other_vpcs_THEN_skips(mock_get_associations):
    # Set up our mock
    mock_ec2_client = mock.Mock()

    mock_provider = mock.Mock()
    mock_provider.get_ec2.return_value = mock_ec2_client

    raw_association_1 = {"clusterAccount": "XXXXXXXXXXXX", "clusterName": "MyCluster", "roleName": "arkime_MyCluster_vpc-08d5c92356da0ccb4", "vpcAccount": "YYYYYYYYYYYY", "vpcId": "vpc-08d5c92356da0ccb4", "vpceServiceId": "vpce-svc-0bf7f421d6596c8cb"}
    association_1 = caw.CrossAccountAssociation(**raw_association_1)
    raw_association_2 = {"clusterAccount": "XXXXXXXXXXXX", "clusterName": "MyCluster", "roleName": "arkime_MyCluster_vpc-0eadcf1a9ad8b3e26", "vpcAccount": "YYYYYYYYYYYY", "vpcId": "vpc-0eadcf1a9ad8b3e26", "vpceServiceId": "vpce-svc-0bf7f421d6596c8cb"}
    association_2 = caw.CrossAccountAssociation(**raw_association_2)
    mock_get_associations.return_value = [association_1, association_2]

    # Run our test
    caw.remove_vpce_permissions("MyCluster", "vpc-08d5c92356da0ccb4", mock_provider)

    # Check the results
    expected_modify_calls = []
    assert expected_modify_calls == mock_ec2_client.modify_vpc_endpoint_service_permissions.call_args_list

@mock.patch("core.cross_account_wrangling.ssm_ops")
def test_WHEN_get_cross_account_associations_called_THEN_as_expected(mock_ssm_ops):
    # Set up our mock
    mock_provider = mock.Mock()

    raw_association_1 = {"clusterAccount": "XXXXXXXXXXXX", "clusterName": "MyCluster", "roleName": "arkime_MyCluster_vpc-08d5c92356da0ccb4", "vpcAccount": "YYYYYYYYYYYY", "vpcId": "vpc-08d5c92356da0ccb4", "vpceServiceId": "vpce-svc-0bf7f421d6596c8cb"}
    raw_association_2 = {"clusterAccount": "XXXXXXXXXXXX", "clusterName": "MyCluster", "roleName": "arkime_MyCluster_vpc-0eadcf1a9ad8b3e26", "vpcAccount": "ZZZZZZZZZZZZ", "vpcId": "vpc-0eadcf1a9ad8b3e26", "vpceServiceId": "vpce-svc-0bf7f421d6596c8cb"}
    mock_ssm_ops.get_ssm_params_by_path.side_effect = [
        [
            {
                'Name': '/arkime/clusters/MyCluster/vpcs/vpc-08d5c92356da0ccb4/cross-account',
                'Value': json.dumps(raw_association_1),
            },
            {
                'Name': '/arkime/clusters/MyCluster/vpcs/vpc-0eadcf1a9ad8b3e26/cross-account',
                'Value': json.dumps(raw_association_2),
            },
            {
                'Name': '/arkime/clusters/MyCluster/vpcs/vpc-0f08710cdbc32d58a',
                'Value': '{"busArn":"arn:aws:events:us-east-2:XXXXXXXXXXXX:event-bus/MyClustervpc0f08710cdbc32d58aMirrorVpcBusAC2AE73F","mirrorFilterId":"tmf-0f84cdfef3cd62b09","mirrorVni":"24","vpcId":"vpc-0f08710cdbc32d58a"}',
            },
            {
                'Name': '/arkime/clusters/MyCluster/vpcs/vpc-0f08710cdbc32d58a/subnets/subnet-04bc404a6e4ef39e3',
                'Value': '{"mirrorTargetId":"tmt-031fd480afeb2cd7b","subnetId":"subnet-04bc404a6e4ef39e3","vpcEndpointId":"vpce-090ba993602e313e6"}',
            },
            {
                'Name': '/arkime/clusters/MyCluster/vpcs/vpc-0f08710cdbc32d58a/subnets/subnet-04bc404a6e4ef39e3/enis/eni-02be669dc1f946dbc',
                'Value': '{"eniId": "eni-02be669dc1f946dbc", "trafficSessionId": "tms-0c987245d763cdc12"}',
            },
        ]
    ]

    # Run our test
    result = caw.get_cross_account_associations("MyCluster", mock_provider)

    # Check our results
    expected_result = [
        caw.CrossAccountAssociation(**raw_association_1),
        caw.CrossAccountAssociation(**raw_association_2)
    ]
    assert expected_result == result

    expected_get_params_path_calls = [
        mock.call(f"{constants.get_cluster_ssm_param_name('MyCluster')}/vpcs", mock_provider, recursive=True),
    ]
    assert expected_get_params_path_calls == mock_ssm_ops.get_ssm_params_by_path.call_args_list

@mock.patch("core.cross_account_wrangling.get_cross_account_associations")
@mock.patch("core.cross_account_wrangling.ssm_ops")
@mock.patch("core.cross_account_wrangling.AwsClientProvider")
def test_WHEN_get_cross_account_vpc_details_called_THEN_as_expected(mock_provider_cls, mock_ssm_ops, mock_get_associations):
    # Set up our mock
    mock_provider = mock.Mock()
    mock_provider._aws_profile = "profile"
    mock_provider._aws_region = "region"
    mock_provider_Y = mock.Mock()
    mock_provider_Z = mock.Mock()
    mock_provider_cls.side_effect = [mock_provider_Y, mock_provider_Z]

    raw_association_1 = {"clusterAccount": "XXXXXXXXXXXX", "clusterName": "MyCluster", "roleName": "arkime_MyCluster_vpc-08d5c92356da0ccb4", "vpcAccount": "YYYYYYYYYYYY", "vpcId": "vpc-08d5c92356da0ccb4", "vpceServiceId": "vpce-svc-0bf7f421d6596c8cb"}
    association_1 = caw.CrossAccountAssociation(**raw_association_1)
    raw_association_2 = {"clusterAccount": "XXXXXXXXXXXX", "clusterName": "MyCluster", "roleName": "arkime_MyCluster_vpc-0eadcf1a9ad8b3e26", "vpcAccount": "ZZZZZZZZZZZZ", "vpcId": "vpc-0eadcf1a9ad8b3e26", "vpceServiceId": "vpce-svc-0bf7f421d6596c8cb"}
    association_2 = caw.CrossAccountAssociation(**raw_association_2)
    mock_get_associations.return_value = [
        association_1, association_2
    ]

    raw_vpc_detail_1 = {"busArn":"arn:aws:events:us-east-2:YYYYYYYYYYYY:event-bus/MyCluster3vpc08d5c92356da0ccb4MirrorVpcBusE8FB13DF","mirrorFilterId":"tmf-0f344ba2525e0857a","mirrorVni":"26","vpcId":"vpc-08d5c92356da0ccb4"}
    raw_vpc_detail_2 = {"busArn":"arn:aws:events:us-east-2:ZZZZZZZZZZZZ:event-bus/MyCluster3vpc0eadcf1a9ad8b3e26MirrorVpcBusFK1238AB","mirrorFilterId":"tmf-1234567890abcdef1","mirrorVni":"11","vpcId":"vpc-0eadcf1a9ad8b3e26"}
    mock_ssm_ops.get_ssm_param_value.side_effect = [
        json.dumps(raw_vpc_detail_1),
        json.dumps(raw_vpc_detail_2),
    ]

    # Run our test
    result = caw.get_cross_account_vpc_details("MyCluster", mock_provider)

    # Check our results
    expected_detail_1 = caw.CrossAccountVpcDetail(
        busArn=raw_vpc_detail_1["busArn"], mirrorFilterId=raw_vpc_detail_1["mirrorFilterId"], mirrorVni=raw_vpc_detail_1["mirrorVni"],
        vpcAccount="YYYYYYYYYYYY", vpcId=raw_vpc_detail_1["vpcId"]
    )
    expected_detail_2 = caw.CrossAccountVpcDetail(
        busArn=raw_vpc_detail_2["busArn"], mirrorFilterId=raw_vpc_detail_2["mirrorFilterId"], mirrorVni=raw_vpc_detail_2["mirrorVni"],
        vpcAccount="ZZZZZZZZZZZZ", vpcId=raw_vpc_detail_2["vpcId"]
    )
    expected_result = [expected_detail_1, expected_detail_2]
    assert expected_result == result

    expected_provider_init_calls = [
        mock.call(
            aws_profile="profile",
            aws_region="region",
            assume_role_arn=f"arn:aws:iam::YYYYYYYYYYYY:role/arkime_MyCluster_vpc-08d5c92356da0ccb4"
        ),
        mock.call(
            aws_profile="profile",
            aws_region="region",
            assume_role_arn=f"arn:aws:iam::ZZZZZZZZZZZZ:role/arkime_MyCluster_vpc-0eadcf1a9ad8b3e26"
        ),
    ]
    assert expected_provider_init_calls == mock_provider_cls.call_args_list

    expected_get_params_calls = [
        mock.call(constants.get_vpc_ssm_param_name("MyCluster", "vpc-08d5c92356da0ccb4"), mock_provider_Y),
        mock.call(constants.get_vpc_ssm_param_name("MyCluster", "vpc-0eadcf1a9ad8b3e26"), mock_provider_Z),
    ]
    assert expected_get_params_calls == mock_ssm_ops.get_ssm_param_value.call_args_list

    

