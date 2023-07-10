import shell_interactions as shell
from core.capacity_planning import ClusterPlan
from core.user_config import UserConfig


from dataclasses import dataclass


@dataclass
class UsageReport:
    prev_plan: ClusterPlan
    next_plan: ClusterPlan
    prev_config: UserConfig
    next_config: UserConfig

    def _line(self, name: str, oldVal, newVal) -> str:
        if oldVal == None or oldVal == newVal:
            return f"    {name}: {newVal}\n"
        else:
            return f"    {name}: \033[1m{oldVal} -> {newVal}\033[0m\n"

    def get_report(self) -> str:
        report_text = (
            "Arkime Metadata:\n"
            + self._line("Session Retention [days]", self.prev_config.spiDays, self.next_config.spiDays)
            + self._line("User History Retention [days]", self.prev_config.historyDays, self.next_config.historyDays)
            + "Capture Nodes:\n"
            + self._line("Max Count", self.prev_plan.captureNodes.maxCount, self.next_plan.captureNodes.maxCount)
            + self._line("Desired Count", self.prev_plan.captureNodes.desiredCount, self.next_plan.captureNodes.desiredCount)
            + self._line("Min Count", self.prev_plan.captureNodes.minCount, self.next_plan.captureNodes.minCount)
            + self._line("Type", self.prev_plan.captureNodes.instanceType, self.next_plan.captureNodes.instanceType)
            + "OpenSearch Domain:\n"
            + self._line("Master Node Count", self.prev_plan.osDomain.masterNodes.count, self.next_plan.osDomain.masterNodes.count)
            + self._line("Master Node Type", self.prev_plan.osDomain.masterNodes.instanceType, self.next_plan.osDomain.masterNodes.instanceType)
            + self._line("Data Node Count", self.prev_plan.osDomain.dataNodes.count, self.next_plan.osDomain.dataNodes.count)
            + self._line("Data Node Type", self.prev_plan.osDomain.dataNodes.instanceType, self.next_plan.osDomain.dataNodes.instanceType)
            + self._line("Data Node Volume Size [GB]", self.prev_plan.osDomain.dataNodes.volumeSize, self.next_plan.osDomain.dataNodes.volumeSize)
            + "S3:\n"
            + self._line("PCAP Retention [days]", self.prev_plan.s3.pcapStorageDays, self.next_plan.s3.pcapStorageDays)
        )
        return report_text

    def get_confirmation(self) -> bool:
        confirm_prompt = (
            "Your settings will result in the follow AWS Resource usage:\n"
            + self.get_report()
            + "\n"
            + "Do you approve this usage (y/yes or n/no)? "
        )
        prompt_response = shell.louder_input(message=confirm_prompt, print_header=True)
        return prompt_response.strip().lower() in ["y", "yes"]
