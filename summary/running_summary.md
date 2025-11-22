# Bandicoot Project - Running Summary

## Overview (Lines 1-1000)

### What is this project?
**Bandicoot** appears to be a project to build an **RMAB (Restless Multi-Armed Bandit) optimization system** for maternal and child health outreach programs, specifically for an organization called **Suvita**.

### The Problem Being Solved
- Maternal health programs have limited health worker resources
- Need to prioritize which expectant/new mothers to contact (call/SMS) to maximize engagement
- Current methods are random or use simple heuristics
- Dropout rates are high (~35%)

### The Solution
Build an AI-powered system using **Restless Multi-Armed Bandits** that:
- Learns from historical engagement data
- Predicts which beneficiaries are most likely to benefit from contact
- Prioritizes outreach to maximize engagement
- Reduces dropout rates by 25-35%

### Proven Success
- **Google Research + ARMMAN NGO** deployed this in India
- Served 100K+ beneficiaries, scaled to 3 million
- **30% reduction in dropout rates** (from ~35% to ~24%)
- **SAHELI** system is first production RMAB in public health

### Technical Approach

#### Core Components:
1. **RMAB Microservice** - Standalone API with two endpoints:
   - `POST /infer` - Offline parameter estimation from historical data
   - `POST /recommend` - Real-time prioritized list of who to contact

2. **Integration Strategy**:
   - Abstract away Suvita's existing ETL pipeline
   - Expose clean REST API
   - Can be called as Cloud Function
   - Minimal disruption to existing workflows

3. **Libraries Being Considered**:
   - **bayesianbandits** - Supports restless bandits, delayed rewards
   - **MABWiser** - Scikit-learn style API from Fidelity
   - **SMPyBandits** - 65+ classical MAB algorithms
   - **Vowpal Wabbit** - Production-scale (Yahoo/Microsoft)
   - **Ray RLlib** - Scalable multi-node

4. **Best for MVP (4-6 weeks)**:
   - bayesianbandits or MABWiser for quick prototyping
   - FastAPI for REST wrapper
   - Twilio for SMS/call integration
   - Docker + Cloud deployment

### Research Papers Leveraged:
1. **SAHELI** - First production RMAB in public health
2. **Decision-Focused Learning** - Train models to optimize deployment metrics directly
3. **BCoR** - Bayesian contextual RMABs for non-stationary behavior
4. **TARI** - Non-Markovian policies using time-series forecasting (90% improvement)
5. **GROUPS** - Robust group-level planning
6. **WHIRL** - Inverse RL for reward learning

### Data Requirements:
From Suvita, need:
1. **Beneficiary Registry** - demographics, gestational week, location, contact info
2. **Call/SMS Logs** - timestamps, outcomes (delivered/engaged/missed)
3. **Appointment Records** - ANC visits, attended/missed
4. **Program Status** - active/dropped-out/completed states

Can create **dummy dataset** for demo with ~50-100 rows if real data not available.

### Architecture Vision:
Modular microservices with specialized endpoints:
- `/infer` - Parameter inference
- `/recommend` - Basic recommendations
- `/train_decision_focused` - DFL training
- `/recommend_contextual` - Bayesian context-aware
- `/recommend_temporal` - Non-Markovian
- `/recommend_grouped` - Robust group planning
- `/learn_rewards` - Inverse RL

### Expected Impact:
- **25-35% dropout reduction**
- **20-60% improvement** in health worker efficiency
- **20-50% faster adaptation** to changing behavior
- Scalable from pilot to national programs

### Implementation Timeline:
- **Week 1-2**: Prototype solver, build FastAPI endpoints
- **Week 3-4**: Add SMS/call integration, containerize
- **Week 5-6**: Connect to live pipelines, A/B testing

## Additional Context (Lines 1000-2000)

### Suvita's Current Model
- **SMS Reminders**: Automated messages 1 day and 7 days before vaccine appointments
- **Scale**: 200,000+ caregivers across 7 states (Bihar, Maharashtra, UP, Rajasthan, West Bengal)
- **Immunization Ambassadors**: 5,000 → 35,000 volunteer community leaders for follow-up
- **Program Impact**:
  - 2pp increase in vaccination rates from SMS ($0.40-$1.71 per child)
  - ~7pp increase from ambassadors ($1-$2 per child)
- **Enrollment**: 600K SMS, 95K pregnancy reminders, 3,500 ambassadors

### Key Differences: Suvita vs. ARMMAN
1. **Target Population**: Caregivers of infants/children (Suvita) vs. Expectant mothers (ARMMAN)
2. **Communication Frequency**: 2-3 messages per vaccination (Suvita) vs. 72 weekly voice messages (ARMMAN)
3. **Engagement Objectives**: Binary clinic attendance (Suvita) vs. Multi-dimensional behavior change (ARMMAN)
4. **Data Complexity**: Lightweight SMS logs (Suvita) vs. Rich call metadata & voice responses (ARMMAN)
5. **Operational Context**: Volunteer ambassadors (Suvita) vs. Professional call center (ARMMAN)

