# RMAB Core Algorithms

**Version:** 1.0
**Last Updated:** November 2025
**Parent Doc:** [00-overview.md](00-overview.md)

---

## Overview

This document details the core RMAB algorithms adapted from SAHELI's proven deployment:
1. Clustering caregivers by passive engagement behavior
2. Learning MDP parameters per cluster using bayesianbandits
3. Computing Whittle indices via binary search + value iteration
4. Features-Only (FO) mapping for cold-start caregivers

**Key Reference:** SAHELI (Google/ARMMAN IAAI 2023), ARMMAN Field Study (AAAI 2022)

---

## Algorithm 1: Clustering (SAHELI Method)

### Objective
Group 200K caregivers into ~20 clusters to:
- Share statistical strength (combat data sparsity)
- Reduce computational complexity (20 MDPs vs 200K)
- Enable fast inference for new caregivers

### Input
Historical SMS engagement data (past 6 months):
```python
{
    'caregiver_id': str,
    'sms_sent': datetime,
    'sms_delivered': datetime,
    'sms_opened': datetime,  # nullable
    'vaccinated': bool,
    'state_before': str,  # 'Responsive' or 'Unresponsive'
    'state_after': str
}
```

### Feature Engineering: Passive Transition Probabilities

**Key Insight (from SAHELI):** Cluster based on how caregivers behave *without* intervention.

```python
def compute_passive_features(caregiver_data):
    """
    Extract passive transition probabilities for a single caregiver.

    Returns:
        np.array([P(R→R|passive), P(R→U|passive), P(U→R|passive), P(U→U|passive)])
    """
    passive_transitions = caregiver_data[caregiver_data['action'] == 'passive']

    # Count transitions
    counts = {
        'R→R': 0, 'R→U': 0,
        'U→R': 0, 'U→U': 0
    }

    for _, row in passive_transitions.iterrows():
        key = f"{row['state_before'][0]}→{row['state_after'][0]}"
        counts[key] += 1

    # Normalize to probabilities (with Laplace smoothing)
    alpha = 1.0  # Smoothing parameter
    features = []

    for start_state in ['R', 'U']:
        total = sum(counts[f'{start_state}→{end}'] for end in ['R', 'U']) + 2*alpha
        for end_state in ['R', 'U']:
            prob = (counts[f'{start_state}→{end_state}'] + alpha) / total
            features.append(prob)

    return np.array(features)
```

### Clustering Algorithm

```python
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

def cluster_caregivers(historical_data, k_range=(15, 25)):
    """
    Cluster caregivers using k-means on passive transition features.

    Args:
        historical_data: DataFrame with caregiver interaction history
        k_range: Tuple (min_k, max_k) for elbow method

    Returns:
        cluster_assignments: Dict[caregiver_id, cluster_id]
        k_optimal: Chosen number of clusters
    """
    # 1. Extract passive features per caregiver
    caregiver_ids = historical_data['caregiver_id'].unique()
    features = []

    for cid in caregiver_ids:
        cdata = historical_data[historical_data['caregiver_id'] == cid]
        features.append(compute_passive_features(cdata))

    X = np.array(features)

    # 2. Elbow method to choose k
    inertias = []
    silhouettes = []

    for k in range(k_range[0], k_range[1] + 1):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)

        inertias.append(kmeans.inertia_)
        silhouettes.append(silhouette_score(X, labels))

    # Choose k with best silhouette score (or manual inspection)
    k_optimal = k_range[0] + np.argmax(silhouettes)

    # 3. Final clustering
    kmeans = KMeans(n_clusters=k_optimal, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)

    cluster_assignments = dict(zip(caregiver_ids, labels))

    return cluster_assignments, k_optimal, kmeans
```

**Hyperparameters:**
- `k_range`: (15, 25) based on SAHELI's ~20 clusters
- `n_init`: 10 initializations to avoid local minima
- `random_state`: 42 for reproducibility

---

## Algorithm 2: MDP Parameter Learning (Per Cluster)

