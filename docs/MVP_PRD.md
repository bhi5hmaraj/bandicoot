# Bandicoot MVP: Product Requirements Document

**Version:** 1.0
**Date:** November 2025
**Target Launch:** 6 weeks from start
**First Deployment:** Suvita (200,000+ caregivers)

---

## Executive Summary

Build a production-ready RMAB (Restless Multi-Armed Bandit) microservice that enables Suvita to intelligently prioritize which caregivers to contact for vaccination reminders, targeting a **25-35% reduction in dropout rates** based on proven Google/ARMMAN SAHELI results.

**MVP Goal:** Demonstrate measurable improvement over current random/heuristic allocation in a controlled A/B test within 6 weeks.

---

## Success Metrics

### Primary (Launch Blockers)
- ✅ **System operational** with <500ms p95 latency for `/recommend` endpoint
- ✅ **A/B test running** with ≥1000 caregivers in treatment group
- ✅ **Data pipeline functional** (ingesting SMS logs, vaccination records)
- ✅ **Cost ≤ $200/month** for 200K caregivers

### Secondary (Post-Launch)
- 📈 **10-15% improvement** in vaccination attendance vs control (Week 4-6)
- 📈 **Health worker efficiency** increase (calls per successful vaccination)
- 📈 **Model confidence** metrics improving over time (convergence)

---

## User Personas

### Primary User: Suvita Program Manager
**Needs:**
- Weekly prioritized list of caregivers to target for outreach
- Confidence that recommendations are better than random
- Simple dashboard to monitor system performance

**Pain Points:**
- Limited health worker bandwidth
- High dropout rates (~25-30% of children not fully vaccinated)
- No way to know who needs help most urgently

### Secondary User: Health Worker / Ambassador Coordinator
**Needs:**
- Clear action list: who to call/visit this week
- Context on why each caregiver is prioritized
- Feedback mechanism if recommendations seem wrong

---

## Core MVP Features

### P0 (Must-Have for Launch)

#### 1. Clustering & Parameter Learning
**User Story:** As a system, I need to learn engagement patterns from historical data to make intelligent recommendations.

**Acceptance Criteria:**
- [ ] Ingest historical SMS/call logs (past 6 months minimum)
- [ ] Cluster caregivers into ~20 groups based on passive transition behavior (k-means)
- [ ] Learn cluster-level MDP parameters using `bayesianbandits.DirichletClassifier`
- [ ] Store learned parameters in PostgreSQL
- [ ] Support periodic retraining (weekly batch job)

