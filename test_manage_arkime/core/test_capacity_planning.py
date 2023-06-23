import pytest
import unittest.mock as mock

import core.capacity_planning as cap


def test_WHEN_get_capture_node_capacity_plan_called_THEN_as_expected():
    # TEST 1: No expected traffic number

    actual_value = cap.get_capture_node_capacity_plan(None)
    expected_value = cap.CaptureNodesPlan(cap.INSTANCE_TYPE_CAPTURE_NODE, 1, 2, 1)

    assert expected_value == actual_value
    
    # TEST 2: Small expected traffic number

    actual_value = cap.get_capture_node_capacity_plan(0.001)
    expected_value = cap.CaptureNodesPlan(cap.INSTANCE_TYPE_CAPTURE_NODE, 1, 2, 1)

    assert expected_value == actual_value

    # TEST 3: Mid-range expected traffic number

    actual_value = cap.get_capture_node_capacity_plan(20)
    expected_value = cap.CaptureNodesPlan(cap.INSTANCE_TYPE_CAPTURE_NODE, 10, 13, 1)

    assert expected_value == actual_value

    # TEST 4: Max expected traffic number

    actual_value = cap.get_capture_node_capacity_plan(cap.MAX_TRAFFIC)
    expected_value = cap.CaptureNodesPlan(cap.INSTANCE_TYPE_CAPTURE_NODE, 50, 63, 1)

    assert expected_value == actual_value

    # TEST 5: Excessive expected traffic number

    with pytest.raises(cap.TooMuchTraffic):
        cap.get_capture_node_capacity_plan(cap.MAX_TRAFFIC + 10)


def test_WHEN_get_ecs_sys_resource_plan_called_THEN_as_expected():
    # TEST 1: Get an m5.xlarge instance
    actual_value = cap.get_ecs_sys_resource_plan(cap.INSTANCE_TYPE_CAPTURE_NODE)
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
    expected_value = cap.DataNodesPlan(2, cap.T3_SMALL_SEARCH.type, cap.T3_SMALL_SEARCH.vol_size)
    assert expected_value == actual_value

    # TEST 2: Tiny setup
    actual_value = cap._get_data_node_plan(650, 3)
    expected_value = cap.DataNodesPlan(7, cap.T3_SMALL_SEARCH.type, cap.T3_SMALL_SEARCH.vol_size)
    assert expected_value == actual_value

    # TEST 2b: Tiny setup, 2 AZs
    actual_value = cap._get_data_node_plan(650, 2)
    expected_value = cap.DataNodesPlan(8, cap.T3_SMALL_SEARCH.type, cap.T3_SMALL_SEARCH.vol_size)
    assert expected_value == actual_value

    # TEST 3: Small setup (1)
    actual_value = cap._get_data_node_plan(1100, 3)
    expected_value = cap.DataNodesPlan(2, cap.R6G_LARGE_SEARCH.type, cap.R6G_LARGE_SEARCH.vol_size)
    assert expected_value == actual_value

    # TEST 4: Small setup (2)
    actual_value = cap._get_data_node_plan(65000, 3)
    expected_value = cap.DataNodesPlan(64, cap.R6G_LARGE_SEARCH.type, cap.R6G_LARGE_SEARCH.vol_size)
    assert expected_value == actual_value

    # TEST 5: Medium setup (1)
    actual_value = cap._get_data_node_plan(90000, 3)
    expected_value = cap.DataNodesPlan(15, cap.R6G_4XLARGE_SEARCH.type, cap.R6G_4XLARGE_SEARCH.vol_size)
    assert expected_value == actual_value

    # TEST 5b: Medium setup (1), 2 AZs
    actual_value = cap._get_data_node_plan(90000, 2)
    expected_value = cap.DataNodesPlan(16, cap.R6G_4XLARGE_SEARCH.type, cap.R6G_4XLARGE_SEARCH.vol_size)
    assert expected_value == actual_value

    # TEST 6: Medium setup (2)
    actual_value = cap._get_data_node_plan(450000, 3)
    expected_value = cap.DataNodesPlan(74, cap.R6G_4XLARGE_SEARCH.type, cap.R6G_4XLARGE_SEARCH.vol_size)
    assert expected_value == actual_value

    # TEST 7: Large setup (1)
    actual_value = cap._get_data_node_plan(500000, 3)
    expected_value = cap.DataNodesPlan(41, cap.R6G_12XLARGE_SEARCH.type, cap.R6G_12XLARGE_SEARCH.vol_size)
    assert expected_value == actual_value

    # TEST 8: Enormous setup
    actual_value = cap._get_data_node_plan(1200000, 3)
    expected_value = cap.DataNodesPlan(98, cap.R6G_12XLARGE_SEARCH.type, cap.R6G_12XLARGE_SEARCH.vol_size)
    assert expected_value == actual_value

def test_WHEN_get_master_node_plan_called_THEN_as_expected():
    # TEST: Non-graviton
    actual_value = cap._get_master_node_plan(5, 2, cap.T3_SMALL_SEARCH.type)
    expected_value = cap.MasterNodesPlan(3, "m5.large.search")
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

    # TEST: Large data w/ lots of data nodes
    actual_value = cap._get_master_node_plan(1250000, 130, "blah")
    expected_value = cap.MasterNodesPlan(3, "r6g.4xlarge.search")
    assert expected_value == actual_value

    # TEST: Enormous data w/ lots of data nodes
    actual_value = cap._get_master_node_plan(3010000, 120, "blah")
    expected_value = cap.MasterNodesPlan(3, "r6g.4xlarge.search")
    assert expected_value == actual_value

