# Technical Design Questions

Architecture decisions, performance optimization, scalability, and implementation choices.

---

## ❓ NumPy vs. JAX Performance Trade-off

**Status:** Investigating
**Priority:** Medium
**Category:** Performance

### Context
We have a working NumPy implementation. JAX could provide 10-50x speedups via JIT compilation and GPU acceleration.

### The Question
Should we migrate to JAX, and if so, when?

### Current Status
- NumPy implementation: ✅ Complete and validated
- JAX prototype: ✅ Created (research/jax/)
- Benchmark: ❌ Not run yet

### Decision Criteria

**Use JAX if:**
- ✅ Performance benchmarks show >5x speedup
- ✅ Numerical validation passes (< 1e-6 error)
- ✅ Deployment complexity is manageable
- ✅ Team is comfortable with JAX

**Stick with NumPy if:**
- ❌ Speedup is marginal (< 2x)
- ❌ Deployment adds significant complexity
- ❌ Numerical issues arise
- ❌ Current performance is acceptable

### What We Need to Know

1. **Scale requirements:**
   - How many caregivers does Suvita have?
   - How many clusters?
   - How often do we need to recompute recommendations?

2. **Performance target:**
   - What is acceptable latency for recommendation generation?
   - Batch: Can we afford 10 minutes? 1 minute?
   - Real-time: Do we need <100ms? <1s?

3. **Infrastructure:**
   - Does Suvita have GPU access?
   - Container/Docker support?
   - Can we install JAX dependencies?

### Next Steps
1. Get Suvita scale requirements (number of caregivers, clusters)
2. Benchmark NumPy at target scale
3. If too slow, run JAX benchmarks
4. Make go/no-go decision on JAX migration

---

## ❓ Deployment: Serverless vs. Server-Based

**Status:** Open
**Priority:** High
**Category:** Deployment

### Context
We need to deploy Bandicoot as a service that generates recommendations.

### The Question
What deployment architecture should we use?

### Options

1. **Serverless Functions (e.g., AWS Lambda, Google Cloud Functions)**
   - API endpoint triggers function
   - Function loads model, generates recommendations, returns results
   - Pros: Auto-scaling, pay-per-use, zero server management
   - Cons: Cold start latency, memory limits, timeout limits (15 min max)

2. **Containerized Service (e.g., Docker on Kubernetes)**
   - Long-running service with HTTP API
   - Pros: Always warm, no timeout limits, full control
   - Cons: Need to manage scaling, more expensive (always running)

3. **Batch Job (e.g., Cron on VM, Kubernetes CronJob)**
   - Scheduled job runs daily to generate recommendations
   - Saves results to database
   - Pros: Simple, predictable, can use large compute
   - Cons: Not real-time, rigid schedule

4. **Hybrid: Batch + API**
   - Daily batch job computes bulk recommendations
   - API endpoint for on-demand refresh
   - Pros: Best of both worlds
   - Cons: More complex architecture

### Considerations

**Model Size:**
- How large are the fitted models? (cluster centroids, MDP parameters, Whittle indices)
- Can they fit in serverless memory limits (512MB - 10GB)?

**Compute Requirements:**
- CPU-bound (NumPy) vs. GPU-bound (JAX)
- If GPU needed, serverless is harder

**Latency:**
- Cold start: 1-10 seconds for serverless
- Warm service: <100ms for API response

**Cost:**
- Serverless: Pay per request (cheap if infrequent)
- Server: Pay for uptime (expensive if low traffic)

### Next Steps
1. Measure model size and compute requirements
2. Estimate request volume (requests/day, requests/second)
3. Understand Suvita's infrastructure (AWS? GCP? On-prem?)
4. Prototype deployment on target platform

---

## ❓ Model Persistence and Versioning

**Status:** Open
**Priority:** Medium
**Category:** MLOps

### Context
Trained models need to be saved, versioned, and loaded for inference.

### The Question
How do we persist and version Bandicoot models?

### Options

1. **Pickle (Python standard)**
   - Save fitted BandicootRMAB object directly
   - Pros: Simple, built-in
   - Cons: Not secure, version-dependent, not cross-language

2. **Custom Format (NumPy .npz)**
   - Save parameters separately: cluster centroids, MDPs, Whittle indices
   - Pros: Lightweight, version-independent, inspectable
   - Cons: Need serialization logic

