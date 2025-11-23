# Cloud-Agnostic Migration Guide

**Version:** 1.0
**Last Updated:** November 2025
**Parent Doc:** [../06-job-execution.md](../06-job-execution.md)

---

## Overview

This guide provides migration paths from GCP Cloud Run Jobs to equivalent services on other cloud providers.

**Why cloud-agnostic?**
- Avoid vendor lock-in
- Support multi-cloud deployments
- Enable cost optimization across providers
- Future-proof architecture

**Abstraction guarantees:**
- Same `JobExecutor` interface works across all clouds
- Application code remains unchanged
- Only configuration changes required

---

## Provider Comparison

| Feature | GCP Cloud Run Jobs | AWS Batch | Azure Batch | Kubernetes Jobs |
|---------|-------------------|-----------|-------------|-----------------|
| **Max Duration** | 24h | Unlimited | Unlimited | Unlimited |
| **Pricing Model** | Per-second billing | Per-second (Fargate) | Per-minute | Infrastructure cost only |
| **Managed Service** | ✅ Fully managed | ⚠️ Semi-managed | ⚠️ Semi-managed | ❌ Self-managed |
| **Job Queuing** | Built-in | Built-in | Built-in | Manual |
| **Retry Logic** | Built-in | Built-in | Built-in | Manual |
| **Spot/Preemptible** | ⚠️ Coming soon | ✅ Spot instances | ✅ Low-priority | ✅ Spot nodes |
| **Portability** | ⚠️ GCP-only | ⚠️ AWS-only | ⚠️ Azure-only | ✅ Multi-cloud |

---

## Migration Path 1: GCP → AWS Batch

### AWS Batch Overview

**Architecture:**
```
EventBridge (Scheduler) → Lambda (trigger) → AWS Batch → ECS Fargate
```

**Equivalent Services:**
- GCP Cloud Run Jobs → AWS Batch (managed job execution)
- GCP Cloud Scheduler → AWS EventBridge Rules
- GCP Container Registry → AWS ECR (Elastic Container Registry)

---

### Implementation

**File:** `src/jobs/aws/batch.py`

```python
from typing import Callable, Optional
import boto3
import uuid
import logging

from ..interface import JobExecutor, JobResult, JobStatus

logger = logging.getLogger(__name__)


class AWSBatchExecutor(JobExecutor):
    """
    AWS Batch implementation of JobExecutor.

    Uses AWS Batch for job execution on ECS Fargate.
    """

    def __init__(
        self,
        job_queue: str,
        job_definition: str,
        region: str = "us-east-1"
    ):
        self.job_queue = job_queue
        self.job_definition = job_definition
        self.region = region

        self.client = boto3.client('batch', region_name=region)

    async def submit(
        self,
        job_name: str,
        handler: Callable,
        **kwargs
    ) -> str:
        """Submit job to AWS Batch."""
        job_id = f"{job_name}-{uuid.uuid4().hex[:8]}"

        # Serialize handler
        job_config = self._serialize_handler(handler, kwargs)

        # Submit to Batch
        response = self.client.submit_job(
            jobName=job_id,
            jobQueue=self.job_queue,
            jobDefinition=self.job_definition,
            containerOverrides={
                'environment': [
                    {'name': 'JOB_CONFIG', 'value': job_config}
                ],
                'resourceRequirements': [
                    {'type': 'VCPU', 'value': str(kwargs.get('cpu', 2))},
                    {'type': 'MEMORY', 'value': str(self._parse_memory(kwargs.get('memory', '4Gi')))}
                ]
            },
            retryStrategy={
                'attempts': kwargs.get('max_retries', 3)
            },
            timeout={
                'attemptDurationSeconds': kwargs.get('timeout', 3600)
            }
        )

        aws_job_id = response['jobId']
        logger.info(f"Submitted AWS Batch job: {aws_job_id}")

        return aws_job_id

    async def get_status(self, job_id: str) -> JobResult:
        """Get job status from AWS Batch."""
        response = self.client.describe_jobs(jobs=[job_id])

        if not response['jobs']:
            return JobResult(
                job_id=job_id,
                status=JobStatus.FAILED,
                started_at=None,
                completed_at=None,
                error="Job not found"
            )

        job = response['jobs'][0]

        # Map AWS status to JobStatus
        status = self._map_status(job['status'])

        return JobResult(
            job_id=job_id,
            status=status,
            started_at=job.get('startedAt'),
            completed_at=job.get('stoppedAt'),
            error=job.get('statusReason') if status == JobStatus.FAILED else None,
            attempts=job.get('attempts', 1)
        )

    async def cancel(self, job_id: str) -> bool:
        """Cancel AWS Batch job."""
        try:
            self.client.terminate_job(
                jobId=job_id,
                reason="User cancelled"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False

    async def wait(
        self,
        job_id: str,
        timeout: Optional[int] = None,
        poll_interval: int = 5
    ) -> JobResult:
        """Poll until completion (same as GCP implementation)."""
        # ... same polling logic as CloudRunJobsExecutor ...

    # Helper methods

    def _map_status(self, aws_status: str) -> JobStatus:
        """Map AWS Batch status to JobStatus."""
        mapping = {
            'SUBMITTED': JobStatus.PENDING,
            'PENDING': JobStatus.PENDING,
            'RUNNABLE': JobStatus.PENDING,
            'STARTING': JobStatus.RUNNING,
            'RUNNING': JobStatus.RUNNING,
            'SUCCEEDED': JobStatus.SUCCEEDED,
            'FAILED': JobStatus.FAILED,
        }
        return mapping.get(aws_status, JobStatus.RUNNING)

    def _parse_memory(self, memory_str: str) -> int:
        """Convert '4Gi' to MB for AWS."""
        if memory_str.endswith('Gi'):
            return int(memory_str[:-2]) * 1024
        elif memory_str.endswith('Mi'):
            return int(memory_str[:-2])
        else:
            return int(memory_str)

    def _serialize_handler(self, handler: Callable, kwargs: dict) -> str:
        """Same as GCP implementation."""
        # ... same cloudpickle serialization ...
```

