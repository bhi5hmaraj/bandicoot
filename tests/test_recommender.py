"""Tests for RMAB recommender system."""

import numpy as np
import pandas as pd
import pytest
from bandicoot.core.recommender import BandicootRMAB, RecommenderResult


class TestBandicootRMAB:
    """Test suite for BandicootRMAB recommender."""

    def test_initialization(self):
        """Test recommender initialization."""
        recommender = BandicootRMAB(n_clusters=20, gamma=0.99, random_state=42)
        assert recommender.n_clusters == 20
        assert recommender.gamma == 0.99
        assert not recommender.is_fitted

    def test_initialization_invalid_n_clusters(self):
        """Test that invalid n_clusters raises error."""
        with pytest.raises(ValueError, match="n_clusters must be"):
            BandicootRMAB(n_clusters=1)

        with pytest.raises(ValueError, match="n_clusters must be"):
            BandicootRMAB(n_clusters=0)

    def test_initialization_invalid_gamma(self):
        """Test that invalid gamma raises error."""
        with pytest.raises(ValueError, match="gamma must be"):
            BandicootRMAB(gamma=0.0)

        with pytest.raises(ValueError, match="gamma must be"):
            BandicootRMAB(gamma=1.0)

        with pytest.raises(ValueError, match="gamma must be"):
            BandicootRMAB(gamma=1.5)

    def test_initialization_invalid_alpha(self):
        """Test that invalid alpha raises error."""
        with pytest.raises(ValueError, match="alpha must be"):
            BandicootRMAB(alpha=0.0)

        with pytest.raises(ValueError, match="alpha must be"):
            BandicootRMAB(alpha=-1.0)

    def test_fit_simple_data(self):
        """Test fitting on simple synthetic data."""
        # Generate simple history
        np.random.seed(42)
        n_caregivers = 30
        n_timesteps = 20

        history_data = []
        for cg_id in range(n_caregivers):
            for t in range(n_timesteps):
                state = np.random.choice([0, 1])
                action = np.random.choice([0, 1])
                history_data.append({
                    'caregiver_id': cg_id,
                    'timestamp': t,
                    'state': state,
                    'action': action
                })

        history = pd.DataFrame(history_data)

        # Fit recommender
        recommender = BandicootRMAB(n_clusters=3, gamma=0.99, random_state=42)
        result = recommender.fit(history, verbose=False)

        # Check that fit returns self
        assert result is recommender

        # Check that recommender is now fitted
        assert recommender.is_fitted

    def test_recommend_before_fit(self):
        """Test that recommending before fit raises error."""
        recommender = BandicootRMAB(n_clusters=5)

        states = np.array([0, 1, 0, 1, 0])

        with pytest.raises(ValueError, match="Must call fit"):
            recommender.recommend(states, budget=2)

    def test_recommend_after_fit(self):
        """Test recommendation after fitting."""
        # Generate history
        np.random.seed(42)
        n_caregivers = 50
        n_timesteps = 20

        history_data = []
        for cg_id in range(n_caregivers):
            for t in range(n_timesteps):
                state = np.random.choice([0, 1])
                action = np.random.choice([0, 1])
                history_data.append({
                    'caregiver_id': cg_id,
                    'timestamp': t,
                    'state': state,
                    'action': action
                })

        history = pd.DataFrame(history_data)

        # Fit
        recommender = BandicootRMAB(n_clusters=5, gamma=0.99, random_state=42)
        recommender.fit(history, verbose=False)

        # Generate recommendations
        current_states = np.random.choice([0, 1], size=n_caregivers)
        budget = 10

        result = recommender.recommend(current_states, budget=budget)

        # Check result
        assert isinstance(result, RecommenderResult)
        assert len(result.recommended_ids) == budget
        assert len(result.priorities) == budget
        assert len(result.all_priorities) == n_caregivers
        assert result.budget_used == budget

        # Check that recommended IDs are valid
        assert np.all(result.recommended_ids >= 0)
        assert np.all(result.recommended_ids < n_caregivers)

        # Check that priorities are sorted descending
        assert np.all(result.priorities[:-1] >= result.priorities[1:])

    def test_recommend_with_custom_ids(self):
        """Test recommendation with custom caregiver IDs."""
        # Generate history with custom IDs
        np.random.seed(42)
        custom_ids = [100, 200, 300, 400, 500]
        n_timesteps = 20

        history_data = []
        for cg_id in custom_ids:
            for t in range(n_timesteps):
                state = np.random.choice([0, 1])
                action = np.random.choice([0, 1])
                history_data.append({
                    'caregiver_id': cg_id,
                    'timestamp': t,
                    'state': state,
                    'action': action
                })

        history = pd.DataFrame(history_data)

        # Fit
        recommender = BandicootRMAB(n_clusters=2, gamma=0.99, random_state=42)
        recommender.fit(history, verbose=False)

        # Recommend with custom IDs
        current_states = np.array([0, 1, 0, 1, 0])
        caregiver_ids = np.array(custom_ids)

        result = recommender.recommend(current_states, budget=3, caregiver_ids=caregiver_ids)

        # Check that recommended IDs are from custom IDs
        assert np.all(np.isin(result.recommended_ids, custom_ids))

    def test_recommend_budget_exceeds_caregivers(self):
        """Test that budget is capped at number of caregivers."""
        # Generate small history
        np.random.seed(42)
        n_caregivers = 5
        n_timesteps = 20

        history_data = []
        for cg_id in range(n_caregivers):
            for t in range(n_timesteps):
                state = np.random.choice([0, 1])
                action = np.random.choice([0, 1])
                history_data.append({
                    'caregiver_id': cg_id,
                    'timestamp': t,
                    'state': state,
                    'action': action
                })

        history = pd.DataFrame(history_data)

        # Fit
        recommender = BandicootRMAB(n_clusters=2, gamma=0.99, random_state=42)
        recommender.fit(history, verbose=False)

        # Request budget > n_caregivers
        current_states = np.array([0, 1, 0, 1, 0])
        result = recommender.recommend(current_states, budget=100)

        # Should only recommend all 5 caregivers
        assert len(result.recommended_ids) == n_caregivers
        assert result.budget_used == n_caregivers

    def test_recommend_invalid_states(self):
        """Test that invalid states raise error."""
        # Generate and fit
        np.random.seed(42)
        history = self._generate_history(n_caregivers=10, n_timesteps=20)

        recommender = BandicootRMAB(n_clusters=2, gamma=0.99, random_state=42)
        recommender.fit(history, verbose=False)

        # Invalid state values
        invalid_states = np.array([0, 1, 2, 0, 1])  # 2 is invalid

        with pytest.raises(ValueError, match="States must be"):
            recommender.recommend(invalid_states, budget=2)

    def test_recommend_invalid_budget(self):
        """Test that invalid budget raises error."""
        # Generate and fit
        np.random.seed(42)
        history = self._generate_history(n_caregivers=10, n_timesteps=20)

        recommender = BandicootRMAB(n_clusters=2, gamma=0.99, random_state=42)
        recommender.fit(history, verbose=False)

        states = np.array([0, 1, 0, 1, 0])

        with pytest.raises(ValueError, match="Budget must be positive"):
            recommender.recommend(states, budget=0)

        with pytest.raises(ValueError, match="Budget must be positive"):
            recommender.recommend(states, budget=-1)

    def test_recommend_length_mismatch(self):
        """Test that length mismatch raises error."""
        # Generate and fit
        np.random.seed(42)
        history = self._generate_history(n_caregivers=10, n_timesteps=20)

        recommender = BandicootRMAB(n_clusters=2, gamma=0.99, random_state=42)
        recommender.fit(history, verbose=False)

        states = np.array([0, 1, 0, 1, 0])
        caregiver_ids = np.array([0, 1, 2])  # Wrong length

        with pytest.raises(ValueError, match="Length mismatch"):
            recommender.recommend(states, budget=2, caregiver_ids=caregiver_ids)

    def test_predict_cluster_before_fit(self):
        """Test that predicting cluster before fit raises error."""
        recommender = BandicootRMAB(n_clusters=5)

        with pytest.raises(ValueError, match="Must call fit"):
            recommender.predict_cluster(1)

    def test_predict_cluster_after_fit(self):
        """Test cluster prediction after fitting."""
        # Generate and fit
        np.random.seed(42)
        history = self._generate_history(n_caregivers=20, n_timesteps=20)

        recommender = BandicootRMAB(n_clusters=3, gamma=0.99, random_state=42)
        recommender.fit(history, verbose=False)

        # Predict cluster for known caregiver
        cluster = recommender.predict_cluster(5)
        assert cluster is not None
        assert 0 <= cluster < 3

        # Predict cluster for unknown caregiver
        cluster_unknown = recommender.predict_cluster(9999)
        assert cluster_unknown is None

    def test_predict_cluster_for_transitions(self):
        """Test cluster prediction for new caregivers."""
        # Generate and fit
        np.random.seed(42)
        history = self._generate_history(n_caregivers=30, n_timesteps=20)

        recommender = BandicootRMAB(n_clusters=5, gamma=0.99, random_state=42)
        recommender.fit(history, verbose=False)

        # Generate new passive transitions
        P_new = np.random.rand(10, 2, 2)
        for i in range(10):
            for s in range(2):
                P_new[i, s, :] /= P_new[i, s, :].sum()

        # Predict clusters
        cluster_labels = recommender.predict_cluster_for_transitions(P_new)

        assert len(cluster_labels) == 10
        assert np.all(cluster_labels >= 0)
        assert np.all(cluster_labels < 5)

    def test_get_cluster_summary_before_fit(self):
        """Test that getting cluster summary before fit raises error."""
        recommender = BandicootRMAB(n_clusters=5)

        with pytest.raises(ValueError, match="Must call fit"):
            recommender.get_cluster_summary()

    def test_get_cluster_summary_after_fit(self):
        """Test cluster summary after fitting."""
        # Generate and fit
        np.random.seed(42)
        history = self._generate_history(n_caregivers=50, n_timesteps=20)

        recommender = BandicootRMAB(n_clusters=5, gamma=0.99, random_state=42)
        recommender.fit(history, verbose=False)

        summary = recommender.get_cluster_summary()

        # Check DataFrame structure
        assert isinstance(summary, pd.DataFrame)
        expected_cols = ['cluster', 'n_caregivers', 'w_responsive', 'w_unresponsive',
                        'retention_R', 'recovery_U']
        assert all(col in summary.columns for col in expected_cols)

        # Check that clusters are represented
        assert len(summary) > 0
        assert len(summary) <= 5

        # Check that caregiver counts sum correctly
        total_caregivers = summary['n_caregivers'].sum()
        assert total_caregivers == 50

    def test_repr_before_fit(self):
        """Test string representation before fit."""
        recommender = BandicootRMAB(n_clusters=10, gamma=0.95)
        repr_str = repr(recommender)

        assert 'BandicootRMAB' in repr_str
        assert 'n_clusters=10' in repr_str
        assert 'gamma=0.95' in repr_str
        assert 'not fitted' in repr_str

    def test_repr_after_fit(self):
        """Test string representation after fit."""
        # Generate and fit
        np.random.seed(42)
        history = self._generate_history(n_caregivers=25, n_timesteps=20)

        recommender = BandicootRMAB(n_clusters=5, gamma=0.99, random_state=42)
        recommender.fit(history, verbose=False)

        repr_str = repr(recommender)

        assert 'BandicootRMAB' in repr_str
        assert 'fitted on 25 caregivers' in repr_str

    # Helper methods

    def _generate_history(self, n_caregivers: int, n_timesteps: int) -> pd.DataFrame:
        """Generate simple random history for testing."""
        history_data = []
        for cg_id in range(n_caregivers):
            for t in range(n_timesteps):
                state = np.random.choice([0, 1])
                action = np.random.choice([0, 1])
                history_data.append({
                    'caregiver_id': cg_id,
                    'timestamp': t,
                    'state': state,
                    'action': action
                })

        return pd.DataFrame(history_data)