3. **ONNX (Open Neural Network Exchange)**
   - Export to ONNX for cross-platform inference
   - Pros: Standard, language-agnostic, optimized runtime
   - Cons: Not designed for RMAB (more for neural nets)

4. **MLflow Model Registry**
   - Use MLflow to track experiments and models
   - Pros: Full lifecycle management, versioning, metadata
   - Cons: Requires MLflow infrastructure

5. **Protocol Buffers / FlatBuffers**
   - Define schema for model parameters
   - Pros: Efficient, version-safe, cross-language
   - Cons: More upfront work to define schema

### Model Versioning Strategy

**What to version:**
- Model parameters (cluster centroids, MDPs, Whittle indices)
- Model metadata (n_clusters, gamma, alpha, training date)
- Training data fingerprint (hash or stats)
- Code version (git commit hash)
- Performance metrics (validation scores)

**Versioning scheme:**
- Semantic versioning? (v1.2.3)
- Date-based? (2025-11-23)
- Sequential? (model-001, model-002)

### Next Steps
1. Define model artifact structure
2. Choose serialization format
3. Implement save/load methods in BandicootRMAB
4. Set up model registry (MLflow or custom)

---

## ❓ API Design: REST vs. gRPC vs. GraphQL

**Status:** Open
**Priority:** Medium
**Category:** System Architecture

### Context
If we deploy Bandicoot as a service, we need an API for clients to request recommendations.

### The Question
What API protocol should we use?

### Options

1. **REST API (JSON over HTTP)**
   - Endpoints: `POST /recommend`, `GET /cluster/:id`, etc.
   - Pros: Universal, easy to use, HTTP-friendly
   - Cons: Verbose, slower than binary protocols

2. **gRPC (Protocol Buffers over HTTP/2)**
   - Define service in .proto file
   - Pros: Fast, type-safe, efficient, supports streaming
   - Cons: Requires code generation, less universal

3. **GraphQL**
   - Client specifies exactly what data they need
   - Pros: Flexible, reduces over-fetching
   - Cons: Overkill for simple use case, added complexity

### Example API Design (REST)

```http
POST /api/v1/recommend
Content-Type: application/json

{
  "caregiver_ids": [1, 2, 3, 4, 5],
  "current_states": [0, 1, 0, 1, 0],
  "budget": 3
}

Response:
{
  "recommended_ids": [2, 4, 5],
  "priorities": [1.23, 1.15, 1.02],
  "model_version": "v1.0.0",
  "timestamp": "2025-11-23T10:30:00Z"
}
```

```http
GET /api/v1/clusters/summary

Response:
{
  "clusters": [
    {
      "cluster_id": 0,
      "n_caregivers": 150,
      "w_responsive": 0.35,
      "w_unresponsive": 0.85,
      "retention_R": 0.82,
      "recovery_U": 0.34
    },
    ...
  ]
}
```

### Next Steps
1. Define API requirements with Suvita team
2. Design endpoint schema
3. Implement REST API (start simple)
4. Consider gRPC if performance becomes issue

---

## ❓ Monitoring and Observability

**Status:** Open
**Priority:** Medium
**Category:** MLOps

### Context
Once deployed, we need to monitor model performance and system health.

### The Question
What should we monitor, and how?

### Metrics to Track

**System Metrics:**
- Request latency (p50, p95, p99)
- Request volume (requests/second)
- Error rate (4xx, 5xx responses)
- Resource usage (CPU, memory, GPU)

**Model Metrics:**
- Recommendation quality (if ground truth available)
- Cluster distribution (are clusters balanced?)
- Whittle index distribution (reasonable range?)
- State distribution (% responsive vs. unresponsive)

**Business Metrics:**
- Engagement rate (% caregivers who respond after intervention)
- Retention rate (% caregivers still engaged after N days)
- Budget utilization (% of recommended interventions actually performed)
- Coverage (% of caregivers receiving recommendations)

### Monitoring Stack Options

1. **Prometheus + Grafana**
   - Prometheus: Metrics collection and storage
   - Grafana: Visualization and alerting
   - Pros: Industry standard, powerful, flexible
   - Cons: Requires infrastructure setup

