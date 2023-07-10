
import unittest.mock as mock

import core.capacity_planning as cap
from core.usage_report import UsageReport
from core.user_config import UserConfig

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
    prev_config = UserConfig(None, None, None, None, None)
    next_config = UserConfig(0.5, 30, 365, 1, 120)

    # Run the test
    actual_report = UsageReport(prev_plan, next_plan, prev_config, next_config).get_report()

    # Check the results
    expected_report = (
        "Arkime Metadata:\n"
        + f"    Session Retention [days]: 30\n"
        + f"    User History Retention [days]: 365\n"
        + "Capture Nodes:\n"
        + "    Max Count: 2\n"
        + "    Desired Count: 1\n"
        + "    Min Count: 1\n"
        + f"    Type: {cap.INSTANCE_TYPE_CAPTURE_NODE}\n"
        + "OpenSearch Domain:\n"
        + "    Master Node Count: 3\n"
        + "    Master Node Type: m6g.large.search\n"
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
    prev_config = UserConfig(None, None, None, None, None)
    next_config = UserConfig(0.5, 30, 365, 1, 120)

    mock_input = mock_shell.louder_input
    mock_input.return_value = "no"

    # Run the test
    actual_value = UsageReport(prev_plan, next_plan, prev_config, next_config).get_confirmation()

    # Check the results
    expected_value = False
    assert expected_value == actual_value
