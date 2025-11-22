# Integration & Data Pipelines

**Version:** 1.0
**Last Updated:** November 2025
**Parent Doc:** [00-overview.md](00-overview.md)

---

## Overview

This document covers data integration between Bandicoot and Suvita's existing systems:
1. **ETL Pipelines** - Extract data from Suvita's PostgreSQL
2. **State Updates** - Sync SMS logs to caregiver states
3. **Recommendation Output** - Feed prioritized caregivers back to SMS system
4. **Event-Driven Updates** (Optional) - Pub/Sub streaming

---

## Data Sources

### 1. Suvita Production Database

**Access:** Read-only replica to avoid impacting production

```python
# Connection to Suvita's PostgreSQL
SUVITA_DB_URL = "postgresql://readonly_user:pass@suvita-replica.db:5432/suvita_production"

# Tables we need access to:
# - caregivers (registry data)
# - sms_logs (delivery, opens, clicks)
# - vaccinations (clinic attendance)
```

**Required Permissions:**
```sql
GRANT SELECT ON suvita_production.caregivers TO bandicoot_etl;
GRANT SELECT ON suvita_production.sms_logs TO bandicoot_etl;
GRANT SELECT ON suvita_production.vaccinations TO bandicoot_etl;
```

---

### 2. Government RCH Database (Optional)

**Note:** Suvita may already mirror RCH data. If not, we rely on Suvita's `vaccinations` table.

---

## ETL Pipeline 1: Initial Data Load (One-Time)

### Objective
Populate Bandicoot's database with historical data for training.

### Extract

```python
import pandas as pd
from sqlalchemy import create_engine

def extract_historical_data(start_date, end_date):
    """
    Extract 6 months of historical SMS and vaccination data.

    Returns:
        DataFrame with columns: caregiver_id, sms_sent, sms_delivered,
        sms_opened, vaccinated, state_before, state_after, action
    """
    suvita_engine = create_engine(SUVITA_DB_URL)

    query = f"""
        SELECT
            sl.caregiver_id,
            sl.sent_at AS sms_sent,
            sl.delivered_at AS sms_delivered,
            sl.opened_at AS sms_opened,
            v.actual_date IS NOT NULL AS vaccinated,
            v.scheduled_date AS vaccine_due_date

        FROM suvita_production.sms_logs sl
        LEFT JOIN suvita_production.vaccinations v
            ON sl.caregiver_id = v.caregiver_id
            AND v.scheduled_date BETWEEN sl.sent_at AND sl.sent_at + INTERVAL '14 days'

        WHERE sl.sent_at >= '{start_date}'
          AND sl.sent_at <= '{end_date}'

        ORDER BY sl.caregiver_id, sl.sent_at
    """

    df = pd.read_sql(query, suvita_engine)
    return df
```

### Transform

```python
def transform_to_rmab_format(df):
    """
    Convert raw logs to (state, action, next_state, reward) tuples.
    """
    # Infer state from SMS engagement
    df['state_before'] = df['sms_opened'].shift(1).notna().map({
        True: 'Responsive',
        False: 'Unresponsive'
    }).fillna('Unresponsive')  # Default for first observation

    df['state_after'] = df['sms_opened'].notna().map({
        True: 'Responsive',
        False: 'Unresponsive'
    })

    # Infer action (did Suvita do extra outreach beyond automated SMS?)
    # For now, assume all SMS are 'active' (future: distinguish SMS vs call)
    df['action'] = 'passive'  # Most SMS are automated
    df.loc[df['message_type'] == 'manual_call', 'action'] = 'active'

    # Reward: 1 if vaccinated within window, 0 otherwise
    df['reward'] = df['vaccinated'].astype(int)

    return df[['caregiver_id', 'state_before', 'action', 'state_after', 'reward', 'sms_sent']]
```

### Load

```python
def load_to_bandicoot_db(df):
    """
    Load transformed data into Bandicoot's training table.
    """
    bandicoot_engine = create_engine(DATABASE_URL)

    df.to_sql(
        'training_data',
        bandicoot_engine,
        if_exists='append',
        index=False,
        method='multi',  # Batch insert
        chunksize=1000
    )

    print(f"Loaded {len(df)} rows to training_data")
```

### Execution

```python
# Run once for initial setup
historical_data = extract_historical_data('2025-05-01', '2025-11-01')
transformed = transform_to_rmab_format(historical_data)
load_to_bandicoot_db(transformed)
```