### Why RMAB Still Makes Sense for Suvita
Despite differences, the **core challenge is identical**:
- **Engagement dropout**: ~30-40% in both programs
- **Limited outreach capacity**: Finite ambassador hours and SMS budgets
- **Data availability**: Suvita has sufficient data for RMAB parameter inference
- **Operational simplicity**: API integration doesn't require pipeline overhaul

### Complexity vs. Benefit Analysis
- **Modern RMAB algorithms** (Restless-UCB, UCBoost) achieve **O(N) or O(1)** complexity per arm
- **UCBoost**: Near-optimal with <1% performance loss, 99% drop in computation
- **Field evidence**: 20-30% improvement in engagement metrics
- **Better than A/B testing**: Dynamic learning vs. wasting samples on poor variants

### Implementation Strategy (Updated)

#### Library Selection:
1. **bayesianbandits** ✅
   - Native restless bandit support
   - Delayed rewards & state transitions
   - Lightweight (scikit-learn, SciPy only)
   - Simple API: `Agent.learn()` / `Agent.recommend()`

2. **MABWiser** ✅
   - Scikit-learn style API
   - Full contextual support (parametric & non-parametric)
   - Built-in simulation & hyperparameter tuning
   - Parallel execution

3. **SMPyBandits** (Alternative)
   - 65+ classical algorithms
   - UCBoost support
   - Good for benchmarking

4. **markovianbandit-pkg** (Advanced)
   - Exact Whittle-index computation
   - For comparing approximate policies

#### Recommended: **Hybrid Approach**
Combine bayesianbandits + MABWiser:
- Use **bayesianbandits** for restless dynamics & delayed feedback
- Use **MABWiser** for contextual features & tuning
- Blend scores: `combined_score = α * restless_score + (1-α) * contextual_score`

#### Phased Rollout:
**Phase 1 (Weeks 1-2): Proof of Concept**
- Generate ~100 synthetic beneficiary rows
- Build FastAPI wrapper with `/infer` and `/recommend` endpoints
- Prototype with dummy data

**Phase 2 (Weeks 3-4): Integration & Deployment**
- Dockerize the FastAPI app
- Deploy to Google Cloud Run / AWS Lambda
- Integrate Twilio for SMS/call write-back

**Phase 3 (Weeks 5-6): Monitoring & Iteration**
- A/B testing vs. heuristic baseline
- Hyperparameter tuning with MABWiser
- Track engagement lift

### Data Requirements from Suvita
1. **Beneficiary Registry**: Demographics, gestational week, location, contact info
2. **Call/SMS Logs**: Timestamps, outcomes (delivered/engaged/missed)
3. **Appointment Records**: ANC visits, attended/missed flags
4. **Program Status**: active/dropped-out/completed states

**Fallback**: Create dummy CSV with 50-100 rows if real data unavailable

### Evaluation Metrics for Synthetic Data
**Performance Metrics:**
- **Cumulative Regret**: Total loss vs. optimal oracle
- **Cumulative Reward**: Sum of rewards collected
- **Simple Regret**: Quality of final recommendation
- **Convergence Speed**: Time to learn optimal policy

**Operational Metrics:**
- **Engagement Rate**: Proportion of positive responses
- **Top-K Hit Rate**: How often best arm appears in top-K
- **Policy Stability**: Action-distribution entropy over time

### Jupyter Notebook Structure
1. **Title & Overview** - Purpose and assumptions
2. **Environment Setup** - Dependencies (bayesianbandits, mabwiser, pandas, matplotlib)
3. **Data Generation** - Synthetic data with state transitions
4. **EDA** - Summary stats, histograms, state transitions
5. **Metric Definitions** - Implement all evaluation functions
6. **Model Implementation** - Run /infer and /recommend loops
7. **Results & Visualization** - Plot regret, rewards, engagement rates
8. **Conclusions & Next Steps** - Findings and real-data integration plan

### RL Primer: What is RMAB?
**Classic Multi-Armed Bandit (MAB)**:
- N arms with unknown reward distributions
- Goal: Maximize cumulative reward
- Balance exploration vs. exploitation

**Restless Multi-Armed Bandit (RMAB)**:
- Each arm = finite-state Markov chain
- **Key difference**: Arm states evolve **even when not played** ("restless")
- At each timestep: select m arms to pull
- **Challenge**: State space grows exponentially (intractable)
- **Solution**: Whittle index policy (near-optimal, relaxes coupled system)