class TestRecommenderIntegration:
    """Integration tests for end-to-end recommender workflow."""

    def test_end_to_end_workflow(self):
        """Test complete workflow from history to recommendations."""
        # Generate realistic history with distinct groups
        np.random.seed(42)

        # Group 1: High retention (stay engaged)
        history_g1 = self._generate_group_history(
            caregiver_ids=range(0, 20),
            n_timesteps=30,
            p_stay_responsive=0.9,
            p_recover=0.4
        )

        # Group 2: Low retention (drift away)
        history_g2 = self._generate_group_history(
            caregiver_ids=range(20, 40),
            n_timesteps=30,
            p_stay_responsive=0.5,
            p_recover=0.2
        )

        # Combine
        history = pd.concat([history_g1, history_g2], ignore_index=True)

        # Fit recommender
        recommender = BandicootRMAB(n_clusters=2, gamma=0.99, random_state=42)
        recommender.fit(history, verbose=True)

        # Current states: mix of responsive and unresponsive
        current_states = np.array([0] * 20 + [1] * 20)

        # Generate recommendations
        result = recommender.recommend(current_states, budget=10)

        # Verify result
        assert len(result.recommended_ids) == 10
        assert result.budget_used == 10

        # Check that priorities make sense (unresponsive should have higher priority)
        # Get priorities for unresponsive caregivers
        unresponsive_mask = current_states == 1
        avg_priority_unresponsive = result.all_priorities[unresponsive_mask].mean()

        # Get priorities for responsive caregivers
        responsive_mask = current_states == 0
        avg_priority_responsive = result.all_priorities[responsive_mask].mean()

        # Unresponsive should generally have higher priority
        assert avg_priority_unresponsive > avg_priority_responsive

        # Get cluster summary
        summary = recommender.get_cluster_summary()
        assert len(summary) == 2

    def test_new_caregiver_assignment(self):
        """Test assigning new caregivers to clusters."""
        # Generate training history
        np.random.seed(42)
        history = self._generate_group_history(
            caregiver_ids=range(0, 30),
            n_timesteps=20,
            p_stay_responsive=0.8,
            p_recover=0.3
        )

        # Fit
        recommender = BandicootRMAB(n_clusters=3, gamma=0.99, random_state=42)
        recommender.fit(history, verbose=False)

        # New caregiver passive transitions
        P_new = np.array([
            [[0.85, 0.15],
             [0.35, 0.65]]
        ])

        # Predict cluster
        cluster_labels = recommender.predict_cluster_for_transitions(P_new)
        assert len(cluster_labels) == 1
        assert 0 <= cluster_labels[0] < 3

    # Helper methods

    def _generate_group_history(
        self,
        caregiver_ids,
        n_timesteps: int,
        p_stay_responsive: float,
        p_recover: float
    ) -> pd.DataFrame:
        """Generate history for a caregiver group with specific transition probabilities."""
        history_data = []

        for cg_id in caregiver_ids:
            state = 0  # Start responsive
            for t in range(n_timesteps):
                # Record current state
                action = np.random.choice([0, 1])
                history_data.append({
                    'caregiver_id': cg_id,
                    'timestamp': t,
                    'state': state,
                    'action': action
                })

                # Transition (using passive dynamics)
                if action == 0:
                    if state == 0:
                        # Responsive -> ?
                        state = 0 if np.random.rand() < p_stay_responsive else 1
                    else:
                        # Unresponsive -> ?
                        state = 0 if np.random.rand() < p_recover else 1
                else:
                    # Active intervention: boost recovery
                    if state == 1:
                        state = 0 if np.random.rand() < (p_recover + 0.3) else 1

        return pd.DataFrame(history_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
