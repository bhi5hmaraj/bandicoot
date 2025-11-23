# JAX for RMAB: Research and Exploration

**Objective:** Explore JAX-based implementations and existing RMAB libraries to potentially improve performance and leverage existing work.

---

## Why JAX for RMAB?

### Benefits

1. **JIT Compilation**
   - Compile Python to XLA (Accelerated Linear Algebra)
   - 10-100x speedup for numerical code
   - Especially beneficial for Whittle index computation (nested loops)

2. **Automatic Differentiation**
   - `jax.grad()` for gradient computation
   - Useful for MDP parameter learning
   - Could enable gradient-based policy optimization

3. **Vectorization**
   - `jax.vmap()` for batch processing
   - Compute Whittle indices for multiple clusters in parallel
   - Process all caregivers simultaneously

4. **GPU/TPU Support**
   - Seamless acceleration on hardware accelerators
   - Important at scale (200K caregivers)
   - No code changes needed

5. **Functional Programming**
   - Pure functions (no side effects)
   - Better for testing and reasoning
   - Natural fit for mathematical algorithms

### Potential Speedups

| Component | NumPy | JAX (CPU) | JAX (GPU) |
|-----------|-------|-----------|-----------|
| Whittle solver (1 cluster) | 1x | 10-50x | 50-200x |
| Batch (20 clusters) | 1x | 50-100x | 200-500x |
| Full pipeline (200K) | 1x | 20-50x | 100-300x |

*Estimates based on typical JAX performance on numerical algorithms*

---

## Existing RMAB Libraries

### 1. **RMABPy** (GitHub: killian-34/RMABPy)
- **Status:** Research code, not production
- **Features:**
  - Whittle index computation
  - Various RMAB algorithms (LP relaxation, Whittle, heuristics)
  - Simulation environments
- **Pros:** Well-tested algorithms
- **Cons:** NumPy-based, not optimized for production

### 2. **OR-Gym** (GitHub: hubbs5/or-gym)
- **Status:** OpenAI Gym for OR problems
- **Features:**
  - RMAB environments
  - RL benchmarks
- **Pros:** Standard interface
- **Cons:** Focus on RL, not classical RMAB

### 3. **PyRMAB** (Hypothetical - to check)
- May exist as academic code
- Check arXiv implementations

### 4. **Restless Bandits Toolkit** (to research)
- Various academic implementations
- Check Google Scholar for recent papers

---

## JAX Implementation Strategy

### Option 1: Direct Port (Recommended for Phase 1)
Convert our proven NumPy implementation to JAX:

```python
import jax.numpy as jnp
from jax import jit, vmap

@jit
def whittle_value_iteration(transition_probs, subsidies, gamma):
    """JAX-compiled value iteration."""
    v_values = jnp.zeros(2)

    def body_fn(v):
        # Vectorized Q-value computation
        q_passive = compute_q_vectorized(v, transition_probs, subsidies, 0, gamma)
        q_active = compute_q_vectorized(v, transition_probs, subsidies, 1, gamma)
        return jnp.maximum(q_passive, q_active)

    # Fixed-point iteration
    v_converged = jax.lax.while_loop(
        lambda v: jnp.max(jnp.abs(v - body_fn(v))) > 1e-4,
        body_fn,
        v_values
    )
    return v_converged

# Batch processing across clusters
batch_whittle = vmap(whittle_solver, in_axes=(0, None))
indices = batch_whittle(all_cluster_transitions, gamma=0.99)
```

**Benefits:**
- Keep proven algorithm
- Get JAX speedups (10-50x)
- Minimal risk

### Option 2: Hybrid Approach
Use NumPy for development/testing, JAX for production:

```python
# bandicoot/core/whittle.py (NumPy - current)
class WhittleIndexSolver:
    def compute_indices(self, P):
        # NumPy implementation (tested, validated)
        pass

# bandicoot/core/whittle_jax.py (JAX - optimized)
from bandicoot.core import whittle
import jax.numpy as jnp

def compute_indices_jax(P):
    """JAX-optimized version of whittle.compute_indices."""
    # Convert to JAX, compile, execute
    P_jax = jnp.array(P)
    return _jax_compiled_solver(P_jax)
```

**Benefits:**
- Development flexibility
- Easy A/B testing
- Gradual migration

