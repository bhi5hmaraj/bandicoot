# SAHELI Implementation Analysis

**Source:** https://github.com/armman-projects/SAHELI
**Organization:** ARMMAN + Google Research
**Impact:** 62% → 80% vaccination completion (18% absolute improvement)
**Scale:** 98K beneficiaries served, 20K enrolling per month

---

## Overview

SAHELI is the proven RMAB implementation for maternal health that Bandicoot is based on. This document analyzes their codebase to inform our library-first development approach.

---

## Codebase Structure

**Extremely simple and focused:**
```
SAHELI/
├── pipeline.py           # Main orchestration (122 lines)
├── whittle_utils.py      # Whittle index computation (169 lines)
├── data_description.md   # Data schema
├── data_utils.py         # (referenced, not in repo)
├── model_utils.py        # (referenced, not in repo)
└── armman_db_utils.py    # (referenced, not in repo)
```

**Key Insight:** The core RMAB logic is ~300 lines of Python. The rest is data loading and database integration.

---

## Configuration Parameters

```python
CONFIG = {
    "problem": {
        "orig_states": ['L', 'H'],           # Low-risk (E), High-risk (NE)
        "actions": ["N", "I"],                # No intervention, Intervention
    },
    "time_step": 7,                           # Weekly decisions
    "gamma": 0.99,                            # Discount factor
    "clusters": 20,                           # K-means clusters
    "transitions": "weekly",
    "clustering": "kmeans",
    "interventions": 1000,                    # Budget K
}
```

**Mapping to Bandicoot:**
- `L` (Low-risk) = `R` (Responsive) in our design
- `H` (High-risk) = `U` (Unresponsive) in our design
- `N` (No intervention) = Passive action
- `I` (Intervention) = Active action

---

## Data Schema

### Socio-Demographic Features
```
- enroll_gest_age: Gestation age at enrollment
- registration_date: Registration date
- language: Preferred language
- age: Beneficiary age
- education: 7 levels (Illiterate to Post Graduate)
- phone_owner: Mother/Husband/Family
- call_slots: Preferred time slot
- enroll_delivery_status: Already delivered? (binary)
- ChannelType: Hospital/Door-to-Door/Partner NGO
- income_bracket: 7 brackets (0-5k to >30k INR)
- ngo_hosp_id: Hospital ID
- g, p, s, l: Gravidity, Parity, Stillbirths, Live births
```

### Call Data Features
```
- user_id: Unique beneficiary ID
- startdatetime: Call timestamp
- duration: Call duration (seconds)
- gest_age: Gestational age when call received
- callStatus: Call connection status
- dropreason: Reason for call end
- media_id: Message content ID
```

**Key for Bandicoot (Suvita Immunization):**
We'll adapt this schema to:
- Replace gestation_age with child_age
- Replace delivery_status with vaccination_status
- Keep demographics (age, education, income, etc.)
- Keep engagement data (SMS delivery, opens, duration)

---

## State Determination Logic

```python
# From pipeline.py lines 81-93
past_days_calls = call_data[
    (call_data["user_id"]==puser_id) &
    (call_data["startdate"]<date_num) &
    (call_data["startdate"]>=date_num - 7)  # Last 7 days
]

past_days_connections = past_days_calls[past_days_calls['duration']>0].shape[0]
past_days_engagements = past_days_calls[past_days_calls['duration'] >= 30].shape[0]

if past_days_engagements == 0:
    curr_state = 3  # NE (Not Engaged / High-risk)
else:
    curr_state = 2  # E (Engaged / Low-risk)
```

**Rule:** If ANY call in last 7 days had duration ≥30 seconds → Engaged

**Bandicoot Adaptation (for SMS):**
```python
# For SMS-based system
past_week_sms = sms_logs[
    (sms_logs["caregiver_id"]==cg_id) &
    (sms_logs["sent_date"]>=today - 7)
]

opened = past_week_sms[past_week_sms['opened']==True].shape[0]

if opened == 0:
    state = "U"  # Unresponsive
else:
    state = "R"  # Responsive
```

---

## Whittle Index Computation

### Algorithm: Binary Search + Value Iteration

**File:** `whittle_utils.py` lines 45-167

