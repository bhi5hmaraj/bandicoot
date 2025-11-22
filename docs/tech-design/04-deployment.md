# Deployment & Infrastructure

**Version:** 1.0
**Last Updated:** November 2025
**Parent Doc:** [00-overview.md](00-overview.md)

---

## Overview

Cost-optimized serverless deployment on Google Cloud Platform:
- **Compute:** Cloud Run (API), Cloud Functions (batch jobs)
- **Storage:** PostgreSQL (shared), Redis (1GB cache)
- **Target Cost:** ≤$200/month for 200K caregivers

---

## Architecture Components

### 1. Cloud Run (FastAPI Service)

**Configuration:**
```yaml
# cloudrun.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: bandicoot-api
  namespace: production
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "0"  # Scale to zero
        autoscaling.knative.dev/maxScale: "10"
        run.googleapis.com/cpu-throttling: "true"  # Cheaper
    spec:
      containerConcurrency: 80
      timeoutSeconds: 300
      containers:
      - image: gcr.io/suvita-prod/bandicoot:latest
        resources:
          limits:
            memory: "512Mi"
            cpu: "1000m"
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: bandicoot-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: bandicoot-secrets
              key: redis-url
        - name: BANDICOOT_API_KEY
          valueFrom:
            secretKeyRef:
              name: bandicoot-secrets
              key: api-key
```

**Autoscaling:**
- Min instances: 0 (scales to zero when idle)
- Max instances: 10
- Target concurrency: 80 requests per instance
- Scale-up: When p95 latency >500ms
- Scale-down: After 5 min idle

**Cost:** ~$50/month (mostly idle time)

---

### 2. Cloud Functions (Batch Jobs)

#### Function: Nightly State Update

```python
# functions/nightly_state_update/main.py

import functions_framework
from google.cloud import secretmanager
import psycopg2

@functions_framework.cloud_event
def nightly_state_update(cloud_event):
    """
    Triggered daily at 01:00 UTC+5:30 to update caregiver states.
    """
    # Fetch database credentials
    db_url = get_secret("database-url")

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    # Update states based on SMS logs
    query = """
        UPDATE caregiver_states cs
        SET current_state = CASE
            WHEN EXISTS (
                SELECT 1 FROM suvita_production.sms_logs sl
                WHERE sl.caregiver_id = cs.caregiver_id
                  AND sl.opened_at >= NOW() - INTERVAL '7 days'
            ) THEN 'Responsive'
            ELSE 'Unresponsive'
        END,
        last_updated = NOW()
        WHERE cs.warmup_end_date <= CURRENT_DATE;
    """

    cursor.execute(query)
    updated = cursor.rowcount

    conn.commit()
    conn.close()

    print(f"Updated {updated} caregiver states")
    return {"updated": updated}
```

**Schedule:** Cloud Scheduler cron `0 1 * * *` (01:00 daily)

**Cost:** ~$5/month

---

#### Function: Weekly Training

```python
# functions/weekly_training/main.py

@functions_framework.http
def weekly_training(request):
    """
    Trigger full training pipeline (clustering, MDP learning, indices).
    """
    # Call /train_clusters API
    response = requests.post(
        "https://bandicoot-api.run.app/train_clusters",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "data_start_date": "2025-05-01",
            "data_end_date": date.today().isoformat(),
            "num_clusters": 20
        }
    )

    job_id = response.json()["job_id"]

    # Wait for completion (or use async callback)
    wait_for_job(job_id)

    # Trigger index computation
    requests.post(
        "https://bandicoot-api.run.app/precompute_indices",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"model_version": get_latest_version()}
    )

    return {"status": "success"}
```

**Schedule:** Cloud Scheduler cron `0 2 * * 0` (02:00 Sunday)

**Timeout:** 60 minutes (for large datasets)

**Cost:** ~$10/month (longer runtime)

---

### 3. PostgreSQL (Cloud SQL)