**Runtime:** ~10 minutes for 200K caregivers × 6 months

---

## ETL Pipeline 2: Nightly State Update

### Objective
Update caregiver states based on latest SMS interactions.

### Cloud Function Implementation

```python
# functions/nightly_state_update/main.py

import functions_framework
from datetime import datetime, timedelta
import psycopg2

@functions_framework.cloud_event
def nightly_state_update(cloud_event):
    """
    Triggered daily at 01:00 UTC+5:30.

    Logic:
    - Responsive: SMS opened in last 7 days
    - Unresponsive: No opens for 7+ days
    """

    # Connect to Suvita's read replica
    suvita_conn = psycopg2.connect(SUVITA_DB_URL)
    suvita_cursor = suvita_conn.cursor()

    # Connect to Bandicoot DB
    bandicoot_conn = psycopg2.connect(DATABASE_URL)
    bandicoot_cursor = bandicoot_conn.cursor()

    # Fetch recent SMS activity (last 7 days)
    cutoff_date = datetime.now() - timedelta(days=7)

    suvita_cursor.execute(f"""
        SELECT DISTINCT caregiver_id
        FROM suvita_production.sms_logs
        WHERE opened_at >= '{cutoff_date}'
    """)

    responsive_ids = [row[0] for row in suvita_cursor.fetchall()]

    # Update Bandicoot states
    # Set Responsive for those with recent opens
    if responsive_ids:
        bandicoot_cursor.execute(f"""
            UPDATE caregiver_states
            SET current_state = 'Responsive',
                last_updated = NOW()
            WHERE caregiver_id = ANY(%s)
              AND warmup_end_date <= CURRENT_DATE
        """, (responsive_ids,))

    # Set Unresponsive for everyone else
    bandicoot_cursor.execute(f"""
        UPDATE caregiver_states
        SET current_state = 'Unresponsive',
            last_updated = NOW()
        WHERE caregiver_id NOT IN (
            SELECT caregiver_id FROM suvita_production.sms_logs
            WHERE opened_at >= '{cutoff_date}'
        )
        AND warmup_end_date <= CURRENT_DATE
    """)

    updated_count = bandicoot_cursor.rowcount

    bandicoot_conn.commit()

    # Update Redis cache
    update_redis_states(responsive_ids)

    print(f"Updated {updated_count} caregiver states")

    suvita_conn.close()
    bandicoot_conn.close()

    return {"updated": updated_count, "timestamp": datetime.now().isoformat()}
```

**Schedule:** Daily at 01:00 (Cloud Scheduler)

---

## ETL Pipeline 3: Weekly Training

### Objective
Retrain clusters and recompute Whittle indices every Sunday.

### Cloud Function Implementation

```python
# functions/weekly_training/main.py

import requests
import os
from datetime import date, timedelta

@functions_framework.http
def weekly_training(request):
    """
    Triggered weekly on Sunday at 02:00.

    Steps:
    1. Call /train_clusters API
    2. Wait for completion
    3. Call /precompute_indices API
    4. Notify Slack on success/failure
    """

    API_BASE = "https://bandicoot-api.run.app"
    API_KEY = os.getenv("BANDICOOT_API_KEY")

    headers = {"Authorization": f"Bearer {API_KEY}"}

    # Step 1: Trigger clustering
    train_response = requests.post(
        f"{API_BASE}/train_clusters",
        headers=headers,
        json={
            "data_start_date": (date.today() - timedelta(days=180)).isoformat(),
            "data_end_date": date.today().isoformat(),
            "num_clusters": 20
        },
        timeout=3600  # 1 hour timeout
    )

    if train_response.status_code != 200:
        notify_slack(f"❌ Training failed: {train_response.text}")
        return {"status": "failed", "error": train_response.text}, 500

    job_id = train_response.json()["job_id"]

    # Step 2: Wait for training job (poll every 30 seconds)
    while True:
        status_response = requests.get(
            f"{API_BASE}/jobs/{job_id}",
            headers=headers
        )

        status = status_response.json()["status"]

        if status == "success":
            break
        elif status == "failed":
            notify_slack(f"❌ Training job {job_id} failed")
            return {"status": "failed"}, 500

        time.sleep(30)

    # Step 3: Trigger index computation
    index_response = requests.post(
        f"{API_BASE}/precompute_indices",
        headers=headers,
        json={"model_version": status_response.json()["model_version"]}
    )

    if index_response.status_code != 200:
        notify_slack(f"❌ Index computation failed: {index_response.text}")
        return {"status": "failed"}, 500

    # Notify success
    notify_slack(f"✅ Weekly training completed. Model version: {model_version}")

    return {"status": "success", "model_version": model_version}


def notify_slack(message):
    """Send notification to Slack webhook."""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if webhook_url:
        requests.post(webhook_url, json={"text": message})
```