### Objective
For each cluster, learn:
- **P(S'|S,A)**: Transition probabilities
- **P(R|S,A)**: Reward probabilities

Where:
- **S** = {Responsive, Unresponsive}
- **A** = {active (SMS/call), passive (no intervention)}
- **R** = {0 (no vaccination), 1 (vaccinated)}

### bayesianbandits Integration

```python
from bayesianbandits import DirichletClassifier

def learn_cluster_mdp(cluster_data):
    """
    Learn MDP parameters for a cluster using Bayesian inference.

    Args:
        cluster_data: DataFrame with (state, action, next_state, reward) tuples

    Returns:
        mdp_params: Dict with P_transition and P_reward
    """
    # Initialize Bayesian model (Beta-Bernoulli for binary outcomes)
    model = DirichletClassifier(
        alpha=1.0,  # Prior pseudo-count
        states=['Responsive', 'Unresponsive'],
        actions=['active', 'passive']
    )

    # Learn transitions: P(S'|S,A)
    for state in ['Responsive', 'Unresponsive']:
        for action in ['active', 'passive']:
            subset = cluster_data[
                (cluster_data['state_before'] == state) &
                (cluster_data['action'] == action)
            ]

            if len(subset) == 0:
                continue  # Use prior if no data

            next_states = subset['state_after'].values
            model.update(state, action, next_states)

    # Extract learned probabilities
    P_transition = {}
    for state in ['Responsive', 'Unresponsive']:
        P_transition[state] = {}
        for action in ['active', 'passive']:
            probs = model.predict_proba(state, action)
            P_transition[state][action] = {
                'Responsive': probs[0],
                'Unresponsive': probs[1]
            }

    # Learn rewards: P(R=1|S,A)
    P_reward = {}
    for state in ['Responsive', 'Unresponsive']:
        P_reward[state] = {}
        for action in ['active', 'passive']:
            subset = cluster_data[
                (cluster_data['state_before'] == state) &
                (cluster_data['action'] == action)
            ]

            if len(subset) == 0:
                P_reward[state][action] = 0.5  # Uninformed prior
            else:
                P_reward[state][action] = subset['vaccinated'].mean()

    return {
        'P_transition': P_transition,
        'P_reward': P_reward
    }
```

**Output Example:**
```json
{
  "P_transition": {
    "Responsive": {
      "active": {"Responsive": 0.85, "Unresponsive": 0.15},
      "passive": {"Responsive": 0.60, "Unresponsive": 0.40}
    },
    "Unresponsive": {
      "active": {"Responsive": 0.50, "Unresponsive": 0.50},
      "passive": {"Responsive": 0.10, "Unresponsive": 0.90}
    }
  },
  "P_reward": {
    "Responsive": {"active": 0.80, "passive": 0.40},
    "Unresponsive": {"active": 0.30, "passive": 0.05}
  }
}
```

---

## Algorithm 3: Whittle Index Computation (SAHELI planinf)

### Background
The Whittle index for state `s` is the subsidy `λ` where:
```
V_active(s) = V_passive(s) + λ
```

Where `V_active(s)` is the value of taking action in state `s`, and `V_passive(s)` is the value of not acting.

**Intuition:** Higher index = higher marginal benefit of intervention.

### Implementation (Binary Search + Value Iteration)

```python
def compute_whittle_index(mdp_params, state, gamma=0.95, tol=1e-6, max_iter=1000):
    """
    Compute Whittle index for a given state using binary search.

    Args:
        mdp_params: Dict with P_transition and P_reward
        state: 'Responsive' or 'Unresponsive'
        gamma: Discount factor (0.95 for ~20-step horizon)
        tol: Convergence tolerance
        max_iter: Max value iteration steps

    Returns:
        index: Whittle index (float)
    """
    P_trans = mdp_params['P_transition']
    P_rew = mdp_params['P_reward']

    states = ['Responsive', 'Unresponsive']

    # Binary search for λ
    lambda_min, lambda_max = 0.0, 10.0

    while lambda_max - lambda_min > 1e-6:
        lambda_mid = (lambda_min + lambda_max) / 2

        # Value iteration for ACTIVE policy
        V_active = value_iteration(
            states, P_trans, P_rew, action='active',
            gamma=gamma, tol=tol, max_iter=max_iter
        )

        # Value iteration for PASSIVE policy (with subsidy λ)
        V_passive = value_iteration(
            states, P_trans, P_rew, action='passive',
            gamma=gamma, tol=tol, max_iter=max_iter,
            subsidy=lambda_mid  # Add λ to passive value
        )

        # Check if active is better than passive + subsidy
        if V_active[state] > V_passive[state]:
            lambda_min = lambda_mid  # Need higher subsidy to balance
        else:
            lambda_max = lambda_mid  # Lower subsidy

    return lambda_mid


def value_iteration(states, P_trans, P_rew, action, gamma, tol, max_iter, subsidy=0.0):
    """
    Standard value iteration for a fixed policy.

    Returns:
        V: Dict[state, value]
    """
    V = {s: 0.0 for s in states}  # Initialize values

    for _ in range(max_iter):
        V_new = {}

        for s in states:
            # Immediate reward
            r = P_rew[s][action]

            # Expected future value
            future = sum(
                P_trans[s][action][s_next] * V[s_next]
                for s_next in states
            )

            V_new[s] = r + gamma * future + subsidy

        # Check convergence
        if max(abs(V_new[s] - V[s]) for s in states) < tol:
            return V_new

        V = V_new

    return V  # Return even if not converged (with warning)
```

### Sleeping State Extension (SAHELI's η=+∞ Approximation)

To prevent over-contacting caregivers, SAHELI adds a "sleeping" period after intervention.

**Simplified Approach for MVP:**
```python
def compute_whittle_with_sleep(mdp_params, state, sleep_duration=2):
    """
    Modify Whittle index to account for sleep period.

    If we intervene, caregiver enters sleep for `sleep_duration` steps
    where no further action can be taken.

    Approximation: Reduce index by penalty proportional to sleep duration.
    """
    base_index = compute_whittle_index(mdp_params, state)

    # Penalty: can't act again for N steps
    sleep_penalty = 0.1 * sleep_duration

    return max(0, base_index - sleep_penalty)
```

**Note:** Full SAHELI approach augments state space to (state, time_since_intervention). For MVP, use simple penalty.

---

## Algorithm 4: Features-Only (FO) Mapping

### Objective
Assign new caregivers to a cluster *immediately* using only demographics (no interaction history).

### Features
```python
FO_FEATURES = [
    'age',
    'district',  # one-hot encoded
    'parity',  # number of children
    'phone_reliable',  # boolean
    'enrollment_source'  # 'hospital', 'community_worker', 'government_portal'
]
```

### Training FO Mapper

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer

def train_fo_mapper(caregiver_data, cluster_assignments):
    """
    Train a classifier: demographics → cluster_id

    Args:
        caregiver_data: DataFrame with FO_FEATURES columns
        cluster_assignments: Dict[caregiver_id, cluster_id]

    Returns:
        fo_model: Trained RandomForestClassifier
        preprocessor: Fitted preprocessing pipeline
    """
    # Prepare training data
    X = caregiver_data[caregiver_data['caregiver_id'].isin(cluster_assignments.keys())]
    y = X['caregiver_id'].map(cluster_assignments)

    # Preprocessing pipeline
    categorical_features = ['district', 'enrollment_source']
    numerical_features = ['age', 'parity']
    boolean_features = ['phone_reliable']

    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features),
            ('num', 'passthrough', numerical_features),
            ('bool', 'passthrough', boolean_features)
        ]
    )

    # Train RandomForest
    from sklearn.pipeline import Pipeline

    model = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        ))
    ])

    model.fit(X[FO_FEATURES], y)

    # Validate accuracy
    from sklearn.model_selection import cross_val_score
    scores = cross_val_score(model, X[FO_FEATURES], y, cv=5)
    print(f"FO Mapper Cross-Val Accuracy: {scores.mean():.2f} ± {scores.std():.2f}")

    return model