## Final Comprehensive Summary (Complete Document)

### Alternative Name Considered: "Parvai"
- Tamil word meaning "view," "sight," or "vision"
- **Clever AI reference**: Ends with "AI"
- Domain likely available (very rare surname)
- Strong branding potential

### Cost Optimization Strategies
**Problem:** Initial GCP estimate was ~$355/month (too expensive for NGOs)

**Optimized Approach (~$100-200/month):**
1. **Cloud Run instead of GKE** - Serverless, scales to zero
2. **Preemptible VMs** for batch jobs - Save 60-90%
3. **Reuse existing infrastructure** - Share Cloud SQL, Redis
4. **Batch Pub/Sub messages** - Reduce API costs by 95%
5. **Free tier quotas** - Cloud Run, Firestore
6. **Commitment discounts** - 1-3 year contracts

### Detailed SAHELI-Inspired Design

**Key Innovations from SAHELI (to adopt):**
1. **Clustering Approach**:
   - Group caregivers by passive transition behavior
   - ~20 clusters via k-means
   - Share MDP parameters within clusters
   - Reduces computational complexity dramatically

2. **Features-Only (FO) Mapping**:
   - Train RandomForest: demographics → cluster_id
   - Solve cold-start problem for new caregivers
   - Immediate cluster assignment

3. **Whittle Index Computation**:
   - Use SAHELI's `planinf` function (binary search + value iteration)
   - Pre-compute indices for (cluster_id, state_id) pairs
   - Store in Redis for O(1) lookup

4. **Sleeping State**:
   - Prevent over-contacting beneficiaries
   - η=+∞ approximation reduces to ~4 core states
   - Computational efficiency

5. **Warmup Period**:
   - 6 weeks of data collection before RMAB
   - Allows sufficient history for clustering

### Updated API Design

**Batch/Training Endpoints:**
- `POST /train_clusters` - Cluster caregivers, learn MDP parameters
- `POST /precompute_whittle_indices` - Pre-compute indices for all (cluster, state) pairs
- `POST /assign_caregiver_cluster` - Map new caregiver to cluster via FO

**Real-Time Endpoints:**
- `POST /update_caregiver_state` - Update engagement state from SMS logs
- `GET /recommend?budget=K` - Get top-K priority caregivers (O(1) lookup)

### Technical Stack (Final)

**Python Libraries:**
- `bayesianbandits` - Restless bandit learning
- `MABWiser` - Contextual features (optional Phase 3)
- `scikit-learn` - Clustering, FO mapping
- `FastAPI` - REST API framework
- `numpy`, `pandas` - Data processing
- SAHELI's Whittle solver (adapted)

**Infrastructure:**
- **Compute:** Cloud Run (serverless), Cloud Functions
- **Storage:** PostgreSQL (state/params), Redis (indices)
- **Events:** Pub/Sub (or Kafka for flexibility)
- **Deployment:** Docker, Kubernetes (optional), Terraform
- **Monitoring:** Prometheus, Grafana

### Comprehensive Research Papers Leveraged

1. **SAHELI (2023)** - First deployed RMAB in public health, 100K+ users
2. **ARMMAN Field Study (AAAI 2022)** - 30% dropout reduction with Whittle index
3. **Decision-Focused Learning** - Direct policy optimization
4. **BCoR (Bayesian Contextual)** - Hierarchical priors, Thompson sampling
5. **TARI (Non-Markovian)** - Time-series forecasting, 90% improvement
6. **GROUPS** - Robust group-level planning
7. **WHIRL (Inverse RL)** - Learn reward functions from expert goals

### Open Source Strategy

**Licensing:**
- Apache 2.0 or MIT (permissive)
- CONTRIBUTING.md, Code of Conduct
- Steering committee (NGOs + academics)

**Repository Structure:**
```
/cmd          # FastAPI service
/pkg/bandit   # bayesianbandits wrapper
/pkg/context  # MABWiser integration
/infra        # Helm charts, Terraform
/docs         # Architecture, onboarding
/examples     # Colab notebooks, demos
```

**Deliverables:**
- Docker images on Docker Hub/GHCR
- Helm charts for Kubernetes
- Terraform modules (GCP, AWS, Azure)
- Example Jupyter notebooks
- Documentation site (MkDocs/Docusaurus)

### Evaluation Metrics (Complete List)

**Performance:**
- Cumulative regret vs optimal oracle
- Cumulative reward
- Simple regret (final recommendation quality)
- Convergence speed
- Policy stability (entropy over time)

**Operational:**
- Vaccination attendance rate
- Engagement rate (SMS open/click)
- Top-K hit rate
- Calls per successful vaccination
- Cost per additional vaccination

**Fairness:**
- Distribution across demographics (education, income, geography)
- Coverage equity
- No systematic bias

