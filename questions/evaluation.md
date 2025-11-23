# Evaluation & Metrics Questions

How to measure success, A/B testing strategy, and performance metrics for the RMAB system.

---

## ❓ Primary Success Metric: What Are We Optimizing?

**Status:** Open
**Priority:** High
**Category:** Evaluation

### Context
RMAB optimizes expected cumulative reward. But what real-world outcome does "reward" represent?

### The Question
What is the primary metric that defines success for Bandicoot at Suvita?

### Candidate Metrics

1. **Engagement Rate**
   - % of caregivers who respond to interventions
   - **Pros:** Direct measure of immediate impact, easy to measure
   - **Cons:** Doesn't capture long-term retention

2. **Retention Rate**
   - % of caregivers still engaged after 30/60/90 days
   - **Pros:** Measures long-term impact
   - **Cons:** Long feedback delay, confounded by other factors

3. **Content Consumption**
   - Average messages read, videos watched, quizzes completed
   - **Pros:** Measures depth of engagement
   - **Cons:** May not correlate with actual behavior change

4. **Behavioral Outcomes**
   - % of caregivers who complete recommended actions (e.g., doctor visits, nutrition practices)
   - **Pros:** True impact on health outcomes
   - **Cons:** Hard to measure, long delay, attribution challenges

5. **Efficiency: Engagement per Contact**
   - Engagement rate / intervention budget
   - **Pros:** Measures resource efficiency
   - **Cons:** May incentivize "cherry-picking" easy wins

### Trade-offs

**Short-term vs. Long-term:**
- Maximize immediate engagement vs. long-term retention?
- RMAB's discount factor (gamma) encodes this trade-off

**Individual vs. Population:**
- Maximize total engagement vs. ensure equitable access?
- RMAB optimizes total, may neglect hard-to-reach caregivers

**Engagement vs. Outcomes:**
- Measure intermediate (engagement) vs. ultimate (health) outcomes?
- Engagement is easier to measure but may not equal impact

### Questions to Answer

1. **What does Suvita care most about?**
   - Immediate responsiveness?
   - Long-term program retention?
   - Health behavior change?

2. **What can we measure reliably?**
   - What outcomes are tracked in Suvita's system?
   - What's the measurement latency?

3. **How does this align with RMAB?**
   - Can we define reward to match Suvita's goal?

### Next Steps
1. Workshop with Suvita stakeholders to define success
2. Map Suvita's goals to RMAB reward structure
3. Define primary and secondary metrics

---

## ❓ Evaluation Methodology: How to Measure Causal Impact?

**Status:** Open
**Priority:** High
**Category:** Evaluation

### Context
To know if Bandicoot works, we need to measure its causal impact on outcomes.

### The Question
How do we rigorously evaluate whether Bandicoot improves outcomes?

### Options

1. **Randomized Controlled Trial (RCT) / A/B Test**
   - Randomly assign caregivers to Bandicoot vs. control
   - Compare outcomes between groups
   - **Pros:** Gold standard, clear causal inference
   - **Cons:** May be unethical to withhold interventions, requires large sample, slow

2. **Cluster Randomization**
   - Randomly assign counselors (not caregivers) to Bandicoot vs. control
   - **Pros:** Avoids spillover effects, more practical
   - **Cons:** Fewer units for randomization, counselor effects

3. **Difference-in-Differences**
   - Compare before/after Bandicoot, relative to control group (or historical trend)
   - **Pros:** Uses all data, less restrictive than RCT
   - **Cons:** Requires parallel trends assumption

4. **Regression Discontinuity**
   - If Bandicoot is deployed based on a threshold (e.g., caregivers above priority X)
   - Compare outcomes just above vs. just below threshold
   - **Pros:** Quasi-experimental, good causal identification
   - **Cons:** Local treatment effect only, requires threshold-based deployment

5. **Synthetic Control**
   - Create a "synthetic" control group by weighting similar historical caregivers
   - **Pros:** Uses all data, good for single treated unit
   - **Cons:** Complex, requires good pre-treatment match

6. **Observational + Propensity Score Matching**
   - Match Bandicoot-recommended caregivers to similar non-recommended ones
   - Compare outcomes
   - **Pros:** Uses all data, no randomization needed
   - **Cons:** Selection bias, unmeasured confounders

### Ethical Considerations

**Is it ethical to withhold interventions?**
- If current system is effective, withholding may harm control group
- If current system is ineffective, control group not harmed

