# Job Execution: Design & Architecture

**Version:** 1.0
**Last Updated:** November 2025
**Parent Doc:** [00-overview.md](00-overview.md)

---

## Problem Statement

Our system has several long-running batch jobs that exceed Cloud Functions' 60-minute timeout:

| Job | Duration | Frequency | Criticality |
|-----|----------|-----------|-------------|
| Weekly training (clustering + MDP learning) | ~30 min | Weekly | High |
| Whittle index computation | ~7 min | Weekly | High |
| Nightly state update | ~2 min | Daily | Medium |
| Historical data ingest (one-time) | ~10 min | Once | Low |

**Requirements:**
1. Support jobs up to 60+ minutes (future-proof for scaling)
2. Reliable retry mechanism
3. Progress tracking and monitoring
4. Cost-effective (<$20/month for all jobs)
5. **Cloud-agnostic abstraction** (easy to swap providers)

---

## Alternatives Comparison

### Option 1: Cloud Run Jobs ⭐ RECOMMENDED

**Architecture:**
```
Cloud Scheduler → Cloud Run Jobs API → Ephemeral container
```

**Pros:**
- ✅ Purpose-built for batch jobs
- ✅ Up to 24-hour execution time
- ✅ Built-in job status tracking
- ✅ Excellent monitoring and logging
- ✅ Parallelism support (multiple instances)

**Cons:**
- ❌ GCP-specific (requires abstraction for portability)

**Cost:** ~$0.63/month (4 weekly + 30 daily jobs)

---

### Option 2: Cloud Tasks

**Architecture:**
```
Cloud Scheduler → Cloud Tasks Queue → Cloud Run worker
```

**Pros:**
- ✅ Built-in retry with exponential backoff
- ✅ Task deduplication (idempotency)
- ✅ Rate limiting and concurrency control

**Cons:**
- ❌ No built-in progress tracking
- ❌ Requires separate worker service

**Cost:** $0 (within free tier)

---

### Option 3: Cloud Workflows

**Architecture:**
```
Cloud Scheduler → Cloud Workflows → Multi-step orchestration
```

**Pros:**
- ✅ Complex multi-step pipelines
- ✅ Visual workflow editor
- ✅ Up to 1-year execution time

**Cons:**
- ❌ Overkill for simple jobs
- ❌ YAML-based (learning curve)

**Cost:** $0 (within free tier)

---

## Decision Matrix

| Criteria | Cloud Run Jobs | Cloud Tasks | Cloud Workflows |
|----------|----------------|-------------|-----------------|
| **Max Duration** | 24h | 24h (via worker) | 1 year |
| **Retry Handling** | ⚠️ Manual | ✅ Built-in | ✅ Built-in |
| **Progress Tracking** | ✅ Built-in | ❌ Custom | ✅ Built-in |
| **Cost (monthly)** | $0.63 | $0 | $0 |
| **Complexity** | Low | Medium | High |
| **Monitoring** | Excellent | Good | Excellent |
| **Portability** | ⚠️ GCP-specific | ⚠️ GCP-specific | ❌ GCP-only |

---

## Decision: Cloud Run Jobs with SOLID Abstraction

**Rationale:**
1. **Purpose-built** for batch processing
2. **24-hour timeout** (future-proof)
3. **Minimal cost** ($0.63/month, <1% of budget)
4. **Excellent observability** (logs, metrics, status tracking)
5. **Scalable** (can parallelize MDP learning across clusters)

**Mitigation for vendor lock-in:**
- Use SOLID abstraction layer (see Architecture below)
- Define cloud-agnostic interface
- Document migration paths to AWS, Azure (see [cloud-agnostic.md](./job-execution/cloud-agnostic.md))

---

## Architecture

### SOLID Principles

Our design follows all 5 SOLID principles:

| Principle | Application |
|-----------|-------------|
| **Single Responsibility** | `JobExecutor` interface only handles job execution |
| **Open/Closed** | New backends can be added without modifying interface |
| **Liskov Substitution** | Any `JobExecutor` implementation is interchangeable |
| **Interface Segregation** | Minimal interface (4 methods: submit, status, cancel, wait) |
| **Dependency Inversion** | App depends on `JobExecutor` abstraction, not GCP APIs |

---

### Interface Definition

```python
# src/jobs/interface.py

from abc import ABC, abstractmethod
from typing import Optional, Callable
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobResult:
    """Cloud-agnostic job result"""
    job_id: str
    status: JobStatus
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[dict] = None
    error: Optional[str] = None
    attempts: int = 1


class JobExecutor(ABC):
    """
    Abstract interface for job execution.

    Any cloud provider (GCP, AWS, Azure) must implement this interface.
    """

    @abstractmethod
    async def submit(self, job_name: str, handler: Callable, **kwargs) -> str:
        """Submit job, return job_id"""
        pass

    @abstractmethod
    async def get_status(self, job_id: str) -> JobResult:
        """Get current job status"""
        pass

    @abstractmethod
    async def cancel(self, job_id: str) -> bool:
        """Cancel running job"""
        pass

    @abstractmethod
    async def wait(self, job_id: str, timeout: Optional[int] = None) -> JobResult:
        """Block until job completes"""
        pass
```

---

### Factory Pattern

```python
# src/jobs/factory.py

from .interface import JobExecutor


class JobExecutorFactory:
    """
    Factory for creating job executors based on config.

    Supports: GCP, AWS, Azure, Local (testing)
    """

    @staticmethod
    def create(backend: Optional[str] = None) -> JobExecutor:
        backend = backend or os.getenv("JOB_EXECUTOR_BACKEND", "gcp_cloudrun")

        if backend == "gcp_cloudrun":
            from .gcp.cloudrun_jobs import CloudRunJobsExecutor
            return CloudRunJobsExecutor(...)

        elif backend == "aws_batch":
            from .aws.batch import AWSBatchExecutor
            return AWSBatchExecutor(...)

        elif backend == "azure_batch":
            from .azure.batch import AzureBatchExecutor
            return AzureBatchExecutor(...)

        elif backend == "local":
            from .local import LocalJobExecutor
            return LocalJobExecutor()

        else:
            raise ValueError(f"Unknown backend: {backend}")
```

---

### Usage in Application Code

```python
# src/api/endpoints/training.py

from src.jobs.factory import JobExecutorFactory


@router.post("/train_clusters")
async def trigger_training():
    """
    Trigger weekly training.

    Implementation is backend-agnostic - works with GCP, AWS, or Azure.
    """
    executor = JobExecutorFactory.create()  # Backend from env var

    job_id = await executor.submit(
        job_name="weekly-training",
        handler=train_clusters,
        cpu="4",
        memory="8Gi",
        timeout=3600  # 60 minutes
    )

    return {"job_id": job_id, "status": "submitted"}
```

---

## Directory Structure

```
docs/tech-design/job-execution/
├── README.md ........................ This file (design overview)
├── gcp-cloudrun-jobs.md ............. GCP Cloud Run Jobs implementation
├── gcp-cloud-tasks.md ............... GCP Cloud Tasks alternative
├── cloud-agnostic.md ................ Migration paths (AWS, Azure)
└── testing.md ....................... Testing strategy with mocks
```

**Code implementations:**
```
src/jobs/
├── interface.py ..................... Abstract base class
├── factory.py ....................... Factory pattern
├── gcp/
│   ├── cloudrun_jobs.py ............. GCP implementation
│   └── cloud_tasks.py ............... GCP alternative
├── aws/
│   └── batch.py ..................... AWS Batch (future)
├── azure/
│   └── batch.py ..................... Azure Batch (future)
└── local.py ......................... Local testing executor
```

---

## Cost Breakdown

### Cloud Run Jobs (Recommended)

```
Weekly training (30 min, 2 vCPU, 4GB):
- 4 runs/month × $0.104 = $0.42

Nightly updates (2 min, 1 vCPU, 2GB):
- 30 runs/month × $0.007 = $0.21

Total: ~$0.63/month
```

