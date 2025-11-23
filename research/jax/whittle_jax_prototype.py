"""
JAX-based Whittle Index Solver Prototype

This is a research implementation to explore JAX benefits for RMAB.
Not for production use yet - requires validation and optimization.
"""

import jax
import jax.numpy as jnp
from jax import jit, vmap
from typing import Tuple
import numpy as np


# ============================================================================
# Core JAX Implementation
# ============================================================================

@jit
def get_reward_jax(state: int, action: int, subsidy: float) -> float:
    """
    Reward function (JAX version).

    Args:
        state: 0=Responsive, 1=Unresponsive
        action: 0=Passive, 1=Active
        subsidy: Subsidy for passive action

    Returns:
        Immediate reward
    """
    # State reward: Responsive=+1, Unresponsive=-1
    state_reward = jnp.where(state == 0, 1.0, -1.0)

    # Add subsidy for passive action
    action_subsidy = jnp.where(action == 0, subsidy, 0.0)

    return state_reward + action_subsidy


@jit
def compute_q_value_jax(
    state: int,
    action: int,
    transition_probs: jnp.ndarray,
    v_values: jnp.ndarray,
    subsidy: float,
    gamma: float
) -> float:
    """
    Compute Q(state, action) using JAX.

    Args:
        state: Current state
        action: Action
        transition_probs: [2, 2, 2] transition matrix
        v_values: [2] value function
        subsidy: Subsidy value
        gamma: Discount factor

    Returns:
        Q-value
    """
    # Immediate reward
    reward = get_reward_jax(state, action, subsidy)

    # Expected future value: sum_s' P(s'|s,a) * V(s')
    probs = transition_probs[state, :, action]  # P(s' | s, a) for all s'
    expected_future = jnp.dot(probs, v_values)

    return reward + gamma * expected_future


@jit
def value_iteration_step_jax(
    v_values: jnp.ndarray,
    transition_probs: jnp.ndarray,
    subsidies: jnp.ndarray,
    gamma: float
) -> jnp.ndarray:
    """
    Single step of value iteration (JAX version).

    Args:
        v_values: Current value function [2]
        transition_probs: Transition probabilities [2, 2, 2]
        subsidies: Subsidies for each state [2]
        gamma: Discount factor

    Returns:
        Updated value function [2]
    """
    def compute_state_value(state):
        # Q-values for both actions
        q_passive = compute_q_value_jax(
            state, 0, transition_probs, v_values, subsidies[state], gamma
        )
        q_active = compute_q_value_jax(
            state, 1, transition_probs, v_values, 0.0, gamma
        )
        return jnp.maximum(q_passive, q_active)

    # Vectorized computation for both states
    return vmap(compute_state_value)(jnp.array([0, 1]))


@jit
def value_iteration_jax(
    transition_probs: jnp.ndarray,
    subsidies: jnp.ndarray,
    gamma: float,
    threshold: float = 1e-4,
    max_iters: int = 1000
) -> jnp.ndarray:
    """
    Run value iteration until convergence (JAX version).

    Args:
        transition_probs: [2, 2, 2] transition matrix
        subsidies: [2] subsidy values
        gamma: Discount factor
        threshold: Convergence threshold
        max_iters: Maximum iterations

    Returns:
        Converged value function [2]
    """
    v_values = jnp.zeros(2)

    def cond_fn(carry):
        iteration, v_old, v_new = carry
        delta = jnp.max(jnp.abs(v_new - v_old))
        return (delta > threshold) & (iteration < max_iters)

    def body_fn(carry):
        iteration, _, v_current = carry
        v_new = value_iteration_step_jax(v_current, transition_probs, subsidies, gamma)
        return (iteration + 1, v_current, v_new)

    # Initial state
    init_carry = (0, v_values, v_values)

    # Run loop
    _, _, v_converged = jax.lax.while_loop(cond_fn, body_fn, init_carry)

    return v_converged


@jit
def compute_q_values_jax(
    transition_probs: jnp.ndarray,
    v_values: jnp.ndarray,
    subsidies: jnp.ndarray,
    gamma: float
) -> jnp.ndarray:
    """
    Compute Q-values for all (state, action) pairs.

    Args:
        transition_probs: [2, 2, 2] transition matrix
        v_values: [2] value function
        subsidies: [2] subsidy values
        gamma: Discount factor

    Returns:
        Q-values [2, 2] where Q[s, a] = Q(s, a)
    """
    def compute_q(state, action):
        subsidy = jnp.where(action == 0, subsidies[state], 0.0)
        return compute_q_value_jax(state, action, transition_probs, v_values, subsidy, gamma)

    # Vectorized over all (state, action) pairs
    states = jnp.array([[0, 0], [1, 1]])  # [[s=0,a=0], [s=0,a=1], ...]
    actions = jnp.array([[0, 1], [0, 1]])

    return vmap(vmap(compute_q))(states, actions)


