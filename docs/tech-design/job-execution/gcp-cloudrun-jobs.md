# GCP Cloud Run Jobs: Implementation Guide

**Version:** 1.0
**Last Updated:** November 2025
**Parent Doc:** [../06-job-execution.md](../06-job-execution.md)

---

## Overview

This document provides implementation details for the GCP Cloud Run Jobs backend.

**When to use:**
- Long-running batch jobs (up to 24 hours)
- Jobs requiring high CPU/memory (up to 8 vCPU, 32GB)
- Jobs that benefit from built-in status tracking

**Prerequisites:**
- GCP project with Cloud Run API enabled
- Service account with `run.jobs.create` permission
- Container image with job execution code

---

## Implementation

### 1. Executor Class

**File:** `src/jobs/gcp/cloudrun_jobs.py`

```python
from typing import Callable, Optional
from google.cloud import run_v2
from google.cloud.run_v2.types import Job, ExecutionTemplate, TaskTemplate
import uuid
import logging

from ..interface import JobExecutor, JobResult, JobStatus

logger = logging.getLogger(__name__)


class CloudRunJobsExecutor(JobExecutor):
    """
    GCP Cloud Run Jobs implementation.

    Delegates job execution to Google Cloud Run Jobs service.
    """

    def __init__(
        self,
        project_id: str,
        region: str = "us-central1",
        image_uri: str = None,
        service_account: str = None
    ):
        self.project_id = project_id
        self.region = region
        self.image_uri = image_uri or f"gcr.io/{project_id}/bandicoot-api"
        self.service_account = service_account

        self.client = run_v2.JobsClient()
        self.executions_client = run_v2.ExecutionsClient()

    async def submit(
        self,
        job_name: str,
        handler: Callable,
        **kwargs
    ) -> str:
        """
        Submit job to Cloud Run Jobs.

        Args:
            job_name: Human-readable job identifier
            handler: Function to execute
            **kwargs: Job configuration (cpu, memory, timeout, etc.)

        Returns:
            Execution name (used as job_id)
        """
        job_id = f"{job_name}-{uuid.uuid4().hex[:8]}"

        # Serialize handler
        job_config = self._serialize_handler(handler, kwargs)

        # Create job definition
        parent = f"projects/{self.project_id}/locations/{self.region}"
        job = self._build_job_spec(job_id, job_config, kwargs)

        # Create and execute
        try:
            operation = self.client.create_job(parent=parent, job=job, job_id=job_id)
            operation.result()  # Wait for job creation

            # Trigger execution
            execution = self.executions_client.run_job(name=job.name)

            logger.info(f"Submitted job {job_id}, execution: {execution.name}")
            return execution.name

        except Exception as e:
            logger.error(f"Failed to submit job {job_id}: {e}")
            raise

    async def get_status(self, job_id: str) -> JobResult:
        """Get execution status from Cloud Run."""
        try:
            execution = self.executions_client.get_execution(name=job_id)

            status = self._map_status(execution.completion_status)

            return JobResult(
                job_id=job_id,
                status=status,
                started_at=execution.start_time,
                completed_at=execution.completion_time,
                error=execution.status_message if status == JobStatus.FAILED else None,
                attempts=execution.task_count,
                metadata={"log_uri": execution.log_uri}
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
        """Cancel running execution."""
        try:
            self.executions_client.cancel_execution(name=job_id)
            logger.info(f"Cancelled job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel {job_id}: {e}")
            return False

    async def wait(
        self,
        job_id: str,
        timeout: Optional[int] = None,
        poll_interval: int = 5
    ) -> JobResult:
        """Poll until completion."""
        import asyncio
        from datetime import datetime

        start = datetime.now()

        while True:
            result = await self.get_status(job_id)

            if result.status in [JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED]:
                return result

            if timeout:
                elapsed = (datetime.now() - start).total_seconds()
                if elapsed > timeout:
                    raise TimeoutError(f"Job {job_id} exceeded timeout")

            await asyncio.sleep(poll_interval)

    # Helper methods

    def _build_job_spec(self, job_id: str, job_config: str, kwargs: dict) -> Job:
        """Build Cloud Run Job specification."""
        parent = f"projects/{self.project_id}/locations/{self.region}"

        return run_v2.Job(
            name=f"{parent}/jobs/{job_id}",
            template=ExecutionTemplate(
                template=TaskTemplate(
                    containers=[{
                        "image": self.image_uri,
                        "command": ["python", "-m", "src.jobs.runner"],
                        "env": [
                            {"name": "JOB_CONFIG", "value": job_config},
                        ],
                        "resources": {
                            "limits": {
                                "cpu": kwargs.get("cpu", "2"),
                                "memory": kwargs.get("memory", "4Gi")
                            }
                        }
                    }],
                    timeout=f"{kwargs.get('timeout', 3600)}s",
                    service_account=self.service_account,
                    max_retries=kwargs.get("max_retries", 3)
                )
            )
        )

    def _serialize_handler(self, handler: Callable, kwargs: dict) -> str:
        """Serialize function for container execution."""
        import json
        import base64
        import cloudpickle

        config = {
            "handler": base64.b64encode(cloudpickle.dumps(handler)).decode(),
            "kwargs": kwargs
        }
        return json.dumps(config)

    def _map_status(self, gcp_status: str) -> JobStatus:
        """Map GCP status to JobStatus enum."""
        mapping = {
            "PENDING": JobStatus.PENDING,
            "RUNNING": JobStatus.RUNNING,
            "SUCCEEDED": JobStatus.SUCCEEDED,
            "FAILED": JobStatus.FAILED,
            "CANCELLED": JobStatus.CANCELLED,
        }
        return mapping.get(gcp_status, JobStatus.RUNNING)
```

