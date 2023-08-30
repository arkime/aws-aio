import pytest

import core.capacity_planning as cap

INSTANCE_TYPE_CAPTURE_NODE = "m5.xlarge";


T3_SMALL_SEARCH = next((instance for instance in cap.DATA_INSTANCES if "t3.small.search" == instance.type))
T3_MEDIUM_SEARCH = next((instance for instance in cap.DATA_INSTANCES if "t3.medium.search" == instance.type))
R6G_LARGE_SEARCH = next((instance for instance in cap.DATA_INSTANCES if "r6g.large.search" == instance.type))
R6G_4XLARGE_SEARCH = next((instance for instance in cap.DATA_INSTANCES if "r6g.4xlarge.search" == instance.type))
R6G_12XLARGE_SEARCH = next((instance for instance in cap.DATA_INSTANCES if "r6g.12xlarge.search" == instance.type))

def test_WHEN_get_capture_node_capacity_plan_called_THEN_as_expected():
    # TEST 1: No expected traffic number

    actual_value = cap.get_capture_node_capacity_plan(None)
    expected_value = cap.CaptureNodesPlan(cap.CAPTURE_INSTANCES[0].instanceType, 1, 2, 1)

    assert expected_value == actual_value

    # TEST 2: Small expected traffic number

    actual_value = cap.get_capture_node_capacity_plan(0.001)
    expected_value = cap.CaptureNodesPlan(cap.CAPTURE_INSTANCES[0].instanceType, 1, 2, 1)

    assert expected_value == actual_value

    # TEST 3: Mid-range expected traffic number

    actual_value = cap.get_capture_node_capacity_plan(20)
    expected_value = cap.CaptureNodesPlan(INSTANCE_TYPE_CAPTURE_NODE, 10, 13, 1)

    assert expected_value == actual_value

    # TEST 4: Max expected traffic number

    actual_value = cap.get_capture_node_capacity_plan(cap.MAX_TRAFFIC)
    expected_value = cap.CaptureNodesPlan(INSTANCE_TYPE_CAPTURE_NODE, 50, 63, 1)

    assert expected_value == actual_value

    # TEST 5: Excessive expected traffic number

    with pytest.raises(cap.TooMuchTraffic):
        cap.get_capture_node_capacity_plan(cap.MAX_TRAFFIC + 10)


def test_WHEN_get_ecs_sys_resource_plan_called_THEN_as_expected():
    # TEST 1: Get an m5.xlarge instance
    actual_value = cap.get_ecs_sys_resource_plan(INSTANCE_TYPE_CAPTURE_NODE)
    expected_value = cap.EcsSysResourcePlan(3584, 15360)

    assert expected_value == actual_value

    # TEST 2: Get an unknown instance type
    with pytest.raises(cap.UnknownInstanceType):
        cap.get_ecs_sys_resource_plan("unknown")

def test_WHEN_get_total_storage_called_THEN_as_expected():
    # TEST 1: No replicas
    actual_value = cap._get_total_storage(10, 30, 0)
    expected_value = 97200

    assert expected_value == actual_value

    # TEST 2: Single replica
    actual_value = cap._get_total_storage(10, 30, 1)
    expected_value = 97200*2

    assert expected_value == actual_value

    # TEST 3: Many replicas
    actual_value = cap._get_total_storage(10, 30, 5)
    expected_value = 97200*6

    assert expected_value == actual_value

def test_WHEN_get_data_node_plan_called_THEN_as_expected():
    # TEST 1: Toy setup
    actual_value = cap._get_data_node_plan(10, 3)
    expected_value = cap.DataNodesPlan(2, T3_SMALL_SEARCH.type, T3_SMALL_SEARCH.volSize)
    assert expected_value == actual_value

    # TEST 2: Tiny setup
    actual_value = cap._get_data_node_plan(650, 3)
    expected_value = cap.DataNodesPlan(4, T3_MEDIUM_SEARCH.type, T3_MEDIUM_SEARCH.volSize)
    assert expected_value == actual_value

    # TEST 2b: Tiny setup, 2 AZs
    actual_value = cap._get_data_node_plan(650, 2)
    expected_value = cap.DataNodesPlan(4, T3_MEDIUM_SEARCH.type, T3_MEDIUM_SEARCH.volSize)
    assert expected_value == actual_value

    # TEST 3: Small setup (1)
    actual_value = cap._get_data_node_plan(1100, 3)
    expected_value = cap.DataNodesPlan(6, T3_MEDIUM_SEARCH.type, T3_MEDIUM_SEARCH.volSize)
    assert expected_value == actual_value

    # TEST 4: Small setup (2)
    actual_value = cap._get_data_node_plan(65000, 3)
    expected_value = cap.DataNodesPlan(64, R6G_LARGE_SEARCH.type, R6G_LARGE_SEARCH.volSize)
    assert expected_value == actual_value

    # TEST 5: Medium setup (1)
    actual_value = cap._get_data_node_plan(90000, 3)
    expected_value = cap.DataNodesPlan(15, R6G_4XLARGE_SEARCH.type, R6G_4XLARGE_SEARCH.volSize)
    assert expected_value == actual_value

    # TEST 5b: Medium setup (1), 2 AZs
    actual_value = cap._get_data_node_plan(90000, 2)
    expected_value = cap.DataNodesPlan(16, R6G_4XLARGE_SEARCH.type, R6G_4XLARGE_SEARCH.volSize)
    assert expected_value == actual_value

    # TEST 6: Medium setup (2)
    actual_value = cap._get_data_node_plan(450000, 3)
    expected_value = cap.DataNodesPlan(74, R6G_4XLARGE_SEARCH.type, R6G_4XLARGE_SEARCH.volSize)
    assert expected_value == actual_value

    # TEST 7: Large setup (1)
    actual_value = cap._get_data_node_plan(500000, 3)
    expected_value = cap.DataNodesPlan(41, R6G_12XLARGE_SEARCH.type, R6G_12XLARGE_SEARCH.volSize)
    assert expected_value == actual_value

    # TEST 8: Enormous setup
    actual_value = cap._get_data_node_plan(1200000, 3)
    expected_value = cap.DataNodesPlan(98, R6G_12XLARGE_SEARCH.type, R6G_12XLARGE_SEARCH.volSize)
    assert expected_value == actual_value

