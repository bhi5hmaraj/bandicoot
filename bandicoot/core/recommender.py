"""
RMAB Recommender System for Caregiver Prioritization.

Orchestrates Whittle index computation, MDP learning, and clustering to generate
intervention recommendations that maximize expected engagement.
"""

from typing import Optional, Tuple, Dict
import numpy as np
from numpy.typing import NDArray
import pandas as pd
from dataclasses import dataclass

from bandicoot.core.whittle import WhittleIndexSolver
from bandicoot.core.mdp import TransitionLearner, extract_transitions_from_history
from bandicoot.core.clustering import (
    PassiveBehaviorClusterer,
    ClusteringResult,
    extract_passive_features
)


@dataclass
class RecommenderResult:
    """
    Result from recommender system.

    Attributes:
        recommended_ids: IDs of caregivers recommended for intervention
        priorities: Priority scores (Whittle indices) for recommended caregivers
        all_priorities: Priority scores for all caregivers
        budget_used: Number of recommendations (≤ budget)
    """
    recommended_ids: NDArray[np.int64]
    priorities: NDArray[np.float64]
    all_priorities: NDArray[np.float64]
    budget_used: int


class BandicootRMAB:
    """
    Main RMAB recommender system for caregiver intervention prioritization.

    This class orchestrates the full RMAB pipeline:
    1. Learn MDP transition probabilities from historical engagement data
    2. Cluster caregivers by passive (no intervention) behavior patterns
    3. Compute Whittle indices for each cluster
    4. Generate top-k intervention recommendations based on current states

    Example:
        >>> # Historical data
        >>> history = pd.DataFrame({
        ...     'caregiver_id': [1, 1, 2, 2, ...],
        ...     'timestamp': [0, 1, 0, 1, ...],
        ...     'state': [0, 0, 1, 0, ...],  # 0=Responsive, 1=Unresponsive
        ...     'action': [0, 1, 0, 0, ...]  # 0=Passive, 1=Active
        ... })
        >>>
        >>> # Fit recommender
        >>> recommender = BandicootRMAB(n_clusters=20, gamma=0.99)
        >>> recommender.fit(history)
        >>>
        >>> # Generate recommendations
        >>> current_states = np.array([0, 1, 0, 1, ...])  # Current state for each caregiver
        >>> result = recommender.recommend(current_states, budget=50)
        >>> print(result.recommended_ids)  # Top 50 caregivers to contact
    """

    def __init__(
        self,
        n_clusters: int = 20,
        gamma: float = 0.99,
        alpha: float = 1.0,
        min_observations: int = 10,
        random_state: int = 42
    ):
        """
        Initialize RMAB recommender system.

        Args:
            n_clusters: Number of caregiver clusters (default: 20, as in SAHELI)
            gamma: Discount factor for future rewards (0 < gamma < 1)
            alpha: Dirichlet prior strength for MDP learning (higher = more smoothing)
            min_observations: Minimum observations needed for reliable MDP estimates
            random_state: Random seed for reproducibility

        Raises:
            ValueError: If parameters are invalid
        """
        if n_clusters < 2:
            raise ValueError(f"n_clusters must be >= 2, got {n_clusters}")
        if not 0 < gamma < 1:
            raise ValueError(f"gamma must be in (0, 1), got {gamma}")
        if alpha <= 0:
            raise ValueError(f"alpha must be positive, got {alpha}")

        self.n_clusters = n_clusters
        self.gamma = gamma
        self.alpha = alpha
        self.min_observations = min_observations
        self.random_state = random_state

        # Components (initialized during fit)
        self._clusterer: Optional[PassiveBehaviorClusterer] = None
        self._cluster_mdps: Optional[Dict[int, NDArray[np.float64]]] = None
        self._whittle_indices: Optional[Dict[int, Tuple[float, float]]] = None
        self._caregiver_to_cluster: Optional[Dict[int, int]] = None
        self._is_fitted = False

    @property
    def is_fitted(self) -> bool:
        """Check if recommender has been fitted."""
        return self._is_fitted

    def fit(
        self,
        history: pd.DataFrame,
        caregiver_id_col: str = 'caregiver_id',
        timestamp_col: str = 'timestamp',
        state_col: str = 'state',
        action_col: str = 'action',
        verbose: bool = True
    ) -> 'BandicootRMAB':
        """
        Fit recommender on historical engagement data.

        This method:
        1. Extracts passive behavior features for each caregiver
        2. Clusters caregivers by passive transition patterns
        3. Learns MDP parameters for each cluster
        4. Computes Whittle indices for each cluster

        Args:
            history: Historical data with columns [caregiver_id, timestamp, state, action]
            caregiver_id_col: Column name for caregiver ID
            timestamp_col: Column name for timestamp
            state_col: Column name for state (0=Responsive, 1=Unresponsive)
            action_col: Column name for action (0=Passive, 1=Active)
            verbose: Print progress messages

        Returns:
            self (for method chaining)

        Raises:
            ValueError: If required columns are missing or data is invalid
        """
        if verbose:
            print(f"Fitting BandicootRMAB on {len(history)} observations...")

        # Step 1: Extract passive behavior features for clustering
        if verbose:
            print("  [1/4] Extracting passive behavior features...")

        # Rename columns if needed to match expected names
        history_copy = history.copy()
        column_mapping = {
            caregiver_id_col: 'caregiver_id',
            timestamp_col: 'timestamp',
            state_col: 'state',
            action_col: 'action'
        }
        history_copy = history_copy.rename(columns=column_mapping)

        P_passive, caregiver_ids = extract_passive_features(
            history_copy,
            caregiver_id_col='caregiver_id'
        )

        n_caregivers = len(caregiver_ids)
        if verbose:
            print(f"        Found {n_caregivers} caregivers")

        # Step 2: Cluster caregivers by passive behavior
        if verbose:
            print(f"  [2/4] Clustering caregivers into {self.n_clusters} clusters...")

        self._clusterer = PassiveBehaviorClusterer(
            n_clusters=self.n_clusters,
            random_state=self.random_state
        )

        clustering_result = self._clusterer.fit(P_passive, caregiver_ids)

        if verbose:
            print(f"        Silhouette score: {clustering_result.silhouette_score:.4f}")

        # Build caregiver -> cluster mapping
        self._caregiver_to_cluster = dict(zip(caregiver_ids, clustering_result.cluster_labels))

        # Step 3: Learn MDP parameters for each cluster
        if verbose:
            print(f"  [3/4] Learning MDP parameters for each cluster...")

        self._cluster_mdps = {}
        transitions = extract_transitions_from_history(
            history_copy,
            caregiver_id_col='caregiver_id',
            timestamp_col='timestamp',
            state_col='state',
            action_col='action'
        )

        for cluster_id in range(self.n_clusters):
            # Get caregivers in this cluster
            cluster_caregivers = [
                cg_id for cg_id, cid in self._caregiver_to_cluster.items()
                if cid == cluster_id
            ]

            if len(cluster_caregivers) == 0:
                if verbose:
                    print(f"        Cluster {cluster_id}: EMPTY (skipping)")
                continue

            # Filter transitions to this cluster
            cluster_transitions = transitions[
                transitions['caregiver_id'].isin(cluster_caregivers)
            ]

            # Learn MDP for this cluster
            learner = TransitionLearner(alpha=self.alpha, min_observations=self.min_observations)
            learner.add_transitions(
                cluster_transitions,
                state_col='state',
                next_state_col='next_state',
                action_col='action'
            )

            # Get transition probabilities
            P_cluster = learner.estimate_transitions(use_prior=True)
            self._cluster_mdps[cluster_id] = P_cluster

            if verbose:
                obs_counts = learner.get_observation_counts()
                total_obs = sum(obs_counts.values())
                print(f"        Cluster {cluster_id}: {len(cluster_caregivers)} caregivers, {total_obs} transitions")

        # Step 4: Compute Whittle indices for each cluster
        if verbose:
            print(f"  [4/4] Computing Whittle indices...")

        self._whittle_indices = {}
        solver = WhittleIndexSolver(gamma=self.gamma)

        for cluster_id, P_cluster in self._cluster_mdps.items():
            w_r, w_u = solver.compute_indices(P_cluster)
            self._whittle_indices[cluster_id] = (w_r, w_u)

            if verbose:
                print(f"        Cluster {cluster_id}: W(R)={w_r:.4f}, W(U)={w_u:.4f}")

        self._is_fitted = True

        if verbose:
            print("Fitting complete!")

        return self

    def recommend(
        self,
        states: NDArray[np.int64],
        budget: int,
        caregiver_ids: Optional[NDArray[np.int64]] = None
    ) -> RecommenderResult:
        """
        Generate intervention recommendations for current caregiver states.

        Recommends the top-k caregivers with highest Whittle indices given their current
        states and cluster assignments.

        Args:
            states: Current state for each caregiver [n_caregivers]
                    (0=Responsive, 1=Unresponsive)
            budget: Maximum number of interventions to recommend
            caregiver_ids: Optional array of caregiver IDs [n_caregivers].
                          If None, uses indices 0, 1, 2, ...

        Returns:
            RecommenderResult with recommended IDs and priorities

        Raises:
            ValueError: If recommender not fitted or inputs invalid
        """
        if not self.is_fitted:
            raise ValueError("Must call fit() before recommend()")

        n_caregivers = len(states)

        if caregiver_ids is None:
            caregiver_ids = np.arange(n_caregivers)

        if len(caregiver_ids) != n_caregivers:
            raise ValueError(
                f"Length mismatch: states has {n_caregivers} elements "
                f"but caregiver_ids has {len(caregiver_ids)}"
            )

        if not np.all((states >= 0) & (states <= 1)):
            raise ValueError("States must be 0 (Responsive) or 1 (Unresponsive)")

        if budget <= 0:
            raise ValueError(f"Budget must be positive, got {budget}")

        # Compute priority for each caregiver
        priorities = np.zeros(n_caregivers, dtype=np.float64)

        for i, (cg_id, state) in enumerate(zip(caregiver_ids, states)):
            # Get cluster for this caregiver
            cluster_id = self.predict_cluster(cg_id)

            if cluster_id is None:
                # Unknown caregiver - use median priority
                all_indices = [w for w_r, w_u in self._whittle_indices.values() for w in [w_r, w_u]]
                priorities[i] = np.median(all_indices)
            else:
                # Get Whittle index for (cluster, state)
                w_r, w_u = self._whittle_indices[cluster_id]
                priorities[i] = w_u if state == 1 else w_r

        # Select top-k caregivers
        budget_used = min(budget, n_caregivers)
        top_k_indices = np.argpartition(priorities, -budget_used)[-budget_used:]
        top_k_indices = top_k_indices[np.argsort(priorities[top_k_indices])[::-1]]

        return RecommenderResult(
            recommended_ids=caregiver_ids[top_k_indices],
            priorities=priorities[top_k_indices],
            all_priorities=priorities,
            budget_used=budget_used
        )

    def predict_cluster(self, caregiver_id: int) -> Optional[int]:
        """
        Predict cluster assignment for a caregiver.

        Args:
            caregiver_id: Caregiver ID

        Returns:
            Cluster ID (0 to n_clusters-1) or None if caregiver not seen during training

        Raises:
            ValueError: If recommender not fitted
        """
        if not self.is_fitted:
            raise ValueError("Must call fit() before predict_cluster()")

        return self._caregiver_to_cluster.get(caregiver_id)

    def predict_cluster_for_transitions(
        self,
        passive_transitions: NDArray[np.float64]
    ) -> NDArray[np.int64]:
        """
        Predict cluster for new caregivers based on their passive transition matrix.

        Useful for assigning clusters to new caregivers not seen during training.

        Args:
            passive_transitions: Passive transition probabilities [n_new, 2, 2]

        Returns:
            Cluster assignments [n_new]

        Raises:
            ValueError: If recommender not fitted
        """
        if not self.is_fitted:
            raise ValueError("Must call fit() before predict_cluster_for_transitions()")

        return self._clusterer.predict(passive_transitions)

    def get_cluster_summary(self) -> pd.DataFrame:
        """
        Get summary statistics for each cluster.

        Returns:
            DataFrame with columns:
            - cluster: Cluster ID
            - n_caregivers: Number of caregivers in cluster
            - w_responsive: Whittle index for Responsive state
            - w_unresponsive: Whittle index for Unresponsive state
            - retention_R: P(R→R | passive)
            - recovery_U: P(U→R | passive)

        Raises:
            ValueError: If recommender not fitted
        """
        if not self.is_fitted:
            raise ValueError("Must call fit() before get_cluster_summary()")

        rows = []
        for cluster_id in range(self.n_clusters):
            # Count caregivers in cluster
            n_cg = sum(1 for c in self._caregiver_to_cluster.values() if c == cluster_id)

            if cluster_id not in self._cluster_mdps:
                continue

            # Get MDP and Whittle indices
            P = self._cluster_mdps[cluster_id]
            w_r, w_u = self._whittle_indices[cluster_id]

            rows.append({
                'cluster': cluster_id,
                'n_caregivers': n_cg,
                'w_responsive': w_r,
                'w_unresponsive': w_u,
                'retention_R': P[0, 0, 0],  # P(R→R | passive)
                'recovery_U': P[1, 0, 0],   # P(U→R | passive)
            })

        return pd.DataFrame(rows)

    def __repr__(self) -> str:
        """String representation."""
        if self.is_fitted:
            n_clusters_with_data = len(self._cluster_mdps)
            return (
                f"BandicootRMAB(n_clusters={self.n_clusters}, gamma={self.gamma}, "
                f"fitted on {len(self._caregiver_to_cluster)} caregivers, "
                f"{n_clusters_with_data} non-empty clusters)"
            )
        else:
            return (
                f"BandicootRMAB(n_clusters={self.n_clusters}, gamma={self.gamma}, "
                f"not fitted)"
            )