```

### Prediction (Cold-Start)

```python
def assign_new_caregiver_cluster(fo_model, caregiver_features):
    """
    Assign a new caregiver to a cluster using FO mapper.

    Args:
        fo_model: Trained RandomForestClassifier
        caregiver_features: Dict with FO_FEATURES

    Returns:
        cluster_id: int
    """
    X = pd.DataFrame([caregiver_features])[FO_FEATURES]
    cluster_id = fo_model.predict(X)[0]

    return cluster_id
```

**Acceptance Criteria:** ≥70% accuracy on validation set.

---

## Algorithm 5: Warmup Period Logic

### Objective
Collect 6 weeks of data for new caregivers before including them in RMAB recommendations.

### Implementation

```python
from datetime import datetime, timedelta

def is_ready_for_rmab(caregiver):
    """
    Check if caregiver has completed warmup period.

    Args:
        caregiver: Dict with 'enrolled_at' and 'warmup_end_date'

    Returns:
        bool: True if warmup complete
    """
    warmup_end = caregiver['warmup_end_date']
    return datetime.now().date() >= warmup_end


def assign_warmup_end_date(enrolled_at, warmup_weeks=6):
    """
    Calculate warmup end date.

    Args:
        enrolled_at: date
        warmup_weeks: int (default 6)

    Returns:
        warmup_end_date: date
    """
    return enrolled_at + timedelta(weeks=warmup_weeks)
