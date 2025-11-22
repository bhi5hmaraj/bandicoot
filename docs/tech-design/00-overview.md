# Bandicoot Technical Design: Overview

**Version:** 1.0
**Last Updated:** November 2025
**Status:** Draft

---

## Document Structure

This technical design is split into modular documents for maintainability:

1. **[00-overview.md](00-overview.md)** (this doc) - System overview and architecture
2. **[01-data-architecture.md](01-data-architecture.md)** - Database schema, data flows, storage
3. **[02-rmab-core.md](02-rmab-core.md)** - Clustering, Whittle index, SAHELI adaptations
4. **[03-api-design.md](03-api-design.md)** - FastAPI endpoints, authentication, rate limiting
5. **[04-deployment.md](04-deployment.md)** - Cloud Run, infrastructure, cost optimization
6. **[05-integration.md](05-integration.md)** - ETL pipelines, state updates, event handling

---

## System Architecture (High-Level)

```
┌─────────────────────────────────────────────────────────┐
│                   Suvita Data Sources                    │
│   (PostgreSQL: Registry, SMS Logs, Vaccination Records) │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────┐
         │    ETL Pipeline          │
         │  (Cloud Functions)       │
         │                          │
         │  • Batch: Nightly        │
         │  • Stream: Pub/Sub       │
         └──────────┬───────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────────────────┐
│          Bandicoot RMAB Service (FastAPI)                 │
│                  [Cloud Run]                              │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────┐        ┌─────────────────┐         │
│  │ Batch Endpoints │        │ Real-Time API   │         │
│  ├─────────────────┤        ├─────────────────┤         │
│  │ /train_clusters │        │ /recommend      │         │
│  │ /precompute_idx │        │ /update_state   │         │
│  │ /assign_cluster │        │ /health         │         │
│  └─────────────────┘        └─────────────────┘         │
│                                                           │
│  ┌───────────────────────────────────────────┐          │
│  │         Core RMAB Logic                   │          │
│  ├───────────────────────────────────────────┤          │
│  │  • bayesianbandits (MDP learning)         │          │
│  │  • scikit-learn (clustering, FO mapper)   │          │
│  │  • SAHELI Whittle solver (planinf)        │          │
│  └───────────────────────────────────────────┘          │
│                                                           │
└───────────────────────────────────────────────────────────┘
              │                           │
              ▼                           ▼
     ┌────────────────┐          ┌────────────────┐
     │  PostgreSQL    │          │     Redis      │
     │                │          │                │
     │ • Clusters     │          │ • Whittle      │
     │ • MDP params   │          │   indices      │
     │ • States       │          │ • Current      │
     │ • History      │          │   states       │
     └────────────────┘          │ (hot cache)    │
              │                  └────────────────┘
              ▼
┌──────────────────────────────────────┐
│  Output: Priority Recommendations    │
│                                      │
│  → Suvita SMS System                │
│  → Ambassador Coordinator            │
│  → Monitoring Dashboard              │
└──────────────────────────────────────┘
```

---

## Core Technology Stack

### Backend
- **Language:** Python 3.10+
- **API Framework:** FastAPI 0.104.0 (async, OpenAPI)
- **RMAB Library:** bayesianbandits 1.0.0 (Bayesian MDP learning)
- **ML/Clustering:** scikit-learn 1.3.0
- **Data Processing:** pandas 2.0.0, numpy 1.24.0

### Storage
- **Primary DB:** PostgreSQL 14+ (shared with Suvita)
- **Cache:** Redis 7+ (Cloud Memorystore, 1GB)
- **State:** PostgreSQL (persistent), Redis (hot reads)

### Infrastructure
- **Compute:** Google Cloud Run (serverless, auto-scaling)
- **Batch Jobs:** Cloud Functions (Python 3.10)
- **Events:** Pub/Sub (optional streaming)
- **Monitoring:** Cloud Logging, Prometheus, Grafana

### Deployment
- **Container:** Docker (multi-stage build)
- **Registry:** Google Container Registry (GCR)
- **IaC:** Terraform modules
- **CI/CD:** GitHub Actions

