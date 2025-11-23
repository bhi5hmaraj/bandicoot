# Job Execution Documentation

This folder contains implementation guides for the job execution abstraction.

## Documents

### Design & Architecture
- **[../06-job-execution.md](../06-job-execution.md)** - Main design doc (alternatives, decision, SOLID architecture)

### Implementation Guides
- **[gcp-cloudrun-jobs.md](./gcp-cloudrun-jobs.md)** - GCP Cloud Run Jobs implementation
- **[gcp-cloud-tasks.md](./gcp-cloud-tasks.md)** - GCP Cloud Tasks alternative *(not yet created)*
- **[cloud-agnostic.md](./cloud-agnostic.md)** - Migration paths for AWS, Azure, Kubernetes
- **[testing.md](./testing.md)** - Testing strategy *(not yet created)*

## Quick Start

**1. Read the design doc first:**
```bash
docs/tech-design/06-job-execution.md
```

**2. Then read implementation for your cloud:**
- GCP: `gcp-cloudrun-jobs.md`
- AWS: `cloud-agnostic.md` (AWS Batch section)
- Azure: `cloud-agnostic.md` (Azure Batch section)
- Multi-cloud: `cloud-agnostic.md` (Kubernetes section)

**3. Implement the abstraction:**
```
src/jobs/
├── interface.py ............... JobExecutor interface
├── factory.py ................. Factory pattern
└── gcp/cloudrun_jobs.py ....... GCP implementation
```

## Directory Structure

```
docs/tech-design/job-execution/
├── README.md .................. This file
├── gcp-cloudrun-jobs.md ....... GCP Cloud Run Jobs (recommended)
├── gcp-cloud-tasks.md ......... GCP Cloud Tasks (alternative)
├── cloud-agnostic.md .......... AWS/Azure/K8s migration paths
└── testing.md ................. Unit & integration tests
```

**Code location:**
```
src/jobs/
├── interface.py ............... Abstract base class (JobExecutor)
├── factory.py ................. Factory for creating executors
├── gcp/
│   ├── cloudrun_jobs.py ....... Cloud Run Jobs implementation
│   └── cloud_tasks.py ......... Cloud Tasks implementation
├── aws/
│   └── batch.py ............... AWS Batch (future)
├── azure/
│   └── batch.py ............... Azure Batch (future)
├── kubernetes/
│   └── jobs.py ................ Kubernetes Jobs (multi-cloud)
├── local.py ................... Local executor (testing)
└── runner.py .................. Job runner (container entrypoint)
```

---

**Next:** Read [../06-job-execution.md](../06-job-execution.md) for design overview