---

### 2. Job Runner (Container Entrypoint)

**File:** `src/jobs/runner.py`

```python
"""
Job runner executed inside Cloud Run Jobs container.

Deserializes job configuration and executes handler function.
"""

import os
import json
import base64
import cloudpickle
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """
    Main entrypoint for job execution.

    Reads JOB_CONFIG from environment, deserializes handler, and executes.
    """
    try:
        # Load job configuration
        job_config_str = os.getenv("JOB_CONFIG")
        if not job_config_str:
            raise ValueError("JOB_CONFIG environment variable not set")

        job_config = json.loads(job_config_str)

        # Deserialize handler
        handler_bytes = base64.b64decode(job_config["handler"])
        handler = cloudpickle.loads(handler_bytes)
        kwargs = job_config.get("kwargs", {})

        logger.info(f"Starting job execution: {handler.__name__}")

        # Execute handler
        result = handler(**kwargs)

        logger.info(f"Job completed successfully: {handler.__name__}")
        logger.info(f"Result: {result}")

        # Exit with success
        sys.exit(0)

    except Exception as e:
        logger.error(f"Job failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

### 3. Container Configuration

**File:** `Dockerfile` (add job runner support)

```dockerfile
# Existing API service stages...

# Add job runner stage
FROM base AS job-runner

# Install additional dependencies for job execution
RUN pip install cloudpickle

# Copy job execution code
COPY src/jobs /app/src/jobs
COPY src/training /app/src/training

# Set entrypoint for job runner
ENTRYPOINT ["python", "-m", "src.jobs.runner"]
```

**Build job image:**
```bash
docker build -t gcr.io/bandicoot-prod/bandicoot-jobs:latest .
docker push gcr.io/bandicoot-prod/bandicoot-jobs:latest
```

---

### 4. IAM Permissions

**Service Account:** `bandicoot-jobs@bandicoot-prod.iam.gserviceaccount.com`

**Required Roles:**
```yaml
roles:
  - run.jobs.create       # Create job definitions
  - run.jobs.run          # Execute jobs
  - run.executions.get    # Get execution status
  - run.executions.cancel # Cancel executions
  - logging.logWriter     # Write logs
  - storage.objectViewer  # Read job artifacts (if needed)