@jit
def binary_search_step_jax(
    bounds: Tuple[jnp.ndarray, jnp.ndarray],
    transition_probs: jnp.ndarray,
    gamma: float
) -> Tuple[jnp.ndarray, jnp.ndarray, float]:
    """
    Single step of binary search for Whittle indices.

    Args:
        bounds: (low_bounds, high_bounds) for subsidies [2]
        transition_probs: [2, 2, 2] transition matrix
        gamma: Discount factor

    Returns:
        (updated_low, updated_high, max_q_diff)
    """
    low_bounds, high_bounds = bounds
    subsidies = (low_bounds + high_bounds) / 2.0

    # Value iteration
    v_values = value_iteration_jax(transition_probs, subsidies, gamma)

    # Compute Q-values
    q_values = compute_q_values_jax(transition_probs, v_values, subsidies, gamma)

    # Find state with max Q-difference
    q_diffs = jnp.abs(q_values[:, 1] - q_values[:, 0])  # |Q(s, active) - Q(s, passive)|
    max_diff_state = jnp.argmax(q_diffs)
    max_q_diff = q_diffs[max_diff_state]

    # Update bounds based on Q-value comparison
    q_passive = q_values[max_diff_state, 0]
    q_active = q_values[max_diff_state, 1]

    # Update lower bound if passive < active
    new_low = jnp.where(
        q_passive < q_active,
        low_bounds.at[max_diff_state].set(subsidies[max_diff_state]),
        low_bounds
    )

    # Update upper bound if passive > active
    new_high = jnp.where(
        q_passive > q_active,
        high_bounds.at[max_diff_state].set(subsidies[max_diff_state]),
        high_bounds
    )

    return (new_low, new_high, max_q_diff)


def compute_whittle_index_jax(
    transition_probs: np.ndarray,
    gamma: float = 0.99,
    q_threshold: float = 1e-5,
    max_iters: int = 1000
) -> Tuple[float, float]:
    """
    Compute Whittle indices using JAX.

    Args:
        transition_probs: [2, 2, 2] NumPy array
        gamma: Discount factor
        q_threshold: Q-value convergence threshold
        max_iters: Maximum binary search iterations

    Returns:
        (whittle_index_responsive, whittle_index_unresponsive)
    """
    # Convert to JAX array
    P_jax = jnp.array(transition_probs)

    # Initialize bounds
    low_bounds = -2.0 * jnp.ones(2)
    high_bounds = 2.0 * jnp.ones(2)

    # Binary search loop (not JIT-compiled due to Python loop)
    for iteration in range(max_iters):
        (low_bounds, high_bounds, max_q_diff) = binary_search_step_jax(
            (low_bounds, high_bounds),
            P_jax,
            gamma
        )

        if max_q_diff < q_threshold:
            break

    # Final Whittle indices
    whittle_indices = (low_bounds + high_bounds) / 2.0

    return float(whittle_indices[0]), float(whittle_indices[1])


# ============================================================================
# Batch Processing (vmap)
# ============================================================================

def compute_batch_whittle_indices_jax(
    transition_probs_batch: np.ndarray,
    gamma: float = 0.99
) -> np.ndarray:
    """
    Compute Whittle indices for multiple clusters in parallel.

    Args:
        transition_probs_batch: [n_clusters, 2, 2, 2] NumPy array
        gamma: Discount factor

    Returns:
        Whittle indices [n_clusters, 2] where [:, 0] = W(R), [:, 1] = W(U)
    """
    # This would use vmap for true parallelization
    # For prototype, just loop
    results = []
    for P in transition_probs_batch:
        w_r, w_u = compute_whittle_index_jax(P, gamma)
        results.append([w_r, w_u])

    return np.array(results)


# ============================================================================
# Comparison Utilities
# ============================================================================

def compare_numpy_vs_jax(transition_probs: np.ndarray, gamma: float = 0.99):
    """
    Compare NumPy vs JAX implementations.

    Args:
        transition_probs: [2, 2, 2] transition matrix
        gamma: Discount factor
    """
    # Import NumPy implementation
    import sys
    sys.path.insert(0, '/home/user/bandicoot')
    from bandicoot.core.whittle import compute_whittle_index as compute_numpy

    # Compute with NumPy
    w_r_np, w_u_np = compute_numpy(transition_probs, gamma)

    # Compute with JAX
    w_r_jax, w_u_jax = compute_whittle_index_jax(transition_probs, gamma)

    # Compare
    diff_r = abs(w_r_np - w_r_jax)
    diff_u = abs(w_u_np - w_u_jax)

    print(f"NumPy: W(R)={w_r_np:.6f}, W(U)={w_u_np:.6f}")
    print(f"JAX:   W(R)={w_r_jax:.6f}, W(U)={w_u_jax:.6f}")
    print(f"Diff:  ΔW(R)={diff_r:.8f}, ΔW(U)={diff_u:.8f}")

    return diff_r < 1e-4 and diff_u < 1e-4


if __name__ == "__main__":
    print("JAX Whittle Index Solver Prototype")
    print("=" * 60)

    # Test data
    P_test = np.array([
        [[0.8, 0.9],   # R → R: passive, active
         [0.2, 0.1]],  # R → U: passive, active
        [[0.3, 0.6],   # U → R: passive, active
         [0.7, 0.4]]   # U → U: passive, active
    ])

    print("\nTest: Single cluster")
    w_r, w_u = compute_whittle_index_jax(P_test, gamma=0.99)
    print(f"W(Responsive):   {w_r:.6f}")
    print(f"W(Unresponsive): {w_u:.6f}")

    print("\nValidation against NumPy:")
    try:
        passed = compare_numpy_vs_jax(P_test)
        if passed:
            print("✓ PASS: JAX matches NumPy (< 1e-4 difference)")
        else:
            print("⚠ WARNING: Differences exceed threshold")
    except Exception as e:
        print(f"Cannot compare: {e}")

    print("\n" + "=" * 60)
    print("Note: This is a prototype. Requires:")
    print("  1. Full validation suite")
    print("  2. Performance benchmarking")
    print("  3. Optimization (full JIT compilation)")
    print("  4. GPU testing")