---

## Design Principles

### 1. SAHELI-Inspired Architecture
Based on proven deployment from Google/ARMMAN:
- **Clustering approach:** ~20 clusters, share MDP parameters
- **Features-Only mapping:** RandomForest for cold-start
- **Pre-computed indices:** O(1) lookup, batch updates
- **Warmup period:** 6 weeks data collection before RMAB

### 2. Cost Optimization
Target: **≤$200/month for 200K caregivers**
- Serverless-first (Cloud Run scales to zero)
- Reuse existing infrastructure (Suvita's PostgreSQL)
- Batch processing on preemptible VMs (60-90% savings)
- Minimal Redis footprint (1GB, indices only)

### 3. Simplicity & Reliability
- 2-state model (`Responsive` / `Unresponsive`)
- Batch updates (nightly) vs real-time complexity
- Fail-safe defaults (conservative state transitions)
- Human-in-the-loop (recommendations, not automation)

### 4. Delivery-Agnostic
- No hard dependency on Twilio or specific SMS provider
- Generic event bus (Pub/Sub or Kafka)
- CSV export fallback for manual processing
- API-first design

---

## Key Algorithms

### Clustering (SAHELI Method)
```python
# Based on passive transition probabilities
# ~20 clusters via k-means
# Feature: historical SMS engagement patterns

from sklearn.cluster import KMeans

# Extract passive transitions for each caregiver
passive_features = compute_passive_transitions(historical_data)

# Cluster into k groups
kmeans = KMeans(n_clusters=20, random_state=42)
cluster_ids = kmeans.fit_predict(passive_features)
```

### MDP Parameter Learning
```python
# Per-cluster, using bayesianbandits

from bayesianbandits import DirichletClassifier

for cluster_id in range(num_clusters):
    cluster_data = historical_data[cluster_data['cluster'] == cluster_id]

    # Learn P(S'|S,A) and P(R|S,A)
    agent = DirichletClassifier()
    agent.fit(cluster_data[['state', 'action']],
              cluster_data['next_state'])

    # Store parameters
    save_mdp_params(cluster_id, agent.get_params())
```

### Whittle Index (SAHELI planinf)
```python
# Binary search + value iteration
# Adapted from SAHELI's whittle_utils.py

def compute_whittle_index(mdp_params, state):
    """
    Compute Whittle index for a given state.
    Uses binary search to find subsidy λ where
    V_active(s) = V_passive(s) + λ
    """
    lambda_min, lambda_max = 0.0, 10.0

    while lambda_max - lambda_min > 1e-6:
        lambda_mid = (lambda_min + lambda_max) / 2

        # Value iteration with subsidy
        v_active = value_iteration(mdp_params, state, action='active')
        v_passive = value_iteration(mdp_params, state, action='passive') + lambda_mid

        if v_active > v_passive:
            lambda_min = lambda_mid
        else:
            lambda_max = lambda_mid

    return lambda_mid
```

---

## Data Flow

### 1. Training Flow (Weekly Batch)
```
Historical Data → Clustering → MDP Learning → Index Computation → Redis Cache
     (6 mo)         (~20)     (per cluster)      (pre-compute)     (O(1) lookup)
```

### 2. Recommendation Flow (On-Demand)
```
GET /recommend?budget=100
  ↓
Fetch current states (PostgreSQL)
  ↓
Lookup pre-computed indices (Redis)
  ↓
Sort by index, return top-K
  ↓
JSON response (< 500ms)
```

### 3. State Update Flow (Nightly)
```
SMS Logs → Parse interactions → Update states → PostgreSQL
            (delivered, opened)   (Responsive/    (bulk update)
                                   Unresponsive)
```

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| `/recommend` latency | <500ms p95 | Cloud Monitoring |
| Clustering time | <30 min for 200K | Batch job logs |
| Index computation | <5 min for 20×4 | Batch job logs |
| State update throughput | >1000/sec | ETL pipeline metrics |
| Monthly cost | ≤$200 | GCP billing |
| Availability | 99.5% | Uptime monitoring |

---

## Security & Privacy

### Data Protection
- **Anonymization:** Only caregiver IDs in RMAB system (no PII)
- **Encryption:** TLS in transit, at-rest encryption (PostgreSQL, Redis)
- **Access Control:** IAM roles, service accounts, API keys

### Authentication
- **API Keys:** Required for all endpoints except `/health`
- **Rate Limiting:** 100 req/min per API key
- **Audit Logs:** All `/train_*` and `/recommend` calls logged

### Compliance
- Follow Suvita's existing data governance policies
- No data leaves India (GCP asia-south1 region)
- GDPR-ready (right to deletion, data portability)

---

## Testing Strategy

### Unit Tests
- Core algorithms (clustering, Whittle solver)
- API endpoints (request/response validation)
- Coverage target: ≥80%

### Integration Tests
- End-to-end `/train_clusters` → `/recommend` flow
- Database transactions (PostgreSQL, Redis)
- Mock Suvita data sources

### Load Tests
- 1000 concurrent `/recommend` requests
- Bulk state updates (10K caregivers)
- Target: p95 latency <500ms under load

### A/B Test
- 1,000 caregivers (500 treatment, 500 control)
- Track vaccination rates over 4-6 weeks
- Statistical significance: p<0.05

---

## Monitoring & Observability

### Metrics (Prometheus)
- API request rate, latency, error rate
- Recommendation generation count
- Cache hit rate (Redis)
- Database query time

### Logs (Cloud Logging)
- Structured JSON logs (timestamp, level, message, context)
- Trace IDs for request correlation
- Error stack traces

### Alerts (Cloud Monitoring)
- API error rate >5% (5 min window)
- Latency p95 >1s (5 min window)
- Database connection failures
- Batch job failures

### Dashboards (Grafana)
- System health (uptime, latency, errors)
- RMAB metrics (recommendations generated, model version)
- A/B test results (vaccination rates by group)
- Cost tracking (GCP spend)

---

## Rollout Plan

### Phase 1: Staging (Weeks 1-4)
- Deploy to Cloud Run staging environment
- Synthetic data testing
- Internal team validation

### Phase 2: Pilot (Weeks 5-6)
- 1,000 caregivers A/B test
- Daily monitoring, weekly reviews
- Bug fixes, performance tuning

### Phase 3: Scale (Weeks 7-12)
- Gradual rollout: 10% → 25% → 50% → 100%
- Monitor impact at each stage
- Refine based on feedback

---

## Rollback Strategy

### Trigger Conditions
- API error rate >20% for >15 minutes
- Vaccination rate drops >10% vs control
- Cost exceeds $500/month
- Data corruption detected

### Rollback Process
1. Revert to previous Cloud Run revision (1-click)
2. Disable RMAB recommendations (fallback to random)
3. Investigate root cause
4. Fix and re-deploy to staging first

---

## Open Questions (To Resolve in Detailed Docs)

1. **Exact Whittle solver implementation:** Which variant of SAHELI's `planinf` to adapt?
2. **State transition thresholds:** 7-day window for `Responsive` vs `Unresponsive`?
3. **Cluster count tuning:** Start with k=20 or tune via elbow method?
4. **Redis eviction policy:** LRU or TTL-based for indices?
5. **PostgreSQL schema migration:** Alembic or manual SQL scripts?

These are addressed in detailed design docs (01-05).

---

## References

- MVP PRD: `docs/MVP_PRD.md`
- SAHELI Paper: Google Research (IAAI 2023)
- ARMMAN Field Study: Mate et al. (AAAI 2022)
- bayesianbandits docs: https://bayesianbandits.readthedocs.io
- Chat Archive: `archive/suvita_rmab_chat.md`

---

**Next Steps:**
1. Review detailed design docs (01-05)
2. Prototype Whittle solver with synthetic data
3. Set up Cloud Run staging environment
4. Request Suvita database schema and sample data