### Risk Mitigation

1. **Model Misspecification** → A/B testing, expert review, monitoring
2. **Data Sparsity** → Clustering, hierarchical models, offline learning
3. **Compute Limits** → Cluster-level decisions, serverless scaling
4. **Privacy** → Anonymized IDs, encrypted storage, access controls
5. **Bias/Fairness** → Regular audits, equity constraints, community feedback
6. **NGO Capacity** → Training, simple UI, human-in-the-loop
7. **Misuse** → Documentation, governance, disclaimers

### Suvita vs ARMMAN: Detailed Comparison

| Aspect | ARMMAN/SAHELI | Suvita |
|--------|---------------|--------|
| **Target** | Expectant/new mothers | Caregivers of infants |
| **Scale** | 23K pilot → 100K → 1M | 200K+ caregivers |
| **Geography** | Mumbai → National (India) | 7 states: Bihar, Maharashtra, UP, Rajasthan, WB |
| **Communication** | 72 weekly voice messages | 2 SMS per vaccine (1 day, 7 days before) |
| **Intervention** | Health worker calls | Volunteer ambassadors + SMS |
| **Frequency** | Weekly engagement | Per vaccination schedule |
| **Metric** | Listening to voice messages | Clinic attendance for vaccination |
| **Reward** | Weekly engagement (continuous) | Binary per vaccine (sparse) |
| **Data** | Call logs, listenership | Government health records (RCH), delayed |
| **Context** | Professional call center | Volunteer network, variable quality |
| **Dropout** | ~40% | ~25-30% of infants not fully immunized |

**Key Insight:** Suvita's problem is more complex (sparser rewards, volunteer-driven, delayed data) but the core RMAB approach still applies with adaptation.

### Future Enhancements (Phase 3+)

1. **Contextual RMAB** - Demographics, geography, temporal features
2. **Non-Stationary** - Sliding windows, change-point detection
3. **Semi-Markov** - Time-since-last-intervention as state
4. **Inverse RL** - Learn from expert preferences (WHIRL)
5. **Decision-Focused** - End-to-end neural network training
6. **Multi-Domain** - Extend to TB, nutrition, antenatal care
7. **Fairness Constraints** - Explicit equity objectives

### Business Model / Sustainability

**For NGOs:**
- Free and open-source
- Self-hostable (~$100-200/month for 200K users)
- Community support

**For Ecosystem:**
- Research collaborations (Google AI for Social Good, universities)
- Workshops and training programs
- Case studies and publications
- Potential consulting for custom deployments

### Connection to Broader Mission

The archive hints at a larger philosophical concern:

> "Without any guardrails, the current economic and geopolitical incentives put us in a trajectory where human agency and participation gets eroded."

**Bandicoot embodies the alternative:**
- Open-source (not proprietary)
- Empowering (not extractive)
- Community-owned (not monopolistic)
- Augmenting human workers (not replacing)
- Transparent (not black-box)

This is **technical infrastructure for preserving human agency** - a concrete example of how AI can serve communities rather than exploit them.

---

## Key Takeaways

### What is Bandicoot?
An **open-source RMAB platform** that helps health NGOs optimize limited outreach resources to maximize vaccination rates and health outcomes.

### Why does it matter?
- **Proven:** 30% dropout reduction in Google/ARMMAN deployment
- **Scalable:** 200K → millions of beneficiaries
- **Accessible:** Free, self-hostable, ~$100-200/month
- **Impactful:** Every 1% improvement = thousands of children vaccinated

### Who benefits?
1. **Suvita** (first implementation) - 200K caregivers across India
2. **Other health NGOs** - Maternal care, TB, nutrition programs
3. **Global health** - Replicable blueprint for resource-constrained settings

### What makes it different?
- **Hybrid approach:** Combines restless + contextual bandits
- **SAHELI-inspired:** Proven techniques from production deployment
- **Cost-optimized:** Serverless-first, reuse existing infrastructure
- **Delivery-agnostic:** Works with any SMS/call provider
- **Community-driven:** Open governance, shared learnings

### How to get started?
1. **Phase 1:** Colab demo with synthetic data (Weeks 1-2)
2. **Phase 2:** Suvita MVP with real data (Weeks 3-6)
3. **Phase 3:** Contextualization and scale (Months 2-3)
4. **Phase 4:** Open source release (Month 4+)

---

*Reading complete: 5909/5909 lines (100%)*

**Document analyzed:** Chat archive about building an RMAB optimization system for Suvita's maternal and child health program, with plans to open-source it as "Bandicoot" for the NGO ecosystem.

**Core insight:** This project combines cutting-edge AI research (RMABs) with grassroots impact (vaccination programs) while embodying values of open access and community empowerment over extractive tech models.
