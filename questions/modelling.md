# Modeling Questions

Questions about RMAB algorithm choices, mathematical assumptions, parameter tuning, and optimization strategies.

---

## ❓ Optimal Number of Clusters (k)

**Status:** Open
**Priority:** High
**Category:** Modeling

### Context
SAHELI uses k=20 clusters by default. We need to determine if this is optimal for Suvita's caregiver population.

### The Question
How should we choose the number of clusters for Suvita's caregivers?

### Options
1. **Use k=20 (SAHELI default)**
   - Pros: Proven in production, validated approach
   - Cons: May not be optimal for Suvita's different population

2. **Silhouette score optimization**
   - Pros: Data-driven, automatic selection
   - Cons: Computationally expensive, may not align with interpretability

3. **Domain-driven segmentation**
   - Pros: Interpretable clusters (e.g., "new moms", "experienced", "at-risk")
   - Cons: Requires domain expertise, may not capture nuanced behavior

4. **Hierarchical approach**
   - Start with 3-5 high-level clusters, refine as needed
   - Pros: Interpretable, scalable
   - Cons: May miss fine-grained patterns

### Implications
- **Performance:** Too few clusters → poor personalization; too many → overfitting
- **Interpretability:** Cluster count affects ability to understand caregiver segments
- **Computational cost:** More clusters = more Whittle index computations

### Next Steps
1. Run silhouette analysis on Suvita's historical data (k=2 to k=50)
2. Compare cluster characteristics for different k values
3. Consult with Suvita team on interpretability needs
4. A/B test different k values in production

---

## ❓ Discount Factor (gamma) Selection

**Status:** Open
**Priority:** Medium
**Category:** Modeling

### Context
SAHELI uses gamma=0.99 (heavily weights long-term outcomes). The discount factor determines how much we prioritize immediate vs. future engagement.

### The Question
What discount factor should we use for Suvita's intervention planning horizon?

### Options
1. **gamma = 0.99 (SAHELI default)**
   - Planning horizon ≈ 100 timesteps
   - Optimizes for long-term engagement

2. **gamma = 0.95**
   - Planning horizon ≈ 20 timesteps
   - More weight on near-term engagement

3. **gamma = 0.90**
   - Planning horizon ≈ 10 timesteps
   - Strong near-term focus

4. **Adaptive gamma based on caregiver lifecycle**
   - Higher gamma for new caregivers (long-term investment)
   - Lower gamma for at-risk caregivers (immediate intervention)

### Implications
- **Higher gamma:** Prioritizes caregivers who will benefit most over the long term
- **Lower gamma:** Prioritizes immediate risk mitigation
- **Program goals:** What is Suvita optimizing for? Retention? Immediate responses?

### Next Steps
1. Understand Suvita's typical engagement timeline (how long do caregivers stay?)
2. Run sensitivity analysis on gamma values (0.90, 0.95, 0.99)
3. Consult with Suvita on program objectives (long-term retention vs. immediate engagement)

---

## ❓ State Definition and Granularity

**Status:** Open
**Priority:** High
**Category:** Modeling

### Context
Currently using binary states: Responsive (R) vs. Unresponsive (U). Real engagement may be more nuanced.

### The Question
Should we use binary states or multi-level engagement states?

### Options
1. **Binary (current): R vs. U**
   - Pros: Simple, proven, easy to interpret
   - Cons: Loses granularity (e.g., "somewhat engaged" → where does it go?)

2. **3-level: High / Medium / Low engagement**
   - Pros: More granular, captures partial engagement
   - Cons: More complex (3x3=9 state transitions per action)

3. **4-level: Highly Engaged / Engaged / At-Risk / Disengaged**
   - Pros: Very interpretable, aligns with common segmentation
   - Cons: Even more complex, needs more data

4. **Continuous engagement score**
   - Pros: Maximum granularity
   - Cons: Doesn't fit RMAB framework (needs discrete states)

### Implications
- **Data requirements:** More states need more historical data for reliable estimation
- **Whittle index computation:** More states = more expensive computation
- **Interpretability:** More states may or may not improve understanding

