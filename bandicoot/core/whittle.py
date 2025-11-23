"""
Whittle Index Solver for RMAB.

Based on the proven SAHELI implementation (ARMMAN + Google Research).
Computes Whittle indices using binary search + value iteration.

Reference:
    Mate et al. "Field Study in Deploying Restless Multi-Armed Bandits"
    https://github.com/armman-projects/SAHELI
"""

from typing import Tuple
import numpy as np
from numpy.typing import NDArray


class WhittleIndexSolver:
    """
    Computes Whittle indices for a 2-state RMAB.

    Uses binary search on subsidy values combined with value iteration
    to find the indifference point where passive and active actions
    have equal Q-values.

    States:
        - 0: Responsive (R) - Low risk of dropout
        - 1: Unresponsive (U) - High risk of dropout

    Actions:
        - 0: Passive (no intervention)
        - 1: Active (send SMS/intervention)

    Attributes:
        gamma: Discount factor (default: 0.99)
        q_convergence_threshold: Q-value difference convergence (default: 1e-5)
        v_convergence_threshold: Value iteration delta (default: 1e-4)
        max_iterations: Maximum iterations to prevent infinite loops
    """

    def __init__(
        self,
        gamma: float = 0.99,
        q_convergence_threshold: float = 1e-5,
        v_convergence_threshold: float = 1e-4,
        max_iterations: int = 1000,
    ):
        """
        Initialize Whittle index solver.

        Args:
            gamma: Discount factor for future rewards (0 < gamma < 1)
            q_convergence_threshold: Convergence threshold for Q-value difference
            v_convergence_threshold: Convergence threshold for value iteration
            max_iterations: Maximum iterations for binary search

        Raises:
            ValueError: If gamma is not in (0, 1)
        """
        if not 0 < gamma < 1:
            raise ValueError(f"Gamma must be in (0, 1), got {gamma}")

        self.gamma = gamma
        self.q_convergence_threshold = q_convergence_threshold
        self.v_convergence_threshold = v_convergence_threshold
        self.max_iterations = max_iterations

    def compute_indices(
        self,
        transition_probs: NDArray[np.float64]
    ) -> Tuple[float, float]:
        """
        Compute Whittle indices for both states.

        Args:
            transition_probs: Transition probability matrix with shape (2, 2, 2)
                where indices are [state, next_state, action]
                - transition_probs[s, s', a] = P(s' | s, a)

        Returns:
            Tuple of (whittle_index_responsive, whittle_index_unresponsive)

        Raises:
            ValueError: If transition probabilities are invalid

        Example:
            >>> solver = WhittleIndexSolver(gamma=0.99)
            >>> # transition_probs[state, next_state, action]
            >>> P = np.array([
            ...     [[0.8, 0.2], [0.7, 0.3]],  # From Responsive
            ...     [[0.6, 0.4], [0.5, 0.5]]   # From Unresponsive
            ... ])
            >>> w_r, w_u = solver.compute_indices(P)
            >>> print(f"W(R)={w_r:.3f}, W(U)={w_u:.3f}")
        """
        self._validate_transition_probs(transition_probs)

        # Initialize binary search bounds for subsidy values
        # subsidy_low[s] and subsidy_high[s] bound the Whittle index for state s
        subsidy_low = -2.0 * np.ones(2)
        subsidy_high = 2.0 * np.ones(2)

        max_q_diff = np.inf
        iteration = 0

        while max_q_diff > self.q_convergence_threshold and iteration < self.max_iterations:
            iteration += 1

            # Midpoint of binary search
            subsidies = (subsidy_low + subsidy_high) / 2.0

            # Run value iteration to compute Q-values for current subsidies
            q_values = self._value_iteration(transition_probs, subsidies)

            # Find state with maximum Q-value difference
            q_diffs = np.abs(q_values[:, 1] - q_values[:, 0])  # |Q(s, active) - Q(s, passive)|
            max_diff_state = np.argmax(q_diffs)
            max_q_diff = q_diffs[max_diff_state]

            # Update binary search bounds
            if max_q_diff > self.q_convergence_threshold:
                if q_values[max_diff_state, 0] < q_values[max_diff_state, 1]:
                    # Passive worse than active → increase subsidy lower bound
                    subsidy_low[max_diff_state] = subsidies[max_diff_state]
                else:
                    # Passive better than active → decrease subsidy upper bound
                    subsidy_high[max_diff_state] = subsidies[max_diff_state]

        # Final Whittle indices are the converged subsidy values
        whittle_indices = (subsidy_low + subsidy_high) / 2.0

        return float(whittle_indices[0]), float(whittle_indices[1])

    def _value_iteration(
        self,
        transition_probs: NDArray[np.float64],
        subsidies: NDArray[np.float64]
    ) -> NDArray[np.float64]:
        """
        Run value iteration to compute Q-values.

        Args:
            transition_probs: Transition probabilities [state, next_state, action]
            subsidies: Subsidy values for passive action (one per state)

        Returns:
            Q-values with shape (2, 2) where Q[s, a] = expected value of (s, a)
        """
        v_values = np.zeros(2)  # Value function V(s)
        delta = np.inf

        while delta > self.v_convergence_threshold:
            delta = 0.0
            new_v_values = np.zeros(2)

            for state in range(2):
                old_v = v_values[state]

                # Compute Q-values for both actions
                q_passive = self._compute_q_value(
                    state, action=0, transition_probs=transition_probs,
                    v_values=v_values, subsidy=subsidies[state]
                )
                q_active = self._compute_q_value(
                    state, action=1, transition_probs=transition_probs,
                    v_values=v_values, subsidy=0.0
                )

                # Value is max over actions
                new_v_values[state] = max(q_passive, q_active)
                delta = max(delta, abs(new_v_values[state] - old_v))

            v_values = new_v_values

        # Compute final Q-values
        q_values = np.zeros((2, 2))
        for state in range(2):
            q_values[state, 0] = self._compute_q_value(
                state, action=0, transition_probs=transition_probs,
                v_values=v_values, subsidy=subsidies[state]
            )
            q_values[state, 1] = self._compute_q_value(
                state, action=1, transition_probs=transition_probs,
                v_values=v_values, subsidy=0.0
            )

        return q_values

    def _compute_q_value(
        self,
        state: int,
        action: int,
        transition_probs: NDArray[np.float64],
        v_values: NDArray[np.float64],
        subsidy: float
    ) -> float:
        """
        Compute Q(state, action) value.

        Q(s, a) = E[r(s, a) + γ * V(s') | s, a]

        Args:
            state: Current state (0=Responsive, 1=Unresponsive)
            action: Action (0=Passive, 1=Active)
            transition_probs: Transition probabilities
            v_values: Value function V(s)
            subsidy: Subsidy for passive action

        Returns:
            Q-value for (state, action)
        """
        # Immediate reward
        reward = self._get_reward(state, action, subsidy)

        # Expected future value
        expected_future = 0.0
        for next_state in range(2):
            prob = transition_probs[state, next_state, action]
            expected_future += prob * v_values[next_state]

        return reward + self.gamma * expected_future

    @staticmethod
    def _get_reward(state: int, action: int, subsidy: float) -> float:
        """
        Reward function for RMAB.

        Reward structure:
        - Responsive state (0): +1 (good outcome)
        - Unresponsive state (1): -1 (bad outcome)
        - Passive action: receives subsidy
        - Active action: no subsidy

        Args:
            state: Current state (0=Responsive, 1=Unresponsive)
            action: Action (0=Passive, 1=Active)
            subsidy: Subsidy value for passive action

        Returns:
            Immediate reward
        """
        # State reward
        state_reward = 1.0 if state == 0 else -1.0

        # Add subsidy for passive action
        action_subsidy = subsidy if action == 0 else 0.0

        return state_reward + action_subsidy

    @staticmethod
    def _validate_transition_probs(transition_probs: NDArray[np.float64]) -> None:
        """
        Validate transition probability matrix.

        Checks:
        1. Shape is (2, 2, 2)
        2. All probabilities in [0, 1]
        3. Probabilities sum to 1 for each (state, action)
        4. No NaN or Inf values

        Args:
            transition_probs: Transition probability matrix

        Raises:
            ValueError: If validation fails
        """
        if transition_probs.shape != (2, 2, 2):
            raise ValueError(
                f"Expected shape (2, 2, 2), got {transition_probs.shape}"
            )

        if np.any(np.isnan(transition_probs)) or np.any(np.isinf(transition_probs)):
            raise ValueError("Transition probabilities contain NaN or Inf values")

        if np.any(transition_probs < 0) or np.any(transition_probs > 1):
            raise ValueError("Transition probabilities must be in [0, 1]")

        # Check probabilities sum to 1 for each (state, action)
        for state in range(2):
            for action in range(2):
                prob_sum = transition_probs[state, :, action].sum()
                if not np.isclose(prob_sum, 1.0, atol=1e-6):
                    raise ValueError(
                        f"Probabilities for state={state}, action={action} "
                        f"sum to {prob_sum}, expected 1.0"
                    )


def compute_whittle_index(
    transition_probs: NDArray[np.float64],
    gamma: float = 0.99
) -> Tuple[float, float]:
    """
    Convenience function to compute Whittle indices.

    Args:
        transition_probs: Transition probability matrix [state, next_state, action]
        gamma: Discount factor (default: 0.99)

    Returns:
        Tuple of (whittle_index_responsive, whittle_index_unresponsive)

    Example:
        >>> P = np.array([
        ...     [[0.8, 0.2], [0.7, 0.3]],
        ...     [[0.6, 0.4], [0.5, 0.5]]
        ... ])
        >>> w_r, w_u = compute_whittle_index(P, gamma=0.99)
    """
    solver = WhittleIndexSolver(gamma=gamma)
    return solver.compute_indices(transition_probs)
