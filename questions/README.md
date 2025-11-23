# Open Questions Tracker

This directory tracks unanswered questions, design decisions, and uncertainties across different aspects of the Bandicoot RMAB project.

## Summary Dashboard

**Total Questions:** 32 open questions across 4 categories
- **Critical Priority:** 8 questions (blocks deployment)
- **High Priority:** 7 questions (affects core functionality)
- **Medium Priority:** 13 questions (affects optimization)
- **Low Priority:** 4 questions (nice to have)

**By Status:**
- ❓ Open: 31 questions
- 🔍 Investigating: 1 question (JAX performance)
- ✅ Resolved: 4 questions

---

## All Questions at a Glance

| # | Question | Category | Priority | Impact | Key Stakeholder(s) |
|---|----------|----------|----------|--------|-------------------|
| **MODELING QUESTIONS** |
| 1 | [Optimal Number of Clusters (k)](./modelling.md#-optimal-number-of-clusters-k) | Modeling | High | High | Data Science, Suvita Product |
| 2 | [Discount Factor (gamma) Selection](./modelling.md#-discount-factor-gamma-selection) | Modeling | Medium | High | Data Science, Suvita Product |
| 3 | [State Definition and Granularity](./modelling.md#-state-definition-and-granularity) | Modeling | **Critical** | **Critical** | Data Science, Suvita Ops |
| 4 | [Action Definition: Intervention Types](./modelling.md#-action-definition-what-counts-as-intervention) | Modeling | **Critical** | **Critical** | Suvita Product, Suvita Ops |
| 5 | [Passive Transition Estimation](./modelling.md#-passive-transition-estimation) | Modeling | Medium | Medium | Data Science |
| 6 | [Time Granularity for Transitions](./modelling.md#-time-granularity-for-state-transitions) | Modeling | Medium | High | Data Science, Suvita Ops |
| 7 | [Handling Non-Stationarity](./modelling.md#-handling-non-stationarity) | Modeling | Low | Medium | Data Science |
| **SUVITA INTEGRATION** |
| 8 | [Historical Data Format & Availability](./suvita-integration.md#-historical-data-format-and-availability) | Integration | **Critical** | **Critical** | Suvita Engineering, Data Science |
| 9 | [Real-Time vs. Batch Recommendations](./suvita-integration.md#-real-time-vs-batch-recommendations) | Integration | **Critical** | **Critical** | Engineering, Suvita Ops |
| 10 | [State Observation Mechanism](./suvita-integration.md#-state-observation-mechanism) | Integration | **Critical** | **Critical** | Data Science, Suvita Engineering |
| 11 | [Intervention Budget Constraint](./suvita-integration.md#-intervention-budget-constraint) | Integration | High | High | Suvita Ops, Product |
| 12 | [Feedback Loop Design](./suvita-integration.md#-feedback-loop-how-to-improve-over-time) | Integration | Medium | High | Data Science, Engineering |
| 13 | [Multi-Arm vs. Single-Arm Deployment](./suvita-integration.md#-multi-arm-vs-single-arm-deployment) | Integration | Medium | Medium | Product, Suvita Leadership |
| 14 | [Personalization Beyond RMAB](./suvita-integration.md#-personalization-beyond-rmab) | Integration | Low | Low | Product (future scope) |
| 15 | [Handling New Caregivers (Cold Start)](./suvita-integration.md#-handling-new-caregivers-cold-start) | Integration | Medium | High | Data Science, Product |
| **TECHNICAL DESIGN** |
| 16 | [NumPy vs. JAX Performance](./tech-design.md#-numpy-vs-jax-performance-trade-off) 🔍 | Tech | Medium | Medium | Engineering, Data Science |
| 17 | [Deployment Architecture](./tech-design.md#-deployment-serverless-vs-server-based) | Tech | **Critical** | **Critical** | Engineering, DevOps |
| 18 | [Model Persistence & Versioning](./tech-design.md#-model-persistence-and-versioning) | Tech | High | High | Engineering, MLOps |
| 19 | [API Design (REST/gRPC/GraphQL)](./tech-design.md#-api-design-rest-vs-grpc-vs-graphql) | Tech | Medium | Medium | Engineering, Suvita Engineering |
| 20 | [Monitoring & Observability](./tech-design.md#-monitoring-and-observability) | Tech | High | High | Engineering, DevOps |
| 21 | [Database Selection](./tech-design.md#-database-for-storing-recommendations-and-history) | Tech | High | High | Engineering, Suvita Engineering |
| 22 | [Testing Strategy for Production](./tech-design.md#-testing-strategy-for-production) | Tech | **Critical** | **Critical** | Engineering, QA |
| 23 | [Model Drift & Retraining](./tech-design.md#-handling-model-drift-and-retraining) | Tech | Medium | High | Data Science, MLOps |
| 24 | [Multi-Tenancy Architecture](./tech-design.md#-multi-tenancy-one-model-or-multiple) | Tech | Low | Low | Engineering (future scope) |
| **EVALUATION & METRICS** |
| 25 | [Primary Success Metric](./evaluation.md#-primary-success-metric-what-are-we-optimizing) | Evaluation | **Critical** | **Critical** | Product, Suvita Leadership |
| 26 | [Evaluation Methodology (RCT/Quasi-Exp)](./evaluation.md#-evaluation-methodology-how-to-measure-causal-impact) | Evaluation | **Critical** | **Critical** | Data Science, Product |
| 27 | [Baseline Comparison Policy](./evaluation.md#-baseline-comparison-what-is-the-counterfactual) | Evaluation | High | High | Data Science, Suvita Ops |
| 28 | [Offline Evaluation Methods](./evaluation.md#-offline-evaluation-can-we-validate-before-deployment) | Evaluation | High | High | Data Science |
| 29 | [Online Metrics to Track](./evaluation.md#-online-metrics-what-to-track-in-production) | Evaluation | High | High | Product, Engineering |
| 30 | [A/B Test Design](./evaluation.md#-ab-test-design-stratification-and-blocking) | Evaluation | Medium | High | Data Science, Product |
| 31 | [Statistical Testing Criteria](./evaluation.md#-statistical-testing-how-to-declare-success) | Evaluation | Medium | High | Data Science |
| 32 | [Long-Term Impact Measurement](./evaluation.md#-long-term-evaluation-how-to-measure-sustained-impact) | Evaluation | Low | Medium | Product, Data Science |

**Legend:**
- 🔍 = Investigating (research in progress)
- **Critical** = Blocks deployment, must be resolved before production
- **High** = Core functionality affected, resolve in Phase 1
- **Medium** = Optimization opportunity, can iterate
- **Low** = Nice to have, can defer to Phase 2+

---

## Prioritized Action Plan

### 🚨 Phase 0: Pre-Deployment Blockers (8 Critical Questions)

**Must resolve before production deployment:**

1. **Define the fundamentals** (Week 1):
   - #3: State definition (binary vs. multi-level engagement)
   - #4: Action definition (what counts as intervention)
   - #25: Primary success metric (what are we optimizing?)
   - #8: Historical data format (understand what data is available)

2. **Design the system** (Week 2):
   - #10: State observation mechanism (how to determine current state)
   - #9: Real-time vs. batch architecture (operational model)
   - #17: Deployment architecture (infrastructure)
   - #22: Testing strategy (how to validate before go-live)

3. **Plan the evaluation** (Week 3):
   - #26: Evaluation methodology (RCT design)

**Stakeholder Meetings Required:**
- **Suvita Product & Leadership:** Questions #3, #4, #25, #9
- **Suvita Engineering:** Questions #8, #10, #17
- **Data Science Team:** Questions #3, #8, #10, #26, #22

---

### 📊 Phase 1: Core Functionality (7 High Priority Questions)

**Resolve during initial deployment:**

4. **Model tuning** (Weeks 4-6):
   - #1: Optimal number of clusters (data-driven selection)
   - #6: Time granularity (daily vs. weekly transitions)
   - #11: Intervention budget (understand constraints)

5. **Infrastructure** (Weeks 4-6):
   - #18: Model persistence & versioning (MLOps setup)
   - #20: Monitoring & observability (production monitoring)
   - #21: Database selection (data storage)

6. **Evaluation setup** (Weeks 4-6):
   - #27: Baseline comparison (define control policy)
   - #28: Offline evaluation (validate on historical data)
   - #29: Online metrics (production dashboards)

---

### ⚙️ Phase 2: Optimization (13 Medium Priority Questions)

**Iterate and improve post-launch:**

7. **Algorithm refinement:**
   - #2: Discount factor tuning
   - #5: Passive transition estimation
   - #15: Cold start handling
   - #23: Model drift & retraining

8. **System improvements:**
   - #12: Feedback loop design
   - #13: Deployment strategy (A/B test vs. full rollout)
   - #16: NumPy vs. JAX (if performance issues)
   - #19: API design refinement

9. **Evaluation rigor:**
   - #30: A/B test stratification
   - #31: Statistical testing criteria

---

### 🔮 Phase 3: Future Enhancements (4 Low Priority Questions)

**Nice to have, defer unless needed:**

10. **Future scope:**
    - #7: Non-stationarity handling
    - #14: Personalization beyond RMAB
    - #24: Multi-tenancy architecture
    - #32: Long-term impact measurement

---

## Question Categories

### 📊 [Modeling Questions](./modelling.md)
RMAB algorithm choices, mathematical assumptions, parameter tuning, and optimization strategies.

### 🔌 [Suvita Integration](./suvita-integration.md)
Questions about integrating Bandicoot with Suvita's production system, data pipelines, and deployment.

### 🏗️ [Technical Design](./tech-design.md)
Architecture decisions, performance optimization, scalability, and implementation choices.

### 📈 [Evaluation & Metrics](./evaluation.md)
How to measure success, A/B testing strategy, and performance metrics.

## How to Use This

1. **Add new questions** as they arise during development
2. **Mark status** for each question:
   - ❓ **Open** - Needs answer
   - 🔍 **Investigating** - Research in progress
   - ⚠️ **Blocked** - Waiting on external input
   - ✅ **Resolved** - Decision made (move to decisions/)
3. **Link to decisions** when questions are resolved
4. **Update regularly** during sprint planning and retrospectives

## Question Template

When adding a new question, use this format:

```markdown
## ❓ Question Title

**Status:** Open | Investigating | Blocked | Resolved
**Priority:** High | Medium | Low
**Category:** Modeling | Integration | Performance | etc.

### Context
Brief background on why this question matters.

### The Question
Clear articulation of what needs to be decided or answered.

### Options
- Option A: ...
- Option B: ...

### Implications
What depends on this decision?

### Next Steps
What needs to happen to resolve this?
```

## Recent Activity

- **2025-11-23**: Created questions tracker structure
- Track updates here as questions are added/resolved
