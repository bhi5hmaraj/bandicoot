# Library-First Development Strategy

**Version:** 1.0
**Last Updated:** November 2025
**Status:** Design Document

---

## Problem

Current MVP plan jumps straight to cloud service development without local validation capability. This creates slow iteration cycles:
- ❌ Need to deploy to test algorithms
- ❌ Hard to debug with real data
- ❌ Expensive to iterate on parameters
- ❌ No quick way to validate with stakeholders

---

## Solution: Library-First Approach

Build a standalone Python library that can:
1. Run locally with CSV data
2. Be validated in Jupyter notebooks
3. Later be wrapped by the FastAPI service
4. Enable rapid experimentation

---

## Architecture

### Phase 0: Core Library (NEW)

```
bandicoot/
├── core/
│   ├── clustering.py       # K-means on passive features
│   ├── mdp.py              # Bayesian MDP learning
│   ├── whittle.py          # Whittle index solver
│   ├── fo_mapper.py        # Features-only mapper
│   └── recommender.py      # Top-K recommendation logic
├── data/
│   ├── loaders.py          # CSV/DataFrame loaders
│   ├── preprocessors.py    # Clean & transform
│   └── validators.py       # Data quality checks
├── models/
│   ├── caregiver.py        # Caregiver dataclass
│   ├── cluster.py          # Cluster model
│   └── state.py            # State machine (R/U)
└── utils/
    ├── metrics.py          # Evaluation metrics
    └── visualization.py    # Plotting helpers

experiments/
├── 01_data_exploration.py      # EDA on Suvita data
├── 02_clustering_validation.py # Cluster quality analysis
├── 03_mdp_learning.py          # MDP parameter estimation
├── 04_whittle_computation.py   # Whittle index analysis
├── 05_recommendation_test.py   # End-to-end test
└── 06_ab_test_simulation.py    # Simulate A/B test

tests/
├── test_clustering.py
├── test_mdp.py
├── test_whittle.py
└── test_recommender.py
```

---

## Development Phases

### Phase 0: Library Development (Week 1-2)

**Goal:** Working library that can process CSV → recommendations

**Deliverables:**
1. `bandicoot` Python package (installable via `pip install -e .`)
2. Core algorithms implemented and tested
3. Jupyter notebooks demonstrating usage
4. Validation on synthetic data
5. Ready for Suvita historical data

**Input:** CSV files with schema:
```csv
caregiver_id,sms_sent,sms_delivered,sms_opened,vaccinated,state_before,state_after,action
CG-001,2025-05-01 10:00,2025-05-01 10:02,2025-05-01 14:30,True,Responsive,Responsive,passive
CG-002,2025-05-02 11:00,2025-05-02 11:01,,False,Unresponsive,Unresponsive,passive
```

**Output:** Recommendations CSV:
```csv
caregiver_id,priority_score,cluster_id,current_state,reason
CG-045,0.91,12,Unresponsive,"High dropout risk, responsive to interventions"
CG-123,0.87,5,Unresponsive,"Missed last 2 vaccines"
```

---

### Phase 1: Service Integration (Week 3-4)

**Goal:** Wrap library in FastAPI service

**Changes:**
- Library stays pure Python (no Flask/FastAPI in core)
- Service (`src/api/`) imports and uses library
- Database layer wraps library's in-memory models

**Example:**
```python
# bandicoot/core/recommender.py (library - no DB)
class Recommender:
    def recommend(self, caregivers: List[Caregiver], budget: int) -> List[Recommendation]:
        # Pure function, no side effects
        pass

# src/api/endpoints.py (service - with DB)
from bandicoot.core.recommender import Recommender

@app.get("/recommend")
async def recommend_endpoint(budget: int):
    # Load from database
    caregivers = load_caregivers_from_db()

    # Use library
    recommender = Recommender(whittle_indices=load_indices())
    recommendations = recommender.recommend(caregivers, budget)

    # Save to database
    save_recommendations(recommendations)

    return recommendations
```

---

### Phase 2: Production Deployment (Week 5-8)

**Goal:** Deploy service to Cloud Run

**Library remains unchanged** - all cloud-specific logic is in service layer.

---

## Library API Design

### Core Usage Pattern

```python
from bandicoot import BandicootRMAB
import pandas as pd

# 1. Load historical data
df = pd.read_csv('suvita_historical.csv')

# 2. Initialize RMAB system
rmab = BandicootRMAB(
    n_clusters=20,
    warmup_weeks=6,
    gamma=0.95  # Discount factor
)

# 3. Train on historical data
rmab.fit(df)

# 4. Get current caregivers (from another CSV)
current = pd.read_csv('suvita_current_states.csv')

# 5. Generate recommendations
recommendations = rmab.recommend(current, budget=1000)

# 6. Evaluate quality
metrics = rmab.evaluate(
    recommendations,
    ground_truth='suvita_outcomes.csv'
)
print(f"Precision@100: {metrics['precision_at_100']}")
```

---

## Experiment Workflow

### Jupyter Notebook Example

