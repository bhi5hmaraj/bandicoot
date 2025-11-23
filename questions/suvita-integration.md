# Suvita Integration Questions

Questions about integrating Bandicoot with Suvita's production system, data pipelines, and deployment.

---

## ❓ Historical Data Format and Availability

**Status:** Open
**Priority:** High
**Category:** Data Integration

### Context
Bandicoot needs historical engagement data to learn MDP parameters and cluster caregivers.

### The Question
What is the format and availability of Suvita's historical engagement data?

### Required Information

**Data Schema:**
1. **Caregiver identifiers**
   - Format: Integer ID? UUID? Phone number?
   - Consistency: Stable over time?

2. **Timestamps**
   - Format: Unix timestamp? ISO 8601? Date only?
   - Timezone: UTC? Local?
   - Granularity: Exact time or daily aggregates?

3. **Engagement events**
   - What events are tracked? (message sent, message opened, message replied, call made, call answered, etc.)
   - Event types: Discrete actions or continuous metrics?

4. **Intervention records**
   - What interventions are logged? (SMS, call, visit, content type, etc.)
   - Who initiated? (automated system vs. human counselor)
   - Outcome recorded? (delivered, opened, replied, etc.)

### Data Quality Questions

1. **Completeness:**
   - How far back does historical data go?
   - Any gaps in data collection?
   - Missing data patterns (missing at random vs. systematic)?

2. **Volume:**
   - How many caregivers?
   - How many interactions per caregiver (average)?
   - Total dataset size?

3. **Label quality:**
   - How is "engagement" defined currently?
   - Is there a ground truth for Responsive vs. Unresponsive state?
   - Inter-rater reliability (if manually labeled)?

### API/Access Questions

1. **Data access:**
   - Database direct access? API? Data export?
   - Batch vs. streaming?
   - Refresh frequency?

2. **Privacy/Security:**
   - PII handling requirements?
   - Data anonymization needed?
   - HIPAA/compliance requirements?

### Next Steps
1. Schedule meeting with Suvita data team
2. Request sample data extract (1000 caregivers, 6 months)
3. Document data schema and quality issues
4. Build data ingestion pipeline

---

## ❓ Real-Time vs. Batch Recommendations

**Status:** Open
**Priority:** High
**Category:** System Architecture

### Context
Bandicoot can generate recommendations in batch (daily) or real-time (on-demand).

### The Question
What is the operational model for generating recommendations at Suvita?

### Options

1. **Daily Batch Processing**
   - Run recommender once per day (e.g., 6am)
   - Generate day's intervention list
   - Pros: Simple, predictable, can use scheduled compute
   - Cons: Can't react to within-day state changes

2. **Real-Time Recommendations**
   - API endpoint: `GET /recommend?caregiver_id=123`
   - Generate recommendations on-demand
   - Pros: Always up-to-date, reactive
   - Cons: Needs low-latency infrastructure, more complex

3. **Hybrid: Batch with Real-Time Override**
   - Daily batch generates baseline recommendations
   - Real-time API can refresh for specific caregivers
   - Pros: Best of both worlds
   - Cons: More complex to maintain

4. **Event-Driven**
   - Trigger recommendation refresh on state change events
   - Pros: Reactive, efficient
   - Cons: Requires event streaming infrastructure

### Questions to Answer

1. **Operational workflow:**
   - How do counselors currently get their daily contact list?
   - Is it a push (system sends list) or pull (counselors request list)?
   - What time of day do they need recommendations?

2. **State update frequency:**
   - How often does caregiver state change?
   - What triggers state change? (engagement event, time decay, counselor input?)

3. **Latency requirements:**
   - How fast must recommendations be generated?
   - Is 1 second acceptable? 100ms? 1 minute?

4. **Compute resources:**
   - What infrastructure does Suvita have? (cloud, on-prem, hybrid)
   - Can we provision batch compute at night?
   - GPU availability?

### Next Steps
1. Shadow Suvita counselors to understand workflow
2. Document current recommendation/triage process
3. Define latency and throughput requirements
4. Design deployment architecture

---

## ❓ State Observation Mechanism

**Status:** Open
**Priority:** High
**Category:** Data Integration

### Context
To generate recommendations, we need to know each caregiver's current state (Responsive vs. Unresponsive).

### The Question
How do we determine a caregiver's current state in Suvita's system?

### Options

1. **Rule-Based State Assignment**
   - Define rules: "Responsive if replied to message in last 7 days"
   - Pros: Simple, interpretable, no ML needed
   - Cons: Rules may not match learned transitions

