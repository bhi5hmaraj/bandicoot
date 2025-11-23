"""
MDP Parameter Learning for RMAB.

Learns transition probabilities P(s'|s,a) from historical engagement data
using Bayesian estimation with Dirichlet priors.
"""

from typing import Dict, Tuple, Optional
import numpy as np
from numpy.typing import NDArray
import pandas as pd
from collections import defaultdict


class TransitionLearner:
    """
    Learn MDP transition probabilities from historical data.

    Uses Bayesian estimation with Dirichlet priors to handle sparse data.
    States: 0=Responsive (R), 1=Unresponsive (U)
    Actions: 0=Passive (no intervention), 1=Active (intervention)

    Attributes:
        alpha: Dirichlet prior parameter (smoothing strength)
        min_observations: Minimum observations before trusting estimates
    """

    def __init__(
        self,
        alpha: float = 1.0,
        min_observations: int = 10
    ):
        """
        Initialize MDP transition learner.

        Args:
            alpha: Dirichlet prior (higher = more smoothing). Default 1.0 = uniform prior
            min_observations: Minimum transitions needed for reliable estimate

        Raises:
            ValueError: If alpha <= 0
        """
        if alpha <= 0:
            raise ValueError(f"Alpha must be positive, got {alpha}")

        self.alpha = alpha
        self.min_observations = min_observations

        # Transition counts: [state, next_state, action]
        self.counts = np.zeros((2, 2, 2), dtype=np.int64)

    def add_transitions(
        self,
        transitions: pd.DataFrame,
        state_col: str = 'state',
        next_state_col: str = 'next_state',
        action_col: str = 'action'
    ) -> None:
        """
        Add observed transitions to learner.

        Args:
            transitions: DataFrame with columns [state, next_state, action]
                - state: 0=Responsive, 1=Unresponsive
                - next_state: 0=Responsive, 1=Unresponsive
                - action: 0=Passive, 1=Active
            state_col: Name of state column
            next_state_col: Name of next_state column
            action_col: Name of action column

        Raises:
            ValueError: If required columns missing or invalid values
        """
        # Validate columns
        required_cols = {state_col, next_state_col, action_col}
        if not required_cols.issubset(transitions.columns):
            missing = required_cols - set(transitions.columns)
            raise ValueError(f"Missing columns: {missing}")

        # Extract columns
        states = transitions[state_col].values
        next_states = transitions[next_state_col].values
        actions = transitions[action_col].values

        # Validate values
        if not np.all((states >= 0) & (states <= 1)):
            raise ValueError("State values must be 0 or 1")
        if not np.all((next_states >= 0) & (next_states <= 1)):
            raise ValueError("Next state values must be 0 or 1")
        if not np.all((actions >= 0) & (actions <= 1)):
            raise ValueError("Action values must be 0 or 1")

        # Count transitions
        for s, s_next, a in zip(states, next_states, actions):
            self.counts[s, s_next, a] += 1

    def add_transition_counts(
        self,
        counts: NDArray[np.int64]
    ) -> None:
        """
        Add pre-aggregated transition counts.

        Args:
            counts: [2, 2, 2] array of transition counts

        Raises:
            ValueError: If shape is wrong or contains negative values
        """
        if counts.shape != (2, 2, 2):
            raise ValueError(f"Expected shape (2, 2, 2), got {counts.shape}")

        if np.any(counts < 0):
            raise ValueError("Counts must be non-negative")

        self.counts += counts

    def estimate_transitions(
        self,
        use_prior: bool = True
    ) -> NDArray[np.float64]:
        """
        Estimate transition probabilities using Bayesian estimation.

        Uses Dirichlet-Multinomial conjugate prior for smoothing:
        P(s'|s,a) = (count(s,s',a) + alpha) / (sum_s' count(s,s',a) + 2*alpha)

        Args:
            use_prior: Whether to use Dirichlet prior for smoothing

        Returns:
            Transition probabilities [2, 2, 2] where P[s, s', a] = P(s'|s,a)

        Raises:
            ValueError: If no observations for any (state, action) pair
        """
        P = np.zeros((2, 2, 2), dtype=np.float64)

        for state in range(2):
            for action in range(2):
                # Count transitions from (state, action)
                total_count = self.counts[state, :, action].sum()

                if total_count == 0:
                    # No observations - use uniform prior
                    if use_prior:
                        P[state, :, action] = 0.5  # Uniform
                    else:
                        raise ValueError(
                            f"No observations for state={state}, action={action}. "
                            "Set use_prior=True to handle missing data."
                        )
                else:
                    # Bayesian estimate with Dirichlet prior
                    if use_prior:
                        # Add alpha to counts (pseudocounts)
                        numerator = self.counts[state, :, action] + self.alpha
                        denominator = total_count + 2 * self.alpha
                        P[state, :, action] = numerator / denominator
                    else:
                        # Maximum likelihood (no smoothing)
                        P[state, :, action] = self.counts[state, :, action] / total_count

        return P

    def get_observation_counts(self) -> Dict[Tuple[int, int], int]:
        """
        Get number of observations for each (state, action) pair.

        Returns:
            Dictionary mapping (state, action) -> count
        """
        obs_counts = {}
        for state in range(2):
            for action in range(2):
                count = self.counts[state, :, action].sum()
                obs_counts[(state, action)] = count

        return obs_counts

    def get_confidence(self) -> NDArray[np.float64]:
        """
        Get confidence score for each (state, action) pair.

        Confidence is based on number of observations relative to min_observations.
        Returns values in [0, 1] where 1 = fully confident.

        Returns:
            Confidence scores [2, 2] where confidence[s, a] = confidence in P(·|s,a)
        """
        confidence = np.zeros((2, 2), dtype=np.float64)

        for state in range(2):
            for action in range(2):
                count = self.counts[state, :, action].sum()
                confidence[state, action] = min(1.0, count / self.min_observations)

        return confidence

    def reset(self) -> None:
        """Reset all transition counts."""
        self.counts = np.zeros((2, 2, 2), dtype=np.int64)

    def __repr__(self) -> str:
        """String representation."""
        obs_counts = self.get_observation_counts()
        total_obs = sum(obs_counts.values())
        return (
            f"TransitionLearner(alpha={self.alpha}, "
            f"total_observations={total_obs})"
        )


