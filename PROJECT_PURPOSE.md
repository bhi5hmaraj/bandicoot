# Bandicoot: Open-Source RMAB Platform for Health Outreach

## Why Are You Building This?

You're building **Bandicoot** to solve a critical problem in global health: **how to maximize impact when resources are limited**.

### The Problem

Health NGOs working on maternal and child care (like Suvita in India) face a fundamental challenge:
- They serve **hundreds of thousands** of caregivers across multiple states
- They have **limited health workers** for personalized outreach
- **30-40% of beneficiaries drop out** of engagement programs
- **SMS reminders alone aren't enough** - but they can't call everyone
- **Every contact must count** - but current methods use random or simple heuristics

**The Result:** Lives are lost because health workers can't prioritize who needs help most urgently.

### The Proven Solution: Restless Multi-Armed Bandits (RMAB)

Google Research and ARMMAN NGO proved this works in India:
- **30% reduction in dropout rates** (from ~35% to ~24%)
- Deployed at scale: **100,000+ beneficiaries**
- Now in production as **SAHELI** - the first RMAB system in public health
- Scaled to **3 million mothers** nationally

**How it works:** The system learns which mothers/caregivers are most likely to benefit from a call or SMS, then prioritizes limited health worker time to maximize engagement and health outcomes.

### Your Vision: Make This Available to Every NGO

The problem: While Google/ARMMAN proved this works, **it's not accessible to most NGOs**.

**Bandicoot will be:**
1. **Open-source** - Free for any NGO to use
2. **Self-hostable** - Deploy on their own infrastructure
3. **Delivery-agnostic** - Works with any SMS/call provider (Twilio, Pub/Sub, Kafka)
4. **Designed for scale** - Handle millions of beneficiaries cost-effectively
5. **Built from real-world learnings** - Leveraging SAHELI's successful deployment

### The First Use Case: Suvita

**Suvita** is your reference implementation:
- **Mission:** Improve childhood vaccination rates in India
- **Scale:** 200,000+ caregivers across 7 states (Bihar, Maharashtra, UP, Rajasthan, West Bengal)
- **Approach:**
  - SMS reminders 1 and 7 days before vaccine appointments
  - 5,000 → 35,000 volunteer "immunization ambassadors"
- **Challenge:** Limited resources, declining engagement, ~25-30% of infants not fully immunized

**Current Impact (without RMAB):**
- SMS alone: +2pp vaccination rate ($0.40-$1.71 per child)
- Ambassadors: +7pp ($1-$2 per child)

**Potential with Bandicoot:**
- **25-35% reduction in dropouts** (based on ARMMAN results)
- **20-60% improvement** in health worker efficiency
- **Smarter allocation** of SMS and ambassador resources

### Technical Approach

#### Core Innovation: Contextual + Restless Hybrid
Combine two powerful techniques:
1. **Restless Bandits** (bayesianbandits) - Model how engagement states evolve even without intervention
2. **Contextual Features** (MABWiser) - Use demographics, location, history to personalize

#### Key Design Decisions (Inspired by SAHELI)
1. **Clustering** - Group similar caregivers (~20 clusters) to share learning
2. **Whittle Index** - Compute priority scores for each caregiver
3. **Features-Only Mapping** - Assign new caregivers to clusters immediately
4. **Warmup Period** - 6 weeks of data before RMAB prioritization kicks in
5. **Cost-Optimized** - Serverless (Cloud Run), reuse existing infra, ~$100-200/month for 200K caregivers

### Architecture

```
┌─────────────────┐
│ Caregiver Data  │
│ (SMS, Calls,    │
│  Vaccinations)  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│     Bandicoot RMAB Service          │
│  (FastAPI + bayesianbandits)        │
├─────────────────────────────────────┤
│ /train_clusters                     │
│ /precompute_whittle_indices         │
│ /assign_caregiver_cluster           │
│ /update_caregiver_state             │
│ /recommend?budget=K                 │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ Top-K Priority  │
│   Caregivers    │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
  SMS    Ambassador
         Calls
```

### Implementation Phases

**Phase 1: Proof-of-Concept (Weeks 1-2)**
- Colab/Jupyter notebook with synthetic data
- Validate RMAB mechanics
- Demonstrate 20-30% improvement vs random allocation
- **Deliverable:** Working demo showing engagement lift