```python
# experiments/02_clustering_validation.py
# %%
import pandas as pd
from bandicoot.core.clustering import ClusteringEngine
from bandicoot.utils.visualization import plot_clusters

# Load Suvita data
df = pd.read_csv('../data/suvita_6months.csv')

# %%
# Run clustering with different k
for k in range(15, 26):
    engine = ClusteringEngine(n_clusters=k)
    clusters = engine.fit(df)

    print(f"k={k}, silhouette={clusters.silhouette_score:.3f}")

# %%
# Visualize best clustering
engine = ClusteringEngine(n_clusters=20)
clusters = engine.fit(df)
plot_clusters(clusters, method='tsne')

# %%
# Analyze cluster characteristics
for cluster_id in range(20):
    cluster_df = df[df['cluster_id'] == cluster_id]
    print(f"\nCluster {cluster_id}:")
    print(f"  Size: {len(cluster_df)}")
    print(f"  Avg engagement: {cluster_df['sms_opened'].notna().mean():.2%}")
    print(f"  Avg vaccination: {cluster_df['vaccinated'].mean():.2%}")
```

---

## Benefits

### Rapid Iteration
- ✅ Test algorithms on laptop (no cloud deployment)
- ✅ Debug with real data in Jupyter
- ✅ Tune hyperparameters interactively
- ✅ Visualize results immediately

### Stakeholder Validation
- ✅ Run on Suvita data and share notebook results
- ✅ Adjust parameters based on feedback
- ✅ No need to explain cloud infrastructure

### Clean Architecture
- ✅ Library has no cloud dependencies
- ✅ Can be reused in different contexts (CLI, web service, batch jobs)
- ✅ Easy to unit test (pure functions)
- ✅ Service layer is thin wrapper

### Cost Savings
- ✅ No cloud costs during development
- ✅ Only deploy when algorithms are validated
- ✅ Fewer failed deployments

---

## Migration Path

### Week 1-2: Library Development
```
bandicoot/          # Pure Python library
experiments/        # Jupyter notebooks
tests/              # Unit tests
data/               # Sample CSVs
```

**Validation:** Run notebooks on synthetic + Suvita data

---

### Week 3-4: Service Wrapper
```
bandicoot/          # Library (unchanged)
src/api/            # FastAPI service
src/db/             # Database layer
src/jobs/           # Job execution
experiments/        # Notebooks (still useful!)
```

**Migration:**
- Import `bandicoot` library in service
- Add database persistence
- Add API authentication

---

### Week 5-8: Cloud Deployment
```
bandicoot/          # Library (unchanged)
src/                # Service (Cloud Run)
experiments/        # Notebooks (for analysis)
.beads/             # Issue tracker
docs/               # Documentation
```

**No library changes** - all cloud logic in `src/`

---

## Testing Strategy

### Unit Tests (Library)
```python
# tests/test_clustering.py
def test_clustering_with_synthetic_data():
    df = generate_synthetic_caregivers(n=1000)
    engine = ClusteringEngine(n_clusters=20)
    clusters = engine.fit(df)

    assert clusters.n_clusters == 20
    assert clusters.silhouette_score > 0.6
    assert len(clusters.assignments) == 1000
```

### Integration Tests (Notebooks)
```python
# experiments/05_recommendation_test.py
# %%
# End-to-end test on Suvita data
rmab = BandicootRMAB(n_clusters=20)
rmab.fit(historical_df)

recs = rmab.recommend(current_df, budget=1000)

# Validate recommendations
assert len(recs) == 1000
assert all(recs['priority_score'] > 0)
assert recs['priority_score'].is_monotonic_decreasing  # Sorted
```

### Validation Metrics
```python
# bandicoot/utils/metrics.py
def evaluate_recommendations(
    recommendations: pd.DataFrame,
    ground_truth: pd.DataFrame
) -> dict:
    """
    Evaluate recommendation quality.

    Returns:
        precision_at_k: % of top-K who actually vaccinated
        recall_at_k: % of vaccinated captured in top-K
        ndcg: Normalized discounted cumulative gain
    """
    pass
```

---

## Package Structure

### `setup.py`
```python
from setuptools import setup, find_packages

setup(
    name="bandicoot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "scikit-learn>=1.3.0",
        "bayesianbandits>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "jupyter>=1.0.0",
            "matplotlib>=3.5.0",
            "seaborn>=0.12.0",
        ]
    }
)
```

### Install for Development
```bash
cd bandicoot
pip install -e ".[dev]"  # Editable install with dev dependencies
```

---

## Deliverables Checklist

### Phase 0 (Library + Experiments)
- [ ] `bandicoot/` package structure
- [ ] Core algorithms implemented
- [ ] Unit tests (≥80% coverage)
- [ ] 6 Jupyter notebooks in `experiments/`
- [ ] Synthetic data generator
- [ ] Validation on Suvita data (10K caregivers)
- [ ] Documentation (README, API reference)

### Phase 1 (Service Integration)
- [ ] FastAPI service wrapper
- [ ] Database layer (PostgreSQL)
- [ ] API endpoints using library
- [ ] Integration tests
- [ ] Deployment to Cloud Run (staging)

### Phase 2 (Production)
- [ ] A/B test framework
- [ ] Monitoring & alerting
- [ ] Production deployment
- [ ] Results analysis (using notebooks!)

---

## Next Steps

1. **Update Beads issues** - Add Phase 0 tasks, reorder dependencies
2. **Create library scaffold** - `bandicoot/` package structure
3. **Set up experiments/** - Jupyter notebooks in `.py` format
4. **Generate synthetic data** - For initial testing
5. **Implement clustering** - First algorithm to validate

---

**Author:** Bandicoot Team
**Status:** Design Approved
**Next:** Update Beads tracker with new Phase 0 tasks