def test_WHEN_get_os_domain_plan_called_THEN_as_expected():
    actual_value = cap.get_os_domain_plan(20, 30, 1, 2)
    expected_value = cap.OSDomainPlan(
        cap.DataNodesPlan(64, cap.R6G_4XLARGE_SEARCH.type, cap.R6G_4XLARGE_SEARCH.vol_size),
        cap.MasterNodesPlan(3, "r6g.2xlarge.search")
    )
    assert expected_value == actual_value

def test_WHEN_UsageReport_get_report_THEN_as_expected():
    # Set up the test
    prev_plan = cap.ClusterPlan(
        cap.CaptureNodesPlan(None, None, None, None),
        cap.CaptureVpcPlan(None),
        cap.EcsSysResourcePlan(None, None),
        cap.OSDomainPlan(cap.DataNodesPlan(None, None, None), cap.MasterNodesPlan(None, None)),
        cap.S3Plan(None, None)
    )
    next_plan = cap.ClusterPlan(
        cap.CaptureNodesPlan(cap.INSTANCE_TYPE_CAPTURE_NODE, 1, 2, 1),
        cap.CaptureVpcPlan(1),
        cap.EcsSysResourcePlan(1, 1),
        cap.OSDomainPlan(cap.DataNodesPlan(2, "t3.small.search", 100), cap.MasterNodesPlan(3, "m6g.large.search")),
        cap.S3Plan(cap.DEFAULT_S3_STORAGE_CLASS, 30)
    )

    # Run the test
    actual_report = cap.UsageReport(prev_plan, next_plan).get_report()

    # Check the results
    expected_report = (
        "Capture Nodes:\n"
        + "    Max Count: None -> 2\n"
        + "    Desired Count: None -> 1\n"
        + "    Min Count: None -> 1\n"
        + f"    Type: None -> {cap.INSTANCE_TYPE_CAPTURE_NODE}\n"
        + "OpenSearch Domain:\n"
        + "    Master Node Count: None -> 3\n"
        + "    Master Node Type: None -> m6g.large.search\n"
        + "    Data Node Count: None -> 2\n"
        + "    Data Node Type: None -> t3.small.search\n"
        + "    Data Node Volume Size [GB]: None -> 100\n"
        + "S3 PCAP:\n"
        + "    Retention Period [days]: None -> 30\n"                       
    )

    assert expected_report == actual_report

@mock.patch('core.capacity_planning.shell')
def test_WHEN_UsageReport_get_confirmation_AND_yes_THEN_as_expected(mock_shell):
    # Set up the test
    prev_plan = cap.ClusterPlan(
        cap.CaptureNodesPlan(None, None, None, None),
        cap.CaptureVpcPlan(None),
        cap.EcsSysResourcePlan(None, None),
        cap.OSDomainPlan(cap.DataNodesPlan(None, None, None), cap.MasterNodesPlan(None, None)),
        cap.S3Plan(None, None)
    )
    next_plan = cap.ClusterPlan(
        cap.CaptureNodesPlan(cap.INSTANCE_TYPE_CAPTURE_NODE, 1, 2, 1),
        cap.CaptureVpcPlan(1),
        cap.EcsSysResourcePlan(1, 1),
        cap.OSDomainPlan(cap.DataNodesPlan(2, "t3.small.search", 100), cap.MasterNodesPlan(3, "m6g.large.search")),
        cap.S3Plan(cap.DEFAULT_S3_STORAGE_CLASS, 30)
    )

    mock_input = mock_shell.louder_input
    mock_input.return_value = "yes"

    # Run the test
    actual_value = cap.UsageReport(prev_plan, next_plan).get_confirmation()

    # Check the results
    expected_value = True
    assert expected_value == actual_value

@mock.patch('core.capacity_planning.shell')
def test_WHEN_UsageReport_get_confirmation_AND_no_THEN_as_expected(mock_shell):
    # Set up the test
    prev_plan = cap.ClusterPlan(
        cap.CaptureNodesPlan(None, None, None, None),
        cap.CaptureVpcPlan(None),
        cap.EcsSysResourcePlan(None, None),
        cap.OSDomainPlan(cap.DataNodesPlan(None, None, None), cap.MasterNodesPlan(None, None)),
        cap.S3Plan(None, None)
    )
    next_plan = cap.ClusterPlan(
        cap.CaptureNodesPlan(cap.INSTANCE_TYPE_CAPTURE_NODE, 1, 2, 1),
        cap.CaptureVpcPlan(1),
        cap.EcsSysResourcePlan(1, 1),
        cap.OSDomainPlan(cap.DataNodesPlan(2, "t3.small.search", 100), cap.MasterNodesPlan(3, "m6g.large.search")),
        cap.S3Plan(cap.DEFAULT_S3_STORAGE_CLASS, 30)
    )

    mock_input = mock_shell.louder_input
    mock_input.return_value = "no"

    # Run the test
    actual_value = cap.UsageReport(prev_plan, next_plan).get_confirmation()

    # Check the results
    expected_value = False
    assert expected_value == actual_value

    