**Options for ethical RCT:**
- **Equipoise:** Only randomize if genuinely uncertain which is better
- **Time-delayed control:** Control group gets intervention later
- **Partial rollout:** Randomize order of receiving intervention (everyone gets it eventually)

### Sample Size and Power

**Key questions:**
- What is minimum detectable effect size? (e.g., 5% improvement in engagement)
- What is baseline engagement rate? (e.g., 40%)
- What sample size needed for 80% power?

**Example calculation:**
- Baseline engagement: 40%
- Target improvement: 5 percentage points (to 45%)
- Alpha: 0.05, Power: 0.80
- **Required sample:** ~2,000 caregivers per group

### Next Steps
1. Define target effect size and acceptable error rates
2. Discuss ethical constraints with Suvita
3. Design evaluation protocol (likely RCT or cluster RCT)
4. Calculate sample size requirements
5. Define primary and secondary endpoints

---

## ❓ Baseline Comparison: What is the Counterfactual?

**Status:** Open
**Priority:** High
**Category:** Evaluation

### Context
To measure Bandicoot's value, we need to compare it to something.

### The Question
What should be the baseline/control policy for comparison?

### Options

1. **Current Suvita Policy**
   - Whatever Suvita currently uses (manual prioritization, simple rules, etc.)
   - **Pros:** Realistic, shows real impact
   - **Cons:** Current policy may be poor, making Bandicoot look good unfairly

2. **Random Selection**
   - Randomly select caregivers to intervene with (uniform distribution)
   - **Pros:** Simple, unbiased, easy to implement
   - **Cons:** Obviously suboptimal, low bar

3. **Greedy Heuristic**
   - Always contact the most unresponsive caregivers (highest risk)
   - **Pros:** Intuitive, commonly used
   - **Cons:** May not be optimal (intervention fatigue)

4. **Round-Robin / Fairness**
   - Ensure all caregivers get equal attention over time
   - **Pros:** Fair, ensures coverage
   - **Cons:** Ignores heterogeneity

5. **Oracle (Upper Bound)**
   - Hypothetical optimal policy with perfect information
   - **Pros:** Shows potential ceiling for improvement
   - **Cons:** Not implementable, only for analysis

6. **Other RL/Bandit Algorithms**
   - Thompson Sampling, UCB, LinUCB, etc.
   - **Pros:** Strong baselines, shows algorithmic contribution
   - **Cons:** Requires implementation, may not be realistic comparison

### Multi-Arm Comparison

Consider comparing Bandicoot to **multiple** baselines:
- Current Suvita policy (real-world comparison)
- Random (lower bound)
- Greedy heuristic (natural baseline)
- RMAB gives us added value over best baseline

### Next Steps
1. Document Suvita's current prioritization process
2. Implement baseline policies for offline evaluation
3. Test baselines on historical data (offline simulation)
4. Choose 1-2 baselines for production A/B test

---

## ❓ Offline Evaluation: Can We Validate Before Deployment?

**Status:** Open
**Priority:** High
**Category:** Evaluation

### Context
Before deploying to production, we want to validate Bandicoot on historical data.

### The Question
How do we evaluate Bandicoot using historical data (before real-world testing)?

### Challenges

1. **Observational Bias:**
   - Historical data shows interventions under old policy
   - Can't directly observe what would happen under Bandicoot's policy

2. **Missing Counterfactuals:**
   - If we intervened, we don't know what would happen if we didn't
   - If we didn't intervene, we don't know what would happen if we did

3. **Distribution Shift:**
   - Bandicoot's recommendations will change caregiver behavior
   - Historical data may not reflect new behavior under Bandicoot

### Methods

1. **Replay Evaluation (Biased but Easy)**
   - Simulate Bandicoot's recommendations on historical data
   - Assume outcomes would be the same
   - **Pros:** Simple, gives rough estimate
   - **Cons:** Ignores counterfactuals, biased

2. **Inverse Propensity Scoring (IPS)**
   - Reweight historical data by probability of intervention
   - Correct for observational bias
   - **Pros:** Unbiased estimator under assumptions
   - **Cons:** High variance, requires logging intervention probabilities

3. **Doubly Robust Estimation**
   - Combine IPS with outcome model
   - **Pros:** More stable than pure IPS
   - **Cons:** Still requires propensity scores

4. **Simulation / Model-Based**
   - Learn MDP from historical data
   - Simulate Bandicoot's policy in learned MDP
   - **Pros:** Can test many policies cheaply
   - **Cons:** Simulation accuracy depends on MDP quality