**Schedule:** Weekly on Sunday at 02:00 (Cloud Scheduler)

---

## Output Integration: Recommendations → SMS System

### Option 1: API Pull (Recommended for MVP)

Suvita's SMS scheduler calls `/recommend` API daily.

```python
# Suvita's cron job (runs daily at 08:00)

import requests

response = requests.get(
    "https://bandicoot-api.run.app/recommend",
    params={"budget": 100, "district": "Bihar-Patna"},
    headers={"Authorization": f"Bearer {SUVITA_API_KEY}"}
)

recommendations = response.json()["recommendations"]

# Send SMS to top-100 prioritized caregivers
for rec in recommendations:
    send_sms(
        to=rec["caregiver_id"],
        message="Reminder: Your child's vaccination is due soon. Please visit the clinic."
    )

    # Log action
    log_recommendation_action(rec["caregiver_id"], "sms_sent")
```

---

### Option 2: CSV Export (Fallback)

If API integration is delayed, export recommendations as CSV.

```python
@app.get("/recommend/export")
async def export_recommendations(budget: int, api_key: str = Depends(verify_api_key)):
    """Export recommendations as CSV for manual processing."""

    recs = await recommend(budget=budget, api_key=api_key)

    df = pd.DataFrame(recs["recommendations"])
    csv = df.to_csv(index=False)

    return Response(content=csv, media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=recommendations.csv"})
```

---

### Option 3: Pub/Sub Push (Future)

Bandicoot publishes recommendations to a Pub/Sub topic, Suvita's SMS service subscribes.

```python
from google.cloud import pubsub_v1

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path("suvita-prod", "sms-recommendations")

# Publish each recommendation
for rec in recommendations:
    message_data = json.dumps(rec).encode("utf-8")
    future = publisher.publish(topic_path, message_data)
    print(f"Published message ID: {future.result()}")
```

---

## Event-Driven Updates (Optional)

### Real-Time State Updates via Pub/Sub

**Scenario:** Suvita's SMS gateway publishes events when SMS is opened.

#### Suvita Publishes Event

```python
# In Suvita's SMS webhook handler

from google.cloud import pubsub_v1

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path("suvita-prod", "caregiver-events")

event = {
    "event_type": "sms_opened",
    "caregiver_id": "CG-12345",
    "timestamp": datetime.now().isoformat(),
    "message_id": "msg-789"
}

publisher.publish(topic_path, json.dumps(event).encode("utf-8"))
```

#### Bandicoot Subscribes

```python
# Cloud Function: pubsub_event_handler

@functions_framework.cloud_event
def handle_caregiver_event(cloud_event):
    """
    Triggered by Pub/Sub message on 'caregiver-events' topic.
    """
    event_data = json.loads(base64.b64decode(cloud_event.data["message"]["data"]))

    caregiver_id = event_data["caregiver_id"]
    event_type = event_data["event_type"]

    if event_type == "sms_opened":
        # Update state to Responsive
        update_state_api(caregiver_id, "Responsive", "SMS opened")

    elif event_type == "vaccination_completed":
        # Log successful outcome
        log_recommendation_outcome(caregiver_id, "vaccinated")

    return {"processed": caregiver_id}
```

**Benefit:** Near real-time state updates (vs nightly batch)

**Trade-off:** Added complexity, cost (~$4/month for Pub/Sub)

---

## Data Synchronization

### Handling New Caregivers

**Trigger:** New caregiver enrolls in Suvita's system

**Flow:**
1. Suvita inserts into `caregivers` table
2. Suvita calls Bandicoot's `/assign_cluster` API
3. Bandicoot assigns cluster via FO mapper
4. Sets warmup end date (enrollment + 6 weeks)
5. Caregiver enters warmup (standard SMS, no RMAB prioritization)