**Core Logic:**
1. **Binary search** on subsidy value `m` to find indifference point
2. **Value iteration** to compute Q-values for each subsidy
3. Iterate until Q(s, passive) ≈ Q(s, active) (within 1e-5)

```python
def planinf(two_state_probs, sleeping_constraint=True, GAMMA=0.99):
    '''
    two_state_probs: transition probabilities [action, state, next_state]
    Returns: [whittle_index_NE, whittle_index_E]
    '''

    # Initialize search bounds
    high_m_values = 2 * np.ones(len(states))
    low_m_values = -2 * np.ones(len(states))

    max_q_diff = np.inf
    while max_q_diff > 1e-5:
        m_values = (low_m_values + high_m_values) / 2

        # Value iteration inner loop
        delta = np.inf
        while delta > 0.0001:
            for i in range(num_states):
                v = v_values[i]
                v_a = np.zeros(num_actions)
                for k in range(num_actions):
                    for j in range(num_states):
                        v_a[k] += t_probs[i, j, k] * (
                            get_reward(state[i], action[k], m_values[i])
                            + gamma * v_values[j]
                        )
                v_values[i] = np.max(v_a)
                delta = max(delta, abs(v_values[i] - v))

        # Compute Q-values
        for state in range(num_states):
            for action in range(num_actions):
                for next_state in range(num_states):
                    q_values[state, action] += t_probs[state, next_state, action] * (
                        get_reward(state, action, m_values[state])
                        + gamma * v_values[next_state]
                    )

        # Find state with max Q-diff
        max_q_diff = 0
        for state in range(num_states):
            if abs(q_values[state, 1] - q_values[state, 0]) > max_q_diff:
                state_idx = state
                max_q_diff = abs(q_values[state, 1] - q_values[state, 0])

        # Update binary search bounds
        if q_values[state_idx, 0] < q_values[state_idx, 1]:
            low_m_values[state_idx] = m_values[state_idx]
        else:
            high_m_values[state_idx] = m_values[state_idx]

    return [m_values[-1], m_values[-2]]  # [W_NE, W_E]
```

**Performance:** Converges in ~10-20 iterations per cluster-state pair

**Bandicoot Implementation Notes:**
- Matches our design exactly (docs/tech-design/02-rmab-core.md)
- Convergence threshold: 1e-5 for Q-value difference
- Convergence threshold: 0.0001 for value iteration delta
- Need numerical stability checks (NaN/Inf detection)

---

## Reward Function

```python
def get_reward(state, action, m):
    if state[0] == "L":  # Low-risk (Engaged)
        reward = 1.0
    else:                # High-risk (Not Engaged)
        reward = -1

    if action == 'N':    # Passive action
        reward += m       # Add subsidy for passive

    return reward
```

**Interpretation:**
- **Engaged state (L/R):** +1 reward (good outcome)
- **Unresponsive state (H/U):** -1 reward (bad outcome)
- **Passive action:** Gets subsidy `m` (found via binary search)
- **Active action:** No subsidy

**Bandicoot Adaptation:**
We can use the same reward structure:
```python
def get_reward(state, action, m):
    if state == "R":  # Responsive
        reward = 1.0
    else:             # Unresponsive
        reward = -1.0

    if action == "passive":
        reward += m

    return reward
```

---

## Pipeline Workflow

**File:** `pipeline.py` - Main orchestration

### Step-by-step execution:

