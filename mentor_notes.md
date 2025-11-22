# MedhAI Mentor Notes: Bandicoot Architecture Review

**Reviewer:** MedhAI (Principal Engineer, ex-Google AI)
**Review Date:** November 2025
**Scope:** MVP PRD + 6 Technical Design Documents
**Context:** 6-week MVP for Suvita NGO, 200K caregivers, ~$200/month budget

---

## Executive Assessment

**TL;DR:** This is a **well-scoped MVP** with solid foundations from SAHELI research. The team clearly learned from Google/ARMMAN's deployment. My main concerns: (1) overly optimistic 6-week timeline given integration complexity, (2) insufficient attention to data quality edge cases, (3) numerical stability risks in Whittle solver not fully addressed.

**Overall Grade:** B+ (would be A- if timeline was 8-10 weeks)

**Ship it?** Yes, but with caveat: expect Week 5-6 to slip to Week 7-8 once you hit Suvita integration reality.

---

## Running Commentary by Document

### 1. MVP PRD Review

#### What I Like ✅

**Clear Success Metrics (Lines 18-30)**
```
✅ <500ms p95 latency for /recommend
✅ A/B test with ≥1000 caregivers
✅ Cost ≤ $200/month
```

This is **exactly** the right level of rigor for an MVP. You're not boiling the ocean. You have concrete, measurable launch blockers. The $200/month constraint is particularly good - forces architectural discipline.

**10 P0 Features - Scope Discipline**

I counted. You have exactly 10 must-haves. Not 15, not 20. This tells me you've done the hard work of prioritization. At Google, we had a saying: "If everything is P0, nothing is P0." You actually mean it here.

**Acceptance Criteria for Each Feature**

Every P0 has checkboxes. This isn't vaporware. Lines 61-67 for clustering, lines 78-88 for Whittle indices - these are testable, specific criteria. Good.

#### What Worries Me 🚨

**Timeline: 6 Weeks is Aggressive (Lines 413-444)**

Let me break down your timeline:
- Week 1-2: Core infrastructure + clustering + Whittle solver
- Week 3-4: Suvita integration + initial training
- Week 5: A/B test setup + monitoring
- Week 6: Launch

**Reality check from my Google deployments:**

Week 3-4 is where you'll get crushed. Here's what you're underestimating:

1. **Data Access Negotiations** - "Read-only access to Suvita's PostgreSQL" sounds simple. In reality:
   - IT approval: 3-5 days
   - Schema doesn't match docs: 2 days debugging
   - VPN/firewall rules: 1-2 days
   - Data quality issues: 1 week of back-and-forth

   **Total: 2 weeks, not 2 days**

2. **The "Synthetic Data Works, Real Data Breaks" Problem**
   Line 421: "Milestone: /train_clusters working with synthetic data"

   This is a trap. Synthetic data is clean. Real data from Suvita will have:
   - Duplicate caregiver IDs (misspellings, data entry errors)
   - Missing SMS timestamps
   - Vaccination dates that predate SMS sends (data corruption)
   - Caregivers with 0 interactions (how do you cluster them?)

   You'll spend Week 3 just writing data cleaning code you didn't anticipate.

3. **A/B Test Setup Isn't 1 Week (Line 434)**
   "A/B test setup" assumes:
   - Suvita's SMS system has an API you can call
   - You can programmatically route caregivers to different message schedules
   - Their team is ready to integrate

   **High chance this becomes manual CSV exports** for the first month. Not a dealbreaker, but adds operational overhead.

