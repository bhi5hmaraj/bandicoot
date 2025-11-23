# Existing RMAB Libraries and Tools

Research document tracking existing open-source RMAB implementations that we could potentially leverage.

---

## Academic/Research Code

### 1. **SAHELI** (ARMMAN + Google Research)
- **Repository:** https://github.com/armman-projects/SAHELI
- **Status:** ✅ Already analyzed and validated against
- **Language:** Python (NumPy)
- **Features:**
  - Whittle index computation (proven in production)
  - 2-state RMAB
  - Binary search + value iteration
- **Pros:**
  - Proven to work (62% → 80% improvement)
  - Well-documented
  - Production-tested
- **Cons:**
  - Minimal - just core algorithm
  - No clustering, no data processing
- **Our approach:** Already used as validation baseline

---

### 2. **RMABs for Public Health** (USC/Harvard)
- **Likely repository:** Check Aditya Mate's GitHub, Milind Tambe lab
- **Papers:**
  - "Field Study in Deploying Restless Multi-Armed Bandits" (AAMAS 2022)
  - "Collapsing Bandits and Their Application to Public Health" (NeurIPS 2020)
- **Expected features:**
  - Whittle indices
  - Collapsing bandits (states with absorbing states)
  - Simulation frameworks
- **Action:** Search for public code releases

---

### 3. **PyRMAB** (If exists)
- **Search:** GitHub, PyPI
- **Expected features:** General RMAB toolkit
- **Status:** To be investigated

---

### 4. **Restless Bandits (Various Academic Labs)**

#### a) **Stanford - Emma Brunskill Lab**
- Focus: RL for healthcare
- Check: https://github.com/StanfordAI4HI
- May have RMAB implementations

#### b) **CMU - Machine Learning Department**
- Search: CMU ML GitHub
- RL and bandits research

#### c) **MIT - Operations Research Center**
- Check: OR-related repositories
- May have optimization code

---

## RL Libraries with RMAB Support

### 5. **OR-Gym**
- **Repository:** https://github.com/hubbs5/or-gym
- **Status:** Active (last update 2023)
- **Language:** Python (OpenAI Gym interface)
- **Features:**
  - RMAB environments for benchmarking
  - Various OR problems (inventory, knapsack, etc.)
  - Compatible with RL frameworks (Stable-Baselines3, Ray RLlib)
- **Pros:**
  - Standard Gym interface
  - Good for RL benchmarking
  - Active community
- **Cons:**
  - Focus on RL approaches, not classical Whittle
  - Environments, not solvers
- **Potential use:** Benchmarking our Whittle solver against RL baselines

---

### 6. **Stable-Baselines3** + Custom RMAB Env
- **Repository:** https://github.com/DLR-RM/stable-baselines3
- **Approach:** Use SB3 algorithms with custom RMAB environment
- **Pros:** State-of-the-art RL algorithms (PPO, A2C, SAC)
- **Cons:** Need to train (slow), less interpretable than Whittle

---

## Optimization Libraries

### 7. **Google OR-Tools**
- **Repository:** https://github.com/google/or-tools
- **Language:** C++ with Python bindings
- **Features:**
  - LP/MIP solvers
  - Constraint programming
  - Routing
- **Potential use:**
  - LP relaxation of RMAB
  - Mixed-integer programming formulation
- **Pros:** Industrial-strength, very fast
- **Cons:** RMAB not built-in, need to formulate

---

### 8. **PuLP** (Python LP)
- **Repository:** https://github.com/coin-or/pulp
- **Language:** Python
- **Features:** Linear programming interface
- **Potential use:** LP relaxation baseline
- **Pros:** Pure Python, easy to use
- **Cons:** Slower than OR-Tools

---

## JAX Ecosystem

### 9. **JAX-MD** (Molecular Dynamics)
- **Repository:** https://github.com/google/jax-md
- **Relevance:** Example of production JAX for science
- **Learnings:** Best practices for JAX in production

---

### 10. **Optax** (JAX Optimization)
- **Repository:** https://github.com/deepmind/optax
- **Language:** JAX
- **Features:** Gradient-based optimizers
- **Potential use:**
  - Optimize Whittle index search with gradients
  - MDP parameter learning
- **Pros:** Designed for JAX, composable
- **Cons:** Overkill for our simple binary search

---

### 11. **Flax** (JAX Neural Networks)
- **Repository:** https://github.com/google/flax
- **Relevance:** If we want to learn Whittle index approximator
- **Potential use:** NN(transition_probs) → whittle_index
- **Note:** Research direction, not immediate need