### What We Can Do

**Given we have historical data with (state, action, next_state):**
1. Learn MDP transitions from historical data ✅
2. Simulate different policies (Bandicoot, random, greedy) in learned MDP ✅
3. Estimate expected cumulative reward under each policy
4. Compare policies in simulation

**Limitations:**
- Simulation is only as good as the learned MDP
- May miss important dynamics not captured in MDP

### Next Steps
1. Implement simulation-based offline evaluation
2. Compare Bandicoot to baselines on historical data
3. Validate MDP quality (held-out prediction accuracy)
4. Use offline eval to build confidence before online testing

---

## ❓ Online Metrics: What to Track in Production?

**Status:** Open
**Priority:** Medium
**Category:** Evaluation

### Context
Once deployed, we need real-time metrics to monitor performance.

### The Question
What metrics should we track in the live system?

### Metric Categories

### 1. **Primary Outcome Metrics**
Track the core objective:
- **Engagement rate:** % of recommended caregivers who respond
- **Retention rate:** % still engaged after 30/60/90 days
- **Response time:** Time from intervention to engagement

### 2. **System Performance Metrics**
Ensure system is working correctly:
- **Recommendation latency:** Time to generate recommendations
- **API availability:** Uptime, error rate
- **Budget utilization:** % of recommendations acted upon

### 3. **Model Quality Metrics**
Monitor model health:
- **Cluster distribution:** Ensure clusters are balanced
- **Whittle index distribution:** Check for anomalies
- **State distribution:** % responsive vs. unresponsive (track over time)
- **Prediction accuracy:** If we have ground truth, check state prediction accuracy

### 4. **Fairness Metrics**
Ensure equitable treatment:
- **Coverage:** % of caregivers who receive interventions over time
- **Per-cluster outcomes:** Ensure no cluster is systematically neglected
- **Disparity metrics:** Compare outcomes across demographic groups (if available)

### 5. **Business Metrics**
Align with organizational goals:
- **Total active caregivers:** Overall program health
- **Counselor productivity:** Interventions per counselor, outcomes per intervention
- **Cost efficiency:** Outcome per dollar spent

### Metric Dashboards

**Real-Time Dashboard (for operators):**
- Current state snapshot (% responsive, budget used today)
- API health (latency, errors)
- Top clusters (sizes, priorities)

**Weekly Review Dashboard (for stakeholders):**
- Engagement/retention trends
- A/B test results (if running)
- Cluster analysis
- Fairness metrics

### Next Steps
1. Define KPIs with Suvita stakeholders
2. Implement metric logging in code
3. Build dashboards
4. Set up alerting for anomalies

---

## ❓ A/B Test Design: Stratification and Blocking

**Status:** Open
**Priority:** Medium
**Category:** Evaluation

### Context
When running an A/B test, random assignment may not be enough. We may want to stratify or block.

### The Question
How should we design randomization for the A/B test?

### Randomization Options

1. **Simple Randomization**
   - Flip a coin for each caregiver: 50% Bandicoot, 50% control
   - **Pros:** Simple, unbiased
   - **Cons:** May have imbalance in covariates (e.g., more new moms in one group)

2. **Stratified Randomization**
   - Randomize within strata (e.g., separately for new vs. existing caregivers)
   - Ensures balance on key variables
   - **Pros:** More power, balanced comparisons
   - **Cons:** Requires defining strata

3. **Blocked Randomization**
   - Randomize in blocks (e.g., counselor-level blocks)
   - Ensures even distribution within blocks
   - **Pros:** Controls for block-level effects (counselor quality)
   - **Cons:** More complex analysis

4. **Cluster Randomization**
   - Randomize at counselor/clinic level (all caregivers of a counselor get same treatment)
   - **Pros:** Avoids spillover, more realistic
   - **Cons:** Fewer units, less power

### Stratification Variables

**What to stratify on:**
- **Caregiver tenure:** New vs. existing
- **Baseline engagement:** Highly engaged vs. at-risk
- **Geography:** Urban vs. rural (if relevant)
- **Demographics:** First-time mom vs. experienced (if available)

### Sample Ratio

**Treatment allocation:**
- **50/50 split:** Maximum power for comparison
- **80/20 split:** Most caregivers get better treatment (if confident Bandicoot is better)
- **Multi-arm:** 40% Bandicoot, 40% control, 20% other baseline

