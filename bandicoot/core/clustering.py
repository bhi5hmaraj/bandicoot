"""
Clustering caregivers by passive engagement behavior.

Uses K-means on passive transition probabilities to discover homogeneous
groups with similar MDP dynamics.
"""

from typing import Optional, Tuple, Dict
import numpy as np
from numpy.typing import NDArray
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from dataclasses import dataclass


@dataclass
class ClusteringResult:
    """Result of clustering operation."""

    cluster_labels: NDArray[np.int64]  # Cluster assignment for each caregiver
    n_clusters: int                     # Number of clusters
    silhouette_score: float            # Quality metric [-1, 1]
    cluster_model: KMeans              # Fitted scikit-learn model
    feature_matrix: NDArray[np.float64]  # Features used for clustering

    def get_cluster_sizes(self) -> Dict[int, int]:
        """Get size of each cluster."""
        unique, counts = np.unique(self.cluster_labels, return_counts=True)
        return dict(zip(unique.tolist(), counts.tolist()))


class PassiveBehaviorClusterer:
    """
    Cluster caregivers based on passive (no intervention) behavior.

    Uses K-means on passive transition probabilities:
    - P(R→R | passive)
    - P(R→U | passive)
    - P(U→R | passive)
    - P(U→U | passive)

    This discovers groups with similar natural engagement patterns.

    Attributes:
        n_clusters: Number of clusters to create
        random_state: Random seed for reproducibility
    """

    def __init__(
        self,
        n_clusters: int = 20,
        random_state: int = 42
    ):
        """
        Initialize clusterer.

        Args:
            n_clusters: Number of clusters (default: 20, as used in SAHELI)
            random_state: Random seed for reproducibility

        Raises:
            ValueError: If n_clusters < 2
        """
        if n_clusters < 2:
            raise ValueError(f"n_clusters must be >= 2, got {n_clusters}")

        self.n_clusters = n_clusters
        self.random_state = random_state
        self._model: Optional[KMeans] = None

    def fit(
        self,
        passive_transitions: NDArray[np.float64],
        caregiver_ids: Optional[NDArray] = None
    ) -> ClusteringResult:
        """
        Fit clustering model on passive transition probabilities.

        Args:
            passive_transitions: [n_caregivers, 2, 2] array where
                passive_transitions[i] = P(·|·, passive) for caregiver i
            caregiver_ids: Optional array of caregiver IDs for tracking

        Returns:
            ClusteringResult with cluster assignments and quality metrics

        Raises:
            ValueError: If data shape is wrong or insufficient caregivers
        """
        n_caregivers = passive_transitions.shape[0]

        # Validate shape
        if passive_transitions.shape != (n_caregivers, 2, 2):
            raise ValueError(
                f"Expected shape (n, 2, 2), got {passive_transitions.shape}"
            )

        # Check sufficient caregivers
        if n_caregivers < self.n_clusters:
            raise ValueError(
                f"Need at least {self.n_clusters} caregivers, got {n_caregivers}"
            )

        # Flatten transition matrices into feature vectors
        # Each caregiver: [P(R→R), P(R→U), P(U→R), P(U→U)]
        feature_matrix = passive_transitions.reshape(n_caregivers, 4)

        # Fit K-means
        self._model = KMeans(
            n_clusters=self.n_clusters,
            random_state=self.random_state,
            n_init=10  # Multiple random initializations
        )
        cluster_labels = self._model.fit_predict(feature_matrix)

        # Compute silhouette score (quality metric)
        if n_caregivers >= self.n_clusters + 1:
            sil_score = silhouette_score(feature_matrix, cluster_labels)
        else:
            sil_score = np.nan  # Not enough samples

        return ClusteringResult(
            cluster_labels=cluster_labels,
            n_clusters=self.n_clusters,
            silhouette_score=sil_score,
            cluster_model=self._model,
            feature_matrix=feature_matrix
        )

    def predict(
        self,
        passive_transitions: NDArray[np.float64]
    ) -> NDArray[np.int64]:
        """
        Predict cluster for new caregivers.

        Args:
            passive_transitions: [n_caregivers, 2, 2] array of passive probabilities

        Returns:
            Cluster labels [n_caregivers]

        Raises:
            ValueError: If model not fitted or wrong shape
        """
        if self._model is None:
            raise ValueError("Must call fit() before predict()")

        n_caregivers = passive_transitions.shape[0]

        if passive_transitions.shape != (n_caregivers, 2, 2):
            raise ValueError(
                f"Expected shape (n, 2, 2), got {passive_transitions.shape}"
            )

        # Flatten to feature vectors
        feature_matrix = passive_transitions.reshape(n_caregivers, 4)

        # Predict clusters
        return self._model.predict(feature_matrix)

    @property
    def is_fitted(self) -> bool:
        """Check if model has been fitted."""
        return self._model is not None

    def __repr__(self) -> str:
        """String representation."""
        fitted_str = "fitted" if self.is_fitted else "not fitted"
        return (
            f"PassiveBehaviorClusterer(n_clusters={self.n_clusters}, "
            f"status={fitted_str})"
        )