### Option 3: Research Novel Algorithms
Explore JAX-specific optimizations:

1. **Differentiable Whittle indices**
   - Use `jax.grad()` to optimize subsidy search
   - Potentially faster convergence

2. **Neural network approximation**
   - Learn Whittle index function: `NN(transition_probs) → indices`
   - Instant inference (no iteration)
   - Requires training data

3. **GPU-accelerated batch processing**
   - Process all 200K caregivers in parallel
   - Sub-second recommendation generation

---

## Performance Comparison Plan

### Benchmark Setup

```python
# research/jax/benchmark.py

import time
import numpy as np
import jax.numpy as jnp
from bandicoot.core.whittle import WhittleIndexSolver
from research.jax.whittle_jax import compute_whittle_index_jax

def benchmark_numpy_vs_jax():
    # Generate test data
    n_clusters = 20
    transitions = generate_random_transitions(n_clusters)

    # Benchmark NumPy
    solver_np = WhittleIndexSolver(gamma=0.99)
    start = time.time()
    for P in transitions:
        solver_np.compute_indices(P)
    numpy_time = time.time() - start

    # Benchmark JAX (with warmup for JIT)
    compute_whittle_index_jax(transitions[0])  # Warmup
    start = time.time()
    for P in transitions:
        compute_whittle_index_jax(P)
    jax_time = time.time() - start

    print(f"NumPy: {numpy_time:.3f}s")
    print(f"JAX:   {jax_time:.3f}s")
    print(f"Speedup: {numpy_time/jax_time:.1f}x")
```

### Metrics to Track

1. **Latency (single cluster)**
   - Time to compute Whittle indices for 1 cluster
   - Target: < 10ms

2. **Throughput (batch)**
   - Clusters processed per second
   - Target: > 1000 clusters/sec

3. **Memory usage**
   - RAM consumption
   - Important for large-scale deployment

4. **Numerical accuracy**
   - Ensure JAX matches NumPy (< 1e-6 difference)

---

## Implementation Roadmap

### Phase 1: JAX Prototype (Week 1)
- [ ] Install JAX: `pip install jax jaxlib`
- [ ] Port Whittle solver to JAX
- [ ] Validate against NumPy implementation
- [ ] Benchmark performance

### Phase 2: Optimization (Week 2)
- [ ] Add `@jit` compilation
- [ ] Vectorize with `vmap` for batch processing
- [ ] GPU testing (if available)
- [ ] Profile and optimize bottlenecks

### Phase 3: Integration (Week 3)
- [ ] Add JAX backend to bandicoot library
- [ ] Feature flag for NumPy/JAX selection
- [ ] Update tests to cover both backends
- [ ] Documentation

### Phase 4: Production (Week 4)
- [ ] Deploy JAX version to staging
- [ ] A/B test performance
- [ ] Monitor production metrics
- [ ] Rollout to 100%

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| JAX adds complexity | High | Keep NumPy as fallback |
| Numerical differences | Medium | Strict validation tests |
| Deployment challenges | Medium | Docker with JAX pre-installed |
| Learning curve | Low | Team training, documentation |
| GPU not available | Low | CPU-only JAX still faster |

---

## Decision Criteria

**Use JAX if:**
- ✅ Performance benchmarks show >5x speedup
- ✅ Numerical validation passes (< 1e-6 error)
- ✅ Deployment complexity is manageable
- ✅ Team is comfortable with JAX

**Stick with NumPy if:**
- ❌ Speedup is marginal (< 2x)
- ❌ Deployment adds significant complexity
- ❌ Numerical issues arise
- ❌ Current performance is acceptable

---

## Next Steps

1. **Research existing libraries**
   - Search GitHub for RMAB implementations
   - Check academic papers for code releases
   - Evaluate if any can be reused

2. **JAX prototype**
   - Implement minimal Whittle solver in JAX
   - Run validation experiment
   - Benchmark vs NumPy

3. **Decision point**
   - Review results
   - Decide: JAX, NumPy, or hybrid
   - Document rationale

4. **Implementation**
   - If JAX: integrate into bandicoot
   - If NumPy: optimize current code
   - If hybrid: support both backends

---

**Status:** 🔬 Research Phase
**Owner:** Research team
**Timeline:** 2-4 weeks
**Priority:** Medium (optimize after core functionality works)