```python
# 1. Load deployment parameters (budget K, date ranges)
df_params = load_params_table()
CONFIG['interventions'] = int(df_params['beneficiary_count'].to_list()[-1])

# 2. Load beneficiary data (demographics + call history)
static_features, beneficiary_data, call_data, user_ids = load_data(CONFIG)

# 3. Load pre-trained clustering model (scikit-learn)
cls, scaler = load_mapping_model(CONFIG)

# 4. Load pre-computed Whittle indices (20 clusters x 2 states)
m_values = load_precomputed_whittle_indices(CONFIG)

# 5. Predict clusters for all beneficiaries
cluster_predictions = cls.predict(scaler.transform(static_features))

# 6. Load previous intervention list (avoid re-contacting)
df_intervention, intervention_users = load_interventions_table(CONFIG)

# 7. Compute current state and Whittle index for each beneficiary
whittle_indices = []
for idx, user_id in enumerate(user_ids):
    if user_id in intervention_users:
        continue  # Skip recently contacted

    # Determine current state (E or NE)
    past_week_calls = call_data[
        (call_data["user_id"]==user_id) &
        (call_data["startdate"]>=date_num - 7)
    ]
    engagements = past_week_calls[past_week_calls['duration'] >= 30].shape[0]
    curr_state = 2 if engagements > 0 else 3  # E=2, NE=3

    # Get cluster prediction
    curr_cluster = cluster_predictions[idx]

    # Fetch Whittle index for (cluster, state)
    whittle_index = m_values[curr_cluster, curr_state]

    whittle_indices.append({
        'user_id': user_id,
        'whittle_index': whittle_index,
        'cluster': curr_cluster,
        'start_state': 'E' if curr_state == 2 else 'NE',
        'registration_date': beneficiary_data[beneficiary_data['user_id']==user_id]['registration_date'].item()
    })

# 8. Rank by Whittle index (descending)
df = pd.DataFrame(whittle_indices)
df = df.sort_values('whittle_index', ascending=False)

# 9. Select top-K and push to intervention system
df_interventions = df[:CONFIG["interventions"]]
push_interventions(df_interventions, CONFIG)
```

**Key Insights:**
1. **Pre-computation:** Clustering model and Whittle indices are pre-trained/computed
2. **Real-time:** Only state determination and ranking happen in real-time
3. **Simplicity:** ~50 lines of core logic for recommendation generation
4. **Stateless:** Each run is independent (no complex state management)

---

## Clustering Details

**Method:** K-means on **passive transition probabilities**

**Features for clustering:**
- Extracted from historical call data
- Focus on passive (no intervention) behavior
- Demographics NOT used for clustering (used for cold-start FO mapper)

**Parameters:**
- k = 20 clusters
- Warmup period: 6 weeks (need engagement history before clustering)

**Bandicoot Notes:**
- SAHELI doesn't show clustering code (in `data_utils.py` not in repo)
- We need to implement from scratch based on docs/tech-design/02-rmab-core.md
- Extract passive transition probabilities: P(R→R|passive), P(R→U|passive), etc.
- Run k-means on feature vector per caregiver

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         OFFLINE TRAINING                         │
│                                                                  │
│  Historical Data (6 months)                                      │
│         ↓                                                        │
│  Extract Features (demographics, call patterns)                  │
│         ↓                                                        │
│  Clustering (K-means, k=20)                                      │
│         ↓                                                        │
│  Train FO Mapper (demographics → cluster)                        │
│         ↓                                                        │
│  Learn MDP Parameters (per cluster)                              │
│         ↓                                                        │
│  Compute Whittle Indices (20 clusters × 2 states)                │
│         ↓                                                        │
│  Save Models: clustering_model.pkl, fo_mapper.pkl, indices.pkl   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      ONLINE RECOMMENDATION                       │
│                                                                  │
│  Load Models (clustering, FO mapper, Whittle indices)            │
│         ↓                                                        │
│  Load Current Beneficiaries (demographics + recent calls)        │
│         ↓                                                        │
│  Predict Cluster (using FO mapper or historical data)            │
│         ↓                                                        │
│  Determine Current State (E or NE based on last 7 days)          │
│         ↓                                                        │
│  Fetch Whittle Index (from pre-computed table)                   │
│         ↓                                                        │
│  Rank by Whittle Index (descending)                              │
│         ↓                                                        │
│  Select Top-K (K=1000)                                           │
│         ↓                                                        │
│  Push to Intervention System                                     │
└─────────────────────────────────────────────────────────────────┘
```

**Key Observation:** Clear separation of offline (training) and online (inference) phases

---

## Comparison with Bandicoot Design

| Aspect | SAHELI | Bandicoot Plan | Match? |
|--------|--------|----------------|--------|
| **States** | 2 (E, NE) | 2 (R, U) | ✅ Same concept |
| **Actions** | 2 (N, I) | 2 (passive, active) | ✅ Same |
| **Clustering** | K-means, k=20 | K-means, k=15-25 | ✅ Same approach |
| **Whittle Solver** | Binary search + value iteration | Binary search + value iteration | ✅ Exact match |
| **Gamma** | 0.99 | 0.95 | ⚠️ Slightly different |
| **Budget** | 1000/week | Configurable | ✅ Similar scale |
| **Warmup** | 6 weeks | 6 weeks | ✅ Same |
| **State Logic** | Duration ≥30s → E | SMS opened → R | ✅ Same pattern |
| **Cold-start** | FO mapper (RandomForest) | FO mapper (RandomForest) | ✅ Same |
| **Time step** | Weekly | Daily (configurable) | ⚠️ Different granularity |

**Conclusion:** Our design is **highly aligned** with proven SAHELI approach

---

## Key Learnings for Bandicoot

### 1. **Library Structure**

**SAHELI lesson:** Keep core logic simple and focused

**Bandicoot structure:**
```
bandicoot/
├── core/
│   ├── clustering.py      # K-means on passive features
│   ├── mdp.py             # MDP parameter learning
│   ├── whittle.py         # Binary search + value iteration (from whittle_utils.py)
│   ├── fo_mapper.py       # RandomForest for cold-start
│   └── recommender.py     # Main orchestration (from pipeline.py)
├── data/
│   ├── loaders.py         # CSV/DataFrame loaders
│   ├── preprocessors.py   # Feature extraction
│   └── synthetic.py       # Data generator for testing
└── utils/
    ├── metrics.py         # Evaluation (precision@k, NDCG)
    └── visualization.py   # Plotting for notebooks