**Technical Details:**
- Use SAHELI's clustering approach (passive transition probabilities)
- Features: SMS open rate, days since last interaction, appointment attendance history
- Output: `cluster_id` and MDP parameters (P(S'|S,A), P(R|S,A)) per cluster

---

#### 2. Whittle Index Pre-Computation
**User Story:** As a system, I need to quickly rank caregivers by priority without real-time computation overhead.

**Acceptance Criteria:**
- [ ] Implement `planinf` function (adapted from SAHELI's Whittle solver)
- [ ] Pre-compute Whittle indices for all (cluster_id, state_id) pairs
- [ ] Store indices in Redis for O(1) lookup
- [ ] Support index refresh after parameter retraining

**Technical Details:**
- Binary search + value iteration algorithm
- Handle sleeping state (η=+∞ approximation → ~4 core states)
- Compute time: <5 minutes for 20 clusters × 4 states

---

#### 3. Features-Only (FO) Mapper
**User Story:** As a system, I need to assign new caregivers to clusters immediately upon enrollment.

**Acceptance Criteria:**
- [ ] Train RandomForest classifier: demographics → cluster_id
- [ ] Features: age, location (district), parity, phone number reliability, enrollment source
- [ ] Achieve ≥70% cluster assignment accuracy on validation set
- [ ] Support real-time prediction (<50ms)

**Technical Details:**
- Use `scikit-learn.RandomForestClassifier`
- Train on historical caregivers with known cluster assignments
- Persist model as pickle/joblib artifact

---

#### 4. State Tracking
**User Story:** As a system, I need to maintain current engagement state for each caregiver to compute accurate recommendations.

**Acceptance Criteria:**
- [ ] Define 2-state model: `Responsive` (interacted with SMS recently) vs `Unresponsive`
- [ ] Update states based on SMS delivery logs and clinic attendance
- [ ] Store current state in PostgreSQL with timestamp
- [ ] Support bulk state updates (batch processing)

**Technical Details:**
- State transition rules:
  - SMS opened/clicked within 7 days → `Responsive`
  - No interaction for 7+ days → `Unresponsive`
  - Vaccination completed → bonus reward, stay in current state
- Table: `caregiver_states(id, cluster_id, current_state, last_updated)`

---

#### 5. Recommendation API
**User Story:** As a Program Manager, I need a weekly list of top-K caregivers to prioritize for outreach.

**Acceptance Criteria:**
- [ ] `GET /recommend?budget=<K>` endpoint returns JSON list of caregiver IDs
- [ ] Recommendations based on pre-computed Whittle indices
- [ ] Support filtering by district/region
- [ ] Response time <500ms for K=100
- [ ] Include confidence score per recommendation

**API Response:**
```json
{
  "recommendations": [
    {
      "caregiver_id": "CG-12345",
      "priority_score": 0.87,
      "current_state": "Unresponsive",
      "cluster_id": 5,
      "reason": "High risk of dropout, responsive to interventions",
      "child_name": "Anonymized",
      "district": "Bihar-Patna"
    }
  ],
  "metadata": {
    "total_evaluated": 150000,
    "budget": 100,
    "generated_at": "2025-11-22T10:30:00Z",
    "model_version": "v1.0.2"
  }
}
```

---

#### 6. Training/Admin API
**User Story:** As a Data Engineer, I need endpoints to retrain models and update system state.

**Acceptance Criteria:**
- [ ] `POST /train_clusters` - Trigger clustering and parameter learning
- [ ] `POST /precompute_indices` - Recompute Whittle indices
- [ ] `POST /assign_cluster` - Assign/reassign caregiver to cluster
- [ ] `POST /update_state` - Update caregiver engagement state (bulk or single)
- [ ] Authentication required (API key)

---

#### 7. Data Integration
**User Story:** As a system, I need to continuously ingest data from Suvita's existing infrastructure.

**Acceptance Criteria:**
- [ ] Connect to Suvita's PostgreSQL database (caregiver registry)
- [ ] Ingest SMS logs (delivery, opens, clicks) from existing system
- [ ] Ingest vaccination records from government RCH database (or Suvita's mirror)
- [ ] Support both batch (nightly) and streaming (Pub/Sub) ingestion

**Data Sources:**
1. **Caregiver Registry:** Demographics, contact info, child vaccination schedule
2. **SMS Logs:** Message sent, delivered, opened, clicked timestamps
3. **Vaccination Records:** Clinic visits, vaccines administered
4. **Ambassador Activity:** Calls made, visit reports (if available)

---

#### 8. Cost-Optimized Deployment
**User Story:** As Suvita, I need the system to run reliably without exceeding our limited budget.

**Acceptance Criteria:**
- [ ] Deploy on Google Cloud Run (serverless, scales to zero)
- [ ] Use Cloud Functions for periodic batch jobs (training, index computation)
- [ ] Reuse Suvita's existing Cloud SQL instance (shared schema)
- [ ] Use Redis (Memorystore) only for hot data (indices, current states)
- [ ] Monthly cost ≤ $200 for 200K active caregivers

**Infrastructure:**
- **Compute:** Cloud Run (FastAPI service), Cloud Functions (batch jobs)
- **Storage:** PostgreSQL (persistent), Redis (cache)
- **Events:** Pub/Sub (optional, for streaming updates)
- **Monitoring:** Cloud Logging + simple dashboard

---

#### 9. Warmup Period
**User Story:** As a system, I should not make recommendations for new caregivers until sufficient data is collected.

**Acceptance Criteria:**
- [ ] Newly enrolled caregivers enter 6-week warmup period
- [ ] During warmup: collect SMS interaction data, assign to cluster via FO mapper
- [ ] After warmup: eligible for RMAB recommendations
- [ ] Warmup caregivers receive standard SMS schedule (no RMAB prioritization)

---

#### 10. Basic Monitoring
**User Story:** As a Program Manager, I need visibility into system health and model performance.

**Acceptance Criteria:**
- [ ] Dashboard showing:
  - Total caregivers active
  - Weekly recommendations generated
  - API latency (p50, p95, p99)
  - Model version and last training date
  - A/B test group sizes and vaccination rates
- [ ] Alerts for:
  - API errors/downtime
  - Recommendation generation failures
  - Database connection issues

**Implementation:**
- Use Cloud Monitoring + simple Grafana dashboard
- Export metrics via Prometheus format
- Alert via email/Slack webhook

---

### P1 (Important but Not Launch Blockers)

#### 11. A/B Testing Framework
**User Story:** As a researcher, I need to rigorously compare RMAB recommendations vs control.

**Acceptance Criteria:**
- [ ] Randomly assign caregivers to treatment (RMAB) or control (random) groups
- [ ] Ensure balanced distribution across districts/demographics
- [ ] Track outcomes separately per group
- [ ] Support gradual rollout (10% → 25% → 50% → 100%)

**Deferred to Week 3-4:** Can manually split caregivers initially, formalize framework post-launch.

---

#### 12. Explainability
**User Story:** As a Health Worker, I want to understand why a caregiver is prioritized.

**Acceptance Criteria:**
- [ ] Include human-readable "reason" in recommendation API
- [ ] Examples: "High dropout risk based on cluster history", "Missed last 2 vaccines, likely to respond to call"

**Deferred to Week 5-6:** Start with cluster ID + state, add narratives later.

---

### P2 (Future Enhancements - Post-MVP)

- ❌ Contextual features beyond clustering (MABWiser integration)
- ❌ Non-Markovian policies (time-series forecasting)
- ❌ Multi-channel optimization (SMS vs call vs ambassador visit)
- ❌ Real-time online learning (currently batch updates only)
- ❌ Mobile app for ambassadors
- ❌ Slack/WhatsApp bot for recommendations

---

## Technical Architecture

### System Diagram
```
┌─────────────────────────────────────────────────┐
│           Suvita Data Sources                   │
│  (PostgreSQL: Registry, SMS Logs, Vaccinations) │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │   ETL Pipeline        │
        │ (Cloud Functions)     │
        │ - Batch: Nightly      │
        │ - Stream: Pub/Sub     │
        └───────────┬───────────┘
                    │
                    ▼
┌───────────────────────────────────────────────────┐
│         Bandicoot RMAB Service (FastAPI)          │
│                  [Cloud Run]                      │
├───────────────────────────────────────────────────┤
│ Batch Endpoints:                                  │
│  POST /train_clusters                             │
│  POST /precompute_indices                         │
│  POST /assign_cluster                             │
│                                                   │
│ Real-Time Endpoints:                              │
│  POST /update_state                               │
│  GET  /recommend?budget=K                         │
├───────────────────────────────────────────────────┤
│ Core Logic:                                       │
│  - bayesianbandits (MDP learning)                 │
│  - scikit-learn (clustering, FO mapper)           │
│  - SAHELI Whittle solver (adapted planinf)        │
└───────────────────────────────────────────────────┘
         │                           │
         ▼                           ▼
┌────────────────┐          ┌────────────────┐
│  PostgreSQL    │          │  Redis         │
│  - Clusters    │          │  - Indices     │
│  - MDP params  │          │  - States      │
│  - States      │          │  (hot cache)   │
└────────────────┘          └────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│   Output: Priority Recommendations  │
│   → Suvita SMS System              │
│   → Ambassador Coordinator          │
└─────────────────────────────────────┘
```

---

## Data Schema

### Core Tables

#### `clusters`
```sql
CREATE TABLE clusters (
    cluster_id INT PRIMARY KEY,
    num_caregivers INT,
    mdp_params JSONB,  -- P(S'|S,A), P(R|S,A)
    last_trained TIMESTAMP,
    model_version VARCHAR(20)
);
```

#### `caregiver_states`
```sql
CREATE TABLE caregiver_states (
    caregiver_id VARCHAR(50) PRIMARY KEY,
    cluster_id INT REFERENCES clusters(cluster_id),
    current_state VARCHAR(20),  -- 'Responsive' or 'Unresponsive'
    last_updated TIMESTAMP,
    warmup_end_date DATE,
    ab_test_group VARCHAR(20)  -- 'treatment', 'control', or NULL
);
```

#### `whittle_indices`
```sql
CREATE TABLE whittle_indices (
    cluster_id INT,
    state VARCHAR(20),
    index_value FLOAT,
    computed_at TIMESTAMP,
    PRIMARY KEY (cluster_id, state)
);
```

#### `recommendations_log`
```sql
CREATE TABLE recommendations_log (
    id SERIAL PRIMARY KEY,
    caregiver_id VARCHAR(50),
    recommended_at TIMESTAMP,
    priority_score FLOAT,
    action_taken VARCHAR(50),  -- 'sms_sent', 'call_scheduled', 'none'
    outcome VARCHAR(50),  -- 'vaccinated', 'missed', 'pending'
    outcome_recorded_at TIMESTAMP
);
```

---

## Technology Stack

### Core Dependencies
```txt
# Python 3.10+
fastapi==0.104.0
uvicorn[standard]==0.24.0
bayesianbandits==1.0.0  # For RMAB learning
scikit-learn==1.3.0     # Clustering, FO mapper
numpy==1.24.0
pandas==2.0.0
redis==5.0.0
psycopg2-binary==2.9.0
pydantic==2.0.0
python-dotenv==1.0.0
```

### Infrastructure
- **Runtime:** Python 3.10
- **API Framework:** FastAPI (OpenAPI docs auto-generated)
- **Deployment:** Docker → Cloud Run
- **Database:** PostgreSQL 14+ (reuse Suvita's instance)
- **Cache:** Redis 7+ (Cloud Memorystore M1, 1GB)
- **Batch Jobs:** Cloud Functions (Python 3.10 runtime)
- **Monitoring:** Cloud Logging + Prometheus metrics

---

## Implementation Timeline (6 Weeks)

### Week 1-2: Core Infrastructure
- [x] Set up repository structure
- [ ] Implement clustering algorithm
- [ ] Adapt SAHELI's Whittle solver (`planinf`)
- [ ] Build FastAPI skeleton with auth
- [ ] Deploy to Cloud Run (staging)
- [ ] **Milestone:** `/train_clusters` endpoint working with synthetic data

### Week 3-4: Integration & Learning
- [ ] Connect to Suvita's PostgreSQL (read-only access)
- [ ] Ingest historical data (6 months of SMS/vaccination logs)
- [ ] Train initial clusters and FO mapper
- [ ] Pre-compute Whittle indices
- [ ] Implement `/recommend` endpoint
- [ ] **Milestone:** Generate first real recommendations (offline validation)

### Week 5: Testing & Refinement
- [ ] A/B test setup (assign caregivers to treatment/control)
- [ ] Integrate with Suvita's SMS system (write-back)
- [ ] Set up monitoring dashboard
- [ ] Batch state update pipeline (nightly)
- [ ] **Milestone:** System running end-to-end in staging

### Week 6: Launch & Monitor
- [ ] Deploy to production
- [ ] Start A/B test with 1,000 caregivers (500 treatment, 500 control)
- [ ] Daily monitoring of recommendations generated
- [ ] Weekly outcome tracking (vaccination rates)
- [ ] **Milestone:** MVP live, generating measurable insights

---

## Success Criteria for MVP Launch

### Technical Readiness
- ✅ All P0 features implemented and tested
- ✅ API latency <500ms p95 for `/recommend`
- ✅ Clustering accuracy ≥70% on validation set
- ✅ Infrastructure cost <$200/month
- ✅ No critical bugs in past 48 hours

### Data Readiness
- ✅ Historical data ingested (≥6 months)
- ✅ Clusters trained on ≥10,000 caregivers
- ✅ Current state synced for ≥100,000 active caregivers
- ✅ A/B test groups assigned and balanced

### Operational Readiness
- ✅ Suvita team trained on dashboard and API usage
- ✅ Alerting configured (email notifications)
- ✅ Incident response plan documented
- ✅ Rollback procedure tested

---

## Risks & Mitigations

### Risk: Data Quality Issues
**Impact:** Inaccurate recommendations if SMS logs incomplete or vaccination records delayed.

**Mitigation:**
- Work with Suvita to validate data completeness (spot-check 100 caregivers)
- Implement data quality checks in ETL pipeline
- Conservative state transitions (assume unresponsive if data missing)

---

### Risk: Model Doesn't Outperform Baseline
**Impact:** A/B test shows no improvement, project stalls.

**Mitigation:**
- Start with small test (1,000 caregivers) to fail fast
- If no signal by Week 4, investigate:
  - Are clusters meaningful? (manual review)
  - Are Whittle indices computed correctly? (unit tests)
  - Is data too noisy? (increase warmup period)
- Fallback: Use simpler heuristic (recency-based prioritization) as baseline

---

### Risk: Integration Complexity
**Impact:** Suvita's existing systems hard to integrate with, delays launch.

**Mitigation:**
- Week 1: Get read-only database access and schema documentation
- Build adapters for their data format (don't modify their system)
- If API integration fails, export recommendations as CSV (manual import)

---

### Risk: Cost Overruns
**Impact:** Infrastructure exceeds $200/month budget.

**Mitigation:**
- Monitor costs weekly (set GCP budget alerts at $150)
- Use preemptible VMs for batch jobs
- Scale Redis down to 512MB if 1GB unused
- Reduce recommendation frequency (weekly → bi-weekly) if needed

---

## Out of Scope for MVP

The following are **explicitly deferred** to post-launch iterations:

❌ **Contextual features beyond clustering** (demographics as direct inputs to policy)
❌ **Multi-channel optimization** (choosing SMS vs call vs ambassador visit)
❌ **Real-time learning** (online updates, currently batch-only)
❌ **Mobile app** for ambassadors
❌ **WhatsApp/Telegram integration**
❌ **Fairness constraints** (explicit equity objectives)
❌ **Advanced explainability** (counterfactual explanations)
❌ **Multi-language support** (API/dashboard English-only)
❌ **Self-service onboarding** (manual setup with Suvita team)

---

## Open Questions

1. **Data Access:** Do we have read access to Suvita's production database, or need export?
   → **Action:** Confirm with Suvita IT team by Week 1.

2. **SMS System Integration:** What API does Suvita's SMS provider expose?
   → **Action:** Get API docs for write-back (or fallback to CSV export).

3. **Vaccination Data Delay:** How long after clinic visit until RCH database updated?
   → **Action:** Analyze timestamps in historical data; adjust warmup if needed.

4. **Ambassador Activity Data:** Is this tracked digitally or only paper logs?
   → **Action:** Nice-to-have, not blocker; use SMS + vaccination only for MVP.

5. **A/B Test Ethics:** Does Suvita need ethics board approval for randomized assignment?
   → **Action:** Consult with Suvita leadership; ensure control group still gets standard care.

---

## Appendix: Key Decisions

### Why 2-State Model?
**Decision:** Start with `Responsive` / `Unresponsive` binary states.

**Rationale:**
- Simplicity reduces bugs and compute time
- SAHELI used 2-state in pilot before expanding
- Can extend to 3-4 states in Phase 2 if needed

**Trade-off:** May miss nuances (e.g., "lapsing" caregivers), but better to ship working MVP.

---

### Why Clustering vs. Individual Learning?
**Decision:** Use ~20 clusters, not per-caregiver MDPs.

**Rationale:**
- 200K individual MDPs = computationally expensive
- Data sparsity: many caregivers have <5 interactions
- SAHELI proved clustering works at scale
- Reduces overfitting

**Trade-off:** Less personalized, but gains from shared statistical strength.

---

### Why Pre-Compute Indices?
**Decision:** Compute Whittle indices offline (batch), cache in Redis.

**Rationale:**
- Real-time computation too slow for K=100 recommendations
- Indices only change when MDP parameters retrained (weekly)
- Redis lookup is O(1), <10ms

**Trade-off:** Slightly stale indices (up to 1 week old), acceptable for MVP.

---

## Acceptance Criteria for "Done"

An MVP feature is **done** when:
1. ✅ Code reviewed and merged to `main`
2. ✅ Unit tests pass with ≥80% coverage
3. ✅ Integration test on staging environment passes
4. ✅ API documentation updated (OpenAPI/Swagger)
5. ✅ Deployed to production (or marked as batch job)
6. ✅ Monitoring/alerting configured
7. ✅ Suvita team demoed and signed off

---

## Next Steps

1. **Week 0 (Pre-Development):**
   - [ ] Finalize data access agreements with Suvita
   - [ ] Set up GCP project and billing
   - [ ] Create GitHub repository with CI/CD
   - [ ] Schedule weekly sync with Suvita team

2. **Week 1 Kickoff:**
   - [ ] Environment setup (Docker, Cloud Run staging)
   - [ ] Implement clustering algorithm
   - [ ] Begin Whittle solver adaptation

3. **Week 2 Review:**
   - [ ] Demo `/train_clusters` with synthetic data
   - [ ] Review first batch of historical data from Suvita
   - [ ] Decide on A/B test cohort size

---

**Document Owner:** Bandicoot Core Team
**Stakeholders:** Suvita (Program Manager, IT Lead), Google AI for Social Good (Advisory)
**Review Cycle:** Weekly sprint reviews, bi-weekly stakeholder check-ins
**Success Review:** Week 8 (2 weeks post-launch) - Analyze A/B test results, decide on Phase 2 scope
