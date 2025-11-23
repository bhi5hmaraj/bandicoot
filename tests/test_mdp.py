"""Tests for MDP parameter learning."""

import numpy as np
import pandas as pd
import pytest
from bandicoot.core.mdp import (
    TransitionLearner,
    extract_transitions_from_history,
    estimate_passive_transitions
)


class TestTransitionLearner:
    """Test suite for TransitionLearner."""

    def test_initialization(self):
        """Test learner initialization."""
        learner = TransitionLearner(alpha=1.0, min_observations=10)
        assert learner.alpha == 1.0
        assert learner.min_observations == 10
        assert learner.counts.shape == (2, 2, 2)
        assert np.all(learner.counts == 0)

    def test_initialization_invalid_alpha(self):
        """Test that invalid alpha raises error."""
        with pytest.raises(ValueError, match="Alpha must be positive"):
            TransitionLearner(alpha=0.0)

        with pytest.raises(ValueError, match="Alpha must be positive"):
            TransitionLearner(alpha=-1.0)

    def test_add_transitions_simple(self):
        """Test adding transitions from DataFrame."""
        learner = TransitionLearner()

        # Simple transitions: R→R with passive action
        transitions = pd.DataFrame({
            'state': [0, 0, 0],
            'next_state': [0, 0, 1],
            'action': [0, 0, 0]
        })

        learner.add_transitions(transitions)

        # Check counts
        assert learner.counts[0, 0, 0] == 2  # R→R | passive
        assert learner.counts[0, 1, 0] == 1  # R→U | passive

    def test_add_transitions_missing_columns(self):
        """Test error on missing columns."""
        learner = TransitionLearner()

        bad_df = pd.DataFrame({'state': [0], 'action': [0]})  # missing next_state

        with pytest.raises(ValueError, match="Missing columns"):
            learner.add_transitions(bad_df)

    def test_add_transitions_invalid_values(self):
        """Test error on invalid state/action values."""
        learner = TransitionLearner()

        # Invalid state value (2)
        bad_df = pd.DataFrame({
            'state': [2],
            'next_state': [0],
            'action': [0]
        })

        with pytest.raises(ValueError, match="State values must be"):
            learner.add_transitions(bad_df)

    def test_add_transition_counts(self):
        """Test adding pre-aggregated counts."""
        learner = TransitionLearner()

        counts = np.array([
            [[10, 5], [2, 1]],   # From R
            [[3, 8], [12, 2]]    # From U
        ])

        learner.add_transition_counts(counts)

        assert learner.counts[0, 0, 0] == 10
        assert learner.counts[1, 1, 1] == 2

    def test_estimate_transitions_ml(self):
        """Test maximum likelihood estimation (no prior)."""
        learner = TransitionLearner()

        # Add observations for all (state, action) pairs
        transitions = pd.DataFrame({
            'state': [0, 0, 0, 0, 0, 1, 1, 1, 0, 1],
            'next_state': [0, 0, 0, 0, 1, 0, 1, 1, 0, 1],
            'action': [0, 0, 0, 0, 0, 1, 1, 1, 1, 0]
        })

        learner.add_transitions(transitions)

        # Estimate without prior
        P = learner.estimate_transitions(use_prior=False)

        # Check (R, passive): 4 R→R, 1 R→U
        assert pytest.approx(P[0, 0, 0], abs=0.01) == 4.0/5.0  # P(R→R | passive)
        assert pytest.approx(P[0, 1, 0], abs=0.01) == 1.0/5.0  # P(R→U | passive)

    def test_estimate_transitions_bayesian(self):
        """Test Bayesian estimation with Dirichlet prior."""
        learner = TransitionLearner(alpha=1.0)

        # Add single observation: R→R
        transitions = pd.DataFrame({
            'state': [0],
            'next_state': [0],
            'action': [0]
        })

        learner.add_transitions(transitions)

        # Estimate with prior
        P = learner.estimate_transitions(use_prior=True)

        # With alpha=1 and 1 observation:
        # P(R→R) = (1 + 1) / (1 + 2*1) = 2/3 ≈ 0.667
        # P(R→U) = (0 + 1) / (1 + 2*1) = 1/3 ≈ 0.333

        assert pytest.approx(P[0, 0, 0], abs=0.01) == 2.0/3.0
        assert pytest.approx(P[0, 1, 0], abs=0.01) == 1.0/3.0

    def test_estimate_transitions_no_data(self):
        """Test handling of missing data."""
        learner = TransitionLearner()

        # No observations - with prior should use uniform
        P = learner.estimate_transitions(use_prior=True)

        # All probabilities should be 0.5 (uniform)
        for s in range(2):
            for a in range(2):
                assert P[s, 0, a] == 0.5
                assert P[s, 1, a] == 0.5

    def test_estimate_transitions_no_data_error(self):
        """Test error when no data and no prior."""
        learner = TransitionLearner()

        with pytest.raises(ValueError, match="No observations"):
            learner.estimate_transitions(use_prior=False)

    def test_get_observation_counts(self):
        """Test getting observation counts."""
        learner = TransitionLearner()

        transitions = pd.DataFrame({
            'state': [0, 0, 0, 1, 1],
            'next_state': [0, 0, 1, 0, 1],
            'action': [0, 0, 0, 1, 1]
        })

        learner.add_transitions(transitions)

        counts = learner.get_observation_counts()

        assert counts[(0, 0)] == 3  # 3 observations of (R, passive)
        assert counts[(0, 1)] == 0  # 0 observations of (R, active)
        assert counts[(1, 0)] == 0  # 0 observations of (U, passive)
        assert counts[(1, 1)] == 2  # 2 observations of (U, active)

    def test_get_confidence(self):
        """Test confidence score calculation."""
        learner = TransitionLearner(min_observations=10)

        # Add 5 observations for (R, passive)
        transitions = pd.DataFrame({
            'state': [0] * 5,
            'next_state': [0] * 5,
            'action': [0] * 5
        })

        learner.add_transitions(transitions)

        confidence = learner.get_confidence()

        # 5/10 = 0.5 confidence for (R, passive)
        assert confidence[0, 0] == 0.5

        # 0 observations = 0 confidence for others
        assert confidence[0, 1] == 0.0
        assert confidence[1, 0] == 0.0
        assert confidence[1, 1] == 0.0

    def test_reset(self):
        """Test resetting counts."""
        learner = TransitionLearner()

        transitions = pd.DataFrame({
            'state': [0, 0],
            'next_state': [0, 1],
            'action': [0, 0]
        })

        learner.add_transitions(transitions)
        assert np.any(learner.counts > 0)

        learner.reset()
        assert np.all(learner.counts == 0)

    def test_repr(self):
        """Test string representation."""
        learner = TransitionLearner(alpha=1.5)
        repr_str = repr(learner)

        assert 'TransitionLearner' in repr_str
        assert 'alpha=1.5' in repr_str