---

### AWS Infrastructure Setup

**1. Create ECR Repository:**
```bash
aws ecr create-repository --repository-name bandicoot-jobs --region us-east-1
```

**2. Create Batch Compute Environment:**
```bash
aws batch create-compute-environment \
  --compute-environment-name bandicoot-compute \
  --type MANAGED \
  --state ENABLED \
  --compute-resources type=FARGATE,maxvCpus=16
```

**3. Create Job Queue:**
```bash
aws batch create-job-queue \
  --job-queue-name bandicoot-queue \
  --state ENABLED \
  --priority 1 \
  --compute-environment-order order=1,computeEnvironment=bandicoot-compute
```

**4. Create Job Definition:**
```bash
aws batch register-job-definition \
  --job-definition-name bandicoot-training \
  --type container \
  --platform-capabilities FARGATE \
  --container-properties '{
    "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/bandicoot-jobs:latest",
    "executionRoleArn": "arn:aws:iam::123456789:role/ecsTaskExecutionRole",
    "resourceRequirements": [
      {"type": "VCPU", "value": "2"},
      {"type": "MEMORY", "value": "4096"}
    ]
  }'
```

---

### Configuration Update

**Before (GCP):**
```bash
JOB_EXECUTOR_BACKEND=gcp_cloudrun
GCP_PROJECT_ID=bandicoot-prod
GCP_REGION=us-central1
```

**After (AWS):**
```bash
JOB_EXECUTOR_BACKEND=aws_batch
AWS_BATCH_JOB_QUEUE=bandicoot-queue
AWS_BATCH_JOB_DEFINITION=bandicoot-training
AWS_REGION=us-east-1
```

**No application code changes required!**

---

## Migration Path 2: GCP → Azure Batch

### Azure Batch Overview

**Architecture:**
```
Azure Logic Apps (Scheduler) → Azure Batch → Container Instances
```

**Equivalent Services:**
- GCP Cloud Run Jobs → Azure Batch (managed job execution)
- GCP Cloud Scheduler → Azure Logic Apps
- GCP Container Registry → Azure Container Registry (ACR)

---

### Implementation

**File:** `src/jobs/azure/batch.py`