```

### 2. **Whittle Index Implementation**

**Copy the algorithm exactly from `whittle_utils.py`:**
- Binary search convergence: `1e-5`
- Value iteration convergence: `0.0001`
- Search bounds: `[-2, 2]`
- Gamma: Start with `0.99` (can experiment with 0.95)

### 3. **State Determination**

**Simple, rule-based approach:**
```python
def determine_state(caregiver_id, sms_logs, lookback_days=7):
    recent_sms = sms_logs[
        (sms_logs['caregiver_id'] == caregiver_id) &
        (sms_logs['sent_date'] >= today - timedelta(days=lookback_days))
    ]

    opened_count = recent_sms[recent_sms['opened'] == True].shape[0]

    return "R" if opened_count > 0 else "U"
```

### 4. **Recommendation Workflow**

**Follow SAHELI's pipeline.py structure:**
```python
class BandicootRMAB:
    def __init__(self, n_clusters=20, warmup_weeks=6, gamma=0.99):
        self.n_clusters = n_clusters
        self.warmup_weeks = warmup_weeks
        self.gamma = gamma
        self.clustering_model = None
        self.fo_mapper = None
        self.whittle_indices = None  # (n_clusters, 2) array

    def fit(self, historical_df):
        """Offline training phase"""
        # 1. Extract features
        features = self._extract_passive_features(historical_df)

        # 2. Cluster
        from sklearn.cluster import KMeans
        self.clustering_model = KMeans(n_clusters=self.n_clusters)
        cluster_assignments = self.clustering_model.fit_predict(features)

        # 3. Train FO mapper
        from sklearn.ensemble import RandomForestClassifier
        demographics = self._extract_demographics(historical_df)
        self.fo_mapper = RandomForestClassifier()
        self.fo_mapper.fit(demographics, cluster_assignments)

        # 4. Learn MDP parameters per cluster
        mdp_params = self._learn_mdp_parameters(historical_df, cluster_assignments)

        # 5. Compute Whittle indices
        self.whittle_indices = np.zeros((self.n_clusters, 2))
        for c in range(self.n_clusters):
            self.whittle_indices[c] = planinf(
                mdp_params[c]['transition_probs'],
                gamma=self.gamma
            )

    def recommend(self, current_df, budget):
        """Online recommendation phase"""
        recommendations = []

        for idx, row in current_df.iterrows():
            # 1. Predict cluster
            demographics = self._extract_demographics_row(row)
            cluster = self.fo_mapper.predict([demographics])[0]

            # 2. Determine current state
            state = self._determine_state(row)
            state_idx = 0 if state == "R" else 1

            # 3. Fetch Whittle index
            whittle_index = self.whittle_indices[cluster, state_idx]

            recommendations.append({
                'caregiver_id': row['caregiver_id'],
                'whittle_index': whittle_index,
                'cluster': cluster,
                'state': state
            })

        # 4. Rank and select top-K
        df = pd.DataFrame(recommendations)
        df = df.sort_values('whittle_index', ascending=False)
        return df.head(budget)
