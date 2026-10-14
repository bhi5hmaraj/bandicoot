# JAX Whittle solver prototype

`whittle_jax_prototype.py` ports the NumPy solver in `bandicoot/core/whittle.py` to JAX. It is research code. The library does not use it.

## What it does

- Uses the same model as the NumPy solver: two states, reward $+1$ in R and $-1$ in U, a passive subsidy per state, and search bounds $[-2, 2]$.
- Compiles the reward, Q-value, value-iteration, and search-step functions with `jax.jit`. Uses `jax.vmap` over states and actions.
- Runs the outer binary search as a Python loop: `q_threshold = 1e-5`, `max_iters = 1000`.
- Value iteration uses `jax.lax.while_loop` with threshold $10^{-4}$ and a cap of 1000 steps.
- `compute_batch_whittle_indices_jax` loops over clusters. It does not use `vmap` across clusters yet.
- `compare_numpy_vs_jax` runs both solvers on one matrix and checks for a difference below $10^{-4}$.

## How to run it

JAX is not in `requirements.txt`. Install it first:

```bash
pip install jax
python research/jax/whittle_jax_prototype.py
```

The script computes the indices for one test matrix and compares them with the NumPy solver.

## Status

The prototype returns wrong values. A run on 2026-10-14 (jax 0.11.2, CPU) gave this output:

| Solver | W(R) | W(U) |
|---|---|---|
| NumPy (`bandicoot/core/whittle.py`) | 0.281647 | 0.844955 |
| JAX prototype | 0.000000 | 0.000000 |

Cause: `value_iteration_jax` starts the loop with `init_carry = (0, v_values, v_values)`. The loop condition tests the change between the two value arrays. Both are zero, so the condition is false and the loop body never runs. With $V = 0$, the search stops at subsidy 0 in the first step.

A test copy with the initial "old" values set to infinity gave $W(R) = 0.281631$ and $W(U) = 0.844940$. This is within $2 \times 10^{-5}$ of NumPy. The fix is not in the repository yet.

## Not measured

- Speed. No benchmark has run in this repository. Earlier speedup figures were estimates and are removed.
- GPU behavior.
- Batch processing with `vmap` across clusters.