def test_WHEN_get_master_node_plan_called_THEN_as_expected():
    # TEST: Non-graviton
    actual_value = cap._get_master_node_plan(5, 2, T3_SMALL_SEARCH.type)
    expected_value = cap.MasterNodesPlan(3, "t3.small.search")
    assert expected_value == actual_value

    # TEST: Small data
    actual_value = cap._get_master_node_plan(5, 2, "blah")
    expected_value = cap.MasterNodesPlan(3, "m6g.large.search")
    assert expected_value == actual_value

    # TEST: Small data w/ lots of data nodes
    actual_value = cap._get_master_node_plan(5, 11, "blah")
    expected_value = cap.MasterNodesPlan(3, "c6g.2xlarge.search")
    assert expected_value == actual_value

    # TEST: Small data w/ lots and lots of data nodes
    actual_value = cap._get_master_node_plan(5, 31, "blah")
    expected_value = cap.MasterNodesPlan(3, "r6g.2xlarge.search")
    assert expected_value == actual_value

    # TEST: Medium data
    actual_value = cap._get_master_node_plan(401000, 20, "blah")
    expected_value = cap.MasterNodesPlan(3, "c6g.2xlarge.search")
    assert expected_value == actual_value

    # TEST: Medium data w/ lots of data nodes
    actual_value = cap._get_master_node_plan(401000, 31, "blah")
    expected_value = cap.MasterNodesPlan(3, "r6g.2xlarge.search")
    assert expected_value == actual_value

    # TEST: Large data
    actual_value = cap._get_master_node_plan(1250000, 80, "blah")
    expected_value = cap.MasterNodesPlan(3, "r6g.2xlarge.search")
    assert expected_value == actual_value

    # TEST: Large data w/ lots of data nodes (trigger nodes)
    actual_value = cap._get_master_node_plan(1250000, 130, "blah")
    expected_value = cap.MasterNodesPlan(3, "r6g.4xlarge.search")
    assert expected_value == actual_value

    # TEST: Enormous data w/ lots of data nodes (trigger data)
    actual_value = cap._get_master_node_plan(4010000, 120, "blah")
    expected_value = cap.MasterNodesPlan(3, "r6g.4xlarge.search")
    assert expected_value == actual_value

def test_WHEN_get_os_domain_plan_called_THEN_as_expected():
    actual_value = cap.get_os_domain_plan(20, 30, 1, 2)
    expected_value = cap.OSDomainPlan(
        cap.DataNodesPlan(64, R6G_4XLARGE_SEARCH.type, R6G_4XLARGE_SEARCH.volSize),
        cap.MasterNodesPlan(3, "r6g.2xlarge.search")
    )
    assert expected_value == actual_value

def test_WHEN_cidr_created_THEN_as_expected():
    # Test: Valid CIDR
    cap.Cidr("1.2.3.4/19")

    # Test: Wrong CIDR form example 1
    with pytest.raises(cap.InvalidCidr):
        cap.Cidr("1.2.3.4 19")

    # Test: Wrong CIDR form example 2
    with pytest.raises(cap.InvalidCidr):
        cap.Cidr("1.2.3/19")

    # Test: Invalid prefix
    with pytest.raises(cap.InvalidCidr):
        cap.Cidr("1.2.3.256/19")

    # Test: Invalid mask
    with pytest.raises(cap.InvalidCidr):
        cap.Cidr("1.2.3.4/33")

def test_WHEN_get_capture_vpc_plan_called_THEN_as_expected():
    # TEST: There's an existing plan, return it
    previous_plan = cap.CaptureVpcPlan(cap.Cidr("1.2.3.4/24"), 2)
    actual_value = cap.get_capture_vpc_plan(previous_plan, "5.5.5.5/16")

    assert previous_plan == actual_value

    # TEST: There's not an existing plan, use defaults
    previous_plan = cap.CaptureVpcPlan(None, None)
    actual_value = cap.get_capture_vpc_plan(previous_plan, None)

    assert cap.CaptureVpcPlan(cap.DEFAULT_VPC_CIDR, cap.DEFAULT_NUM_AZS) == actual_value

    # TEST: There's not an existing plan, use specified CIDR
    previous_plan = cap.CaptureVpcPlan(None, None)
    actual_value = cap.get_capture_vpc_plan(previous_plan, "5.5.5.5/16")

    assert cap.CaptureVpcPlan(cap.Cidr("5.5.5.5/16"), cap.DEFAULT_NUM_AZS) == actual_value