### Next Steps
1. Analyze distribution of Suvita's engagement metrics
2. Check if binary split captures most variance (or if we're losing information)
3. Prototype 3-state model and compare to binary
4. Evaluate data sufficiency for multi-state modeling

---

## ❓ Action Definition: What Counts as Intervention?

**Status:** Open
**Priority:** High
**Category:** Modeling

### Context
Currently using binary actions: Passive (no contact) vs. Active (intervention). But Suvita has multiple intervention types.

### The Question
How should we model different intervention types?

### Options
1. **Binary: Contact vs. No Contact**
   - Pros: Simple, aligns with RMAB framework
   - Cons: Treats all interventions equally (SMS = phone call = home visit?)

2. **Multi-action: {None, SMS, Call, Visit}**
   - Pros: Can optimize intervention *type*, not just whether to intervene
   - Cons: More complex, may need different RMAB formulation

3. **Action intensity: {None, Low, Medium, High}**
   - Aggregate interventions by intensity/cost
   - Pros: Captures intervention strength, stays in RMAB framework
   - Cons: Requires defining "intensity" mapping

4. **Separate models per intervention type**
   - Build separate RMAB for SMS, calls, visits
   - Pros: Clean separation, can optimize each channel
   - Cons: Doesn't capture cross-channel effects

### Implications
- **Optimization:** Binary action optimizes *who* to contact; multi-action optimizes *who* and *how*
- **Complexity:** More actions exponentially increase state space
- **Data requirements:** Need sufficient observations for each action type

### Next Steps
1. Get breakdown of Suvita's intervention types and their costs
2. Analyze transition probabilities for different intervention types
3. Decide if intervention type selection is in scope (or separate system)
4. Consider hierarchical approach: RMAB for "who", separate model for "how"

---

## ❓ Passive Transition Estimation

**Status:** Open
**Priority:** Medium
**Category:** Modeling

### Context
We cluster caregivers by passive (no intervention) behavior. But what if we have limited passive observations?

### The Question
How do we handle caregivers with very few passive observations?

### Options
1. **Bayesian smoothing (current approach)**
   - Use Dirichlet prior (alpha=1.0) to smooth sparse estimates
   - Pros: Principled, handles missing data
   - Cons: Prior may not reflect true passive behavior

2. **Informative priors from population**
   - Use population-level passive behavior as prior
   - Pros: More realistic prior than uniform
   - Cons: Requires two-stage estimation

3. **Minimum observation threshold**
   - Only cluster caregivers with ≥N passive observations
   - Pros: Ensures reliable estimates
   - Cons: May exclude many caregivers

4. **Semi-supervised approach**
   - Use caregiver features (demographics, etc.) to predict passive behavior
   - Pros: Leverages all available data
   - Cons: Requires feature engineering, more complex

### Implications
- **Cluster quality:** Poor passive estimates → poor clustering → poor recommendations
- **Coverage:** Strict thresholds may exclude caregivers who need help most
- **Bias:** If we only cluster "data-rich" caregivers, may introduce selection bias

### Next Steps
1. Analyze distribution of passive observation counts in Suvita's data
2. Test sensitivity of clustering to different prior strengths (alpha)
3. Compare cluster assignments with vs. without minimum thresholds

---

## ❓ Time Granularity for State Transitions

**Status:** Open
**Priority:** Medium
**Category:** Modeling

### Context
State transitions depend on the time window. Do we measure engagement daily? Weekly? Monthly?

### The Question
What time granularity should we use for defining state transitions?

### Options
1. **Daily**
   - Pros: Fine-grained, captures rapid changes
   - Cons: May be too noisy, many missing observations

2. **Weekly**
   - Pros: Balances granularity and stability
   - Cons: May miss important short-term dynamics

3. **Monthly**
   - Pros: Stable estimates, fewer missing data points
   - Cons: Too coarse, can't react quickly to changes

4. **Event-based (after each interaction)**
   - Pros: Natural time scale for transitions
   - Cons: Irregular timing, harder to model

### Implications
- **Responsiveness:** Finer granularity = faster adaptation to state changes
- **Data sparsity:** Finer granularity = more missing observations
- **Planning horizon:** Time granularity affects interpretation of gamma

### Next Steps
1. Understand Suvita's typical interaction cadence (how often do they contact caregivers?)
2. Analyze autocorrelation of engagement at different time scales
3. Match time granularity to program intervention frequency

---

## ❓ Handling Non-Stationarity

**Status:** Open
**Priority:** Low
**Category:** Modeling

### Context
RMAB assumes stationary transition probabilities. But caregiver behavior may change over time (seasonality, lifecycle).

### The Question
How do we handle time-varying transition probabilities?

### Options
1. **Assume stationarity (current approach)**
   - Pros: Simple, standard RMAB assumption
   - Cons: May not reflect reality (e.g., behavior changes as baby grows)

2. **Sliding window estimation**
   - Re-estimate transitions using only recent history (e.g., last 3 months)
   - Pros: Adapts to recent behavior
   - Cons: Requires frequent re-training

3. **Online learning**
   - Update transition estimates incrementally as new data arrives
   - Pros: Always up-to-date
   - Cons: More complex, may drift

4. **Lifecycle-aware modeling**
   - Separate models for different caregiver lifecycle stages
   - Pros: Captures systematic changes (e.g., prenatal vs. postnatal)
   - Cons: Requires lifecycle segmentation

### Implications
- **Model accuracy:** Stale estimates may give poor recommendations
- **Computational cost:** Frequent re-training is expensive
- **Concept drift:** Caregiver behavior may genuinely change over time

### Next Steps
1. Analyze temporal stability of transition probabilities in Suvita's data
2. Test sliding window approach (compare 1-month, 3-month, 6-month windows)
3. Consider if lifecycle stages are available and useful

---

## ✅ Resolved Questions

*Resolved questions will be moved here with links to decision documents*

### Initial State Space Design
**Decision:** Use binary states (Responsive vs. Unresponsive)
**Rationale:** Aligns with SAHELI, simpler to validate, can expand later if needed
**Date:** 2025-11-22
