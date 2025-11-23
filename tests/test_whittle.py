"""Tests for Whittle index solver."""

import numpy as np
import pytest
from bandicoot.core.whittle import WhittleIndexSolver, compute_whittle_index


class TestWhittleIndexSolver:
    """Test suite for WhittleIndexSolver."""

    def test_initialization(self):
        """Test solver initialization with valid parameters."""
        solver = WhittleIndexSolver(gamma=0.95)
        assert solver.gamma == 0.95
        assert solver.q_convergence_threshold == 1e-5
        assert solver.v_convergence_threshold == 1e-4

    def test_initialization_invalid_gamma(self):
        """Test that invalid gamma raises ValueError."""
        with pytest.raises(ValueError, match="Gamma must be in"):
            WhittleIndexSolver(gamma=1.5)

        with pytest.raises(ValueError, match="Gamma must be in"):
            WhittleIndexSolver(gamma=0.0)

    def test_validate_transition_probs_shape(self):
        """Test validation rejects wrong shape."""
        solver = WhittleIndexSolver()

        # Wrong shape
        invalid_probs = np.ones((3, 3, 2))
        with pytest.raises(ValueError, match="Expected shape"):
            solver._validate_transition_probs(invalid_probs)

    def test_validate_transition_probs_range(self):
        """Test validation rejects probabilities outside [0, 1]."""
        solver = WhittleIndexSolver()

        # Probabilities > 1
        invalid_probs = np.array([
            [[1.5, 0.2], [0.7, 0.3]],
            [[0.6, 0.4], [0.5, 0.5]]
        ])
        with pytest.raises(ValueError, match="must be in"):
            solver._validate_transition_probs(invalid_probs)

        # Negative probabilities
        invalid_probs = np.array([
            [[-0.1, 0.2], [0.7, 0.3]],
            [[0.6, 0.4], [0.5, 0.5]]
        ])
        with pytest.raises(ValueError, match="must be in"):
            solver._validate_transition_probs(invalid_probs)

    def test_validate_transition_probs_sum(self):
        """Test validation rejects probabilities that don't sum to 1."""
        solver = WhittleIndexSolver()

        # Probabilities don't sum to 1
        invalid_probs = np.array([
            [[0.5, 0.2], [0.7, 0.3]],  # sums to 0.7 for state=0, action=0
            [[0.6, 0.4], [0.5, 0.5]]
        ])
        with pytest.raises(ValueError, match="sum to"):
            solver._validate_transition_probs(invalid_probs)

    def test_validate_transition_probs_nan_inf(self):
        """Test validation rejects NaN/Inf values."""
        solver = WhittleIndexSolver()

        # NaN values
        invalid_probs = np.array([
            [[np.nan, 0.2], [0.7, 0.3]],
            [[0.6, 0.4], [0.5, 0.5]]
        ])
        with pytest.raises(ValueError, match="NaN or Inf"):
            solver._validate_transition_probs(invalid_probs)

        # Inf values
        invalid_probs = np.array([
            [[np.inf, 0.2], [0.7, 0.3]],
            [[0.6, 0.4], [0.5, 0.5]]
        ])
        with pytest.raises(ValueError, match="NaN or Inf"):
            solver._validate_transition_probs(invalid_probs)

    def test_get_reward(self):
        """Test reward function."""
        # Responsive state (0) gives +1
        assert WhittleIndexSolver._get_reward(0, 0, subsidy=0.5) == 1.5  # state + subsidy
        assert WhittleIndexSolver._get_reward(0, 1, subsidy=0.5) == 1.0  # state only

        # Unresponsive state (1) gives -1
        assert WhittleIndexSolver._get_reward(1, 0, subsidy=0.5) == -0.5  # state + subsidy
        assert WhittleIndexSolver._get_reward(1, 1, subsidy=0.5) == -1.0  # state only

    def test_compute_indices_deterministic(self):
        """Test Whittle index computation with deterministic transitions."""
        solver = WhittleIndexSolver(gamma=0.99)

        # Deterministic: R always stays R, U always stays U
        # P[state, next_state, action]
        P = np.array([
            # From Responsive (state 0)
            [[1.0, 1.0],   # to R (next_state 0): passive, active
             [0.0, 0.0]],  # to U (next_state 1): passive, active
            # From Unresponsive (state 1)
            [[0.0, 0.0],   # to R (next_state 0): passive, active
             [1.0, 1.0]]   # to U (next_state 1): passive, active
        ])

        w_r, w_u = solver.compute_indices(P)

        # With deterministic transitions and no state changes,
        # Whittle indices should reflect the infinite horizon value difference
        assert isinstance(w_r, float)
        assert isinstance(w_u, float)
        assert not np.isnan(w_r) and not np.isnan(w_u)
        assert not np.isinf(w_r) and not np.isinf(w_u)

    def test_compute_indices_stochastic(self):
        """Test Whittle index computation with stochastic transitions."""
        solver = WhittleIndexSolver(gamma=0.99)

        # Realistic probabilities: passive drift, active recovery
        # P[state, next_state, action]
        P = np.array([
            # From Responsive (state 0)
            [[0.8, 0.9],   # to R (next_state 0): passive, active
             [0.2, 0.1]],  # to U (next_state 1): passive, active
            # From Unresponsive (state 1)
            [[0.3, 0.6],   # to R (next_state 0): passive, active
             [0.7, 0.4]]   # to U (next_state 1): passive, active
        ])

        w_r, w_u = solver.compute_indices(P)

        # Sanity checks
        assert isinstance(w_r, float)
        assert isinstance(w_u, float)
        assert not np.isnan(w_r) and not np.isnan(w_u)
        assert not np.isinf(w_r) and not np.isinf(w_u)

        # Whittle index for Unresponsive should be higher
        # (higher priority to intervene)
        assert w_u > w_r, f"Expected W(U) > W(R), got W(U)={w_u}, W(R)={w_r}"

    def test_compute_indices_consistency(self):
        """Test that indices are consistent across multiple runs."""
        P = np.array([
            [[0.7, 0.8],   # From R to R: passive, active
             [0.3, 0.2]],  # From R to U: passive, active
            [[0.4, 0.5],   # From U to R: passive, active
             [0.6, 0.5]]   # From U to U: passive, active
        ])

        solver = WhittleIndexSolver(gamma=0.99)

        # Run multiple times
        results = [solver.compute_indices(P) for _ in range(5)]

        # All results should be identical
        for i in range(1, len(results)):
            np.testing.assert_allclose(results[i], results[0], rtol=1e-10)

    def test_convenience_function(self):
        """Test the convenience function."""
        P = np.array([
            [[0.8, 0.9],   # From R to R: passive, active
             [0.2, 0.1]],  # From R to U: passive, active
            [[0.3, 0.6],   # From U to R: passive, active
             [0.7, 0.4]]   # From U to U: passive, active
        ])

        w_r, w_u = compute_whittle_index(P, gamma=0.95)

        assert isinstance(w_r, float)
        assert isinstance(w_u, float)
        assert not np.isnan(w_r) and not np.isnan(w_u)

    def test_different_gammas(self):
        """Test that different gamma values produce different indices."""
        P = np.array([
            [[0.8, 0.9],   # From R to R: passive, active
             [0.2, 0.1]],  # From R to U: passive, active
            [[0.3, 0.6],   # From U to R: passive, active
             [0.7, 0.4]]   # From U to U: passive, active
        ])

        w_r_99, w_u_99 = compute_whittle_index(P, gamma=0.99)
        w_r_90, w_u_90 = compute_whittle_index(P, gamma=0.90)

        # Different gammas should give different indices
        assert w_r_99 != w_r_90
        assert w_u_99 != w_u_90

    def test_extreme_case_always_responsive(self):
        """Test case where intervention always keeps responsive."""
        P = np.array([
            [[0.5, 1.0],   # From R to R: passive, active (active guarantees R)
             [0.5, 0.0]],  # From R to U: passive, active
            [[0.1, 0.8],   # From U to R: passive, active (active helps recovery)
             [0.9, 0.2]]   # From U to U: passive, active
        ])

        w_r, w_u = compute_whittle_index(P, gamma=0.99)

        # Should still prioritize Unresponsive
        assert w_u > w_r


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