2. **Observed Last Interaction**
   - Use most recent engagement event as state indicator
   - Pros: Direct observation, no inference needed
   - Cons: May be stale, doesn't account for unobserved decay

3. **State Inference from History**
   - Use hidden state inference (e.g., forward algorithm)
   - Infer most likely current state given interaction history
   - Pros: Accounts for uncertainty, uses all available information
   - Cons: More complex, computationally expensive

4. **Counselor Annotation**
   - Counselors manually mark caregivers as engaged/unengaged
   - Pros: Human judgment, accounts for context
   - Cons: Subjective, labor-intensive, doesn't scale

### Questions to Answer

1. **What signals are available?**
   - Message delivery status (delivered, opened, replied)?
   - Call outcomes (answered, voicemail, declined)?
   - App usage (if mobile app exists)?
   - Content engagement (watched video, completed quiz)?

2. **What is the ground truth?**
   - How does Suvita currently assess engagement?
   - Is there a labeled dataset we can validate against?

3. **State persistence:**
   - Once labeled as "Unresponsive", when do they become "Responsive" again?
   - Is there a decay function? (engaged → at-risk → unresponsive over time)

### Next Steps
1. Get list of all available engagement signals
2. Analyze correlation between signals and outcomes
3. Propose state definition aligned with Suvita's domain understanding
4. Validate state assignments against counselor judgment

---

## ❓ Intervention Budget Constraint

**Status:** Open
**Priority:** Medium
**Category:** System Design

### Context
RMAB recommends top-k caregivers to intervene with, given a budget constraint.

### The Question
How is the intervention budget determined for Suvita?

### Questions to Answer

1. **Budget type:**
   - Fixed number per day? (e.g., "contact 50 caregivers daily")
   - Counselor capacity? (e.g., "each counselor can handle 20 calls/day")
   - Resource-based? (e.g., "cost budget for SMS/calls")

2. **Budget variability:**
   - Is budget constant or dynamic?
   - Does it vary by day of week? (e.g., more on weekdays)
   - Seasonal variation? (holidays, campaign periods)

3. **Budget enforcement:**
   - Hard constraint? (must stay within budget)
   - Soft constraint? (can exceed if high priority)
   - Tiered? (different budgets for different intervention types)

4. **Multi-constraint:**
   - Do we need to optimize under multiple constraints?
   - Example: "50 SMS + 20 calls per day"
   - Example: "10 interventions per caregiver per month"

### Implications

- **Recommendation count:** Budget determines how many IDs we return
- **Priority threshold:** May need minimum Whittle index to recommend
- **Fairness:** How do we ensure all caregivers get attention over time?

### Next Steps
1. Understand current counselor workflow and capacity
2. Get budget allocation by intervention type
3. Analyze historical intervention volume and variability
4. Design budget management interface

---

## ❓ Feedback Loop: How to Improve Over Time

**Status:** Open
**Priority:** Medium
**Category:** MLOps

### Context
Bandicoot's recommendations will influence caregiver engagement, which generates new data to retrain the model.

### The Question
How do we close the feedback loop to continuously improve recommendations?

### Challenges

1. **Feedback delay:**
   - Intervention → outcome may take days/weeks
   - How long do we wait before retraining?

2. **Exploration vs. Exploitation:**
   - If we always follow Whittle indices (exploitation), we never learn about new strategies
   - Need some randomization (exploration) to discover better policies

3. **Non-stationarity:**
   - As we improve, caregiver behavior may change
   - Model trained on old data may not reflect new behavior

4. **Causal confusion:**
   - Caregivers we intervene with ≠ random sample
   - Can't directly estimate counterfactual (what if we didn't intervene?)

### Options

1. **Periodic Retraining (Simple)**
   - Retrain every week/month on all historical data
   - Pros: Simple, standard MLOps
   - Cons: Doesn't handle selection bias

2. **Online Learning**
   - Update model parameters incrementally as new data arrives
   - Pros: Always current, adapts quickly
   - Cons: Complex, may be unstable

3. **Counterfactual Evaluation**
   - Use inverse propensity weighting to estimate counterfactuals
   - Pros: Handles selection bias
   - Cons: Requires logging intervention probabilities, complex

4. **A/B Testing Framework**
   - Randomize some caregivers to control group (no RMAB)
   - Compare outcomes to validate model
   - Pros: Clean causal inference
   - Cons: May be unethical to withhold interventions

5. **Thompson Sampling / Contextual Bandits**
   - Add exploration noise to recommendations
   - Balance exploration and exploitation
   - Pros: Principled, adapts over time
   - Cons: More complex than pure RMAB