2. **Cloud Provider Monitoring**
   - AWS CloudWatch, GCP Cloud Monitoring, Azure Monitor
   - Pros: Integrated, easy setup
   - Cons: Vendor lock-in, can be expensive

3. **Application Performance Monitoring (APM)**
   - Datadog, New Relic, Sentry
   - Pros: Full-stack visibility, anomaly detection
   - Cons: Can be expensive

4. **Lightweight: Logging + Alerts**
   - Structure logs with metrics
   - Alert on anomalies
   - Pros: Simple, low overhead
   - Cons: Less visibility, manual analysis

### Alerting Strategy

**When to alert:**
- Latency >2x baseline
- Error rate >5%
- Model metrics out of expected range
- Business metrics degrading (e.g., engagement drops 20%)

**Who to alert:**
- On-call engineer (system issues)
- Data scientist (model drift)
- Product team (business impact)

### Next Steps
1. Choose monitoring stack aligned with Suvita's infrastructure
2. Instrument code with metrics and logging
3. Create dashboards for key metrics
4. Set up alerting rules

---

## ❓ Database for Storing Recommendations and History

**Status:** Open
**Priority:** Medium
**Category:** System Architecture

### Context
We may need to store generated recommendations, outcomes, and historical data.

### The Question
What database should we use for storing RMAB-related data?

### Data to Store

1. **Generated Recommendations:**
   - Which caregivers were recommended
   - Their priority scores
   - When the recommendation was generated
   - Model version used

2. **Intervention Outcomes:**
   - Was the recommended intervention performed?
   - What was the outcome? (replied, no response, etc.)
   - When did the outcome occur?

3. **Model Artifacts:**
   - Trained model parameters
   - Training metadata
   - Performance metrics

4. **Caregiver State History:**
   - Time-series of state changes
   - Intervention history
   - Features for cold-start

### Database Options

1. **PostgreSQL (Relational)**
   - Structured tables, ACID transactions
   - Pros: Mature, queryable, good for analytics
   - Cons: Schema rigidity, horizontal scaling harder

2. **MongoDB (Document Store)**
   - Flexible JSON documents
   - Pros: Schema flexibility, easy to scale
   - Cons: Less structure, eventual consistency

3. **TimescaleDB (Time-Series)**
   - PostgreSQL extension for time-series data
   - Pros: Optimized for time-series queries, retention policies
   - Cons: Requires PostgreSQL

4. **S3 + Parquet (Data Lake)**
   - Store data in columnar format on object storage
   - Pros: Cheap, scalable, queryable with Athena/Spark
   - Cons: Not real-time, complex for transactional workloads

5. **Redis (In-Memory Cache)**
   - Store current state and recent recommendations
   - Pros: Very fast, good for real-time lookups
   - Cons: Not persistent (needs backup), expensive for large data

### Hybrid Approach

**Hot data (recent, frequently accessed):** Redis cache
**Warm data (current cycle):** PostgreSQL
**Cold data (historical):** S3 + Parquet

### Next Steps
1. Understand Suvita's existing database infrastructure
2. Define data retention requirements
3. Design database schema
4. Implement data access layer

---

## ❓ Testing Strategy for Production

**Status:** Open
**Priority:** High
**Category:** Software Engineering

### Context
We have 67 unit/integration tests for the library. But we need additional testing for production deployment.

### The Question
What additional testing do we need before production deployment?

### Testing Levels

1. **Unit Tests (✅ Complete)**
   - Test individual components (Whittle solver, MDP learner, etc.)
   - 67 tests, 100% passing

2. **Integration Tests (✅ Complete)**
   - Test end-to-end workflow
   - Included in test suite

3. **Performance Tests (❌ TODO)**
   - Benchmark latency at scale
   - Test with 10K, 100K, 200K caregivers
   - Identify bottlenecks

4. **Load Tests (❌ TODO)**
   - Simulate high request volume
   - Test API under load (100 req/s, 1000 req/s)
   - Check for memory leaks, resource exhaustion

5. **Data Validation Tests (❌ TODO)**
   - Test with real Suvita data
   - Check for edge cases in production data
   - Validate state assignments

6. **Shadow Testing (❌ TODO)**
   - Run Bandicoot in parallel with current system
   - Compare recommendations (without acting on them)
   - Build confidence before full deployment