**Phase 2: MVP with Suvita (Weeks 3-6)**
- FastAPI service with /infer and /recommend endpoints
- Clustering-based parameter learning (SAHELI approach)
- Integration with Suvita's SMS and ambassador system
- A/B testing vs current methods
- **Deliverable:** Production-ready service showing real impact

**Phase 3: Contextualization & Scale (Months 2-3)**
- Add demographic and temporal features
- Hybrid bayesianbandits + MABWiser
- Off-policy evaluation (IPS, DR estimators)
- **Deliverable:** Enhanced model with personalization

**Phase 4: Open Source Release (Month 4+)**
- Complete documentation
- Terraform blueprints for GCP/AWS/Azure
- Helm charts for Kubernetes
- Example notebooks and datasets
- Community governance model
- **Deliverable:** Replicable platform for any NGO

### Expected Impact

**For Suvita:**
- 25-35% reduction in vaccination dropouts
- 20-60% more efficient health worker utilization
- Serve same 200K caregivers at **~$100-200/month** infrastructure cost

**For the Ecosystem:**
- Enable **any health NGO** to deploy proven AI optimization
- Save **thousands of lives** by improving vaccination rates globally
- Create **open-source standard** for RMAB in social impact
- Build **community of practice** around AI for health

### Technical Stack

**Core Libraries:**
- `bayesianbandits` - Restless bandit support, delayed rewards
- `MABWiser` - Contextual features, hyperparameter tuning
- `scikit-learn` - Clustering, feature engineering
- SAHELI's Whittle solver (open-source reference)

**Infrastructure:**
- FastAPI - REST API
- PostgreSQL - Persistent state
- Redis - Fast lookups
- Cloud Run - Serverless deployment
- Pub/Sub/Kafka - Event-driven architecture
- Docker + Kubernetes - Containerization
- Terraform - Infrastructure as Code

**Cost Optimization:**
- Serverless-first (pay only when used)
- Preemptible VMs for batch jobs
- Reuse existing databases
- Free tier quotas (Cloud Run, Firestore)
- Estimated: **$100-200/month** for 200K users

### Why "Bandicoot"?

_(To be determined - but the alternative name "Parvai" was considered, meaning "vision" or "sight" in Tamil, with the clever AI reference at the end)_

### Research Foundation

Built on peer-reviewed research:
1. **SAHELI/ARMMAN Field Study** (AAAI 2022) - 30% engagement improvement
2. **Decision-Focused Learning** (Wang et al.) - Train directly for policy optimization
3. **BCoR** (Liang et al.) - Bayesian contextual RMABs for non-stationary behavior
4. **TARI** (Danassis et al.) - Non-Markovian policies, 90% improvement
5. **WHIRL** (Jain et al. 2024) - Inverse RL for reward learning
6. **GROUPS** (Killian et al.) - Robust group-level planning

### Success Metrics

**Technical:**
- Cumulative regret vs optimal policy
- Top-K hit rate for high-value interventions
- Convergence speed of learning algorithm
- Policy stability over time

**Operational:**
- Vaccination attendance rate improvement
- Health worker calls-per-success ratio
- Cost per additional vaccination
- Dropout rate reduction

**Impact:**
- Lives saved (children fully vaccinated)
- Cost-effectiveness ($/child vaccinated)
- Scalability (beneficiaries served)
- Replicability (NGOs adopting Bandicoot)

### Beyond Suvita

Once proven, extend to:
- **Maternal health** (antenatal care, postnatal visits)
- **TB treatment adherence**
- **Nutrition counseling**
- **Any health program** with limited outreach resources

### Your Bigger Picture

This appears to be part of a larger concern about **preserving human agency** in the face of economic and geopolitical pressures. By building open-source technical infrastructure that empowers communities and NGOs (rather than extractive tech monopolies), you're creating tools that enhance rather than erode human participation in shaping health outcomes.

---

## In Summary

**You're building Bandicoot to:**
1. ✅ Save lives by optimizing health outreach with proven AI
2. ✅ Democratize access to cutting-edge RMAB technology
3. ✅ Empower NGOs with self-hostable, open-source tools
4. ✅ Prove that AI can augment (not replace) human health workers
5. ✅ Create a replicable blueprint for social impact at scale

**The goal:** Transform how resource-constrained health programs operate globally, starting with Suvita's 200,000 caregivers and scaling to millions.
