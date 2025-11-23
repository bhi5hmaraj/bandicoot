"""
Integration tests for Bandicoot RMAB API.

Tests the full API workflow with synthetic data.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestAPIIntegration:
    """Test full API workflow."""

    def test_root_endpoint(self):
        """Test root endpoint returns service info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert data["status"] == "running"

    def test_health_check_before_training(self):
        """Test health endpoint before model is trained."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["model_loaded"] == False  # Not yet trained

    def test_recommend_before_training(self):
        """Test that recommend fails gracefully when model not trained."""
        response = client.post("/api/v1/recommend", json={"budget": 10})
        assert response.status_code == 400
        assert "not fitted" in response.json()["detail"].lower()

    def test_train_clusters(self):
        """Test training endpoint with synthetic data."""
        response = client.post(
            "/api/v1/train_clusters",
            json={"n_clusters": 5, "min_observations": 5}
        )
        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert data["status"] == "success"
        assert data["n_clusters"] == 5
        assert data["n_caregivers"] > 0
        assert "clusters" in data
        assert len(data["clusters"]) <= 5  # May have empty clusters

        # Verify cluster summaries
        for cluster in data["clusters"]:
            assert "cluster_id" in cluster
            assert "n_caregivers" in cluster
            assert "w_responsive" in cluster
            assert "w_unresponsive" in cluster

    def test_health_check_after_training(self):
        """Test health endpoint after model is trained."""
        # First train
        client.post("/api/v1/train_clusters", json={"n_clusters": 3})

        # Then check health
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["model_loaded"] == True  # Now trained

    def test_recommend_after_training(self):
        """Test recommendation endpoint after training."""
        # First train
        client.post("/api/v1/train_clusters", json={"n_clusters": 5})

        # Then get recommendations
        response = client.post(
            "/api/v1/recommend",
            json={"budget": 10}
        )
        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "recommendations" in data
        assert "metadata" in data

        recommendations = data["recommendations"]
        assert len(recommendations) == 10

        # Verify recommendation structure
        for rec in recommendations:
            assert "caregiver_id" in rec
            assert "priority_score" in rec
            assert "current_state" in rec
            assert rec["current_state"] in ["Responsive", "Unresponsive"]
            assert "cluster_id" in rec
            assert "reason" in rec

        # Verify metadata
        metadata = data["metadata"]
        assert metadata["budget"] == 10
        assert metadata["total_evaluated"] > 0
        assert "generated_at" in metadata
        assert "model_version" in metadata

        # Verify recommendations are sorted by priority (descending)
        priorities = [rec["priority_score"] for rec in recommendations]
        assert priorities == sorted(priorities, reverse=True)

    def test_recommend_custom_budget(self):
        """Test recommendation with different budget sizes."""
        # Train first
        client.post("/api/v1/train_clusters", json={"n_clusters": 3})

        # Test different budgets
        for budget in [5, 20, 50]:
            response = client.post(
                "/api/v1/recommend",
                json={"budget": budget}
            )
            assert response.status_code == 200
            data = response.json()
            # Budget may be capped by available caregivers
            assert len(data["recommendations"]) <= budget
            assert data["metadata"]["budget"] <= budget

    def test_precompute_indices(self):
        """Test precompute indices endpoint."""
        # Train first
        client.post("/api/v1/train_clusters", json={"n_clusters": 3})

        # Precompute indices
        response = client.post("/api/v1/precompute_indices")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["n_clusters"] > 0
        assert data["indices_computed"] > 0
        assert "computed_at" in data

    def test_update_state(self):
        """Test state update endpoint."""
        response = client.post(
            "/api/v1/update_state",
            json={
                "updates": [
                    {"caregiver_id": "CG-001", "state": 0},
                    {"caregiver_id": "CG-002", "state": 1}
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()

        assert data["status"] in ["success", "partial_success"]
        assert data["updated_count"] == 2
        assert data["failed_count"] == 0

    def test_update_state_invalid(self):
        """Test state update with invalid data."""
        response = client.post(
            "/api/v1/update_state",
            json={
                "updates": [
                    {"caregiver_id": "CG-001", "state": 2},  # Invalid state
                    {"caregiver_id": "CG-002"},  # Missing state
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "partial_success"
        assert data["failed_count"] == 2
        assert data["errors"] is not None


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow."""

    def test_complete_workflow(self):
        """Test the complete workflow from training to recommendations."""
        # Step 1: Check health (should be healthy but not trained)
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["model_loaded"] == False

        # Step 2: Train model
        train_response = client.post(
            "/api/v1/train_clusters",
            json={"n_clusters": 5}
        )
        assert train_response.status_code == 200
        training_data = train_response.json()
        print(f"\nTraining complete: {training_data['n_caregivers']} caregivers, "
              f"{training_data['n_clusters']} clusters")

        # Step 3: Check health (now trained)
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["model_loaded"] == True

        # Step 4: Precompute indices (already done during training, but test endpoint)
        indices_response = client.post("/api/v1/precompute_indices")
        assert indices_response.status_code == 200
        print(f"Indices computed: {indices_response.json()['indices_computed']}")

        # Step 5: Get recommendations
        recommend_response = client.post(
            "/api/v1/recommend",
            json={"budget": 20}
        )
        assert recommend_response.status_code == 200
        recommendations = recommend_response.json()

        print(f"\nGenerated {len(recommendations['recommendations'])} recommendations")
        print(f"Top 3 priorities:")
        for i, rec in enumerate(recommendations['recommendations'][:3], 1):
            print(f"  {i}. {rec['caregiver_id']}: {rec['priority_score']:.4f} "
                  f"({rec['current_state']}, cluster {rec['cluster_id']})")

        # Verify all recommendations are valid
        assert len(recommendations['recommendations']) == 20
        # Whittle indices can be negative or positive, just check they're finite
        assert all(
            -10 <= rec['priority_score'] <= 10  # Reasonable range for Whittle indices
            for rec in recommendations['recommendations']
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