```

**Grant permissions:**
```bash
gcloud projects add-iam-policy-binding bandicoot-prod \
  --member="serviceAccount:bandicoot-jobs@bandicoot-prod.iam.gserviceaccount.com" \
  --role="roles/run.admin"
```

---

### 5. Configuration

**Environment Variables:**

```bash
# In Cloud Run API service

JOB_EXECUTOR_BACKEND=gcp_cloudrun
GCP_PROJECT_ID=bandicoot-prod
GCP_REGION=us-central1
JOB_IMAGE_URI=gcr.io/bandicoot-prod/bandicoot-jobs:latest
JOB_SERVICE_ACCOUNT=bandicoot-jobs@bandicoot-prod.iam.gserviceaccount.com
```

---

## Usage Examples

### Submit Weekly Training Job

```python
from src.jobs.factory import JobExecutorFactory
from src.training.pipeline import train_clusters

executor = JobExecutorFactory.create()  # Uses GCP Cloud Run Jobs

job_id = await executor.submit(
    job_name="weekly-training",
    handler=train_clusters,
    cpu="4",         # 4 vCPUs
    memory="8Gi",    # 8GB RAM
    timeout=3600,    # 60 minutes
    max_retries=2    # Retry twice on failure
)

print(f"Job submitted: {job_id}")
```

### Wait for Completion

```python
result = await executor.wait(job_id, timeout=3600)

if result.status == JobStatus.SUCCEEDED:
    print(f"Job completed: {result.result}")
else:
    print(f"Job failed: {result.error}")
```

### Check Status (Non-Blocking)

```python
result = await executor.get_status(job_id)
print(f"Status: {result.status.value}")
print(f"Started: {result.started_at}")
print(f"Log URI: {result.metadata['log_uri']}")
```

---

## Monitoring

### View Job Logs

```bash
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=weekly-training" \
  --limit 50 \
  --format json
```

### View Job Status

```bash
gcloud run jobs executions list \
  --job=weekly-training \
  --region=us-central1
```

### Metrics in Cloud Console

Navigate to: **Cloud Run → Jobs → weekly-training**

View:
- Execution history
- Duration histogram
- Success/failure rate
- Resource utilization (CPU, memory)

---

## Cost Optimization

### Right-Size Resources

```python
# For clustering (CPU-intensive)
job_id = await executor.submit(
    job_name="clustering",
    cpu="4",      # Use more CPUs
    memory="4Gi"  # Moderate memory
)

# For MDP learning (memory-intensive)
job_id = await executor.submit(
    job_name="mdp-learning",
    cpu="2",      # Fewer CPUs
    memory="8Gi"  # More memory
)
```

### Use Spot/Preemptible Instances (Future)

Cloud Run Jobs doesn't yet support preemptible instances, but this may be added in the future.

---

## Troubleshooting

### Job Fails Immediately

**Symptom:** Status goes from PENDING → FAILED in <5 seconds

**Cause:** Container startup error (missing dependencies, syntax error)

**Debug:**
```bash
gcloud logging read "resource.type=cloud_run_job" --limit 10
```

### Job Hangs (Never Completes)

**Symptom:** Status stuck in RUNNING for hours

**Cause:** Infinite loop, deadlock, or missing exit

**Debug:**
- Check logs for last message
- Add more logging to handler
- Set shorter timeout for testing

### Permission Denied

**Symptom:** `403 Forbidden` when submitting job

**Cause:** Service account lacks permissions

**Fix:**
```bash
gcloud projects add-iam-policy-binding bandicoot-prod \
  --member="serviceAccount:bandicoot-api@bandicoot-prod.iam.gserviceaccount.com" \
  --role="roles/run.admin"
```

---

## Next Steps

- **Implement alternative:** [GCP Cloud Tasks](./gcp-cloud-tasks.md)
- **Cloud-agnostic migration:** [cloud-agnostic.md](./cloud-agnostic.md)
- **Testing:** [testing.md](./testing.md)

---

**Author:** Bandicoot Team
**Status:** Implementation Guide
