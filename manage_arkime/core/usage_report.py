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

    def get_report(self) -> str:
        report_text = (
            "Arkime Metadata:\n"
            + f"    Session Retention [days]: {self.prev_config.spiDays} -> {self.next_config.spiDays}\n"
            + f"    User History Retention [days]: {self.prev_config.historyDays} -> {self.next_config.historyDays}\n"
            + "Capture Nodes:\n"
            + f"    Max Count: {self.prev_plan.captureNodes.maxCount} -> {self.next_plan.captureNodes.maxCount}\n"
            + f"    Desired Count: {self.prev_plan.captureNodes.desiredCount} -> {self.next_plan.captureNodes.desiredCount}\n"
            + f"    Min Count: {self.prev_plan.captureNodes.minCount} -> {self.next_plan.captureNodes.minCount}\n"
            + f"    Type: {self.prev_plan.captureNodes.instanceType} -> {self.next_plan.captureNodes.instanceType}\n"
            + "OpenSearch Domain:\n"
            + f"    Master Node Count: {self.prev_plan.osDomain.masterNodes.count} -> {self.next_plan.osDomain.masterNodes.count}\n"
            + f"    Master Node Type: {self.prev_plan.osDomain.masterNodes.instanceType} -> {self.next_plan.osDomain.masterNodes.instanceType}\n"
            + f"    Data Node Count: {self.prev_plan.osDomain.dataNodes.count} -> {self.next_plan.osDomain.dataNodes.count}\n"
            + f"    Data Node Type: {self.prev_plan.osDomain.dataNodes.instanceType} -> {self.next_plan.osDomain.dataNodes.instanceType}\n"
            + f"    Data Node Volume Size [GB]: {self.prev_plan.osDomain.dataNodes.volumeSize} -> {self.next_plan.osDomain.dataNodes.volumeSize}\n"
            + "S3:\n"
            + f"    PCAP Retention [days]: {self.prev_plan.s3.pcapStorageDays} -> {self.next_plan.s3.pcapStorageDays}\n"
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