**Configuration:**
```bash
gcloud sql instances create bandicoot-db \
    --database-version=POSTGRES_14 \
    --tier=db-custom-2-4096 \  # 2 vCPU, 4GB RAM
    --region=asia-south1 \
    --storage-size=20GB \
    --storage-type=SSD \
    --backup-start-time=03:00 \
    --backup-location=asia-south1 \
    --enable-point-in-time-recovery \
    --insights-config-query-insights-enabled \
    --database-flags=shared_buffers=1GB,max_connections=100
```

**Reuse Strategy:**
- Share Suvita's existing Cloud SQL instance (different schema)
- Use `bandicoot` database within same instance
- Save ~$100/month vs separate instance

**Connection Pooling:**
```python
# Use PgBouncer for connection pooling
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800  # Recycle connections every 30 min
)
```

**Cost:** ~$30/month (shared allocation)

---

### 4. Redis (Cloud Memorystore)

**Configuration:**
```bash
gcloud redis instances create bandicoot-cache \
    --size=1 \  # 1GB
    --region=asia-south1 \
    --tier=basic \  # No HA for cost savings
    --redis-version=redis_7_0 \
    --eviction-policy=volatile-lru
```

**Usage:**
- Whittle indices (40 keys × ~50 bytes = ~2KB)
- Current states (200K × ~200 bytes = ~40MB)
- FO mapper model (~5MB)
- Recommendation cache (~10MB with 1-hour TTL)

**Total:** ~60MB / 1GB = 6% utilization (room to grow)

**Cost:** ~$47/month

---

### 5. Pub/Sub (Optional Streaming)

**Topic: `caregiver-events`**

```bash
gcloud pubsub topics create caregiver-events
gcloud pubsub subscriptions create bandicoot-state-updates \
    --topic=caregiver-events \
    --ack-deadline=60
```

**Event Schema:**
```json
{
  "event_type": "sms_delivered|sms_opened|vaccination_completed",
  "caregiver_id": "CG-12345",
  "timestamp": "2025-11-22T10:30:00Z",
  "metadata": {
    "message_id": "msg-789",
    "clinic": "Patna General Hospital"
  }
}
```

**Subscriber:** Cloud Function triggers `/update_state` API

**Cost:** ~$4/month (100GB/month at $0.04/GB)

---

## Docker Container

### Dockerfile (Multi-Stage Build)

```dockerfile
# Stage 1: Builder
FROM python:3.10-slim as builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target /app/packages

# Stage 2: Runtime
FROM python:3.10-slim

WORKDIR /app

# Copy installed packages
COPY --from=builder /app/packages /usr/local/lib/python3.10/site-packages

# Copy application code
COPY ./bandicoot /app/bandicoot

# Expose port
EXPOSE 8080

# Run FastAPI with Uvicorn
CMD ["uvicorn", "bandicoot.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Build & Push:**
```bash
docker build -t gcr.io/suvita-prod/bandicoot:v1.0.2 .
docker push gcr.io/suvita-prod/bandicoot:v1.0.2
```

---

## Secrets Management

### Google Secret Manager

```bash
# Create secrets
echo -n "postgresql://user:pass@host/db" | gcloud secrets create database-url --data-file=-
echo -n "redis://host:6379" | gcloud secrets create redis-url --data-file=-
echo -n "sk_prod_abc123" | gcloud secrets create api-key --data-file=-

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding database-url \
    --member=serviceAccount:bandicoot-sa@suvita-prod.iam.gserviceaccount.com \
    --role=roles/secretmanager.secretAccessor
```

**Access in Code:**
```python
from google.cloud import secretmanager

def get_secret(secret_id):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/suvita-prod/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

DATABASE_URL = get_secret("database-url")
```

---

## CI/CD Pipeline (GitHub Actions)

### `.github/workflows/deploy.yml`

```yaml
name: Build and Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pytest tests/ --cov=bandicoot

  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1

      - name: Build Docker image
        run: |
          docker build -t gcr.io/suvita-prod/bandicoot:$GITHUB_SHA .
          docker tag gcr.io/suvita-prod/bandicoot:$GITHUB_SHA gcr.io/suvita-prod/bandicoot:latest

      - name: Push to GCR
        run: |
          gcloud auth configure-docker
          docker push gcr.io/suvita-prod/bandicoot:$GITHUB_SHA
          docker push gcr.io/suvita-prod/bandicoot:latest

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy bandicoot-api \
            --image gcr.io/suvita-prod/bandicoot:$GITHUB_SHA \
            --region asia-south1 \
            --platform managed \
            --allow-unauthenticated