**My Recommendation:**
- Keep the scope as-is (it's good!)
- Change timeline to **8-10 weeks**
- Add explicit buffer: "Week 7-8: Integration refinement & bug fixes"
- Set internal deadline at Week 8, tell stakeholders Week 10

---

**Data Quality Section is Too Brief (Lines 471-479)**

You have 1 paragraph under "Risk: Data Quality Issues". This should be a **full page**.

Questions you haven't answered:
- What % of SMS logs have `opened_at` populated? (If it's <30%, your state model breaks)
- How do you handle caregivers who enrolled before SMS tracking started?
- What if vaccination records are 2-4 weeks delayed in RCH database?
- Do SMS logs include "bounced" / "phone number invalid" events?

**Action Item:** Add a "Data Quality Audit" task to Week 1. Before you write any ML code, analyze:
```python
# Week 1 checklist
- % of SMS with delivery confirmation
- % with open tracking
- Distribution of interactions per caregiver (histogram)
- Vaccination record lag (time from clinic visit to DB update)
- Caregiver ID collision rate
```

If >20% of SMS logs are missing critical fields, **your 2-state model needs redesign**. Better to learn this Week 1 than Week 4.

---

**Out of Scope is Good, But Missing One Item (Lines 516-528)**

You correctly defer:
- ❌ Multi-channel optimization
- ❌ Real-time learning
- ❌ Mobile app

But you're missing:
- ❌ **Model versioning and rollback strategy**

What happens if Week 6 training produces a bad model? Do you have:
- A way to rollback to previous model version?
- A canary deployment (10% traffic to new model, 90% to old)?
- Model quality metrics (e.g., "new model recommends 95% same caregivers as old - probably a bug")?

Add to P1 features:
```
#### 13. Model Versioning (P1, Week 5)
- Store model_version in all recommendations_log entries
- Support /recommend?model_version=v1.0.1 (pin to specific version)
- Automated rollback if new model produces anomalous recommendations
```

---

### 2. Data Architecture Review (01-data-architecture.md)

#### What I Like ✅

**Redis for Hot Path, PostgreSQL for Cold Storage (Lines 20-80)**

This is **textbook correct** for cost optimization:
- Whittle indices in Redis (40 keys, ~2KB) - O(1) lookup
- Full state history in PostgreSQL
- Redis eviction policy: `volatile-lru`

You understand the access patterns. At 200K caregivers, this will scale to 1M+ without rearchitecture.

**Connection Pooling (Lines 195-207 in deployment doc)**

```python
pool_size=10,
max_overflow=20,
pool_recycle=1800  # Recycle every 30 min
```

This is right for serverless. Cloud Run instances come and go - connection pooling prevents "too many connections" errors. You've thought this through.

#### What Worries Me 🚨

**No Handling of Concurrent Training Jobs (Lines 88-120)**

Your `clusters` table schema:
```sql
CREATE TABLE clusters (
    cluster_id INTEGER PRIMARY KEY,
    mdp_params JSONB NOT NULL,
    last_trained TIMESTAMP,
    model_version VARCHAR(20)
);
```

What happens if:
1. Weekly training starts at 02:00 Sunday (as per deployment doc)
2. Takes 45 minutes
3. Meanwhile, `/recommend` is called at 02:20
4. Reads half-updated clusters table?

**You need:**
- `model_status` column: 'training' | 'active' | 'retired'
- `/recommend` should NEVER read a model with status='training'
- Atomic swap: train new model in shadow tables, then swap pointer

**Pattern to steal from Google:**
```sql
CREATE TABLE models (
    model_version VARCHAR(20) PRIMARY KEY,
    status VARCHAR(20),  -- 'training', 'validation', 'active', 'retired'
    created_at TIMESTAMP,
    activated_at TIMESTAMP
);

CREATE TABLE clusters (
    cluster_id INTEGER,
    model_version VARCHAR(20) REFERENCES models(model_version),
    mdp_params JSONB NOT NULL,
    PRIMARY KEY (cluster_id, model_version)
);

-- /recommend always queries:
SELECT * FROM clusters
WHERE model_version = (SELECT model_version FROM models WHERE status='active')
```

This adds 10 lines of code but prevents **catastrophic mid-training corruption**.

---

**Warmup Period Logic Has Edge Case (Lines 461-496 in RMAB core doc)**

```python
def is_ready_for_rmab(caregiver):
    warmup_end = caregiver['warmup_end_date']
    return datetime.now().date() >= warmup_end
```

What if a caregiver enrolled 8 weeks ago but has **zero SMS interactions**? (Phone number was invalid, all messages bounced.)

According to your logic:
- ✅ Warmup complete (6 weeks passed)
- ❌ No data to determine state
- ❌ No passive features to cluster

**Result:** FO mapper assigns to cluster based on demographics, but cluster MDP parameters assume ≥5 interactions. **Your recommendations will be garbage for this caregiver.**

**Fix:**
```python
def is_ready_for_rmab(caregiver):
    warmup_end = caregiver['warmup_end_date']
    min_interactions = 3  # At least 3 SMS sends

    if datetime.now().date() < warmup_end:
        return False

    if caregiver['total_sms_sent'] < min_interactions:
        # Extend warmup by 2 weeks
        caregiver['warmup_end_date'] += timedelta(weeks=2)
        return False

    return True
```

Add this to your `caregiver_states` table:
```sql
ALTER TABLE caregiver_states ADD COLUMN total_interactions INT DEFAULT 0;
```

---

### 3. RMAB Core Algorithms Review (02-rmab-core.md)

#### What I Like ✅

**You Adapted SAHELI's Approach, Not Reinvented It (Lines 11-18)**

Key insight: clustering by **passive transition probabilities**, not demographics.

This is the magic of SAHELI. Lesser teams would cluster by age/district (easy but wrong). You're doing the hard thing correctly.

```python
def compute_passive_features(caregiver_data):
    # Cluster based on how caregivers behave *without* intervention
    passive_transitions = caregiver_data[caregiver_data['action'] == 'passive']
```

**Validation:** When you train on Suvita data, sanity check that clusters are **behaviorally distinct**, not just demographic duplicates. E.g.:
- Cluster 5: High P(U→U|passive) = 0.9 (sticky unresponsive)
- Cluster 12: High P(R→U|passive) = 0.6 (lapses quickly)
- If all clusters have similar transition matrices, your clustering failed.

---

**Laplace Smoothing for Sparse Data (Lines 68-76)**

```python
alpha = 1.0  # Smoothing parameter
prob = (counts[f'{start_state}→{end_state}'] + alpha) / total
```

This is **correct and necessary**. Without smoothing, caregivers with 2-3 interactions would have transition probabilities of 0.0 or 1.0 (overfitting).

Pro tip from my RMAB research: `alpha=1.0` is reasonable, but consider tuning it:
- If clusters have >1000 caregivers each: alpha=0.5 (less smoothing)
- If clusters have <100 caregivers: alpha=2.0 (more shrinkage toward uniform prior)

Add a hyperparameter sweep in Week 2:
```python
for alpha in [0.5, 1.0, 2.0]:
    clusters = train_with_smoothing(alpha)
    silhouette = evaluate_clustering(clusters)
    print(f"alpha={alpha}, silhouette={silhouette}")
```

Pick the alpha that maximizes silhouette score.

#### What Worries Me 🚨

**Whittle Index Binary Search: Numerical Instability Not Addressed (Lines 254-333)**

Your Whittle solver:
```python
def compute_whittle_index(mdp_params, state, gamma=0.95, tol=1e-6, max_iter=1000):
    # Binary search for λ
    lambda_min, lambda_max = 0.0, 10.0

    while lambda_max - lambda_min > 1e-6:
        lambda_mid = (lambda_min + lambda_max) / 2
        # ... value iteration ...
```

**Three problems:**

1. **Hardcoded λ_max = 10.0**
   What if true Whittle index is 15.7? Your binary search will return 10.0 and never converge.

   **Fix:** Adaptive bounds
   ```python
   lambda_max = 10.0
   while True:
       index = binary_search(lambda_min, lambda_max)
       if index < lambda_max * 0.99:  # Converged within bounds
           break
       lambda_max *= 2  # Double upper bound
       if lambda_max > 1000:
           raise ValueError("Whittle index diverged - check MDP params")
   ```

2. **Value Iteration May Not Converge (Lines 302-332)**
   ```python
   for _ in range(max_iter):
       # ...
       if max(abs(V_new[s] - V[s]) for s in states) < tol:
           return V_new
   return V  # Return even if not converged (with warning)
   ```

   "Return with warning" is **dangerous in production**. If value iteration doesn't converge, your Whittle indices are **meaningless**.

   **What causes non-convergence:**
   - Badly estimated transition probabilities (e.g., P(R→U|active) + P(R→R|active) ≠ 1.0 due to floating point)
   - Gamma too close to 1.0 (0.99+ makes value iteration slow)
   - Reward probabilities outside [0,1]

   **Fix:** Add validation
   ```python
   def learn_cluster_mdp(cluster_data):
       # ... existing code ...

       # VALIDATE learned MDP parameters
       for state in ['Responsive', 'Unresponsive']:
           for action in ['active', 'passive']:
               p_sum = sum(P_transition[state][action].values())
               if not (0.99 <= p_sum <= 1.01):
                   raise ValueError(f"Invalid transition probs: {state},{action} sum={p_sum}")

               if not (0.0 <= P_reward[state][action] <= 1.0):
                   raise ValueError(f"Reward probability out of bounds: {P_reward[state][action]}")

       return {'P_transition': P_transition, 'P_reward': P_reward}
   ```

3. **No Fallback for Failed Index Computation**
   If Whittle solver fails for (cluster_id=5, state='Unresponsive'), what happens?
   - Current code: Crashes or returns NaN
   - Production needs: Fallback to median index across other clusters

   ```python
   try:
       index = compute_whittle_index(mdp_params, state)
   except Exception as e:
       logger.error(f"Whittle computation failed for cluster {cluster_id}: {e}")
       # Fallback: use median index from other clusters in same state
       index = redis_client.get(f"median_index:{state}") or 0.5
   ```

**Why this matters:** Week 4, you'll train on real Suvita data. **I guarantee at least 1 cluster will have weird transition probabilities** (data bug, small sample size, etc.). Your solver will crash. With proper error handling, you degrade gracefully instead of taking down the whole service.

---

**FO Mapper: No Cross-Validation Mentioned (Lines 378-434)**

```python
def train_fo_mapper(caregiver_data, cluster_assignments):
    # ... train RandomForest ...
    scores = cross_val_score(model, X[FO_FEATURES], y, cv=5)
    print(f"FO Mapper Cross-Val Accuracy: {scores.mean():.2f}")
```

Good! You're doing 5-fold CV. But you don't specify:
- Train/test split strategy
- What if accuracy is 52%? (barely better than random for 20 clusters)
- Acceptance threshold: you say "≥70%" in PRD line 97

**Add to your training script:**
```python
if scores.mean() < 0.70:
    logger.warning(f"FO mapper accuracy {scores.mean():.2f} below threshold")
    # Option 1: Reduce number of clusters (fewer classes = easier)
    # Option 2: Add more features (e.g., first SMS open rate)
    # Option 3: Fallback to assigning everyone to largest cluster
```

Also: **70% accuracy means 30% of new caregivers are misassigned**. Over 6 months, that's 60,000 caregivers with suboptimal recommendations. Not a launch blocker, but track this metric:
```sql
-- How often do caregivers switch clusters after warmup?
SELECT
    COUNT(*) as cluster_changes,
    AVG(weeks_until_change)
FROM cluster_reassignments
WHERE assigned_via='fo_mapper';
```

If 50%+ of FO-mapped caregivers get reassigned after warmup, your features are weak. Consider adding:
- Initial SMS open rate (first 2 weeks)
- Enrollment source (hospital vs community worker)
- Day of week enrolled (proxy for motivation?)

---

### 4. API Design Review (03-api-design.md)

#### What I Like ✅

**Rate Limiting by Endpoint (Lines 527-546)**

```python
@limiter.limit("100/minute")  # /recommend
@limiter.limit("1000/minute")  # /update_state
@limiter.limit("1/hour")       # /train_*
```

This is **pragmatic**. You're not building a public API - this is for Suvita's internal use. 100 req/min is **way** more than they need (they'll call `/recommend` once daily).

The 1/hour limit on training endpoints is smart - prevents accidental double-triggers.

**Standard Error Response Format (Lines 550-580)**

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Budget must be between 1 and 1000",
    "details": {"field": "budget", "value": 5000}
  },
  "request_id": "abc-123-def"
}
```

`request_id` is the key. When Suvita reports "recommendations API is broken," you can grep logs for `abc-123-def` and debug instantly. Many junior teams forget this.

**Pro tip:** Also return `request_id` in **success responses**. Makes correlation easier:
```json
{
  "recommendations": [...],
  "metadata": {
    "request_id": "abc-123-def",  // ADD THIS
    "generated_at": "2025-11-22T10:30:00Z"
  }
}
```

#### What Worries Me 🚨

**No Pagination on /recommend (Lines 324-445)**

Current API:
```
GET /recommend?budget=100
```

Returns 100 caregivers in one response. What if Suvita asks for budget=5000? You'll:
- Fetch 5000 rows from PostgreSQL
- Sort by Whittle index (in-memory)
- Serialize 5000 JSON objects

**This will blow your 500ms latency target.**

Add pagination:
```
GET /recommend?budget=5000&page=1&page_size=100
```

Return:
```json
{
  "recommendations": [...],  // 100 items
  "pagination": {
    "page": 1,
    "page_size": 100,
    "total_pages": 50,
    "next_page": "/recommend?budget=5000&page=2"
  }
}
```

**Alternatively:** If budget >500, return HTTP 400 with error message:
```json
{
  "error": {
    "code": "BUDGET_TOO_LARGE",
    "message": "Maximum budget is 500. For larger batches, use /recommend/export (CSV)"
  }
}
```

Force them to use CSV export for bulk operations. Keeps API fast.

---

**Missing Idempotency on /train_clusters (Lines 51-115)**

Current behavior:
```python
@app.post("/train_clusters")
async def train_clusters(request: TrainClustersRequest):
    job_id = create_training_job(...)  # Always creates new job
    background_tasks.add_task(run_clustering_pipeline, job_id)
```

What if:
1. User calls `/train_clusters` at 02:00
2. Network timeout (no response received)
3. User retries at 02:05
4. Now 2 training jobs are running in parallel!

**Result:** Database corruption as both jobs write to same `clusters` table.

**Fix:** Idempotency key
```python
@app.post("/train_clusters")
async def train_clusters(request: TrainClustersRequest):
    # Check if training already in progress
    existing_job = db.execute(
        "SELECT job_id, status FROM training_jobs WHERE status='running' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()

    if existing_job:
        return {
            "job_id": existing_job.job_id,
            "status": "already_running",
            "message": "Training job already in progress. Wait for completion or use force_retrain=true."
        }

    # Proceed with new job
    job_id = create_training_job(...)
    ...
```

Or use request headers (like Stripe):
```
POST /train_clusters
Idempotency-Key: train-2025-11-22
```

If same key is reused, return cached response from first call.

---

### 5. Deployment Review (04-deployment.md)

#### What I Like ✅

**Cost Breakdown is Detailed and Realistic (Lines 396-410)**

```
Cloud Run: $50
Cloud Functions: $15
Cloud SQL (shared): $30
Redis 1GB: $47
Total: ~$157/month
```

You itemized everything. And you **hit the $200 budget**. This tells me you actually priced this out, not just guessed.

One thing that's often wrong in cost estimates: **egress costs**. You allocated $10/month for 50GB egress. Let me validate:

- `/recommend` response: ~10KB per call
- Called daily = 30 calls/month
- Total: 300KB/month ≈ $0.01

Even if called 100x/day = 30MB/month ≈ $0.30. You're safe.

Where egress could spike: **CSV exports**. If Suvita downloads 200K caregiver recommendations as CSV:
- 200K rows × 500 bytes = 100MB per export
- 4 exports/month = 400MB = $0.04

Still well under budget. You're good.

**Monitoring Alerts are Specific (Lines 413-451)**

```
1. API error rate >5% (5 min window)
2. Latency p95 >1s (5 min window)
3. Cloud SQL connections >90%
4. Redis memory >90%
5. Training job failed
```

These are the **right alerts**. You're not monitoring vanity metrics (requests per second, CPU usage). You're monitoring **failure modes**:
- Error rate = are we serving bad responses?
- Latency = are users waiting too long?
- SQL connections = are we about to crash?
- Training failed = is the system degrading?

**One addition:** Alert on **recommendation staleness**
```
6. Last successful training >10 days ago (immediate)
```

If weekly training silently fails 2 weeks in a row, your Whittle indices are stale. Your recommendations are drifting from reality. This should wake someone up.

#### What Worries Me 🚨

**"Scale to Zero" Might Hurt Cold Start Latency (Lines 34-36)**

```yaml
autoscaling.knative.dev/minScale: "0"  # Scale to zero
```

Cloud Run with minScale=0 means:
- After 5 min idle, instance shuts down
- Next request triggers cold start
- Cold start latency: **3-8 seconds** (load Python + FastAPI + dependencies)

If Suvita calls `/recommend` once daily at 08:00, **every call will be a cold start**. Your 500ms latency target becomes 5000ms.

**Options:**

1. **Set minScale=1** (keep 1 instance always warm)
   Cost impact: +$15-20/month (small price for reliability)

2. **Use Cloud Scheduler to ping /health every 5 minutes**
   Keeps instance warm, but wastes compute on no-op requests

3. **Accept cold starts, document in SLA**
   "First request of the day may take 5-8 seconds. Subsequent requests <500ms."

For an MVP, I'd recommend **option 1 (minScale=1)**. The cost delta is <10% of total budget, and it guarantees fast responses. You can optimize later.

---

**Rollback Strategy Exists But Not Tested (Lines 455-473)**

```bash
gcloud run services update-traffic bandicoot-api \
    --to-revisions bandicoot-api-00042-xyz=100
```

You documented the command. **Have you rehearsed it?**

In Week 5, add a drill:
1. Deploy a intentionally broken version (e.g., `/recommend` returns empty list)
2. Notice via alerts
3. Execute rollback
4. Verify service restored
5. Time the process

**Target: <10 minutes from "deploy broken version" to "rollback complete".**

If rollback takes 30+ minutes (waiting for DNS propagation, discovering commands don't work, etc.), your downtime window is too long for Suvita's daily operations.

---

**No Discussion of Database Migrations (Missing)**

Your schema will evolve:
- Week 2: Add `total_interactions` column to `caregiver_states`
- Week 4: Add `ab_test_group` column
- Week 6: Add index on `warmup_end_date` for faster queries

How do you handle schema changes in production?

Use a migration tool: **Alembic** (for SQLAlchemy) or **Flyway**.

```bash
# Generate migration
alembic revision --autogenerate -m "Add ab_test_group column"

# Apply migration
alembic upgrade head
```

Add to CI/CD pipeline:
```yaml
# .github/workflows/deploy.yml
- name: Run database migrations
  run: alembic upgrade head
```

**Why this matters:** Week 6, you're racing to launch. You push a code change that assumes `ab_test_group` column exists. You forget to run the migration. **App crashes in production.** With automated migrations in CI/CD, this can't happen.

---

### 6. Integration Review (05-integration.md)

#### What I Like ✅

**Three Output Options (Lines 337-406)**

You planned for:
1. API Pull (ideal)
2. CSV Export (fallback)
3. Pub/Sub Push (future)

This is **pessimism-driven design** - exactly right for MVP with external dependencies. If Suvita's SMS system doesn't have an API (Week 4 discovery), you pivot to CSV without rearchitecting.

**Data Quality Monitoring (Lines 520-556)**

```python
def validate_data_quality():
    # 1. No duplicate caregiver IDs
    # 2. All caregivers have valid cluster assignments
    # 3. States are within valid set
    # 4. Reasonable engagement rate (5-95%)
```

These checks catch **data pipeline bugs**, not just data quality issues. For example:
- Check #2 fails → Your clustering code is broken
- Check #4 fails → Your state update logic is wrong (everyone marked Unresponsive)

Run these checks **after every ETL run**. If any fail, **halt the pipeline** and alert. Don't let bad data propagate downstream.

#### What Worries Me 🚨

**Nightly State Update is Brittle (Lines 158-241)**

Current logic:
```python
suvita_cursor.execute(f"""
    SELECT DISTINCT caregiver_id
    FROM suvita_production.sms_logs
    WHERE opened_at >= '{cutoff_date}'
""")
```

**Problem 1: SQL Injection Risk**

You're using f-strings to build SQL queries. If `cutoff_date` ever comes from user input (e.g., via `/update_state?since=...`), this is exploitable.

**Fix:** Use parameterized queries
```python
suvita_cursor.execute(
    "SELECT DISTINCT caregiver_id FROM sms_logs WHERE opened_at >= %s",
    (cutoff_date,)
)
```

**Problem 2: What if Suvita's DB is Down?**

Your ETL crashes. Then what? Options:
1. Retry 3x with exponential backoff
2. Skip this run, try again tomorrow (states become stale)
3. Alert on-call engineer

Add retry logic:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
def fetch_recent_opens(cutoff_date):
    suvita_cursor.execute(...)
    return suvita_cursor.fetchall()
```

If retries exhausted, **send alert but don't crash**:
```python
try:
    responsive_ids = fetch_recent_opens(cutoff_date)
except Exception as e:
    logger.error(f"Failed to fetch SMS opens: {e}")
    notify_slack("⚠️ Nightly state update failed - Suvita DB unreachable")
    return  # Skip this run, try tomorrow
```

**Problem 3: Race Condition with /recommend**

Timeline:
- 01:00: Nightly state update starts
- 01:15: Update in progress, `caregiver_states` table partially updated
- 01:20: Suvita calls `/recommend` (cron job)
- Result: Recommendations use mix of old and new states

**Fix:** Use transactions
```python
bandicoot_conn.autocommit = False  # Disable autocommit
try:
    # Update all states
    bandicoot_cursor.execute("UPDATE caregiver_states SET ...")
    bandicoot_cursor.execute("UPDATE caregiver_states SET ...")

    # Commit atomically
    bandicoot_conn.commit()
except Exception:
    bandicoot_conn.rollback()
```

With `autocommit=False`, updates are invisible to other queries until `commit()`. `/recommend` will see either all-old or all-new states, never a mix.

---

**Weekly Training Has No Progress Tracking (Lines 243-334)**

```python
# Step 2: Wait for training job (poll every 30 seconds)
while True:
    status = requests.get(f"{API_BASE}/jobs/{job_id}")
    if status["status"] == "success":
        break
    time.sleep(30)
```

**Problem:** Cloud Functions timeout after 60 minutes (default). If training takes 75 minutes, function crashes mid-wait.

**Better design:** Async with callback
```python
# Step 1: Trigger training with callback URL
train_response = requests.post(
    f"{API_BASE}/train_clusters",
    json={
        "callback_url": f"{API_BASE}/training_complete_webhook"
    }
)

# Step 2: Exit immediately
return {"status": "triggered", "job_id": job_id}

# Separate endpoint: /training_complete_webhook
@app.post("/training_complete_webhook")
def handle_training_complete(job_id: int, status: str):
    if status == "success":
        # Trigger index computation
        requests.post(f"{API_BASE}/precompute_indices", ...)
    else:
        notify_slack(f"❌ Training failed: {job_id}")
```

This decouples long-running training from Cloud Function timeout.

---

### 7. Cross-Cutting Concerns

#### Security 🔒

**API Key Rotation (Lines 22-46 in API design)**

You mention "rotate keys quarterly." **This is manual**. What's the process?

1. Generate new key in Secret Manager
2. Update Cloud Run environment variables
3. Give new key to Suvita team
4. Wait for them to update their scripts
5. Disable old key

**Step 4 is the blocker.** If Suvita doesn't update immediately, their integration breaks.

**Better approach:** Dual key support
```python
VALID_API_KEYS = [
    os.getenv("BANDICOOT_API_KEY_PRIMARY"),
    os.getenv("BANDICOOT_API_KEY_SECONDARY")
]

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
```

**Rotation process:**
1. Add new key as SECONDARY
2. Give to Suvita, ask them to switch "within 2 weeks"
3. After 2 weeks, promote SECONDARY to PRIMARY, delete old key

This gives them a grace period instead of immediate breakage.

---

#### Observability 📊

**Missing: Request Tracing**

You have logging. You have metrics. But do you have **distributed tracing**?

When `/recommend` is slow, you need to know:
- Was it PostgreSQL query? (5ms vs 200ms)
- Was it Redis lookup? (should be <1ms)
- Was it JSON serialization? (10ms for 100 caregivers)

Add OpenTelemetry:
```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

@app.get("/recommend")
async def recommend(budget: int):
    with trace.get_tracer(__name__).start_as_current_span("fetch_states"):
        # PostgreSQL query
        caregivers = db.execute(query).fetchall()

    with trace.get_tracer(__name__).start_as_current_span("lookup_indices"):
        # Redis lookups
        for cg in caregivers:
            index = redis_client.get(...)
```

Export traces to Cloud Trace. Now when latency spikes, you can pinpoint which span is slow.

**Cost:** $0 (Cloud Trace free tier is generous)
**Effort:** 2 hours to instrument
**Value:** Massive (saves hours of debugging in production)

---

#### Testing Strategy (Underspecified)

You mention unit tests, integration tests, load tests. But no **test coverage targets**.

**Add to PRD:**
```
Acceptance Criteria for "Done":
1. ✅ Unit tests with ≥80% line coverage
2. ✅ Integration tests for all P0 API endpoints
3. ✅ Load test: 1000 concurrent /recommend requests, p95 <500ms
4. ✅ Chaos test: Kill Redis mid-request, verify graceful degradation
```

**Chaos test** is critical. What happens if:
- Redis is unreachable → Fallback to PostgreSQL (slower but functional)
- PostgreSQL is down → Return HTTP 503 with retry-after header
- Both down → Return cached recommendations from 24h ago

Document these failure modes. Test them. Don't discover them at 2am on launch day.

---

## What's Missing Entirely

### 1. **Data Privacy / PHI Handling**

You're dealing with caregiver names, phone numbers, vaccination records. This is **PHI (Protected Health Information)** in many jurisdictions.

Questions you haven't answered:
- Are you HIPAA-compliant? (probably not required for NGO, but check)
- Do you log caregiver IDs in plaintext? (current code: yes)
- Can Suvita team members query raw data in PostgreSQL? (access control?)

**Minimum bar for MVP:**
- Encrypt database at rest (Cloud SQL: enable by default)
- Don't log `caregiver_id` in structured logs (use hashed ID)
- API keys should have permissions (read-only vs admin)

Add to PRD under P1:
```
#### 14. Data Privacy (P1, Week 4)
- Encrypt all PII fields in database
- Audit log for all data access (who queried which caregiver_id, when)
- API keys with scoped permissions (Suvita gets read-only key)
```

---

### 2. **Incident Response Plan**

You have monitoring. You have rollback. But no **runbook**.

What if:
- **Scenario 1:** `/recommend` returns empty list (bug in Whittle solver)
  - Detection: Alert fires within 5 minutes
  - Response: ???

- **Scenario 2:** Training job fails 3 weeks in a row (data pipeline broken)
  - Detection: "Last training >10 days" alert
  - Response: ???

**Create a runbook:**
```markdown
# Incident Response: Empty Recommendations

## Symptoms
- /recommend returns {"recommendations": []}
- No alerts in PostgreSQL or Redis

## Diagnosis
1. Check latest model version: SELECT * FROM models WHERE status='active'
2. Check if Whittle indices exist: redis-cli KEYS whittle:*
3. Check training job logs: gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=weekly_training" --limit 50

## Mitigation
- Rollback to previous model version: UPDATE models SET status='active' WHERE model_version='v1.0.1'
- Manually trigger training: curl -X POST https://bandicoot-api.run.app/train_clusters ...

## Prevention
- Add test: "Recommendations endpoint should return >0 results for any budget >0"
```

Write 3-5 runbooks in Week 5. Rehearse them. You want to be bored when incidents happen ("oh this again, I know exactly what to do"), not panicked.

---

### 3. **User Feedback Loop**

PRD mentions Suvita Program Manager needs "feedback mechanism if recommendations seem wrong" (line 50). But **how**?

Options:
1. **Slack channel:** Suvita team posts "Caregiver CG-12345 was recommended but already vaccinated"
2. **Feedback API:** `POST /feedback` with `{caregiver_id, issue, notes}`
3. **Weekly survey:** "Rate quality of this week's recommendations 1-5"

For MVP, even option 1 (Slack) is valuable. You'll learn:
- Are recommendations useful?
- What edge cases are you missing?
- Is the system actually helping or just generating noise?

Add to Week 6 launch checklist:
```
- [ ] Create #bandicoot-feedback Slack channel
- [ ] Invite Suvita Program Manager and Health Worker lead
- [ ] Ask them to report 3 examples: good recommendation, bad recommendation, confusing recommendation
```

Review feedback in Week 7-8. If 50%+ of recommendations are flagged as "bad," you have a model problem. If <10%, you're on the right track.

---

## Final Recommendations

### Must-Fix Before Launch 🚨

1. **Timeline:** Extend to 8-10 weeks (integration will take longer than expected)
2. **Data quality audit:** Week 1, analyze Suvita's actual data completeness
3. **Whittle solver numerical stability:** Add validation and fallback logic
4. **Idempotency on /train_clusters:** Prevent duplicate training jobs
5. **Database migration strategy:** Add Alembic or Flyway
6. **Monitoring:** Add "recommendation staleness" alert
7. **Incident runbooks:** Write 3-5 scenarios and rehearse

### Nice-to-Have (Post-Launch) 💡

1. **Request tracing:** OpenTelemetry for latency debugging
2. **Dual API key support:** Graceful key rotation
3. **Chaos testing:** Kill Redis, verify fallback to PostgreSQL
4. **User feedback channel:** Slack or API for Suvita to report issues
5. **Model quality metrics:** Track "% of FO-mapped caregivers that get reassigned"

---

## Overall Verdict

This is a **B+ architecture** for an MVP. You've clearly learned from SAHELI and made smart trade-offs (clustering vs. individual, pre-computed indices, cost-optimized deployment).

**What would make it an A:**
- More realistic timeline (8-10 weeks, not 6)
- Deeper data quality analysis upfront
- Better error handling in Whittle solver
- Incident response plans

**What would make it fail:**
- Ignoring data quality issues until Week 4 (too late to redesign)
- No rollback rehearsal (panic during production incident)
- Underestimating Suvita integration complexity (optimistic API assumptions)

**My advice:** Ship this, but **over-communicate risks** to Suvita. Tell them:
> "We're aiming for 6 weeks, but integration complexity might push us to 8-10 weeks. We'll know by Week 3 once we've seen your real data. The system is designed to degrade gracefully if anything breaks, but expect some rough edges in the first month."

Underpromise, overdeliver. They'll appreciate the honesty.

---

## Next Steps for You

1. **Review this critique** with your team
2. **Pick 5 items** from "Must-Fix Before Launch" to address in Week 1-2
3. **Schedule a data access meeting** with Suvita in next 48 hours
4. **Set up a weekly check-in** with me (MedhAI) to review progress

Happy to dive deeper on any section. Good luck with the MVP! 🚀

---

**Signed,**
**MedhAI**
*Ex-Google Principal Engineer, AI for Social Good*
*Mentor, Not Your Boss™*