### Next Steps
1. Identify key stratification variables in Suvita's data
2. Decide on randomization unit (caregiver vs. counselor)
3. Calculate sample size per arm
4. Implement randomization service

---

## ❓ Statistical Testing: How to Declare Success?

**Status:** Open
**Priority:** Medium
**Category:** Evaluation

### Context
After running an A/B test, we need to decide if Bandicoot is "better."

### The Question
What statistical test and decision criteria should we use?

### Hypothesis Test

**Null hypothesis (H0):** Bandicoot and control have equal outcomes
**Alternative (H1):** Bandicoot has better outcomes

**Test statistic:**
- Two-sample t-test (if outcome is continuous)
- Two-sample proportion test (if outcome is binary, like engagement rate)

**Significance level (alpha):** 0.05 (standard), or 0.01 (more conservative)

**Power (1-beta):** 0.80 (80% chance of detecting true effect)

### Multiple Testing Correction

If testing multiple outcomes (engagement, retention, etc.), need to correct for multiple comparisons:
- **Bonferroni:** Divide alpha by number of tests
- **Holm:** Sequential testing procedure
- **Primary + secondary:** Pre-specify one primary outcome, others are exploratory

### Stopping Rules

**When to stop the test:**
1. **Fixed horizon:** Run for pre-specified duration (e.g., 4 weeks)
   - **Pros:** Controlled error rates
   - **Cons:** May run longer than needed if effect is large

2. **Sequential testing:** Check p-value at intervals, stop if significant
   - **Pros:** Can stop early if clear winner
   - **Cons:** Inflates Type I error (unless using proper sequential methods)

3. **Bayesian decision:** Stop when posterior probability crosses threshold
   - **Pros:** Principled, incorporates prior beliefs
   - **Cons:** More complex, requires prior specification

### Decision Criteria

**What counts as "success":**
- **Statistical significance:** p < 0.05
- **AND practical significance:** Effect size > minimum valuable improvement (e.g., +5% engagement)
- **AND non-inferiority on secondary metrics:** Bandicoot doesn't harm retention, fairness, etc.

### Next Steps
1. Define null and alternative hypotheses
2. Calculate required sample size for desired power
3. Pre-register analysis plan (before running test)
4. Decide on stopping rule

---

## ❓ Long-Term Evaluation: How to Measure Sustained Impact?

**Status:** Open
**Priority:** Low
**Category:** Evaluation

### Context
Initial A/B test may show short-term lift. But does the effect persist?

### The Question
How do we evaluate long-term impact of Bandicoot?

### Challenges

**Novelty Effect:**
- Initial improvement may be due to novelty of new system
- Effect may decay over time

**Adaptation:**
- Caregivers and counselors may adapt to Bandicoot
- Behavior may change in unpredictable ways

**External Factors:**
- Seasonality, policy changes, external events
- Hard to attribute long-term trends to Bandicoot

### Methods

1. **Extended A/B Test**
   - Run test for 3-6 months instead of 4 weeks
   - Track outcomes over time, check for decay
   - **Pros:** Clean causal inference
   - **Cons:** Expensive, may be unethical to keep control group

2. **Time Series Analysis**
   - Deploy Bandicoot to all, track outcomes over time
   - Compare to historical trend (before Bandicoot)
   - **Pros:** Uses all data, long time horizon
   - **Cons:** Confounded by other changes

3. **Interrupted Time Series**
   - Deploy Bandicoot at a specific time
   - Look for discontinuity in outcomes at deployment time
   - **Pros:** Quasi-experimental, can detect causal impact
   - **Cons:** Requires stable pre-trend, sensitive to timing

4. **Rollout Staggered Over Time/Regions**
   - Deploy Bandicoot to different regions at different times
   - Use early regions as control for late regions (and vice versa)
   - **Pros:** Identifies causal effect
   - **Cons:** Requires staggered rollout plan

### Next Steps
1. Plan for extended evaluation beyond initial A/B test
2. Set up longitudinal tracking of outcomes
3. Define success criteria for sustained impact

---

## ✅ Resolved Questions

*Resolved questions will be moved here with links to decision documents*

### Validation Metric: Whittle Index Accuracy
**Decision:** Use numerical agreement with SAHELI as validation metric
**Rationale:** SAHELI is proven, so matching it validates correctness
**Date:** 2025-11-22
**Result:** Perfect match (max error: 0.000091) ✅