```

---

## Cost Breakdown (Monthly)

| Service | Configuration | Est. Cost |
|---------|---------------|-----------|
| Cloud Run | 0-10 instances, 512MB, 1 vCPU | $50 |
| Cloud Functions | 2 functions, daily/weekly triggers | $15 |
| Cloud SQL | Shared 2 vCPU, 4GB RAM, 20GB SSD | $30 |
| Cloud Memorystore | 1GB Redis, Basic tier | $47 |
| Pub/Sub | 100GB/month (optional) | $4 |
| Networking | Egress ~50GB | $10 |
| Secret Manager | 6 secrets | $1 |
| **TOTAL** | | **~$157/month** |

**Target Met:** ✅ Under $200/month

---

## Monitoring & Alerting

### Cloud Logging

```python
import logging
from google.cloud import logging as cloud_logging

# Configure structured logging
client = cloud_logging.Client()
client.setup_logging()

logger = logging.getLogger(__name__)
logger.info("Recommendation generated", extra={
    "caregiver_id": "CG-12345",
    "priority_score": 0.87,
    "cluster_id": 5
})
```

### Cloud Monitoring Alerts

```bash
# Alert: High error rate
gcloud alpha monitoring policies create \
    --notification-channels=projects/suvita-prod/notificationChannels/EMAIL \
    --display-name="High API Error Rate" \
    --condition-threshold-value=0.05 \
    --condition-threshold-duration=300s \
    --condition-display-name="Error rate > 5%" \
    --condition-filter='metric.type="run.googleapis.com/request_count" AND metric.label.response_code_class="5xx"'
```

**Alerts:**
1. API error rate >5% (5 min window)
2. Latency p95 >1s (5 min window)
3. Cloud SQL connections >90% (immediate)
4. Redis memory >90% (immediate)
5. Training job failed (immediate)

---

## Rollback Strategy

### Instant Rollback (Cloud Run)

```bash
# List revisions
gcloud run revisions list --service bandicoot-api

# Rollback to previous revision
gcloud run services update-traffic bandicoot-api \
    --to-revisions bandicoot-api-00042-xyz=100
```

**Trigger Conditions:**
- Error rate >20% for >15 minutes
- Latency p95 >2s consistently
- Training job fails 3 times
- Manual rollback requested

---

## Disaster Recovery

### Database Backup & Restore

**Automated Backups:** Daily at 03:00 UTC+5:30, 7-day retention

**Manual Restore:**
```bash
gcloud sql backups list --instance=bandicoot-db
gcloud sql backups restore BACKUP_ID --backup-instance=bandicoot-db
```

### Redis Failover

**Scenario:** Redis becomes unavailable

**Fallback:**
1. Serve Whittle indices from PostgreSQL (slower, ~200ms latency)
2. Disable recommendation caching
3. Alert ops team
4. Restore Redis from RDB snapshot

---

## Scaling Strategy

### Current (MVP): 200K caregivers
- Cloud Run: 0-10 instances
- PostgreSQL: 2 vCPU, 4GB RAM
- Redis: 1GB

### Phase 2: 500K caregivers
- Cloud Run: 0-20 instances
- PostgreSQL: 4 vCPU, 8GB RAM (or separate instance)
- Redis: 2GB

### Phase 3: 1M+ caregivers
- Cloud Run: 0-50 instances
- Cloud SQL HA (primary + replica)
- Redis: 4GB with read replicas
- Consider GKE for batch jobs (more cost-effective at scale)

---

## Next Steps
1. Set up GCP project and enable APIs
2. Deploy Cloud SQL and Redis staging instances
3. Build and push Docker image
4. Deploy to Cloud Run staging
5. Set up Cloud Scheduler for batch jobs
6. Configure monitoring and alerts
7. Load test and optimize resource limits
