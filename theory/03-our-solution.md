# Our Solution: Bandicoot's RMAB System

**Level:** Semi-Technical (for engineers and data-savvy stakeholders)
**Prerequisites:** Read 01-rmab-fundamentals.md and 02-healthcare-problem.md
**Reading Time:** 25 minutes

---

## Design Philosophy

### Three Guiding Principles

**1. SAHELI-Inspired, Not SAHELI-Clone**
- Start with proven approach (Google/ARMMAN's deployment)
- Adapt to Suvita's context (smaller budget, different infrastructure)
- Simplify where possible (2-state model vs 4-state, pre-computed indices)

**2. MVP-First, Scale Later**
- Ship working system in 6-8 weeks
- Defer non-essential features (multi-channel, fairness constraints, real-time learning)
- Learn from production before over-engineering

**3. Cost-Optimized for NGOs**
- Target: <$200/month for 200K caregivers
- Serverless architecture (Cloud Run, Cloud Functions)
- Shared infrastructure with Suvita's existing systems

---

## System Architecture

### High-Level Overview

```
┌────────────────────────────────────────────────────────────┐
│                    Suvita Data Sources                     │
│     (PostgreSQL: Registry, SMS Logs, Vaccinations)         │
└─────────────────────────┬──────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   ETL Pipeline        │
              │  (Cloud Functions)    │
              │  • Nightly: States    │
              │  • Weekly: Training   │
              └───────────┬───────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────┐
│              Bandicoot RMAB Service (FastAPI)              │
│                      [Cloud Run]                           │
├────────────────────────────────────────────────────────────┤
│  Batch Endpoints:                                          │
│    POST /train_clusters      (trigger weekly training)     │
│    POST /precompute_indices  (recompute Whittle indices)   │
│    POST /assign_cluster      (onboard new caregivers)      │
│                                                            │
│  Real-Time Endpoints:                                      │
│    GET  /recommend?budget=K  (daily prioritization)        │
│    POST /update_state        (sync engagement states)      │
├────────────────────────────────────────────────────────────┤
│  Core Algorithms:                                          │
│    • K-Means Clustering (passive features)                 │
│    • Bayesian MDP Learning (bayesianbandits)               │
│    • Whittle Index Solver (binary search + value iter)     │
│    • Features-Only Mapper (RandomForest)                   │
└────────────────────────────────────────────────────────────┘
              │                           │
              ▼                           ▼
    ┌────────────────┐          ┌────────────────┐
    │  PostgreSQL    │          │  Redis         │
    │  • Clusters    │          │  • Indices     │
    │  • MDP params  │          │  • States      │
    │  • States      │          │  (hot cache)   │
    │  • Logs        │          └────────────────┘
    └────────────────┘
              │
              ▼
    ┌─────────────────────────────────────┐
    │  Output: Priority Recommendations   │
    │    → Suvita SMS System              │
    │    → Health Worker Dashboard        │
    └─────────────────────────────────────┘
```

---

## Core Components

### 1. Clustering Engine

**Purpose:** Group 200K caregivers into ~20 behavioral clusters

**Input:** Historical SMS logs (6 months minimum)
```python
{
  'caregiver_id': 'CG-12345',
  'sms_sent': '2025-05-01 10:00',
  'sms_delivered': '2025-05-01 10:02',
  'sms_opened': '2025-05-01 14:30',  # nullable
  'state_before': 'Responsive',
  'state_after': 'Responsive',
  'action': 'passive'  # or 'active'
}
```

**Algorithm:**
1. Extract passive transition probabilities per caregiver:
   ```
   Features = [P(R→R|passive), P(R→U|passive), P(U→R|passive), P(U→U|passive)]
   ```

2. K-means clustering with elbow method:
   ```python
   for k in range(15, 26):
       kmeans = KMeans(n_clusters=k, n_init=10)
       silhouette = silhouette_score(X, kmeans.labels_)

   k_optimal = argmax(silhouette)  # Typically 18-22
   ```

3. Store cluster assignments in PostgreSQL:
   ```sql
   UPDATE caregiver_states
   SET cluster_id = ?
   WHERE caregiver_id = ?
   ```

**Output:**
- Cluster assignments: `{caregiver_id: cluster_id}`
- Cluster centroids (for visualization)
- Silhouette score (quality metric)

**Frequency:** Weekly (Sunday 02:00)

---

### 2. MDP Learning Engine

**Purpose:** Learn transition/reward probabilities per cluster

**Input:** Historical data for caregivers in cluster C
```python
cluster_data = data[data['cluster_id'] == C]
```

**Algorithm (Bayesian):**
```python
from bayesianbandits import DirichletClassifier

model = DirichletClassifier(alpha=1.0)  # Laplace smoothing

# Learn P(s' | s, a) for each (state, action) pair
for state in ['Responsive', 'Unresponsive']:
    for action in ['active', 'passive']:
        transitions = cluster_data[
            (cluster_data['state_before'] == state) &
            (cluster_data['action'] == action)
        ]['state_after']

        model.update(state, action, transitions)

# Extract probabilities
P_transition = model.get_transition_probs()
P_reward = compute_reward_probs(cluster_data)
```

**Output (per cluster):**
```json
{
  "cluster_id": 5,
  "P_transition": {
    "Responsive": {
      "active": {"Responsive": 0.85, "Unresponsive": 0.15},
      "passive": {"Responsive": 0.60, "Unresponsive": 0.40}
    },
    "Unresponsive": {
      "active": {"Responsive": 0.50, "Unresponsive": 0.50},
      "passive": {"Responsive": 0.10, "Unresponsive": 0.90}
    }
  },
  "P_reward": {
    "Responsive": {"active": 0.80, "passive": 0.40},
    "Unresponsive": {"active": 0.30, "passive": 0.05}
  },
  "num_samples": 12500
}
```

**Storage:** PostgreSQL `clusters` table (JSONB column)

**Frequency:** Weekly (after clustering)

---

### 3. Whittle Index Solver

**Purpose:** Compute priority scores for each (cluster, state) pair

**Input:** MDP parameters from learning engine
```python
mdp_params = {
    'P_transition': {...},
    'P_reward': {...}
}
```

**Algorithm:**
```python
def compute_whittle_index(mdp_params, state):
    """
    Binary search for subsidy λ where V_passive = V_active
    """
    lambda_min, lambda_max = 0.0, 10.0

    while lambda_max - lambda_min > 1e-6:
        lambda_mid = (lambda_min + lambda_max) / 2

        # Value iteration for active policy
        V_active = value_iteration(
            mdp_params, policy='active', gamma=0.95
        )

        # Value iteration for passive policy (with subsidy)
        V_passive = value_iteration(
            mdp_params, policy='passive', gamma=0.95,
            subsidy=lambda_mid
        )

        # Adjust search bounds
        if V_active[state] > V_passive[state]:
            lambda_min = lambda_mid
        else:
            lambda_max = lambda_mid

    return lambda_mid


def value_iteration(mdp_params, policy, gamma, subsidy=0.0):
    """
    Standard value iteration for fixed policy
    """
    states = ['Responsive', 'Unresponsive']
    V = {s: 0.0 for s in states}

    for _ in range(1000):  # max iterations
        V_new = {}
        for s in states:
            r = mdp_params['P_reward'][s][policy]
            future = sum(
                mdp_params['P_transition'][s][policy][s_next] * V[s_next]
                for s_next in states
            )
            V_new[s] = r + gamma * future + subsidy

        # Check convergence
        if max(abs(V_new[s] - V[s]) for s in states) < 1e-6:
            return V_new

        V = V_new

    return V
```

**Output:**
```
Cluster 5:
  W(Responsive)   = 0.42
  W(Unresponsive) = 0.73

Cluster 12:
  W(Responsive)   = 0.38
  W(Unresponsive) = 0.91
```

**Storage:**
- PostgreSQL: `whittle_indices` table (persistent)
- Redis: Hot cache for O(1) lookup during `/recommend`

**Frequency:** Weekly (after MDP learning)

---

### 4. Features-Only (FO) Mapper

**Purpose:** Assign new caregivers to clusters based on demographics

**Input:** Caregiver demographics (no interaction history)
```python
{
  'age': 24,
  'district': 'Bihar-Patna',
  'parity': 1,  # number of children
  'phone_reliable': True,
  'enrollment_source': 'hospital'
}
```

**Training:**
```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder

# Prepare training data (historical caregivers with known clusters)
X = caregivers[['age', 'district', 'parity', 'phone_reliable', 'enrollment_source']]
y = caregivers['cluster_id']

# Train classifier
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    random_state=42
)
model.fit(X, y)

# Cross-validation
scores = cross_val_score(model, X, y, cv=5)
print(f"FO Mapper Accuracy: {scores.mean():.2f}")  # Target: ≥0.70
```

**Prediction (Cold-Start):**
```python
new_caregiver = {'age': 22, 'district': 'Bihar-Patna', ...}
predicted_cluster = model.predict([new_caregiver])[0]
```

**Storage:** Pickle file in Cloud Storage, loaded into Redis for fast prediction

**Frequency:** Weekly (retrain with updated cluster assignments)

---

### 5. State Tracking System

**Purpose:** Maintain current engagement state for each caregiver

**States:**
- **Responsive (R):** Opened SMS in last 7 days, attended recent appointment
- **Unresponsive (U):** No interaction in 7+ days

**Update Logic:**
```python
def update_caregiver_state(caregiver_id, sms_logs, vaccination_logs):
    """
    Determine state based on recent activity
    """
    cutoff = datetime.now() - timedelta(days=7)

    # Check SMS engagement
    recent_opens = sms_logs[
        (sms_logs['caregiver_id'] == caregiver_id) &
        (sms_logs['opened_at'] >= cutoff)
    ]

    # Check vaccination attendance
    recent_vaccinations = vaccination_logs[
        (vaccination_logs['caregiver_id'] == caregiver_id) &
        (vaccination_logs['actual_date'] >= cutoff)
    ]

    if len(recent_opens) > 0 or len(recent_vaccinations) > 0:
        return 'Responsive'
    else:
        return 'Unresponsive'
```

**Storage:**
```sql
CREATE TABLE caregiver_states (
    caregiver_id VARCHAR(50) PRIMARY KEY,
    cluster_id INT,
    current_state VARCHAR(20),  -- 'Responsive' or 'Unresponsive'
    last_updated TIMESTAMP,
    warmup_end_date DATE,
    ab_test_group VARCHAR(20)  -- 'treatment', 'control', NULL
);
```

**Update Frequency:** Nightly (01:00 IST)

---

### 6. Recommendation Engine

**Purpose:** Generate daily top-K prioritized caregivers

**API Endpoint:**
```
GET /recommend?budget=1000&district=Bihar-Patna
```

**Algorithm:**
```python
def recommend(budget: int, filters: dict):
    """
    Return top-K caregivers ranked by Whittle index
    """
    # 1. Fetch eligible caregivers
    caregivers = db.execute("""
        SELECT caregiver_id, cluster_id, current_state
        FROM caregiver_states
        WHERE warmup_end_date <= CURRENT_DATE
          AND ab_test_group IN ('treatment', NULL)
          AND district = ?
    """, filters['district']).fetchall()

    # 2. Lookup Whittle indices from Redis
    priorities = []
    for cg in caregivers:
        index_key = f"whittle:{cg.cluster_id}:{cg.current_state}"
        whittle_index = redis.get(index_key)
        priorities.append({
            'caregiver_id': cg.caregiver_id,
            'priority_score': float(whittle_index),
            'cluster_id': cg.cluster_id,
            'current_state': cg.current_state
        })

    # 3. Sort by index (descending) and take top-K
    priorities.sort(key=lambda x: x['priority_score'], reverse=True)
    top_k = priorities[:budget]

    # 4. Log recommendations for tracking
    log_recommendations(top_k)

    return {
        'recommendations': top_k,
        'metadata': {
            'total_evaluated': len(caregivers),
            'budget': budget,
            'generated_at': datetime.now().isoformat()
        }
    }
```

**Response:**
```json
{
  "recommendations": [
    {
      "caregiver_id": "CG-45678",
      "priority_score": 0.91,
      "current_state": "Unresponsive",
      "cluster_id": 12,
      "reason": "High dropout risk, responsive to interventions"
    },
    ...
  ],
  "metadata": {
    "total_evaluated": 145000,
    "budget": 1000,
    "generated_at": "2025-11-22T08:00:00Z"
  }
}
```

**Performance:**
- **Latency:** <500ms (p95)
- **Throughput:** 100 requests/min (more than sufficient)

---

## Data Flows

### Training Pipeline (Weekly)

```
Sunday 02:00
    │
    ├─> Extract historical data (6 months)
    │   └─> SELECT * FROM suvita.sms_logs WHERE sent_at >= '2025-05-22'
    │
    ├─> Cluster caregivers (k-means)
    │   └─> 20 clusters, silhouette score = 0.68
    │
    ├─> Learn MDP parameters per cluster (Bayesian)
    │   └─> Store in PostgreSQL: clusters.mdp_params
    │
    ├─> Compute Whittle indices (binary search)
    │   └─> 20 clusters × 2 states = 40 indices
    │
    ├─> Cache indices in Redis
    │   └─> SET whittle:5:Responsive 0.42
    │   └─> SET whittle:5:Unresponsive 0.73
    │
    └─> Train FO mapper (RandomForest)
        └─> Save model to Cloud Storage
        └─> Load into Redis for prediction

Total time: ~30 minutes
```

---

### Daily Recommendation Flow

```
Every morning 08:00
    │
    ├─> Suvita calls GET /recommend?budget=1000
    │
    ├─> Bandicoot fetches eligible caregivers
    │   └─> PostgreSQL: caregiver_states (WHERE warmup complete)
    │
    ├─> Lookup Whittle indices from Redis
    │   └─> O(1) per caregiver, <10ms total for 200K lookups
    │
    ├─> Sort by index, return top-1000
    │   └─> O(K log K) sorting
    │
    ├─> Log recommendations
    │   └─> PostgreSQL: recommendations_log
    │
    └─> Return JSON response

Latency: ~300ms (p95)
```

---

### Nightly State Update

```
Every night 01:00
    │
    ├─> Fetch recent SMS activity from Suvita DB
    │   └─> SELECT caregiver_id FROM sms_logs WHERE opened_at >= NOW() - 7 days
    │
    ├─> Fetch recent vaccinations
    │   └─> SELECT caregiver_id FROM vaccinations WHERE actual_date >= NOW() - 7 days
    │
    ├─> Update states in Bandicoot DB
    │   └─> UPDATE caregiver_states SET current_state = 'Responsive' WHERE ...
    │   └─> UPDATE caregiver_states SET current_state = 'Unresponsive' WHERE ...
    │
    └─> Sync to Redis cache
        └─> Update hot cache for fast /recommend lookups

Total time: ~2 minutes
```

---

## Key Design Decisions

### 1. Why 2-State Model (Not 4-State)?

**SAHELI used 4 states:**
- Responsive (engaged)
- Unresponsive (at-risk)
- Sleeping (recently contacted, can't contact again)
- Absorbed (completed program)

**We use 2 states (MVP):**
- Responsive
- Unresponsive

**Rationale:**
- ✅ Simpler to implement (fewer transitions to learn)
- ✅ Faster Whittle computation (2x speedup)
- ✅ Easier to explain to stakeholders
- ✅ SAHELI pilot also started with 2 states

**Future:** Add sleeping state in Phase 2 if over-contacting becomes an issue.

---

### 2. Why Pre-Compute Indices (Not Real-Time)?

**Alternative:** Compute Whittle index on-demand during `/recommend`

**Why we pre-compute:**
- ✅ Indices only change when MDP parameters update (weekly)
- ✅ Real-time computation: ~10s per (cluster, state) → 400s total
- ✅ Pre-computed + Redis lookup: <10ms
- ✅ Meets <500ms latency requirement

**Trade-off:** Indices are up to 7 days stale (acceptable for MVP)

---

### 3. Why Clustering (Not Individual RMABs)?

**Alternative:** Learn one RMAB per caregiver (200K RMABs)

**Why we cluster:**
- ✅ Computational: 20 RMABs vs 200K (10,000× reduction)
- ✅ Statistical: Caregivers with <5 interactions → sparse data → overfitting
- ✅ Proven: SAHELI used clustering at scale
- ✅ Scalable: Can grow to 1M caregivers without rearchitecture

**Trade-off:** Less personalized (but clusters capture behavioral variation)

---

### 4. Why Serverless (Cloud Run)?

**Alternative:** Always-on VM (Compute Engine)

**Why serverless:**
- ✅ Scales to zero when idle (save costs)
- ✅ Auto-scales on demand (handles traffic spikes)
- ✅ Pay-per-request pricing (aligns with NGO budget)
- ✅ Managed infrastructure (no ops overhead)

**Trade-off:** Cold start latency (mitigated by minScale=1)

**Cost comparison:**
```
Compute Engine (e2-small, 24/7):  ~$25/month
Cloud Run (with traffic):         ~$50/month
Cloud Run (idle):                 ~$15/month

Average (mix of idle + active):   ~$30/month
```

---

## Technology Stack

### Backend
- **Language:** Python 3.10+
- **Framework:** FastAPI (async, type-safe, auto-docs)
- **RMAB Library:** bayesianbandits (Bayesian MDP learning)
- **ML Library:** scikit-learn (clustering, FO mapper)
- **Database Driver:** psycopg2 (PostgreSQL), redis-py

### Infrastructure
- **Compute:** Cloud Run (API), Cloud Functions (batch jobs)
- **Storage:** PostgreSQL (persistent), Redis (cache)
- **Orchestration:** Cloud Scheduler (cron jobs)
- **Monitoring:** Cloud Logging, Prometheus, Grafana

### Deployment
- **Container:** Docker (multi-stage build)
- **CI/CD:** GitHub Actions
- **Secrets:** Secret Manager
- **Networking:** VPC, Cloud SQL Proxy

---

## Cost Breakdown (Target: <$200/month)

```
Cloud Run (API service):
  - 1M requests/month × $0.40/M = $0.40
  - 100 GB-hours compute × $0.24/GB-hr = $24
  - Total: ~$50/month

Cloud Functions (batch jobs):
  - Weekly training: 4 runs × 30 min × $0.10/hr = $2
  - Nightly state update: 30 runs × 2 min × $0.10/hr = $1
  - Total: ~$15/month

PostgreSQL (shared with Suvita):
  - Bandicoot schema: ~5GB storage
  - Marginal cost (shared instance): ~$30/month

Redis (Memorystore M1, 1GB):
  - Standard tier: $47/month

Cloud Storage (model artifacts):
  - 500MB × $0.02/GB = $0.01/month

Egress (API responses):
  - 50GB × $0.12/GB = $6/month

Monitoring (Cloud Logging):
  - 10GB logs × $0.50/GB = $5/month

──────────────────────────────────
Total: ~$153/month
──────────────────────────────────

Buffer: $47/month (for spikes, experimentation)
──────────────────────────────────
Total Budget: $200/month
```

---

## Performance Benchmarks

### Training Pipeline
| Task | Time | Frequency |
|------|------|-----------|
| Clustering (200K caregivers) | 15 min | Weekly |
| MDP learning (20 clusters) | 10 min | Weekly |
| Whittle indices (40 pairs) | 7 min | Weekly |
| FO mapper training | 5 min | Weekly |
| **Total** | **~30 min** | **Weekly** |

### API Endpoints
| Endpoint | Latency (p95) | Throughput |
|----------|---------------|------------|
| GET /recommend | <500ms | 100 req/min |
| POST /update_state | <100ms | 1000 req/min |
| POST /train_clusters | N/A (async) | 1 req/hour |

### Data Pipeline
| Task | Volume | Time |
|------|--------|------|
| Nightly state update | 200K caregivers | 2 min |
| Historical data ingest | 6 months × 200K | 10 min (one-time) |

---

## A/B Testing Strategy

### Study Design

**Treatment Group:**
- 1,000 caregivers
- Receive RMAB-prioritized outreach
- SMS/calls based on Whittle index rankings

**Control Group:**
- 1,000 caregivers
- Receive standard care (random/heuristic allocation)
- Same budget (balanced comparison)

**Randomization:**
- Stratified by district and age (ensure balanced demographics)
- Assigned at enrollment, persists for 6 months

**Blinding:**
- Health workers don't know which group (avoid bias)
- System tags recommendations, but UI doesn't show group

### Metrics

**Primary:**
- Vaccination completion rate (all doses)

**Secondary:**
- SMS open rate
- Time to vaccination (days from reminder to clinic visit)
- Cost per successful vaccination

**Guardrail:**
- No group should have <50% completion (ethical threshold)

### Analysis Plan

**Week 4-6:** Interim analysis
- Check for early signal (≥10% improvement → promising)
- Monitor for negative effects (stop if control outperforms)

**Week 8-12:** Final analysis
- Two-sample t-test: P(vaccination | treatment) vs P(vaccination | control)
- Power analysis: 1000 per group → 80% power to detect 10% difference

**Decision:**
- If treatment wins: Scale to 10K → 50K → full rollout
- If no difference: Debug (check data quality, model assumptions)
- If control wins: Investigate root cause, redesign

---

## Failure Modes & Mitigations

### 1. Training Job Fails
**Symptom:** No new model version for 2+ weeks

**Mitigation:**
- Alert: "Last training >10 days ago"
- Automatic retry (3 attempts with exponential backoff)
- Fallback: Use previous model version

### 2. Whittle Solver Diverges
**Symptom:** Index computation returns NaN or Inf

**Mitigation:**
- Validation: Check MDP params sum to 1.0
- Fallback: Use median index from other clusters
- Alert: Notify engineer to investigate

### 3. Redis Down
**Symptom:** `/recommend` latency spikes to 5s+

**Mitigation:**
- Graceful degradation: Fall back to PostgreSQL
- Circuit breaker: If Redis fails 3x, switch to DB for 5 min
- Alert: "Redis unreachable"

### 4. A/B Test Shows No Improvement
**Symptom:** Treatment and control have same vaccination rates

**Investigation:**
- Check data quality (are SMS opens being logged?)
- Check model quality (are clusters meaningful?)
- Check implementation (are recommendations actually being used?)

**Pivot:**
- Extend warmup period (6 weeks → 8 weeks)
- Increase cluster count (20 → 30)
- Add features to FO mapper

---

## Summary

### What We Built
- RMAB-based prioritization system for 200K caregivers
- Clustering for scalability (20 clusters)
- Whittle indices for optimal allocation
- Features-only mapper for cold-start
- Cost-optimized serverless architecture (<$200/month)

### Key Innovations
- Adapted SAHELI approach to NGO context (smaller budget)
- Pre-computed indices for <500ms latency
- Integrated with Suvita's existing infrastructure
- A/B testing framework for validation

### Expected Impact
- 20-26% improvement in vaccination completion
- 14,000+ children vaccinated per year
- $8K/month cost savings for Suvita

### Next Steps
- Week 1-2: Core infrastructure + algorithms
- Week 3-4: Suvita integration + initial training
- Week 5-6: A/B test setup + monitoring
- Week 8: Launch and evaluate

---

## Further Reading

- **04-whittle-index.md:** Deep dive into index computation
- **05-clustering-rationale.md:** Why clustering beats individual learning
- **docs/tech-design/:** Implementation details (6 documents)
- **mentor_notes.md:** MedhAI's architectural critique

---

**Author:** Bandicoot Team
**Last Updated:** November 2025
**Status:** MVP Design Complete, Implementation In Progress