```python
from typing import Callable, Optional
from azure.batch import BatchServiceClient
from azure.batch.models import JobAddParameter, PoolInformation, TaskAddParameter
from azure.common.credentials import ServicePrincipalCredentials
import uuid
import logging

from ..interface import JobExecutor, JobResult, JobStatus

logger = logging.getLogger(__name__)


class AzureBatchExecutor(JobExecutor):
    """
    Azure Batch implementation of JobExecutor.

    Uses Azure Batch for job execution.
    """

    def __init__(
        self,
        batch_account_url: str,
        pool_id: str,
        credentials: ServicePrincipalCredentials
    ):
        self.pool_id = pool_id
        self.client = BatchServiceClient(credentials, batch_account_url)

    async def submit(
        self,
        job_name: str,
        handler: Callable,
        **kwargs
    ) -> str:
        """Submit job to Azure Batch."""
        job_id = f"{job_name}-{uuid.uuid4().hex[:8]}"

        # Create job
        job = JobAddParameter(
            id=job_id,
            pool_info=PoolInformation(pool_id=self.pool_id)
        )
        self.client.job.add(job)

        # Serialize handler
        job_config = self._serialize_handler(handler, kwargs)

        # Create task
        task = TaskAddParameter(
            id=f"{job_id}-task",
            command_line=f"python -m src.jobs.runner",
            environment_settings=[
                {'name': 'JOB_CONFIG', 'value': job_config}
            ],
            resource_files=[],
            user_identity={'auto_user': {'scope': 'pool', 'elevation_level': 'nonadmin'}}
        )

        self.client.task.add(job_id=job_id, task=task)

        logger.info(f"Submitted Azure Batch job: {job_id}")
        return job_id

    async def get_status(self, job_id: str) -> JobResult:
        """Get job status from Azure Batch."""
        task_id = f"{job_id}-task"

        try:
            task = self.client.task.get(job_id, task_id)
            status = self._map_status(task.state)

            return JobResult(
                job_id=job_id,
                status=status,
                started_at=task.execution_info.start_time if task.execution_info else None,
                completed_at=task.execution_info.end_time if task.execution_info else None,
                error=task.execution_info.failure_info.message if status == JobStatus.FAILED else None,
                attempts=task.execution_info.retry_count if task.execution_info else 1
            )
        except Exception as e:
            logger.error(f"Failed to get status for {job_id}: {e}")
            return JobResult(
                job_id=job_id,
                status=JobStatus.FAILED,
                started_at=None,
                completed_at=None,
                error=str(e)
            )

    async def cancel(self, job_id: str) -> bool:
        """Cancel Azure Batch job."""
        try:
            self.client.job.terminate(job_id, terminate_reason="User cancelled")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False

    # ... wait() and helper methods similar to AWS/GCP ...
```

---

## Migration Path 3: Any Cloud → Kubernetes Jobs

### Why Kubernetes?

**Benefits:**
- ✅ Runs on any cloud (GCP GKE, AWS EKS, Azure AKS)
- ✅ Can run on-premises
- ✅ True multi-cloud portability
- ✅ Open-source (no vendor lock-in)

**Drawbacks:**
- ❌ More operational complexity (need to manage cluster)
- ❌ Manual setup for retry, monitoring
- ❌ No built-in job queue (need to add tools like Argo)

---

### Implementation

**File:** `src/jobs/kubernetes/jobs.py`

