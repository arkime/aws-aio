
import unittest.mock as mock

import core.capacity_planning as cap
from core.usage_report import UsageReport
from core.user_config import UserConfig

INSTANCE_TYPE_CAPTURE_NODE = "m5.xlarge"

def test_WHEN_UsageReport_get_report_THEN_as_expected():
    # Set up the test
    prev_plan = cap.ClusterPlan(
        cap.CaptureNodesPlan(None, None, None, None),
        cap.VpcPlan(None, None, None),
        cap.EcsSysResourcePlan(None, None),
        cap.OSDomainPlan(cap.DataNodesPlan(None, None, None), cap.MasterNodesPlan(None, "m6g.before.search")),
        cap.S3Plan(None, None),
        cap.ViewerNodesPlan(None, None),
        None
    )
    next_plan = cap.ClusterPlan(
        cap.CaptureNodesPlan(INSTANCE_TYPE_CAPTURE_NODE, 1, 2, 1),
        cap.VpcPlan(cap.DEFAULT_VPC_CIDR, 1, cap.DEFAULT_CAPTURE_PUBLIC_MASK),
        cap.EcsSysResourcePlan(1, 1),
        cap.OSDomainPlan(cap.DataNodesPlan(2, "t3.small.search", 100), cap.MasterNodesPlan(3, "m6g.large.search")),
        cap.S3Plan(cap.DEFAULT_S3_STORAGE_CLASS, 30),
        cap.ViewerNodesPlan(5, 3),
        None
    )
    prev_config = UserConfig(0.1, 10, None, None, None)
    next_config = UserConfig(0.5, 30, 365, 1, 120)

    # Run the test
    actual_report = UsageReport(prev_plan, next_plan, prev_config, next_config).get_report()

    # Check the results
    expected_report = (
        "Arkime Metadata:\n"
        + f"    Session Retention [days]: \033[1m10 -> 30\033[0m\n"
        + f"    User History Retention [days]: 365\n"
        + "Capture Nodes:\n"
        + "    Max Count: 2\n"
        + "    Desired Count: 1\n"
        + "    Min Count: 1\n"
        + f"    Type: {INSTANCE_TYPE_CAPTURE_NODE}\n"
        + "Viewer Nodes:\n"
        + "    Max Count: 5\n"
        + "    Min Count: 3\n"
        + "OpenSearch Domain:\n"
        + "    Master Node Count: 3\n"
        + "    Master Node Type: \033[1mm6g.before.search -> m6g.large.search\033[0m\n"
        + "    Data Node Count: 2\n"
        + "    Data Node Type: t3.small.search\n"
        + "    Data Node Volume Size [GB]: 100\n"
        + "S3:\n"
        + "    PCAP Retention [days]: 30\n"
    )

    assert expected_report == actual_report

@mock.patch('core.usage_report.shell')
def test_WHEN_UsageReport_get_confirmation_AND_yes_THEN_as_expected(mock_shell):
    # Set up the test
    prev_plan = cap.ClusterPlan(
        cap.CaptureNodesPlan(None, None, None, None),
        cap.VpcPlan(None, None, None),
        cap.EcsSysResourcePlan(None, None),
        cap.OSDomainPlan(cap.DataNodesPlan(None, None, None), cap.MasterNodesPlan(None, None)),
        cap.S3Plan(None, None),
        cap.ViewerNodesPlan(None, None),
        None
    )
    next_plan = cap.ClusterPlan(
        cap.CaptureNodesPlan(INSTANCE_TYPE_CAPTURE_NODE, 1, 2, 1),
        cap.VpcPlan(cap.DEFAULT_VPC_CIDR, 1, cap.DEFAULT_CAPTURE_PUBLIC_MASK),
        cap.EcsSysResourcePlan(1, 1),
        cap.OSDomainPlan(cap.DataNodesPlan(2, "t3.small.search", 100), cap.MasterNodesPlan(3, "m6g.large.search")),
        cap.S3Plan(cap.DEFAULT_S3_STORAGE_CLASS, 30),
        cap.ViewerNodesPlan(4, 2),
        None
    )
    prev_config = UserConfig(None, None, None, None, None)
    next_config = UserConfig(0.5, 30, 365, 1, 120)

    mock_input = mock_shell.louder_input
    mock_input.return_value = "yes"

    # Run the test
    actual_value = UsageReport(prev_plan, next_plan, prev_config, next_config).get_confirmation()

    # Check the results
    expected_value = True
    assert expected_value == actual_value

@mock.patch('core.usage_report.shell')
def test_WHEN_UsageReport_get_confirmation_AND_no_THEN_as_expected(mock_shell):
    # Set up the test
    prev_plan = cap.ClusterPlan(
        cap.CaptureNodesPlan(None, None, None, None),
        cap.VpcPlan(None, None, None),
        cap.EcsSysResourcePlan(None, None),
        cap.OSDomainPlan(cap.DataNodesPlan(None, None, None), cap.MasterNodesPlan(None, None)),
        cap.S3Plan(None, None),
        cap.ViewerNodesPlan(None, None),
        None
    )
    next_plan = cap.ClusterPlan(
        cap.CaptureNodesPlan(INSTANCE_TYPE_CAPTURE_NODE, 1, 2, 1),
        cap.VpcPlan(cap.DEFAULT_VPC_CIDR, 1, cap.DEFAULT_CAPTURE_PUBLIC_MASK),
        cap.EcsSysResourcePlan(1, 1),
        cap.OSDomainPlan(cap.DataNodesPlan(2, "t3.small.search", 100), cap.MasterNodesPlan(3, "m6g.large.search")),
        cap.S3Plan(cap.DEFAULT_S3_STORAGE_CLASS, 30),
        cap.ViewerNodesPlan(4, 2),
        None
    )
    prev_config = UserConfig(None, None, None, None, None)
    next_config = UserConfig(0.5, 30, 365, 1, 120)

    mock_input = mock_shell.louder_input
    mock_input.return_value = "no"

    # Run the test
    actual_value = UsageReport(prev_plan, next_plan, prev_config, next_config).get_confirmation()

    # Check the results
    expected_value = False
    assert expected_value == actual_value
