"""
Synthetic data generator for testing RMAB algorithms.

Generates realistic transition probabilities for different caregiver engagement patterns.
"""

from typing import Dict, Tuple
import numpy as np
from numpy.typing import NDArray


class TransitionGenerator:
    """
    Generate synthetic transition probabilities for different caregiver types.

    Creates realistic MDP transition matrices that reflect different
    engagement behaviors (highly engaged, moderately engaged, disengaged).
    """

    def __init__(self, seed: int = 42):
        """
        Initialize generator with random seed.

        Args:
            seed: Random seed for reproducibility
        """
        self.rng = np.random.RandomState(seed)

    def generate_highly_engaged(self) -> NDArray[np.float64]:
        """
        Generate transitions for highly engaged caregivers.

        Characteristics:
        - High probability to stay Responsive with or without intervention
        - Quick recovery from Unresponsive state with intervention
        - Moderate drift to Unresponsive without intervention

        Returns:
            Transition probability matrix [state, next_state, action]
        """
        # From Responsive state
        r_to_r_passive = 0.85 + self.rng.uniform(-0.05, 0.05)  # Stay responsive
        r_to_r_active = 0.95 + self.rng.uniform(-0.03, 0.03)   # Almost always stay

        # From Unresponsive state
        u_to_r_passive = 0.40 + self.rng.uniform(-0.05, 0.05)  # Some recovery
        u_to_r_active = 0.75 + self.rng.uniform(-0.05, 0.05)   # Good recovery

        return self._build_transition_matrix(
            r_to_r_passive, r_to_r_active,
            u_to_r_passive, u_to_r_active
        )

    def generate_moderately_engaged(self) -> NDArray[np.float64]:
        """
        Generate transitions for moderately engaged caregivers.

        Characteristics:
        - Moderate probability to stay Responsive
        - Intervention helps significantly
        - Higher drift to Unresponsive without intervention

        Returns:
            Transition probability matrix [state, next_state, action]
        """
        # From Responsive state
        r_to_r_passive = 0.70 + self.rng.uniform(-0.05, 0.05)
        r_to_r_active = 0.85 + self.rng.uniform(-0.05, 0.05)

        # From Unresponsive state
        u_to_r_passive = 0.25 + self.rng.uniform(-0.05, 0.05)
        u_to_r_active = 0.60 + self.rng.uniform(-0.05, 0.05)

        return self._build_transition_matrix(
            r_to_r_passive, r_to_r_active,
            u_to_r_passive, u_to_r_active
        )

    def generate_disengaged(self) -> NDArray[np.float64]:
        """
        Generate transitions for disengaged caregivers.

        Characteristics:
        - Low probability to stay Responsive without intervention
        - Intervention helps but not dramatically
        - Slow recovery from Unresponsive state

        Returns:
            Transition probability matrix [state, next_state, action]
        """
        # From Responsive state
        r_to_r_passive = 0.50 + self.rng.uniform(-0.05, 0.05)
        r_to_r_active = 0.70 + self.rng.uniform(-0.05, 0.05)

        # From Unresponsive state
        u_to_r_passive = 0.15 + self.rng.uniform(-0.05, 0.05)
        u_to_r_active = 0.40 + self.rng.uniform(-0.05, 0.05)

        return self._build_transition_matrix(
            r_to_r_passive, r_to_r_active,
            u_to_r_passive, u_to_r_active
        )

    def generate_batch(
        self,
        n_highly_engaged: int = 5,
        n_moderately_engaged: int = 10,
        n_disengaged: int = 5
    ) -> Dict[str, list]:
        """
        Generate a batch of transition matrices for different caregiver types.

        Args:
            n_highly_engaged: Number of highly engaged patterns
            n_moderately_engaged: Number of moderately engaged patterns
            n_disengaged: Number of disengaged patterns

        Returns:
            Dictionary with keys 'highly_engaged', 'moderately_engaged', 'disengaged'
            containing lists of transition matrices
        """
        return {
            'highly_engaged': [
                self.generate_highly_engaged() for _ in range(n_highly_engaged)
            ],
            'moderately_engaged': [
                self.generate_moderately_engaged() for _ in range(n_moderately_engaged)
            ],
            'disengaged': [
                self.generate_disengaged() for _ in range(n_disengaged)
            ]
        }

    @staticmethod
    def _build_transition_matrix(
        r_to_r_passive: float,
        r_to_r_active: float,
        u_to_r_passive: float,
        u_to_r_active: float
    ) -> NDArray[np.float64]:
        """
        Build normalized transition matrix from individual probabilities.

        Args:
            r_to_r_passive: P(R → R | passive)
            r_to_r_active: P(R → R | active)
            u_to_r_passive: P(U → R | passive)
            u_to_r_active: P(U → R | active)

        Returns:
            Transition probability matrix [state, next_state, action]
        """
        # Clip probabilities to [0, 1]
        r_to_r_passive = np.clip(r_to_r_passive, 0, 1)
        r_to_r_active = np.clip(r_to_r_active, 0, 1)
        u_to_r_passive = np.clip(u_to_r_passive, 0, 1)
        u_to_r_active = np.clip(u_to_r_active, 0, 1)

        # Complementary probabilities
        r_to_u_passive = 1 - r_to_r_passive
        r_to_u_active = 1 - r_to_r_active
        u_to_u_passive = 1 - u_to_r_passive
        u_to_u_active = 1 - u_to_r_active

        # Build matrix: P[state, next_state, action]
        P = np.array([
            # From Responsive (state 0)
            [[r_to_r_passive, r_to_r_active],   # to R (next_state 0)
             [r_to_u_passive, r_to_u_active]],  # to U (next_state 1)
            # From Unresponsive (state 1)
            [[u_to_r_passive, u_to_r_active],   # to R (next_state 0)
             [u_to_u_passive, u_to_u_active]]   # to U (next_state 1)
        ])

        return P

    @staticmethod
    def print_transition_matrix(P: NDArray[np.float64], name: str = "Transition Matrix"):
        """
        Pretty print a transition matrix.

        Args:
            P: Transition probability matrix [state, next_state, action]
            name: Name to display
        """
        print(f"\n{name}")
        print("=" * 60)
        print("\nFrom RESPONSIVE (R):")
        print(f"  P(R → R | passive) = {P[0, 0, 0]:.3f}  |  P(R → R | active) = {P[0, 0, 1]:.3f}")
        print(f"  P(R → U | passive) = {P[0, 1, 0]:.3f}  |  P(R → U | active) = {P[0, 1, 1]:.3f}")

        print("\nFrom UNRESPONSIVE (U):")
        print(f"  P(U → R | passive) = {P[1, 0, 0]:.3f}  |  P(U → R | active) = {P[1, 0, 1]:.3f}")
        print(f"  P(U → U | passive) = {P[1, 1, 0]:.3f}  |  P(U → U | active) = {P[1, 1, 1]:.3f}")
        print()


def generate_test_scenarios() -> Dict[str, NDArray[np.float64]]:
    """
    Generate standard test scenarios for experiments.

    Returns:
        Dictionary mapping scenario names to transition matrices
    """
    gen = TransitionGenerator(seed=42)

    return {
        'highly_engaged': gen.generate_highly_engaged(),
        'moderately_engaged': gen.generate_moderately_engaged(),
        'disengaged': gen.generate_disengaged(),
    }
