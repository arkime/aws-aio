import logging


from aws_interactions.aws_client_provider import AwsClientProvider

logger = logging.getLogger(__name__)


def force_ecs_deployment(cluster_id: str, service_id: str, aws_provider: AwsClientProvider):
    ecs_client = aws_provider.get_ecs()
    ecs_client.update_service(
        cluster=cluster_id,
        service=service_id,
        forceNewDeployment=True,
    )

def is_deployment_in_progress(cluster_id: str, service_id: str, aws_provider: AwsClientProvider):
    ecs_client = aws_provider.get_ecs()
    describe_response = ecs_client.describe_services(
        cluster=cluster_id,
        services=[service_id],
    )
    deployment_statuses = [dep["rolloutState"] for dep in describe_response["services"][0]["deployments"]]
    return "IN_PROGRESS" in deployment_statuses

def get_failed_task_count(cluster_id: str, service_id: str, aws_provider: AwsClientProvider):
    ecs_client = aws_provider.get_ecs()
    describe_response = ecs_client.describe_services(
        cluster=cluster_id,
        services=[service_id],
    )
    failed_task_counts = [dep["failedTasks"] for dep in describe_response["services"][0]["deployments"]]
    return sum(failed_task_counts)