```python
from typing import Callable, Optional
from kubernetes import client, config
import uuid
import logging

from ..interface import JobExecutor, JobResult, JobStatus

logger = logging.getLogger(__name__)


class KubernetesJobExecutor(JobExecutor):
    """
    Kubernetes Jobs implementation (cloud-agnostic).

    Works on GKE, EKS, AKS, or any Kubernetes cluster.
    """

    def __init__(self, namespace: str = "default", image: str = None):
        self.namespace = namespace
        self.image = image or "bandicoot-jobs:latest"

        # Load kube config (in-cluster or from ~/.kube/config)
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()

        self.batch_api = client.BatchV1Api()

    async def submit(
        self,
        job_name: str,
        handler: Callable,
        **kwargs
    ) -> str:
        """Submit Kubernetes Job."""
        job_id = f"{job_name}-{uuid.uuid4().hex[:8]}"

        # Serialize handler
        job_config = self._serialize_handler(handler, kwargs)

        # Create job spec
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(name=job_id),
            spec=client.V1JobSpec(
                template=client.V1PodTemplateSpec(
                    spec=client.V1PodSpec(
                        containers=[client.V1Container(
                            name="job",
                            image=self.image,
                            command=["python", "-m", "src.jobs.runner"],
                            env=[
                                client.V1EnvVar(name="JOB_CONFIG", value=job_config)
                            ],
                            resources=client.V1ResourceRequirements(
                                requests={
                                    "cpu": kwargs.get("cpu", "2"),
                                    "memory": kwargs.get("memory", "4Gi")
                                }
                            )
                        )],
                        restart_policy="Never"
                    )
                ),
                backoff_limit=kwargs.get("max_retries", 3)
            )
        )

        # Create job
        self.batch_api.create_namespaced_job(
            namespace=self.namespace,
            body=job
        )

        logger.info(f"Created Kubernetes job: {job_id}")
        return job_id

    async def get_status(self, job_id: str) -> JobResult:
        """Get Kubernetes job status."""
        job = self.batch_api.read_namespaced_job_status(
            name=job_id,
            namespace=self.namespace
        )

        status = self._map_status(job.status)

        return JobResult(
            job_id=job_id,
            status=status,
            started_at=job.status.start_time,
            completed_at=job.status.completion_time,
            error=job.status.conditions[0].message if status == JobStatus.FAILED else None,
            attempts=job.status.failed or 1
        )

    async def cancel(self, job_id: str) -> bool:
        """Delete Kubernetes job."""
        try:
            self.batch_api.delete_namespaced_job(
                name=job_id,
                namespace=self.namespace,
                propagation_policy='Background'
            )
            return True
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False

    # ... wait() and helper methods ...
```

---

## Decision Matrix: When to Migrate?

| Scenario | Recommended Backend |
|----------|-------------------|
| **Startup on GCP** | Cloud Run Jobs (simplest) |
| **Startup on AWS** | AWS Batch (native integration) |
| **Startup on Azure** | Azure Batch |
| **Multi-cloud from day 1** | Kubernetes Jobs |
| **Migrating GCP → AWS** | AWS Batch (managed) or Kubernetes (portable) |
| **Cost optimization** | Spot instances (AWS Batch or Kubernetes) |
| **On-premises requirement** | Kubernetes Jobs (only option) |

---

## Cost Comparison

### Weekly Training Job (30 min, 2 vCPU, 4GB)

| Provider | Service | Monthly Cost |
|----------|---------|--------------|
| **GCP** | Cloud Run Jobs | $0.42 |
| **AWS** | Batch (Fargate) | $0.53 |
| **AWS** | Batch (EC2 Spot) | $0.15 |
| **Azure** | Batch | $0.48 |
| **Kubernetes (GKE)** | Jobs on Standard node | $0.60 |
| **Kubernetes (GKE)** | Jobs on Spot node | $0.18 |

**Winner:** AWS Batch with Spot instances ($0.15/month)

**But:** GCP Cloud Run Jobs has better DX (developer experience) and observability.

---

## Migration Checklist

### Before Migration

- [ ] Confirm `JobExecutor` interface is stable
- [ ] All jobs use factory pattern (no direct GCP imports)
- [ ] Integration tests pass with mock executor
- [ ] Document current GCP costs for baseline

### During Migration

- [ ] Implement new backend (AWS/Azure/K8s)
- [ ] Test with synthetic job in new environment
- [ ] Compare costs (actual vs estimated)
- [ ] Set up monitoring and alerts
- [ ] Run A/B test (10% traffic to new backend)

### After Migration

- [ ] Monitor job success rate for 1 week
- [ ] Compare costs (GCP vs new provider)
- [ ] Update documentation
- [ ] Decommission old infrastructure

---

## Next Steps

- **GCP implementation:** [gcp-cloudrun-jobs.md](./gcp-cloudrun-jobs.md)
- **Testing guide:** [testing.md](./testing.md)
- **Back to design:** [../06-job-execution.md](../06-job-execution.md)

---

**Author:** Bandicoot Team
**Status:** Migration Guide
