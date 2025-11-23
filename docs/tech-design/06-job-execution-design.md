# Job Execution Design: Long-Running Tasks

**Version:** 1.0
**Last Updated:** November 2025
**Parent Doc:** [00-overview.md](00-overview.md)

---

## Problem Statement

Our system has several long-running batch jobs:

| Job | Duration | Frequency | Criticality |
|-----|----------|-----------|-------------|
| Weekly training (clustering + MDP learning) | ~30 min | Weekly | High |
| Whittle index computation | ~7 min | Weekly | High |
| Nightly state update | ~2 min | Daily | Medium |
| Historical data ingest (one-time) | ~10 min | Once | Low |

**Current Issues with Cloud Functions:**
- 60-minute timeout (can't extend for longer jobs)
- Polling pattern for job status is inefficient
- No built-in retry/failure handling
- Difficult to monitor long-running progress

**Requirements:**
1. Support jobs up to 60+ minutes
2. Reliable retry mechanism
3. Progress tracking and monitoring
4. Cost-effective (<$20/month for all jobs)
5. Easy to swap implementations (SOLID principles)

---

## Alternatives Comparison

### Option 1: Cloud Tasks

**How it works:**
```
Cloud Scheduler → Cloud Tasks Queue → Cloud Run (worker)
```

**Pros:**
- ✅ Built-in retry with exponential backoff
- ✅ Rate limiting and concurrency control
- ✅ Task deduplication (idempotency)
- ✅ Can route to Cloud Run (24-hour timeout) or HTTP endpoints
- ✅ Dead letter queue for failed tasks

**Cons:**
- ❌ No built-in progress tracking (need custom solution)
- ❌ Requires Cloud Run worker (always-on or cold start)
- ❌ Slightly more complex setup

**Cost:**
```
1M operations free/month
Beyond: $0.40 per million operations

Our usage:
- Weekly training: 4 tasks/month
- Nightly updates: 30 tasks/month
- Total: ~35 tasks/month

Cost: $0 (well within free tier)
```

**Timeout:**
- Cloud Tasks itself: No timeout
- Target Cloud Run: Up to 24 hours (configurable)

**Best for:** Reliable task queuing with retries

---

### Option 2: Cloud Run Jobs

**How it works:**
```
Cloud Scheduler → Cloud Run Jobs API → Ephemeral container
```

**Pros:**
- ✅ Purpose-built for batch jobs
- ✅ Up to 24-hour execution time
- ✅ Built-in job status tracking (running, succeeded, failed)
- ✅ Automatic logging and monitoring
- ✅ Container can have high CPU/memory (up to 8 vCPU, 32GB)
- ✅ Parallelism support (run multiple instances)
- ✅ No cold start (spins up fresh container each time)

**Cons:**
- ❌ More expensive than Cloud Functions for short jobs
- ❌ Requires separate container image (can share with API service)

**Cost:**
```
vCPU: $0.00002400 per vCPU-second
Memory: $0.00000250 per GiB-second

Weekly training (30 min, 2 vCPU, 4GB):
- vCPU: 1800s × 2 × $0.000024 = $0.086
- Memory: 1800s × 4 × $0.0000025 = $0.018
- Total per run: $0.104
- Monthly (4 runs): $0.42

Nightly updates (2 min, 1 vCPU, 2GB):
- Total per run: $0.007
- Monthly (30 runs): $0.21

Total: ~$0.63/month
```

**Timeout:**
- Up to 24 hours (configurable)

**Best for:** Long-running batch jobs with high resource needs

---

### Option 3: Cloud Workflows

**How it works:**
```
Cloud Scheduler → Cloud Workflows → Orchestrate multiple steps
```

**Pros:**
- ✅ Orchestrate complex multi-step pipelines
- ✅ Built-in retry and error handling
- ✅ Visual workflow editor
- ✅ Can call Cloud Run, Cloud Functions, HTTP APIs
- ✅ State machine with conditional logic
- ✅ Long-running (up to 1 year execution time)

**Cons:**
- ❌ Overkill for simple jobs
- ❌ Learning curve (YAML-based workflow definition)
- ❌ Each step still subject to timeout (but workflow continues)

**Cost:**
```
$0.01 per 1000 internal steps
2000 internal steps free/month

Our usage:
- Weekly training: ~10 steps (cluster → learn → compute indices)
- Monthly: 40 steps

Cost: $0 (within free tier)
```

**Best for:** Complex multi-step workflows with dependencies

---

### Option 4: Pub/Sub + Cloud Run

**How it works:**
```
Cloud Scheduler → Pub/Sub Topic → Cloud Run subscription
```

**Pros:**
- ✅ Decoupled architecture (publisher/subscriber)
- ✅ Multiple subscribers can process same event
- ✅ Built-in retry with dead letter topics
- ✅ At-least-once delivery guarantee
- ✅ Can scale to millions of messages

**Cons:**
- ❌ More complex than direct invocation
- ❌ Requires managing topics and subscriptions
- ❌ Overkill for scheduled batch jobs

**Cost:**
```
10GB message delivery free/month
Beyond: $40 per TB

Our usage: <1MB/month
Cost: $0
```

**Best for:** Event-driven architectures with multiple consumers

---

### Option 5: Direct Cloud Run (Long-Running)

**How it works:**
```
Cloud Scheduler → Cloud Run HTTP endpoint → Long-running job
```

**Pros:**
- ✅ Simplest architecture
- ✅ Reuse existing API service container
- ✅ No additional infrastructure
- ✅ Up to 60-minute timeout (request timeout) or background tasks

**Cons:**
- ❌ 60-minute request timeout (can use background tasks but no built-in retry)
- ❌ If container restarts, job is lost
- ❌ No job status tracking (need custom implementation)
- ❌ Holding HTTP connection open for 30 minutes is wasteful

**Cost:**
```
Same as Cloud Run service: ~$50/month (already budgeted)
```

**Best for:** Short jobs (<10 minutes) or when minimizing infrastructure

---

## Decision Matrix

| Criteria | Cloud Tasks | Cloud Run Jobs | Cloud Workflows | Pub/Sub | Direct Cloud Run |
|----------|-------------|----------------|-----------------|---------|------------------|
| **Max Duration** | 24h (via Cloud Run) | 24h | 1 year | 24h (via Cloud Run) | 60 min |
| **Retry Handling** | ✅ Built-in | ⚠️ Manual | ✅ Built-in | ✅ Built-in | ❌ Manual |
| **Progress Tracking** | ❌ Custom | ✅ Built-in | ✅ Built-in | ❌ Custom | ❌ Custom |
| **Cost (monthly)** | $0 | $0.63 | $0 | $0 | $0 (included) |
| **Complexity** | Medium | Low | High | Medium | Low |
| **Idempotency** | ✅ Built-in | ⚠️ Manual | ✅ Built-in | ⚠️ Manual | ❌ Manual |
| **Monitoring** | Good | Excellent | Excellent | Good | Basic |
| **Best Use Case** | Reliable queuing | Batch jobs | Multi-step workflows | Event-driven | Simple tasks |

---

## Recommendation

### For Bandicoot MVP: **Cloud Run Jobs**

**Rationale:**
1. **Purpose-built for batch processing** (training, index computation)
2. **Excellent monitoring** (built-in job status, logs, execution history)
3. **24-hour timeout** (future-proof if training grows beyond 60 min)
4. **Minimal cost** ($0.63/month, <1% of budget)
5. **Simple architecture** (no queues or workflows to manage)
6. **Parallelism support** (can speed up training by running clusters in parallel)

**When to use alternatives:**
- **Cloud Tasks:** If we need task queuing with strict ordering/rate limiting
- **Cloud Workflows:** If training pipeline becomes multi-step with dependencies
- **Pub/Sub:** If we add real-time event processing (SMS opens, vaccinations)
- **Direct Cloud Run:** For very short jobs (<5 minutes) like data validation

---

## SOLID Design: Job Execution Abstraction

### Interface Definition

```python
# src/jobs/interface.py

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class JobStatus(Enum):
    """Job execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class JobResult:
    """Result of a job execution"""
    job_id: str
    status: JobStatus
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    attempts: int = 1
    metadata: Optional[Dict[str, Any]] = None


class JobExecutor(ABC):
    """
    Abstract interface for job execution backends.

    Follows SOLID principles:
    - Single Responsibility: Only handles job execution
    - Open/Closed: Open for extension (new backends), closed for modification
    - Liskov Substitution: Any JobExecutor can replace another
    - Interface Segregation: Minimal interface (submit, status, cancel)
    - Dependency Inversion: Depend on abstraction, not concrete implementation
    """

    @abstractmethod
    async def submit(
        self,
        job_name: str,
        handler: Callable,
        *args,
        **kwargs
    ) -> str:
        """
        Submit a job for execution.

        Args:
            job_name: Human-readable job identifier
            handler: Function to execute (must be serializable)
            *args: Positional arguments for handler
            **kwargs: Keyword arguments for handler

        Returns:
            job_id: Unique identifier for tracking
        """
        pass

    @abstractmethod
    async def get_status(self, job_id: str) -> JobResult:
        """
        Get current status of a job.

        Args:
            job_id: Job identifier from submit()

        Returns:
            JobResult with current status
        """
        pass

    @abstractmethod
    async def cancel(self, job_id: str) -> bool:
        """
        Cancel a running job.

        Args:
            job_id: Job identifier

        Returns:
            True if cancelled, False if already completed/failed
        """
        pass

    @abstractmethod
    async def wait(
        self,
        job_id: str,
        timeout: Optional[int] = None,
        poll_interval: int = 5
    ) -> JobResult:
        """
        Block until job completes or timeout.

        Args:
            job_id: Job identifier
            timeout: Maximum seconds to wait (None = infinite)
            poll_interval: Seconds between status checks

        Returns:
            Final JobResult

        Raises:
            TimeoutError: If timeout exceeded
        """
        pass


class JobScheduler(ABC):
    """
    Abstract interface for job scheduling (cron-like).
    """

    @abstractmethod
    async def schedule(
        self,
        schedule: str,
        job_name: str,
        handler: Callable,
        *args,
        **kwargs
    ) -> str:
        """
        Schedule a recurring job.

        Args:
            schedule: Cron expression (e.g., "0 2 * * 0" for Sunday 2am)
            job_name: Unique job name
            handler: Function to execute
            *args, **kwargs: Arguments for handler

        Returns:
            schedule_id: Identifier for the schedule
        """
        pass

    @abstractmethod
    async def unschedule(self, schedule_id: str) -> bool:
        """Remove a scheduled job."""
        pass
```

---

### Implementation: Cloud Run Jobs Backend

```python
# src/jobs/cloudrun_jobs.py

import asyncio
import uuid
from datetime import datetime
from typing import Callable, Optional, Dict, Any
from google.cloud import run_v2
from google.cloud.run_v2.types import Job, ExecutionTemplate, TaskTemplate
import logging

from .interface import JobExecutor, JobResult, JobStatus

logger = logging.getLogger(__name__)


class CloudRunJobsExecutor(JobExecutor):
    """
    Cloud Run Jobs implementation of JobExecutor.

    Delegates actual execution to Google Cloud Run Jobs service.
    """

    def __init__(
        self,
        project_id: str,
        region: str = "us-central1",
        image_uri: str = None,
        service_account: str = None
    ):
        """
        Initialize Cloud Run Jobs executor.

        Args:
            project_id: GCP project ID
            region: GCP region (default: us-central1)
            image_uri: Container image (default: same as API service)
            service_account: Service account for job execution
        """
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
        *args,
        **kwargs
    ) -> str:
        """
        Submit job to Cloud Run Jobs.

        Creates a job definition and executes it immediately.
        """
        # Generate unique job ID
        job_id = f"{job_name}-{uuid.uuid4().hex[:8]}"

        # Serialize handler and arguments
        job_config = self._serialize_job(handler, args, kwargs)

        # Create Cloud Run Job definition
        parent = f"projects/{self.project_id}/locations/{self.region}"
        job = run_v2.Job(
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
                    timeout=kwargs.get("timeout", "3600s"),
                    service_account=self.service_account,
                    max_retries=kwargs.get("max_retries", 3)
                )
            )
        )

        try:
            # Create and execute job
            operation = self.client.create_job(parent=parent, job=job, job_id=job_id)
            operation.result()  # Wait for job creation

            # Trigger execution
            execution_name = f"{job.name}/executions/{uuid.uuid4().hex[:8]}"
            execution = self.executions_client.run_job(name=job.name)

            logger.info(f"Submitted job {job_id}, execution: {execution.name}")
            return execution.name

        except Exception as e:
            logger.error(f"Failed to submit job {job_id}: {e}")
            raise

    async def get_status(self, job_id: str) -> JobResult:
        """Get job execution status from Cloud Run."""
        try:
            execution = self.executions_client.get_execution(name=job_id)

            # Map Cloud Run status to JobStatus
            status_map = {
                "PENDING": JobStatus.PENDING,
                "RUNNING": JobStatus.RUNNING,
                "SUCCEEDED": JobStatus.SUCCEEDED,
                "FAILED": JobStatus.FAILED,
                "CANCELLED": JobStatus.CANCELLED,
            }

            status = status_map.get(
                execution.completion_status,
                JobStatus.RUNNING
            )

            return JobResult(
                job_id=job_id,
                status=status,
                started_at=execution.start_time,
                completed_at=execution.completion_time,
                error=execution.status_message if status == JobStatus.FAILED else None,
                attempts=execution.task_count,
                metadata={
                    "execution_name": execution.name,
                    "log_uri": execution.log_uri
                }
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
        """Cancel a running job execution."""
        try:
            self.executions_client.cancel_execution(name=job_id)
            logger.info(f"Cancelled job {job_id}")
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
        """Poll job status until completion."""
        start_time = datetime.now()

        while True:
            result = await self.get_status(job_id)

            # Check if completed
            if result.status in [
                JobStatus.SUCCEEDED,
                JobStatus.FAILED,
                JobStatus.CANCELLED
            ]:
                return result

            # Check timeout
            if timeout:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > timeout:
                    raise TimeoutError(f"Job {job_id} exceeded timeout of {timeout}s")

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    def _serialize_job(
        self,
        handler: Callable,
        args: tuple,
        kwargs: dict
    ) -> str:
        """
        Serialize job configuration for container execution.

        In production, use cloudpickle or JSON-serializable config.
        """
        import json
        import base64
        import cloudpickle

        config = {
            "handler": base64.b64encode(cloudpickle.dumps(handler)).decode(),
            "args": args,
            "kwargs": kwargs
        }

        return json.dumps(config)
```

---

### Implementation: Cloud Tasks Backend (Alternative)

```python
# src/jobs/cloud_tasks.py

import asyncio
import uuid
import json
from datetime import datetime, timedelta
from typing import Callable, Optional
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

from .interface import JobExecutor, JobResult, JobStatus

import logging
logger = logging.getLogger(__name__)


class CloudTasksExecutor(JobExecutor):
    """
    Cloud Tasks implementation with Cloud Run target.

    Good for reliable task queuing with retries.
    """

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        queue_name: str = "bandicoot-jobs",
        worker_url: str = None
    ):
        self.project_id = project_id
        self.location = location
        self.queue_name = queue_name
        self.worker_url = worker_url  # Cloud Run service URL

        self.client = tasks_v2.CloudTasksClient()
        self.queue_path = self.client.queue_path(project_id, location, queue_name)

        # In-memory job tracking (production: use Redis/Firestore)
        self._jobs: Dict[str, JobResult] = {}

    async def submit(
        self,
        job_name: str,
        handler: Callable,
        *args,
        **kwargs
    ) -> str:
        """Submit task to Cloud Tasks queue."""
        job_id = f"{job_name}-{uuid.uuid4().hex[:8]}"

        # Serialize job payload
        payload = {
            "job_id": job_id,
            "job_name": job_name,
            "handler_path": f"{handler.__module__}.{handler.__name__}",
            "args": args,
            "kwargs": kwargs
        }

        # Create task
        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": f"{self.worker_url}/jobs/execute",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(payload).encode(),
            },
            "retry_config": {
                "max_attempts": kwargs.get("max_retries", 3),
                "max_retry_duration": timedelta(hours=1),
                "min_backoff": timedelta(seconds=10),
                "max_backoff": timedelta(minutes=5),
            }
        }

        # Schedule task
        response = self.client.create_task(parent=self.queue_path, task=task)

        # Track job
        self._jobs[job_id] = JobResult(
            job_id=job_id,
            status=JobStatus.PENDING,
            started_at=None,
            completed_at=None,
            metadata={"task_name": response.name}
        )

        logger.info(f"Submitted task {response.name} for job {job_id}")
        return job_id

    async def get_status(self, job_id: str) -> JobResult:
        """Get job status (from tracking store)."""
        return self._jobs.get(
            job_id,
            JobResult(
                job_id=job_id,
                status=JobStatus.FAILED,
                started_at=None,
                completed_at=None,
                error="Job not found"
            )
        )

    async def cancel(self, job_id: str) -> bool:
        """Cancel pending task (if not started)."""
        if job_id not in self._jobs:
            return False

        job = self._jobs[job_id]
        if job.status != JobStatus.PENDING:
            return False  # Already running or completed

        task_name = job.metadata.get("task_name")
        if task_name:
            try:
                self.client.delete_task(name=task_name)
                job.status = JobStatus.CANCELLED
                return True
            except Exception as e:
                logger.error(f"Failed to cancel task {task_name}: {e}")

        return False

    async def wait(
        self,
        job_id: str,
        timeout: Optional[int] = None,
        poll_interval: int = 2
    ) -> JobResult:
        """Poll job status until completion."""
        start_time = datetime.now()

        while True:
            result = await self.get_status(job_id)

            if result.status in [JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED]:
                return result

            if timeout:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > timeout:
                    raise TimeoutError(f"Job {job_id} exceeded timeout")

            await asyncio.sleep(poll_interval)

    def update_job_status(self, job_id: str, status: JobStatus, **kwargs):
        """
        Update job status (called by worker endpoint).

        This method would be called by the Cloud Run worker
        when it starts/completes a job.
        """
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.status = status

            if status == JobStatus.RUNNING and not job.started_at:
                job.started_at = datetime.now()

            if status in [JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED]:
                job.completed_at = datetime.now()
                job.result = kwargs.get("result")
                job.error = kwargs.get("error")
```

---

### Factory Pattern for Executor Selection

```python
# src/jobs/factory.py

import os
from typing import Optional
from .interface import JobExecutor
from .cloudrun_jobs import CloudRunJobsExecutor
from .cloud_tasks import CloudTasksExecutor


class JobExecutorFactory:
    """
    Factory for creating job executors.

    Follows Dependency Inversion Principle:
    - Application depends on JobExecutor interface
    - Factory provides concrete implementation based on config
    """

    @staticmethod
    def create(backend: Optional[str] = None) -> JobExecutor:
        """
        Create job executor based on configuration.

        Args:
            backend: Override backend type (for testing)
                    Options: 'cloudrun_jobs', 'cloud_tasks', 'local'

        Returns:
            Configured JobExecutor instance
        """
        backend = backend or os.getenv("JOB_EXECUTOR_BACKEND", "cloudrun_jobs")
        project_id = os.getenv("GCP_PROJECT_ID")
        region = os.getenv("GCP_REGION", "us-central1")

        if backend == "cloudrun_jobs":
            return CloudRunJobsExecutor(
                project_id=project_id,
                region=region,
                service_account=os.getenv("JOB_SERVICE_ACCOUNT")
            )

        elif backend == "cloud_tasks":
            return CloudTasksExecutor(
                project_id=project_id,
                location=region,
                worker_url=os.getenv("WORKER_URL")
            )

        elif backend == "local":
            # For development/testing
            from .local import LocalJobExecutor
            return LocalJobExecutor()

        else:
            raise ValueError(f"Unknown job backend: {backend}")
```

---

### Usage Example

```python
# src/api/endpoints/training.py

from fastapi import APIRouter, BackgroundTasks
from src.jobs.factory import JobExecutorFactory
from src.training.pipeline import train_clusters, precompute_indices

router = APIRouter()


@router.post("/train_clusters")
async def trigger_training(background_tasks: BackgroundTasks):
    """
    Trigger weekly training pipeline.

    Uses JobExecutor abstraction - actual backend is configurable.
    """
    # Get executor (Cloud Run Jobs in production, local in dev)
    executor = JobExecutorFactory.create()

    # Submit training job
    job_id = await executor.submit(
        job_name="weekly-training",
        handler=train_clusters,
        cpu="4",  # 4 vCPUs for faster training
        memory="8Gi",
        timeout="3600s",  # 60 minutes
        max_retries=2
    )

    # Return immediately (don't block API request)
    return {
        "status": "submitted",
        "job_id": job_id,
        "message": "Training started. Check /jobs/{job_id} for status."
    }


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a running job."""
    executor = JobExecutorFactory.create()
    result = await executor.get_status(job_id)

    return {
        "job_id": result.job_id,
        "status": result.status.value,
        "started_at": result.started_at,
        "completed_at": result.completed_at,
        "error": result.error,
        "metadata": result.metadata
    }


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running job."""
    executor = JobExecutorFactory.create()
    cancelled = await executor.cancel(job_id)

    return {
        "job_id": job_id,
        "cancelled": cancelled
    }
```

---

### Orchestration Example (Multi-Step Workflow)

```python
# src/training/pipeline.py

from src.jobs.factory import JobExecutorFactory
from src.jobs.interface import JobStatus
import logging

logger = logging.getLogger(__name__)


async def run_weekly_training_pipeline():
    """
    Orchestrate multi-step training workflow.

    Steps:
    1. Cluster caregivers
    2. Learn MDP parameters per cluster
    3. Compute Whittle indices
    4. Train FO mapper
    """
    executor = JobExecutorFactory.create()

    # Step 1: Clustering
    logger.info("Starting clustering job...")
    cluster_job_id = await executor.submit(
        job_name="clustering",
        handler=cluster_caregivers,
        cpu="4",
        memory="8Gi"
    )

    # Wait for clustering to complete
    cluster_result = await executor.wait(cluster_job_id, timeout=1800)  # 30 min

    if cluster_result.status != JobStatus.SUCCEEDED:
        logger.error(f"Clustering failed: {cluster_result.error}")
        raise RuntimeError("Clustering failed")

    num_clusters = cluster_result.result["num_clusters"]
    logger.info(f"Clustering complete: {num_clusters} clusters")

    # Step 2: Learn MDP parameters (parallel for each cluster)
    logger.info("Starting MDP learning jobs...")
    mdp_job_ids = []

    for cluster_id in range(num_clusters):
        job_id = await executor.submit(
            job_name=f"mdp-learning-cluster-{cluster_id}",
            handler=learn_cluster_mdp,
            cluster_id=cluster_id
        )
        mdp_job_ids.append(job_id)

    # Wait for all MDP jobs to complete
    for job_id in mdp_job_ids:
        result = await executor.wait(job_id, timeout=600)  # 10 min
        if result.status != JobStatus.SUCCEEDED:
            logger.error(f"MDP learning failed for job {job_id}")
            raise RuntimeError("MDP learning failed")

    logger.info("All MDP learning complete")

    # Step 3: Compute Whittle indices
    logger.info("Starting Whittle index computation...")
    indices_job_id = await executor.submit(
        job_name="whittle-indices",
        handler=precompute_indices
    )

    indices_result = await executor.wait(indices_job_id, timeout=600)

    if indices_result.status != JobStatus.SUCCEEDED:
        logger.error("Whittle index computation failed")
        raise RuntimeError("Index computation failed")

    logger.info("Training pipeline complete!")

    return {
        "status": "success",
        "num_clusters": num_clusters,
        "model_version": indices_result.result["model_version"]
    }
```

---

## Testing Strategy

### Unit Tests (Mock Executor)

```python
# tests/test_jobs.py

import pytest
from src.jobs.interface import JobExecutor, JobResult, JobStatus
from unittest.mock import AsyncMock


class MockJobExecutor(JobExecutor):
    """Mock executor for testing."""

    async def submit(self, job_name, handler, *args, **kwargs):
        return f"mock-job-{job_name}"

    async def get_status(self, job_id):
        return JobResult(
            job_id=job_id,
            status=JobStatus.SUCCEEDED,
            started_at=None,
            completed_at=None
        )

    async def cancel(self, job_id):
        return True

    async def wait(self, job_id, timeout=None, poll_interval=1):
        return await self.get_status(job_id)


@pytest.mark.asyncio
async def test_training_pipeline_with_mock():
    """Test pipeline logic without actual GCP calls."""
    from src.training.pipeline import run_weekly_training_pipeline
    from src.jobs.factory import JobExecutorFactory

    # Inject mock executor
    JobExecutorFactory.create = lambda: MockJobExecutor()

    result = await run_weekly_training_pipeline()

    assert result["status"] == "success"
    assert "model_version" in result
```

---

## Migration Path

### Phase 1: Implement Abstraction (Week 1)
- ✅ Define `JobExecutor` interface
- ✅ Implement `CloudRunJobsExecutor`
- ✅ Create `JobExecutorFactory`
- ✅ Add unit tests with mock executor

### Phase 2: Deploy to Staging (Week 2)
- ✅ Build Cloud Run Jobs container image
- ✅ Set up IAM permissions
- ✅ Test weekly training job manually
- ✅ Verify monitoring and logging

### Phase 3: Production Rollout (Week 3)
- ✅ Switch `JOB_EXECUTOR_BACKEND=cloudrun_jobs` in production
- ✅ Monitor first weekly training run
- ✅ Compare costs vs Cloud Functions

### Phase 4: Optimize (Week 4+)
- ⚠️ Add parallelism for MDP learning (speed up by 5x)
- ⚠️ Implement `CloudTasksExecutor` as alternative
- ⚠️ Add progress tracking UI

---

## Summary

### Decision: **Cloud Run Jobs** with SOLID Abstraction

**Benefits:**
1. ✅ Purpose-built for long-running batch jobs
2. ✅ 24-hour timeout (future-proof)
3. ✅ Excellent monitoring and status tracking
4. ✅ Minimal cost increase ($0.63/month)
5. ✅ Easy to swap implementations via factory pattern

**SOLID Principles Applied:**
- **S**ingle Responsibility: `JobExecutor` only handles execution
- **O**pen/Closed: New backends (Cloud Workflows, Pub/Sub) can be added without modifying interface
- **L**iskov Substitution: Any `JobExecutor` can replace another
- **I**nterface Segregation: Minimal interface (submit, status, cancel, wait)
- **D**ependency Inversion: Application depends on `JobExecutor` abstraction, not concrete GCP services

**Next Steps:**
1. Implement `CloudRunJobsExecutor` (this week)
2. Test with synthetic training job (week 2)
3. Deploy to production (week 3)
4. Monitor and optimize (ongoing)

---

**Author:** Bandicoot Team
**Reviewers:** MedhAI
**Status:** Design Complete, Ready for Implementation