```

### 5. **Testing Strategy**

**SAHELI doesn't show tests, but we should add:**
- Unit tests for Whittle solver (validate properties)
- Unit tests for state determination logic
- Integration tests on synthetic data
- Validation on historical Suvita data

### 6. **Deployment Pattern**

**SAHELI uses:**
- Pre-trained models saved as `.pkl` files
- Weekly training jobs (offline)
- Daily recommendation generation (online)
- Database integration for fetching data and pushing results

**Bandicoot Phase 0 (Library):**
- Pure Python, no database
- Save models to pickle files
- Focus on algorithm correctness

**Bandicoot Phase 1 (Service):**
- Wrap library in FastAPI
- Add database layer
- Add caching (Redis)

---

## Adaptation Checklist for Suvita

### Data Schema Mapping

| SAHELI (Maternal) | Bandicoot (Immunization) |
|-------------------|--------------------------|
| Gestational age | Child age (months) |
| Delivery status | Vaccination status |
| Call duration | SMS opened/delivered |
| Call engagement | SMS engagement |
| Pregnancy parity | Number of children |
| Registration hospital | Registration clinic |

### Engagement Metrics

**SAHELI:**
- Call duration ≥30 seconds → Engaged
- Lookback: 7 days

**Bandicoot:**
- SMS opened → Responsive
- SMS delivered but not opened → Check delivery status
- No SMS sent → Check if in warmup period
- Lookback: 7 days (configurable)

### Budget Constraints

**SAHELI:**
- 1000 interventions/week
- 98K beneficiaries
- Intervention rate: ~1%

**Bandicoot (Suvita):**
- Budget: TBD (ask Suvita)
- Scale: 200K caregivers
- Suggested: 1000-2000 SMS/day (7K-14K per week)

---

## Implementation Priorities

Based on SAHELI analysis, implement in this order:

### Phase 0.1: Core Algorithms (Week 1)
1. **Whittle solver** (`whittle.py`) - Copy from SAHELI, add tests
2. **Clustering** (`clustering.py`) - K-means on passive features
3. **MDP learning** (`mdp.py`) - Parameter estimation per cluster
4. **State determination** - Simple rule-based logic

### Phase 0.2: Integration (Week 1-2)
5. **Recommender** (`recommender.py`) - Orchestration (follow pipeline.py)
6. **FO mapper** (`fo_mapper.py`) - RandomForest for cold-start
7. **Data loaders** (`loaders.py`) - CSV → DataFrame
8. **Preprocessors** (`preprocessors.py`) - Feature extraction

### Phase 0.3: Validation (Week 2)
9. **Synthetic data generator** - For testing
10. **Experiments** - Jupyter notebooks for validation
11. **Documentation** - API reference
12. **Suvita pilot** - 10K caregiver test

---

## Code Reuse from SAHELI

### Direct Copy (with attribution)
- `whittle_utils.py` → `bandicoot/core/whittle.py`
  - Keep the algorithm exactly as-is (proven to work)
  - Add docstrings and type hints
  - Add numerical stability checks

### Adapt Structure
- `pipeline.py` → `bandicoot/core/recommender.py`
  - Same workflow, different data source
  - Make it database-agnostic (use DataFrames)

### Implement from Scratch
- Clustering (not in SAHELI repo)
- MDP learning (not in SAHELI repo)
- FO mapper (not in SAHELI repo)
- Data preprocessing (specific to Suvita)

---

## Next Steps

1. **Copy Whittle solver** from SAHELI to `bandicoot/core/whittle.py`
2. **Create synthetic data generator** matching Suvita schema
3. **Implement clustering** on synthetic data
4. **Test Whittle solver** on synthetic MDP parameters
5. **Build recommender** following pipeline.py pattern
6. **Validate on synthetic data** (end-to-end)
7. **Test on Suvita sample** (10K caregivers)

---

**Author:** Bandicoot Team
**Date:** November 2025
**Status:** Analysis Complete → Ready for Implementation