### Cloud Tasks (Alternative)

```
35 tasks/month = $0 (within free tier of 1M ops/month)

Additional Cloud Run worker cost:
- Included in existing API service (no extra cost)
```

---

## Migration Path

### Phase 1: Implement Abstraction (Week 1)
- Define `JobExecutor` interface
- Implement `CloudRunJobsExecutor` (GCP)
- Create `JobExecutorFactory`
- Add unit tests with mock executor

### Phase 2: Deploy to Staging (Week 2)
- Build Cloud Run Jobs container image
- Set up IAM permissions
- Test weekly training job
- Verify monitoring and logging

### Phase 3: Production Rollout (Week 3)
- Set `JOB_EXECUTOR_BACKEND=gcp_cloudrun` in production
- Monitor first weekly training run
- Compare costs vs Cloud Functions

### Phase 4: Cloud-Agnostic Support (Future)
- Implement AWS Batch executor (if migrating to AWS)
- Implement Azure Batch executor (if migrating to Azure)
- Document migration procedure (see [cloud-agnostic.md](./job-execution/cloud-agnostic.md))

---

## Monitoring & Observability

### Metrics to Track

```
Job Execution Metrics:
- job_duration_seconds (histogram)
- job_status_total (counter by status)
- job_retry_count (histogram)
- job_cost_usd (gauge)

Resource Metrics:
- job_cpu_utilization (gauge)
- job_memory_usage_bytes (gauge)
```

### Alerts

```yaml
- name: JobFailureRate
  condition: job_status_total{status="failed"} / job_status_total > 0.1
  threshold: 10% failure rate
  action: Notify on-call engineer

- name: JobDurationAnomaly
  condition: job_duration_seconds > 2 × historical_p95
  threshold: 2× slower than usual
  action: Investigate performance degradation

- name: JobStuck
  condition: job_status{status="running"} AND time_since_start > timeout × 1.5
  threshold: Job running 50% longer than expected
  action: Cancel and retry
```

---

## Testing Strategy

### Unit Tests (with Mock Executor)

See [testing.md](./job-execution/testing.md) for detailed test suite.

```python
class MockJobExecutor(JobExecutor):
    async def submit(self, job_name, handler, **kwargs):
        return f"mock-{job_name}-{uuid.uuid4().hex[:8]}"

    async def get_status(self, job_id):
        return JobResult(job_id=job_id, status=JobStatus.SUCCEEDED, ...)
```

### Integration Tests (with Real GCP)

```python
@pytest.mark.integration
async def test_real_cloudrun_job():
    executor = CloudRunJobsExecutor(project_id="test-project")
    job_id = await executor.submit("test-job", dummy_handler)
    result = await executor.wait(job_id, timeout=60)
    assert result.status == JobStatus.SUCCEEDED
```

---

## Next Steps

1. **Read implementation guides:**
   - [GCP Cloud Run Jobs Implementation](./job-execution/gcp-cloudrun-jobs.md)
   - [Cloud-Agnostic Migration](./job-execution/cloud-agnostic.md)

2. **Implement core interface:**
   - `src/jobs/interface.py`
   - `src/jobs/factory.py`

3. **Implement GCP backend:**
   - `src/jobs/gcp/cloudrun_jobs.py`

4. **Test thoroughly:**
   - Unit tests with mock executor
   - Integration tests with real GCP project

5. **Deploy to staging:**
   - Build container image
   - Set up IAM permissions
   - Test weekly training job

---

## Related Documentation

- **Implementation Guides:** [job-execution/](./job-execution/)
- **Deployment:** [04-deployment.md](./04-deployment.md)
- **Integration:** [05-integration.md](./05-integration.md)
- **MedhAI Review:** [/mentor_notes.md](/mentor_notes.md)

---

**Author:** Bandicoot Team
**Status:** Design Complete, Implementation In Progress
