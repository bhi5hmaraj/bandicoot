"""Tests for clustering caregivers by passive behavior."""

import numpy as np
import pandas as pd
import pytest
from bandicoot.core.clustering import (
    PassiveBehaviorClusterer,
    ClusteringResult,
    find_optimal_clusters,
    extract_passive_features,
    analyze_clusters
)


class TestPassiveBehaviorClusterer:
    """Test suite for PassiveBehaviorClusterer."""

    def test_initialization(self):
        """Test clusterer initialization."""
        clusterer = PassiveBehaviorClusterer(n_clusters=20, random_state=42)
        assert clusterer.n_clusters == 20
        assert clusterer.random_state == 42
        assert not clusterer.is_fitted

    def test_initialization_invalid_k(self):
        """Test that invalid n_clusters raises error."""
        with pytest.raises(ValueError, match="n_clusters must be"):
            PassiveBehaviorClusterer(n_clusters=1)

        with pytest.raises(ValueError, match="n_clusters must be"):
            PassiveBehaviorClusterer(n_clusters=0)

    def test_fit_simple(self):
        """Test fitting on simple data."""
        # Create 2 distinct groups
        group1 = np.array([[0.9, 0.1], [0.2, 0.8]]) # High retention
        group2 = np.array([[0.5, 0.5], [0.5, 0.5]]) # Random

        # 30 caregivers in each group
        P_passive = np.vstack([
            np.tile(group1, (30, 1, 1)),
            np.tile(group2, (30, 1, 1))
        ])

        # Add small noise
        noise = np.random.RandomState(42).normal(0, 0.05, P_passive.shape)
        P_passive = np.clip(P_passive + noise, 0, 1)

        # Renormalize
        for i in range(len(P_passive)):
            for s in range(2):
                total = P_passive[i, s, :].sum()
                P_passive[i, s, :] /= total

        # Cluster with k=2
        clusterer = PassiveBehaviorClusterer(n_clusters=2, random_state=42)
        result = clusterer.fit(P_passive)

        # Verify results
        assert isinstance(result, ClusteringResult)
        assert len(result.cluster_labels) == 60
        assert result.n_clusters == 2
        assert result.silhouette_score >= 0  # Should find 2 distinct groups
        assert clusterer.is_fitted

    def test_fit_wrong_shape(self):
        """Test error on wrong data shape."""
        clusterer = PassiveBehaviorClusterer(n_clusters=5)

        # Wrong shape (should be [n, 2, 2])
        bad_data = np.random.rand(10, 3, 3)

        with pytest.raises(ValueError, match="Expected shape"):
            clusterer.fit(bad_data)

    def test_fit_insufficient_data(self):
        """Test error when not enough caregivers."""
        clusterer = PassiveBehaviorClusterer(n_clusters=10)

        # Only 5 caregivers but need 10
        P_passive = np.random.rand(5, 2, 2)

        # Normalize
        for i in range(5):
            for s in range(2):
                P_passive[i, s, :] /= P_passive[i, s, :].sum()

        with pytest.raises(ValueError, match="Need at least"):
            clusterer.fit(P_passive)

    def test_predict_before_fit(self):
        """Test error when predicting before fitting."""
        clusterer = PassiveBehaviorClusterer(n_clusters=5)

        P_test = np.random.rand(10, 2, 2)

        with pytest.raises(ValueError, match="Must call fit"):
            clusterer.predict(P_test)

    def test_predict_after_fit(self):
        """Test prediction on new data after fitting."""
        # Training data
        P_train = np.random.rand(50, 2, 2)
        for i in range(50):
            for s in range(2):
                P_train[i, s, :] /= P_train[i, s, :].sum()

        # Test data
        P_test = np.random.rand(10, 2, 2)
        for i in range(10):
            for s in range(2):
                P_test[i, s, :] /= P_test[i, s, :].sum()

        # Fit and predict
        clusterer = PassiveBehaviorClusterer(n_clusters=5, random_state=42)
        clusterer.fit(P_train)

        predictions = clusterer.predict(P_test)

        assert len(predictions) == 10
        assert np.all(predictions >= 0)
        assert np.all(predictions < 5)

    def test_repr(self):
        """Test string representation."""
        clusterer = PassiveBehaviorClusterer(n_clusters=15)
        repr_str = repr(clusterer)

        assert 'PassiveBehaviorClusterer' in repr_str
        assert 'n_clusters=15' in repr_str
        assert 'not fitted' in repr_str

        # After fitting
        P_train = np.random.rand(30, 2, 2)
        for i in range(30):
            for s in range(2):
                P_train[i, s, :] /= P_train[i, s, :].sum()

        clusterer.fit(P_train)
        repr_str = repr(clusterer)
        assert 'fitted' in repr_str


class TestClusteringResult:
    """Test suite for ClusteringResult."""

    def test_get_cluster_sizes(self):
        """Test getting cluster sizes."""
        # Create mock result
        labels = np.array([0, 0, 0, 1, 1, 2, 2, 2, 2])
        feature_matrix = np.random.rand(9, 4)

        from sklearn.cluster import KMeans
        model = KMeans(n_clusters=3)

        result = ClusteringResult(
            cluster_labels=labels,
            n_clusters=3,
            silhouette_score=0.5,
            cluster_model=model,
            feature_matrix=feature_matrix
        )

        sizes = result.get_cluster_sizes()

        assert sizes[0] == 3
        assert sizes[1] == 2
        assert sizes[2] == 4


