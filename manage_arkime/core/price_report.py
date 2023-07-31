from core.capacity_planning import ClusterPlan
from core.user_config import UserConfig
from typing import Dict
from dataclasses import dataclass
import math

AWS_HOURS_PER_MONTH=730
AWS_SECS_PER_MONTH=60*60*AWS_HOURS_PER_MONTH

us_east_1_prices: Dict[str, float] = {
    "t3.small.search": 0.0360 * AWS_HOURS_PER_MONTH,
    "m5.large.search": 0.1420 * AWS_HOURS_PER_MONTH,
    "m6g.large.search": 0.1280  * AWS_HOURS_PER_MONTH,
    "c6g.2xlarge.search": 0.4520 * AWS_HOURS_PER_MONTH,
    "r6g.large.search": 0.1670 * AWS_HOURS_PER_MONTH,
    "r6g.2xlarge.search": 0.6690 * AWS_HOURS_PER_MONTH,
    "r6g.4xlarge.search": 1.3390 * AWS_HOURS_PER_MONTH,
    "r6g.12xlarge.search": 4.0160 * AWS_HOURS_PER_MONTH,
    "m5.xlarge": 0.1920 * AWS_HOURS_PER_MONTH,

    "s3-STANDARD-50-GB": 0.023, # https://aws.amazon.com/s3/pricing/
    "s3-STANDARD-450-GB": 0.022,
    "s3-STANDARD-REST-GB": 0.021,
    "ebs-GB": 0.10, # https://aws.amazon.com/ebs/pricing/
    "gwlb-GB": 0.004, # https://aws.amazon.com/elasticloadbalancing/pricing/?nc=sn&loc=3
    "gwlbe-GB": 0.0035, # https://aws.amazon.com/privatelink/pricing/

    "fargate": 0.04048 * AWS_HOURS_PER_MONTH, # https://aws.amazon.com/fargate/pricing/

    "trafficmirror": 0.015 * AWS_HOURS_PER_MONTH, # https://aws.amazon.com/vpc/pricing/
}


@dataclass
class PriceReport:
    plan: ClusterPlan
    config: UserConfig
    prices = us_east_1_prices # ALW - Not sure how to do type hint, was getting errors

    total: float = 0 # ALW - Not sure how to do a class variable that isn't passed in

    def _line(self, name: str, key: str, num: float) -> str:
        if key == "total":
            return f"   {name:23}                             ${self.total:10.2f}/mo\n"

        if num <= 0:
            return ""

        cost: float = self.prices[key]
        self.total += cost * num
        if key.endswith("-GB"):
            return f"   {name:23} {num:9,} * ${cost:9.4f}/GB = ${cost * num:10.2f}/mo\n"
        else:
            return f"   {name:23} {num:9,} * ${cost:9.4f}/mo = ${cost * num:10.2f}/mo\n"

    def get_report(self) -> str:
        expectedTraffic = self.config.expectedTraffic/8
        # Expect to only saving 25% of pcap because of TLS and zlib
        s3 = math.ceil(self.plan.s3.pcapStorageDays * expectedTraffic * 0.25 * 60 * 60 * 24)
        report_text = (
            "OnDemand us-east-1 cost estimate, your cost may be different based on region, discounts or reserve instances:\n"
            + "Fixed:\n"
            + self._line("Capture", self.plan.captureNodes.instanceType, self.plan.captureNodes.desiredCount)
            + self._line("Viewer", "fargate", 2) # ALW - Not sure where to get number of viewer nodes from
            + self._line("OS Master Node", self.plan.osDomain.masterNodes.instanceType, self.plan.osDomain.masterNodes.count)
            + self._line("OS Data Node", self.plan.osDomain.dataNodes.instanceType, self.plan.osDomain.dataNodes.count)
            + self._line("OS Storage", "ebs-GB", self.plan.osDomain.dataNodes.count*self.plan.osDomain.dataNodes.volumeSize)
            + "Variable:\n"
            + self._line("PCAP Storage first 50TB", "s3-STANDARD-50-GB", min(s3, 50000))
            + self._line("PCAP Storage next 450TB", "s3-STANDARD-450-GB", min(s3 - 50000, 450000))
            + self._line("PCAP Storage", "s3-STANDARD-REST-GB", s3 - 500000)
            + self._line("GWLB", "gwlb-GB", math.ceil(expectedTraffic * AWS_SECS_PER_MONTH))
            + self._line("GWLBE", "gwlbe-GB", math.ceil(expectedTraffic * AWS_SECS_PER_MONTH))
            + self._line("Traffic Mirror/ENI", "trafficmirror", 1)
            + "Total:\n"
            + self._line("", "total", 0)

        )
        return report_text