---

## Related Tools

### 12. **scikit-learn** (Already using)
- **Repository:** https://github.com/scikit-learn/scikit-learn
- **Current use:** Clustering (K-means), RandomForest (FO mapper)
- **Status:** ✅ Already integrated

---

### 13. **bayesianbandits** (Mentioned in SAHELI)
- **Repository:** Need to search (may be internal Google)
- **Expected features:** Bayesian parameter estimation for bandits
- **SAHELI use:** MDP parameter learning with Dirichlet
- **Action:** Investigate if public or need alternative

---

## Benchmarking Suites

### 14. **RMAB Benchmark Datasets**
- **Paper:** "Restless Bandits with Many Arms: Beating the Central Limit Theorem"
- **Check:** Author repositories for benchmark datasets
- **Use:** Validate our implementation on standard benchmarks

---

## Evaluation Matrix

| Library | RMAB Focus | Production-Ready | JAX Support | License | Priority |
|---------|------------|------------------|-------------|---------|----------|
| SAHELI | ✅ High | ✅ Yes | ❌ No | Apache 2.0 | ✅ Used |
| OR-Gym | ⚠️ RL | ⚠️ Research | ❌ No | MIT | ⚠️ Explore |
| OR-Tools | ⚠️ General | ✅ Yes | ❌ No | Apache 2.0 | ⚠️ Maybe |
| Optax | ❌ No | ✅ Yes | ✅ Yes | Apache 2.0 | ⚠️ JAX research |
| scikit-learn | ❌ No | ✅ Yes | ❌ No | BSD | ✅ Using |

---

## Research Action Items

### High Priority (Next 1-2 weeks)

1. **Search for RMABPy or similar**
   - GitHub search: "RMAB", "Whittle index", "Restless bandits"
   - Check recent NeurIPS/ICML/AAMAS papers with code
   - Action: Web search + GitHub search

2. **Investigate bayesianbandits**
   - Is it public? Alternative?
   - Needed for MDP parameter learning
   - Action: Search PyPI, GitHub

3. **Explore OR-Gym RMAB environments**
   - Clone repository
   - Review RMAB environment implementations
   - Benchmark our Whittle solver
   - Action: Clone and test

### Medium Priority (Weeks 3-4)

4. **JAX prototype validation**
   - Implement research/jax/whittle_jax_prototype.py
   - Run performance benchmarks
   - Decision: JAX vs NumPy
   - Action: Hands-on experimentation

5. **LP relaxation baseline**
   - Implement RMAB as LP using OR-Tools or PuLP
   - Compare vs Whittle indices
   - Validate optimality
   - Action: Implement and compare

### Low Priority (Future)

6. **RL baseline comparison**
   - Train PPO/A2C on RMAB environment
   - Compare sample efficiency vs Whittle
   - Publish results
   - Action: Research project

7. **Neural Whittle approximator**
   - Train NN to predict Whittle indices
   - Instant inference (no iteration)
   - Action: Advanced research

---

## Decision Framework

**When to use existing library:**
- ✅ Well-maintained (commits in last 6 months)
- ✅ Good documentation
- ✅ Compatible license (Apache 2.0, MIT, BSD)
- ✅ Active community / issues being addressed
- ✅ Matches our use case (2-state RMAB, Whittle indices)

**When to implement ourselves:**
- ❌ Library unmaintained
- ❌ Doesn't match our needs (different RMAB formulation)
- ❌ Poor code quality / no tests
- ❌ Restrictive license (GPL)
- ❌ Adds unnecessary complexity

---

## Conclusions So Far

1. **SAHELI is the gold standard**
   - Already validated against it
   - Our implementation matches exactly
   - No need to replace core algorithm

2. **No clear winner for clustering + MDP learning**
   - bayesianbandits may not be public
   - Need to implement ourselves or find alternative
   - scikit-learn + custom code seems best path

3. **JAX is promising for performance**
   - Worth prototyping
   - Could give 10-50x speedup
   - Keep NumPy as fallback

4. **OR-Gym useful for validation**
   - Good RMAB environments for testing
   - Can benchmark against RL baselines
   - Not a replacement for Whittle solver

---

**Next Steps:**
1. Web search for recent RMAB papers with code (2022-2024)
2. Clone OR-Gym and explore RMAB environments
3. Test JAX prototype
4. Implement MDP parameter learning with scikit-learn alternative to bayesianbandits