### Next Steps
1. Define key performance metrics (KPIs) to optimize
2. Design logging infrastructure to capture intervention outcomes
3. Prototype offline evaluation using historical data
4. Discuss ethical constraints on randomization with Suvita

---

## ❓ Multi-Arm vs. Single-Arm Deployment

**Status:** Open
**Priority:** Low
**Category:** Deployment Strategy

### Context
We can deploy Bandicoot to replace the entire recommendation system, or use it alongside existing systems.

### The Question
Should Bandicoot fully replace Suvita's current prioritization, or run in parallel?

### Options

1. **Full Replacement**
   - Bandicoot generates all recommendations
   - Pros: Clean, full control, simpler system
   - Cons: Risky, hard to rollback, no safety net

2. **Parallel System (A/B Test)**
   - Some counselors use Bandicoot, others use current system
   - Pros: Can compare outcomes, de-risked
   - Cons: Randomization may not be fair, more complex operations

3. **Ensemble/Hybrid**
   - Combine Bandicoot recommendations with current system
   - Example: "Bandicoot top-30 + current system top-20"
   - Pros: Safety net, can gradually increase Bandicoot weight
   - Cons: Complex, unclear who to credit for outcomes

4. **Shadow Mode First**
   - Bandicoot generates recommendations but they're not acted on
   - Compare Bandicoot vs. actual interventions to build confidence
   - Pros: Risk-free validation
   - Cons: Delayed impact, no causal evaluation

### Next Steps
1. Understand Suvita's risk tolerance and change management
2. Propose phased rollout plan
3. Define success criteria for each phase

---

## ❓ Personalization Beyond RMAB

**Status:** Open
**Priority:** Low
**Category:** System Design

### Context
RMAB optimizes *who* to contact. But there are many other personalization dimensions.

### The Question
What other aspects of intervention should be personalized?

### Dimensions to Consider

1. **Message Content:**
   - Personalize content to caregiver preferences/needs
   - Example: Emphasize nutrition vs. mental health based on history

2. **Communication Channel:**
   - SMS vs. call vs. WhatsApp vs. app notification
   - Optimize channel based on caregiver responsiveness

3. **Timing:**
   - Time of day to send message
   - Day of week (weekday vs. weekend)

4. **Frequency:**
   - Some caregivers may prefer daily nudges, others weekly

5. **Language/Tone:**
   - Formal vs. casual
   - Language preference (if multilingual)

### Integration Questions

1. **Is this in scope for Bandicoot?**
   - Or separate recommendation system?

2. **How does it interact with RMAB?**
   - Example: RMAB says "contact caregiver 123", then content system says "send message about nutrition at 9am"

3. **Data requirements:**
   - Need labeled data for content/channel/timing preferences

### Next Steps
1. Clarify scope: Is this part of RMAB project or separate?
2. If in scope, design multi-armed RMAB formulation
3. If separate, define API contract between systems

---

## ❓ Handling New Caregivers (Cold Start)

**Status:** Open
**Priority:** Medium
**Category:** Modeling

### Context
New caregivers have no historical engagement data. How do we generate recommendations for them?

### The Question
How do we handle the cold-start problem for newly onboarded caregivers?

### Options

1. **Default Policy**
   - Treat all new caregivers the same (e.g., high priority for first week)
   - Pros: Simple, ensures early engagement
   - Cons: Ignores heterogeneity

2. **Feature-Based Cluster Assignment**
   - Use demographics/registration data to assign to cluster
   - Example: "first-time moms → cluster 3"
   - Pros: Leverages available data
   - Cons: Requires feature engineering, may not match behavioral clustering

3. **Exploration Phase**
   - Randomly intervene with new caregivers to gather data
   - After N interactions, assign to cluster based on observed behavior
   - Pros: Data-driven cluster assignment
   - Cons: May miss early critical engagement window

4. **Population Prior**
   - Use population-level statistics as prior
   - Gradually update with individual data
   - Pros: Principled Bayesian approach
   - Cons: Requires careful prior specification

### Next Steps
1. Analyze onboarding flow: What data is available at registration?
2. Test cluster prediction using registration features
3. Define minimum data requirement before personalization kicks in

---

## ✅ Resolved Questions

*Resolved questions will be moved here with links to decision documents*

### Data Format for Initial Prototype
**Decision:** Use pandas DataFrame with columns [caregiver_id, timestamp, state, action]
**Rationale:** Simple, flexible, matches research code conventions
**Date:** 2025-11-22