class TestTransitionExtraction:
    """Test suite for transition extraction utilities."""

    def test_extract_transitions_from_history(self):
        """Test extracting transitions from time-series data."""
        history = pd.DataFrame({
            'caregiver_id': [1, 1, 1, 2, 2],
            'timestamp': [0, 1, 2, 0, 1],
            'state': [0, 0, 1, 1, 0],
            'action': [0, 1, 1, 0, 1]
        })

        transitions = extract_transitions_from_history(history)

        # Should have 4 transitions (drop last for each caregiver)
        assert len(transitions) == 3  # 2 from cg1, 1 from cg2

        # Check first transition: cg1, s=0, a=0, s'=0
        assert transitions.iloc[0]['caregiver_id'] == 1
        assert transitions.iloc[0]['state'] == 0
        assert transitions.iloc[0]['action'] == 0
        assert transitions.iloc[0]['next_state'] == 0

    def test_extract_transitions_unsorted(self):
        """Test extraction with unsorted data."""
        history = pd.DataFrame({
            'caregiver_id': [1, 2, 1, 2, 1],
            'timestamp': [2, 1, 0, 0, 1],
            'state': [1, 0, 0, 1, 0],
            'action': [1, 1, 0, 0, 1]
        })

        transitions = extract_transitions_from_history(history, sort=True)

        # After sorting, should be in correct order
        assert len(transitions) == 3

        # First cg1 transition should be t=0→t=1
        cg1_trans = transitions[transitions['caregiver_id'] == 1]
        assert cg1_trans.iloc[0]['state'] == 0  # t=0
        assert cg1_trans.iloc[0]['next_state'] == 0  # t=1

    def test_estimate_passive_transitions(self):
        """Test estimating passive transition probabilities."""
        history = pd.DataFrame({
            'caregiver_id': [1] * 10,
            'timestamp': list(range(10)),
            'state': [0, 0, 0, 0, 1, 1, 0, 0, 0, 1],
            'action': [0] * 10  # All passive
        })

        P_passive = estimate_passive_transitions(history)

        # Should be [2, 2] matrix
        assert P_passive.shape == (2, 2)

        # Probabilities should sum to 1 for each state
        assert pytest.approx(P_passive[0, :].sum(), abs=0.01) == 1.0
        assert pytest.approx(P_passive[1, :].sum(), abs=0.01) == 1.0

        # All values should be in [0, 1]
        assert np.all(P_passive >= 0)
        assert np.all(P_passive <= 1)


class TestIntegration:
    """Integration tests for MDP learning."""

    def test_end_to_end_learning(self):
        """Test complete workflow from history to transition probabilities."""
        # Simulate caregiver history
        history = pd.DataFrame({
            'caregiver_id': [1]*20 + [2]*20,
            'timestamp': list(range(20)) * 2,
            'state': ([0]*5 + [1]*5 + [0]*5 + [1]*5) * 2,  # Oscillating
            'action': ([0]*10 + [1]*10) * 2  # First half passive, second active
        })

        # Extract transitions
        transitions = extract_transitions_from_history(history)

        # Learn parameters
        learner = TransitionLearner(alpha=1.0)
        learner.add_transitions(transitions)

        # Estimate probabilities
        P = learner.estimate_transitions(use_prior=True)

        # Basic sanity checks
        assert P.shape == (2, 2, 2)

        # Probabilities sum to 1 for each (state, action)
        for s in range(2):
            for a in range(2):
                assert pytest.approx(P[s, :, a].sum(), abs=0.01) == 1.0

        # All probabilities in [0, 1]
        assert np.all(P >= 0)
        assert np.all(P <= 1)

        # Check confidence
        confidence = learner.get_confidence()
        assert confidence.shape == (2, 2)
        assert np.all(confidence >= 0)
        assert np.all(confidence <= 1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