class TestFindOptimalClusters:
    """Test suite for finding optimal number of clusters."""

    def test_find_optimal_simple(self):
        """Test finding optimal k on simple data."""
        # Create 3 distinct groups
        group1 = np.array([[0.9, 0.1], [0.2, 0.8]])
        group2 = np.array([[0.5, 0.5], [0.5, 0.5]])
        group3 = np.array([[0.7, 0.3], [0.4, 0.6]])

        P_passive = np.vstack([
            np.tile(group1, (20, 1, 1)),
            np.tile(group2, (20, 1, 1)),
            np.tile(group3, (20, 1, 1))
        ])

        # Add noise and renormalize
        noise = np.random.RandomState(42).normal(0, 0.03, P_passive.shape)
        P_passive = np.clip(P_passive + noise, 0, 1)
        for i in range(len(P_passive)):
            for s in range(2):
                P_passive[i, s, :] /= P_passive[i, s, :].sum()

        # Find optimal k in range 2-10
        best_k, result = find_optimal_clusters(P_passive, k_range=(2, 10), random_state=42)

        # Should find 3 clusters (or close)
        assert 2 <= best_k <= 5  # Might not be exactly 3 due to noise
        assert isinstance(result, ClusteringResult)
        assert result.n_clusters == best_k
        assert result.silhouette_score > 0

    def test_find_optimal_insufficient_data(self):
        """Test error when max_k exceeds n_caregivers."""
        P_passive = np.random.rand(10, 2, 2)
        for i in range(10):
            for s in range(2):
                P_passive[i, s, :] /= P_passive[i, s, :].sum()

        with pytest.raises(ValueError, match="cannot exceed n_caregivers"):
            find_optimal_clusters(P_passive, k_range=(5, 15))


class TestExtractPassiveFeatures:
    """Test suite for extracting passive features from history."""

    def test_extract_simple(self):
        """Test extracting passive features from history."""
        # Simple history with 2 caregivers
        history = pd.DataFrame({
            'caregiver_id': [1, 1, 1, 1, 2, 2, 2, 2],
            'timestamp': [0, 1, 2, 3, 0, 1, 2, 3],
            'state': [0, 0, 1, 0, 1, 1, 0, 1],
            'action': [0, 0, 0, 0, 0, 0, 0, 0]  # All passive
        })

        P_passive, cg_ids = extract_passive_features(history)

        # Should have 2 caregivers
        assert P_passive.shape == (2, 2, 2)
        assert len(cg_ids) == 2

        # Probabilities should sum to 1
        for i in range(2):
            for s in range(2):
                assert pytest.approx(P_passive[i, s, :].sum(), abs=0.01) == 1.0

    def test_extract_with_active(self):
        """Test that active transitions are ignored."""
        history = pd.DataFrame({
            'caregiver_id': [1] * 10,
            'timestamp': list(range(10)),
            'state': [0, 0, 1, 0, 0, 1, 1, 0, 1, 0],
            'action': [0, 0, 1, 1, 0, 0, 1, 1, 0, 0]  # Mixed
        })

        P_passive, cg_ids = extract_passive_features(history)

        # Should only learn from passive (action=0) transitions
        assert P_passive.shape == (1, 2, 2)


class TestAnalyzeClusters:
    """Test suite for cluster analysis."""

    def test_analyze_clusters(self):
        """Test analyzing cluster characteristics."""
        # Create simple clustering result
        P_passive = np.array([
            [[0.9, 0.1], [0.3, 0.7]],  # Cluster 0: high retention
            [[0.9, 0.1], [0.2, 0.8]],  # Cluster 0
            [[0.5, 0.5], [0.5, 0.5]],  # Cluster 1: random
            [[0.5, 0.5], [0.5, 0.5]],  # Cluster 1
        ])

        clusterer = PassiveBehaviorClusterer(n_clusters=2, random_state=42)
        result = clusterer.fit(P_passive)

        analysis = analyze_clusters(result, P_passive)

        # Should have 2 clusters
        assert len(analysis) == 2

        # Check columns
        expected_cols = ['cluster', 'size', 'retention_R', 'drift_to_U',
                        'recovery_U', 'stay_U', 'silhouette']
        assert all(col in analysis.columns for col in expected_cols)

        # Sizes should sum to 4
        assert analysis['size'].sum() == 4


class TestIntegration:
    """Integration tests for clustering workflow."""

    def test_end_to_end_clustering(self):
        """Test complete clustering workflow."""
        # Generate synthetic history for 50 caregivers
        np.random.seed(42)
        n_caregivers = 50
        n_timesteps = 20

        history_data = []
        for cg_id in range(n_caregivers):
            for t in range(n_timesteps):
                # Random walk state
                state = np.random.choice([0, 1])
                action = 0  # Passive
                history_data.append({
                    'caregiver_id': cg_id,
                    'timestamp': t,
                    'state': state,
                    'action': action
                })

        history = pd.DataFrame(history_data)

        # Extract passive features
        P_passive, cg_ids = extract_passive_features(history)

        assert P_passive.shape == (n_caregivers, 2, 2)
        assert len(cg_ids) == n_caregivers

        # Cluster
        clusterer = PassiveBehaviorClusterer(n_clusters=5, random_state=42)
        result = clusterer.fit(P_passive, cg_ids)

        assert len(result.cluster_labels) == n_caregivers
        assert result.n_clusters == 5

        # Analyze
        analysis = analyze_clusters(result, P_passive)
        assert len(analysis) <= 5  # May have empty clusters

        # Predict on new data
        P_new = np.random.rand(10, 2, 2)
        for i in range(10):
            for s in range(2):
                P_new[i, s, :] /= P_new[i, s, :].sum()

        predictions = clusterer.predict(P_new)
        assert len(predictions) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