7. **A/B Testing (❌ TODO)**
   - Randomize caregivers to Bandicoot vs. control
   - Measure causal impact on engagement
   - Statistical rigor for evaluation

### Test Infrastructure Needs

**Performance/Load Testing:**
- Tools: pytest-benchmark, locust, k6
- Infrastructure: Staging environment at production scale

**Shadow Testing:**
- Logging infrastructure to capture parallel recommendations
- Analytics pipeline to compare systems

**A/B Testing:**
- Randomization service
- Metric tracking and statistical analysis
- Guardrails (stop if harm detected)

### Next Steps
1. Set up performance benchmarking suite
2. Create staging environment with production-scale data
3. Design shadow testing pipeline
4. Define A/B test protocol and success criteria

---

## ❓ Handling Model Drift and Retraining

**Status:** Open
**Priority:** Medium
**Category:** MLOps

### Context
Caregiver behavior may change over time, causing model performance to degrade.

### The Question
How do we detect and handle model drift?

### Types of Drift

1. **Data Drift:**
   - Input distribution changes (e.g., more new caregivers, different demographics)
   - Detection: Monitor feature distributions, use KS test or PSI

2. **Concept Drift:**
   - Relationship between inputs and outputs changes (e.g., interventions become less effective)
   - Detection: Monitor outcome metrics, performance degradation

3. **Label Drift:**
   - Definition of "engaged" changes (e.g., policy change, new engagement channels)
   - Detection: Monitor label distributions, consult with domain experts

### Drift Detection Methods

1. **Statistical Tests:**
   - Kolmogorov-Smirnov test for distribution change
   - Population Stability Index (PSI)
   - Alert if drift > threshold

2. **Performance Monitoring:**
   - Track engagement rate, retention rate
   - Alert if metrics drop > X%

3. **Manual Review:**
   - Periodic (weekly/monthly) review of model behavior
   - Spot-check recommendations

### Retraining Strategy

**When to retrain:**
- Scheduled: Every week/month regardless of drift
- Triggered: When drift detected above threshold
- On-demand: When new intervention types added, policy changes

**How to retrain:**
- Full retrain: Use all historical data
- Incremental: Update with recent data only
- Sliding window: Use last N months only

**Validation before deployment:**
- Offline validation on held-out data
- Shadow testing (parallel run)
- Gradual rollout (10% → 50% → 100%)

### Next Steps
1. Implement drift detection monitoring
2. Define retraining triggers and cadence
3. Automate retraining pipeline
4. Set up model validation and rollback procedures

---

## ❓ Multi-Tenancy: One Model or Multiple?

**Status:** Open
**Priority:** Low
**Category:** System Design

### Context
If Bandicoot is deployed to multiple organizations (not just Suvita), how do we handle multi-tenancy?

### The Question
Should we train one shared model or separate models per organization?

### Options

1. **One Model Per Tenant (Isolated)**
   - Pros: Privacy, custom parameters, no interference
   - Cons: Less data per model, more infrastructure

2. **Shared Model (Pooled)**
   - Train on data from all tenants
   - Pros: More data, better estimates, shared learning
   - Cons: Privacy concerns, cross-contamination

3. **Hierarchical: Shared Base + Tenant Customization**
   - Pre-train on pooled data
   - Fine-tune on tenant-specific data
   - Pros: Best of both worlds
   - Cons: More complex

4. **Federated Learning**
   - Train local models at each tenant
   - Aggregate parameters centrally
   - Pros: Privacy-preserving, collaborative
   - Cons: Very complex, requires coordination

### Current Status
- Single tenant (Suvita) for now
- Can defer this decision until multi-tenancy needed

### Next Steps
- Monitor: If we get second customer, revisit this question

---

## ✅ Resolved Questions

*Resolved questions will be moved here with links to decision documents*

### Programming Language: Python
**Decision:** Use Python for implementation
**Rationale:** Standard for ML, team expertise, rich ecosystem (NumPy, scikit-learn, pandas)
**Date:** 2025-11-22

### Testing Framework: pytest
**Decision:** Use pytest for all testing
**Rationale:** Standard Python testing framework, good fixture support
**Date:** 2025-11-22

### Code Structure: SOLID Principles
**Decision:** Follow SOLID design, avoid over-abstraction
**Rationale:** Maintainable, testable, easy to understand
**Date:** 2025-11-22
