
import unittest.mock as mock

import core.capacity_planning as cap
from core.price_report import PriceReport
from core.user_config import UserConfig

INSTANCE_TYPE_CAPTURE_NODE = "m5.xlarge";

def test_WHEN_PriceReport_get_report_THEN_as_expected():
    # Set up the test
    plan = cap.ClusterPlan(
        cap.CaptureNodesPlan(INSTANCE_TYPE_CAPTURE_NODE, 1, 2, 1),
        cap.CaptureVpcPlan(cap.DEFAULT_VPC_CIDR, 1),
        cap.EcsSysResourcePlan(1, 1),
        cap.OSDomainPlan(cap.DataNodesPlan(2, "t3.small.search", 100), cap.MasterNodesPlan(3, "m6g.large.search")),
        cap.S3Plan(cap.DEFAULT_S3_STORAGE_CLASS, 30),
        cap.ViewerNodesPlan(5, 3),
    )
    config = UserConfig(0.5, 30, 365, 1, 120)

    # Run the test
    actual_report = PriceReport(plan, config).get_report()

    # Check the results
    expected_report = (
      "OnDemand us-east-1 cost estimate, your cost may be different based on region, discounts or reserve instances:\n"
      + "Allocated:\n"
      + "   Capture                         1 * $ 140.1600/mo = $    140.16/mo\n"
      + "   Viewer                          3 * $  29.5504/mo = $     88.65/mo\n"
      + "   OS Master Node                  3 * $  93.4400/mo = $    280.32/mo\n"
      + "   OS Data Node                    2 * $  26.2800/mo = $     52.56/mo\n"
      + "   OS Storage                    200 * $   0.1000/GB = $     20.00/mo\n"
      + "Variable:\n"
      + "   PCAP Storage first 50TB    40,500 * $   0.0230/GB = $    931.50/mo\n"
      + "   GWLB                      164,250 * $   0.0040/GB = $    657.00/mo\n"
      + "   GWLBE                     164,250 * $   0.0035/GB = $    574.88/mo\n"
      + "   Traffic Mirror/ENI              1 * $  10.9500/mo = $     10.95/mo\n"
      + "Total:\n"
      + "                                                       $   2756.02/mo\n"
    )

    assert expected_report == actual_report