```python
# Suvita's enrollment handler

new_caregiver = {
    "caregiver_id": "CG-99999",
    "age": 25,
    "district": "Bihar-Patna",
    "parity": 1,
    "phone_reliable": True,
    "enrollment_source": "hospital",
    "enrolled_at": "2025-11-22"
}

response = requests.post(
    "https://bandicoot-api.run.app/assign_cluster",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={"caregivers": [new_caregiver]}
)

cluster_assignment = response.json()["assignments"][0]
print(f"Assigned to cluster {cluster_assignment['cluster_id']}, warmup until {cluster_assignment['warmup_end_date']}")
```

---

### Handling Inactive/Completed Caregivers

**Trigger:** Child completes vaccination schedule or caregiver opts out

**Flow:**
1. Suvita marks caregiver as `inactive` in their DB
2. Bandicoot excludes inactive caregivers from `/recommend`

```sql
-- In Bandicoot's recommend query
WHERE cs.warmup_end_date <= CURRENT_DATE
  AND cs.status = 'active'  -- Exclude inactive
```

---

## Data Quality Monitoring

### Validation Checks (Nightly)

```python
def validate_data_quality():
    """
    Run data quality checks after nightly ETL.
    """
    checks = []

    # 1. No duplicate caregiver IDs
    dups = db.execute("SELECT caregiver_id, COUNT(*) FROM caregiver_states GROUP BY caregiver_id HAVING COUNT(*) > 1").fetchall()
    checks.append(("no_duplicates", len(dups) == 0))

    # 2. All caregivers have valid cluster assignments
    invalid = db.execute("SELECT COUNT(*) FROM caregiver_states WHERE cluster_id IS NULL OR cluster_id < 0").fetchone()[0]
    checks.append(("valid_clusters", invalid == 0))

    # 3. States are within valid set
    invalid_states = db.execute("SELECT COUNT(*) FROM caregiver_states WHERE current_state NOT IN ('Responsive', 'Unresponsive')").fetchone()[0]
    checks.append(("valid_states", invalid_states == 0))

    # 4. Reasonable engagement rate (5-95%)
    engagement_rate = db.execute("SELECT AVG(CASE WHEN current_state = 'Responsive' THEN 1.0 ELSE 0.0 END) FROM caregiver_states").fetchone()[0]
    checks.append(("engagement_rate_sane", 0.05 <= engagement_rate <= 0.95))

    # Alert if any check fails
    for name, passed in checks:
        if not passed:
            notify_slack(f"⚠️ Data quality check failed: {name}")
            raise ValueError(f"Data quality issue: {name}")

    return checks
```

**Schedule:** After nightly state update (01:30 daily)

---

## Logging & Audit Trail

### ETL Job Logs

```python
import logging
from google.cloud import logging as cloud_logging

cloud_logging.Client().setup_logging()
logger = logging.getLogger("bandicoot.etl")

# Structured logging
logger.info("ETL job started", extra={
    "job_type": "nightly_state_update",
    "start_time": datetime.now().isoformat()
})

# ... run ETL ...

logger.info("ETL job completed", extra={
    "job_type": "nightly_state_update",
    "end_time": datetime.now().isoformat(),
    "caregivers_updated": 185000,
    "duration_seconds": 120
})
```

---

## Testing Integration

### Mock Suvita Database

```python
# tests/test_etl.py

import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_suvita_db():
    """Create mock Suvita database with sample data."""
    mock_engine = MagicMock()

    # Mock read_sql to return sample DataFrame
    pd.read_sql = MagicMock(return_value=pd.DataFrame({
        "caregiver_id": ["CG-001", "CG-002"],
        "sms_sent": [datetime.now(), datetime.now()],
        "sms_opened": [datetime.now(), None],
        "vaccinated": [True, False]
    }))

    return mock_engine


def test_extract_historical_data(mock_suvita_db):
    """Test data extraction from Suvita."""
    df = extract_historical_data("2025-01-01", "2025-11-01")

    assert len(df) == 2
    assert "caregiver_id" in df.columns
```

---

## Next Steps
1. Request read-only access to Suvita's database replica
2. Set up VPN/private connection (Cloud SQL Proxy)
3. Implement initial data load ETL
4. Deploy nightly state update Cloud Function
5. Test end-to-end flow with sample data
6. Coordinate with Suvita team on API integration vs CSV export