```

**During Warmup:**
- Caregivers receive standard SMS schedule (no RMAB prioritization)
- Data collected and logged for future clustering
- Assigned to cluster via FO mapper (for initial state estimation)

---

## Full Training Pipeline

### Pseudocode

```python
def train_rmab_system(historical_data):
    """
    End-to-end training pipeline.

    Steps:
        1. Cluster caregivers
        2. Learn MDP parameters per cluster
        3. Compute Whittle indices
        4. Train FO mapper
        5. Save to PostgreSQL and Redis
    """
    # Step 1: Clustering
    cluster_assignments, k, kmeans_model = cluster_caregivers(historical_data)

    # Step 2: Learn MDPs per cluster
    cluster_mdps = {}
    for cluster_id in range(k):
        cluster_data = historical_data[
            historical_data['caregiver_id'].isin(
                [cid for cid, cid_cluster in cluster_assignments.items()
                 if cid_cluster == cluster_id]
            )
        ]
        cluster_mdps[cluster_id] = learn_cluster_mdp(cluster_data)

    # Step 3: Compute Whittle indices
    whittle_indices = {}
    for cluster_id in range(k):
        for state in ['Responsive', 'Unresponsive']:
            index = compute_whittle_index(cluster_mdps[cluster_id], state)
            whittle_indices[(cluster_id, state)] = index

    # Step 4: Train FO mapper
    caregiver_data = load_caregiver_demographics()
    fo_model = train_fo_mapper(caregiver_data, cluster_assignments)

    # Step 5: Save to database
    save_clusters_to_db(cluster_mdps)
    save_indices_to_db(whittle_indices)
    save_indices_to_redis(whittle_indices)
    save_fo_model_to_redis(fo_model)

    return {
        'num_clusters': k,
        'model_version': generate_version(),
        'training_completed_at': datetime.now()
    }
```

---

## Performance Benchmarks

### Clustering (200K caregivers)
- **Time:** ~15 minutes (single-threaded CPU)
- **Memory:** ~2GB
- **Optimization:** Use MiniBatchKMeans if >500K caregivers

### MDP Learning (per cluster)
- **Time:** ~30 seconds per cluster (parallelizable)
- **Total:** ~10 minutes for 20 clusters (sequential)

### Whittle Index Computation
- **Time:** ~10 seconds per (cluster, state) pair
- **Total:** ~7 minutes for 20 clusters × 2 states × 2 actions

### FO Mapper Training
- **Time:** ~5 minutes (100 trees, 10K samples)
- **Accuracy:** Target ≥70%, typically ~75-80%

**Total Training Time:** ~30 minutes for full pipeline.

---

## Error Handling

### Clustering Failures
```python
try:
    cluster_assignments, k, kmeans_model = cluster_caregivers(historical_data)
except Exception as e:
    # Fallback: Use previous clustering if available
    logger.error(f"Clustering failed: {e}")
    cluster_assignments = load_previous_clustering()
```

### Insufficient Data
```python
if len(cluster_data) < MIN_CLUSTER_SIZE:
    logger.warning(f"Cluster {cluster_id} has only {len(cluster_data)} samples")
    # Use global priors instead of cluster-specific learning
    cluster_mdps[cluster_id] = DEFAULT_MDP_PARAMS
```

### Numerical Instability
```python
# In value iteration, check for NaN or Inf
if not np.isfinite(V_new[s]):
    logger.error("Value iteration diverged")
    return DEFAULT_VALUE
```

---

## Testing

### Unit Tests

```python
def test_compute_passive_features():
    """Test feature extraction."""
    mock_data = pd.DataFrame({
        'state_before': ['R', 'R', 'U', 'U'],
        'state_after': ['R', 'U', 'R', 'U'],
        'action': ['passive'] * 4
    })

    features = compute_passive_features(mock_data)

    assert len(features) == 4
    assert np.allclose(features.sum(), 2.0)  # Probabilities sum to 1 per start state


def test_whittle_index_properties():
    """Test Whittle index satisfies expected properties."""
    mock_mdp = {
        'P_transition': {...},
        'P_reward': {...}
    }

    index_responsive = compute_whittle_index(mock_mdp, 'Responsive')
    index_unresponsive = compute_whittle_index(mock_mdp, 'Unresponsive')

    # Property: Responsive state should have lower index (already engaged)
    assert index_unresponsive > index_responsive
```

### Integration Test

```python
def test_full_training_pipeline():
    """Test end-to-end training on synthetic data."""
    synthetic_data = generate_synthetic_engagement_data(num_caregivers=1000)

    result = train_rmab_system(synthetic_data)

    assert result['num_clusters'] >= 10
    assert result['num_clusters'] <= 30
    assert 'model_version' in result
```

---

## Next Steps
1. Implement Whittle solver in Python (adapt from SAHELI's planinf)
2. Validate on synthetic data (known ground truth)
3. Benchmark on Suvita historical data (6 months)
4. Tune hyperparameters (k, gamma, warmup_weeks)
5. Document edge cases and fallback strategies