def extract_transitions_from_history(
    history: pd.DataFrame,
    caregiver_id_col: str = 'caregiver_id',
    timestamp_col: str = 'timestamp',
    state_col: str = 'state',
    action_col: str = 'action',
    sort: bool = True
) -> pd.DataFrame:
    """
    Extract state transitions from historical engagement data.

    Converts time-series data into (state, action, next_state) tuples.

    Args:
        history: Historical data with columns [caregiver_id, timestamp, state, action]
        caregiver_id_col: Column name for caregiver ID
        timestamp_col: Column name for timestamp
        state_col: Column name for state (0=R, 1=U)
        action_col: Column name for action (0=passive, 1=active)
        sort: Whether to sort by caregiver and timestamp

    Returns:
        DataFrame with columns [caregiver_id, state, action, next_state]

    Example:
        >>> history = pd.DataFrame({
        ...     'caregiver_id': [1, 1, 1, 2, 2],
        ...     'timestamp': [0, 1, 2, 0, 1],
        ...     'state': [0, 0, 1, 1, 0],
        ...     'action': [0, 1, 1, 0, 1]
        ... })
        >>> transitions = extract_transitions_from_history(history)
        >>> # Returns: [(cg=1, s=0, a=0, s'=0), (cg=1, s=0, a=1, s'=1), ...]
    """
    # Sort by caregiver and time
    if sort:
        df = history.sort_values([caregiver_id_col, timestamp_col]).copy()
    else:
        df = history.copy()

    # Create next_state by shifting within each caregiver
    df['next_state'] = df.groupby(caregiver_id_col)[state_col].shift(-1)

    # Drop last observation for each caregiver (no next state)
    df = df.dropna(subset=['next_state'])

    # Convert to int
    df['next_state'] = df['next_state'].astype(int)

    # Select relevant columns
    transitions = df[[caregiver_id_col, state_col, action_col, 'next_state']].copy()

    return transitions


def estimate_passive_transitions(
    history: pd.DataFrame,
    **kwargs
) -> NDArray[np.float64]:
    """
    Estimate passive transition probabilities (no intervention).

    Convenience function for clustering based on passive behavior.

    Args:
        history: Historical data
        **kwargs: Arguments for extract_transitions_from_history

    Returns:
        Passive transition probabilities [2, 2] where P[s, s'] = P(s'|s, passive)
    """
    # Extract transitions
    transitions = extract_transitions_from_history(history, **kwargs)

    # Filter to passive actions only
    passive_transitions = transitions[transitions['action'] == 0]

    # Learn probabilities
    learner = TransitionLearner(alpha=1.0)
    learner.add_transitions(passive_transitions)

    # Get full transition matrix and extract passive slice
    P_full = learner.estimate_transitions(use_prior=True)

    # Extract passive transitions: P[state, next_state, action=0]
    P_passive = P_full[:, :, 0]

    return P_passive