def find_optimal_clusters(
    passive_transitions: NDArray[np.float64],
    k_range: Tuple[int, int] = (15, 25),
    random_state: int = 42
) -> Tuple[int, ClusteringResult]:
    """
    Find optimal number of clusters using silhouette score.

    Tests different values of k and returns the one with highest silhouette score.

    Args:
        passive_transitions: [n_caregivers, 2, 2] passive transition probabilities
        k_range: (min_k, max_k) range to search (default: 15-25 as in SAHELI)
        random_state: Random seed for reproducibility

    Returns:
        (optimal_k, clustering_result) tuple

    Example:
        >>> P_passive = ... # [n_caregivers, 2, 2]
        >>> best_k, result = find_optimal_clusters(P_passive, k_range=(10, 30))
        >>> print(f"Optimal k={best_k}, silhouette={result.silhouette_score:.3f}")
    """
    min_k, max_k = k_range
    n_caregivers = passive_transitions.shape[0]

    if max_k > n_caregivers:
        raise ValueError(
            f"max_k ({max_k}) cannot exceed n_caregivers ({n_caregivers})"
        )

    best_k = None
    best_score = -np.inf
    best_result = None

    for k in range(min_k, max_k + 1):
        clusterer = PassiveBehaviorClusterer(n_clusters=k, random_state=random_state)
        result = clusterer.fit(passive_transitions)

        if not np.isnan(result.silhouette_score) and result.silhouette_score > best_score:
            best_score = result.silhouette_score
            best_k = k
            best_result = result

    if best_k is None:
        raise ValueError("Could not find valid clustering")

    return best_k, best_result


def extract_passive_features(
    history: pd.DataFrame,
    caregiver_id_col: str = 'caregiver_id'
) -> Tuple[NDArray[np.float64], NDArray]:
    """
    Extract passive transition probabilities for each caregiver.

    Args:
        history: Historical data with columns [caregiver_id, timestamp, state, action]
        caregiver_id_col: Column name for caregiver ID

    Returns:
        (passive_transitions, caregiver_ids) where:
        - passive_transitions: [n_caregivers, 2, 2] array
        - caregiver_ids: [n_caregivers] array of IDs

    Example:
        >>> history = pd.DataFrame({...})
        >>> P_passive, cg_ids = extract_passive_features(history)
        >>> clusterer = PassiveBehaviorClusterer(n_clusters=20)
        >>> result = clusterer.fit(P_passive, cg_ids)
    """
    from bandicoot.core.mdp import extract_transitions_from_history, TransitionLearner

    # Extract all transitions
    transitions = extract_transitions_from_history(history)

    # Filter to passive only
    passive_transitions = transitions[transitions['action'] == 0]

    # Group by caregiver and learn passive probabilities
    caregiver_ids = history[caregiver_id_col].unique()
    n_caregivers = len(caregiver_ids)

    P_passive_all = np.zeros((n_caregivers, 2, 2))

    for i, cg_id in enumerate(caregiver_ids):
        cg_transitions = passive_transitions[
            passive_transitions[caregiver_id_col] == cg_id
        ]

        if len(cg_transitions) > 0:
            # Learn transitions for this caregiver
            learner = TransitionLearner(alpha=1.0)
            learner.add_transitions(cg_transitions)
            P_full = learner.estimate_transitions(use_prior=True)

            # Extract passive slice
            P_passive_all[i] = P_full[:, :, 0]
        else:
            # No passive observations - use uniform prior
            P_passive_all[i] = np.array([[0.5, 0.5], [0.5, 0.5]])

    return P_passive_all, caregiver_ids


def analyze_clusters(
    result: ClusteringResult,
    passive_transitions: NDArray[np.float64]
) -> pd.DataFrame:
    """
    Analyze cluster characteristics.

    Args:
        result: ClusteringResult from fitting
        passive_transitions: Original transition data

    Returns:
        DataFrame with cluster statistics

    Example:
        >>> analysis = analyze_clusters(result, P_passive)
        >>> print(analysis)
           cluster  size  retention_R  recovery_U  silhouette
        0        0    50        0.850       0.320       0.654
        1        1    75        0.720       0.180       0.612
        ...
    """
    cluster_labels = result.cluster_labels
    n_caregivers = len(cluster_labels)

    rows = []
    for cluster_id in range(result.n_clusters):
        mask = cluster_labels == cluster_id
        cluster_size = mask.sum()

        if cluster_size == 0:
            continue

        # Get transitions for this cluster
        cluster_trans = passive_transitions[mask]

        # Compute average transition probabilities
        avg_trans = cluster_trans.mean(axis=0)

        # Compute cluster-specific silhouette (if possible)
        if cluster_size > 1 and result.n_clusters > 1:
            # Use silhouette_samples to get per-sample scores, then average for this cluster
            from sklearn.metrics import silhouette_samples
            sample_scores = silhouette_samples(result.feature_matrix, cluster_labels)
            cluster_sil = sample_scores[mask].mean()
        else:
            cluster_sil = np.nan

        rows.append({
            'cluster': cluster_id,
            'size': cluster_size,
            'retention_R': avg_trans[0, 0],  # P(R→R | passive)
            'drift_to_U': avg_trans[0, 1],   # P(R→U | passive)
            'recovery_U': avg_trans[1, 0],   # P(U→R | passive)
            'stay_U': avg_trans[1, 1],       # P(U→U | passive)
            'silhouette': cluster_sil
        })

    return pd.DataFrame(rows)
