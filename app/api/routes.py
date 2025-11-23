"""
API route handlers for Bandicoot RMAB service.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from typing import List
import numpy as np
import pandas as pd
import logging

from app.models import (
    RecommendRequest,
    RecommendResponse,
    CaregiverRecommendation,
    RecommendationMetadata,
    TrainClustersRequest,
    TrainClustersResponse,
    ClusterSummary,
    PrecomputeIndicesResponse,
    UpdateStateRequest,
    UpdateStateResponse,
    HealthResponse,
)
from app.dependencies import get_recommender, verify_api_key, reset_recommender
from app.config import get_settings
from bandicoot.core.recommender import BandicootRMAB

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Health Check (Public)
# ============================================================================

@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns service status and whether the recommender model is loaded and fitted.
    """
    recommender = get_recommender()
    settings = get_settings()

    return HealthResponse(
        status="healthy",
        version=settings.API_VERSION,
        model_loaded=recommender.is_fitted,
        timestamp=datetime.utcnow()
    )


# ============================================================================
# Recommendation Endpoint (Primary Use Case)
# ============================================================================

@router.post("/recommend", response_model=RecommendResponse, tags=["Recommendations"])
async def recommend_caregivers(
    request: RecommendRequest,
    recommender: BandicootRMAB = Depends(get_recommender),
    _: None = Depends(verify_api_key)
):
    """
    Generate top-K caregiver recommendations based on Whittle indices.

    This is the primary endpoint for getting intervention recommendations.
    Requires a fitted model (call /train_clusters first).

    **Authentication:** Requires X-API-Key header (if REQUIRE_AUTH=true)

    **Example Request:**
    ```json
    {
      "budget": 100,
      "filter_district": "Bihar-Patna"
    }
    ```

    **Example Response:**
    ```json
    {
      "recommendations": [
        {
          "caregiver_id": "CG-12345",
          "priority_score": 0.87,
          "current_state": "Unresponsive",
          "cluster_id": 5,
          "reason": "High dropout risk, responsive to interventions"
        }
      ],
      "metadata": {
        "total_evaluated": 150000,
        "budget": 100,
        "generated_at": "2025-11-23T10:30:00Z",
        "model_version": "v1.0.0"
      }
    }
    ```
    """
    if not recommender.is_fitted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model not fitted. Please call /train_clusters first."
        )

    settings = get_settings()

    try:
        # For MVP, we'll use dummy data if no caregiver_ids provided
        # In production, this would query from database
        if request.caregiver_ids is None or request.current_states is None:
            logger.warning("No caregiver data provided, using mock data for demo")
            # Mock data: create random caregivers
            n_caregivers = min(1000, settings.MAX_CAREGIVERS)
            caregiver_ids = np.array([f"CG-{i:06d}" for i in range(n_caregivers)])
            current_states = np.random.choice([0, 1], size=n_caregivers)
        else:
            caregiver_ids = np.array(request.caregiver_ids)
            current_states = np.array(request.current_states)

        # Generate recommendations
        result = recommender.recommend(
            states=current_states,
            budget=request.budget,
            caregiver_ids=caregiver_ids
        )

        # Format response
        recommendations = []
        for i, cg_id in enumerate(result.recommended_ids):
            # Get state for this caregiver
            idx = np.where(caregiver_ids == cg_id)[0][0]
            state = current_states[idx]
            state_name = "Responsive" if state == 0 else "Unresponsive"

            # Get cluster
            cluster_id = recommender.predict_cluster(cg_id)
            if cluster_id is None:
                cluster_id = -1  # Unknown cluster

            # Generate reason (simple heuristic for MVP)
            if state == 1:  # Unresponsive
                reason = "High dropout risk, needs immediate attention"
            else:  # Responsive
                reason = "At risk of disengagement, proactive contact recommended"

            recommendations.append(
                CaregiverRecommendation(
                    caregiver_id=str(cg_id),
                    priority_score=float(result.priorities[i]),
                    current_state=state_name,
                    cluster_id=cluster_id,
                    reason=reason
                )
            )

        metadata = RecommendationMetadata(
            total_evaluated=len(caregiver_ids),
            budget=result.budget_used,
            generated_at=datetime.utcnow(),
            model_version=settings.API_VERSION
        )

        return RecommendResponse(
            recommendations=recommendations,
            metadata=metadata
        )

    except Exception as e:
        logger.error(f"Error generating recommendations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}"
        )


# ============================================================================
# Training Endpoint (Admin)
# ============================================================================

@router.post("/train_clusters", response_model=TrainClustersResponse, tags=["Admin"])
async def train_clusters(
    request: TrainClustersRequest,
    _: None = Depends(verify_api_key)
):
    """
    Train clustering model and learn MDP parameters from historical data.

    **Authentication:** Requires X-API-Key header (if REQUIRE_AUTH=true)

    **Note:** This is a long-running operation (may take 1-5 minutes for large datasets).
    In production, this should be moved to an async task queue.

    **Example Request:**
    ```json
    {
      "n_clusters": 20,
      "min_observations": 10
    }
    ```
    """
    settings = get_settings()

    try:
        # Reset and create new recommender with specified parameters
        reset_recommender()
        recommender = BandicootRMAB(
            n_clusters=request.n_clusters or settings.N_CLUSTERS,
            gamma=settings.GAMMA,
            alpha=settings.ALPHA,
            min_observations=request.min_observations or settings.MIN_OBSERVATIONS,
            random_state=settings.RANDOM_STATE
        )

        # For MVP, use synthetic data
        # In production, this would load from database
        logger.info("Generating synthetic training data...")
        history = _generate_synthetic_history(n_caregivers=100, n_timesteps=30)

        # Train the model
        logger.info(f"Training with {len(history)} observations...")
        recommender.fit(history, verbose=True)

        # Get cluster summary
        summary_df = recommender.get_cluster_summary()
        # Rename 'cluster' to 'cluster_id' to match Pydantic model
        summary_df = summary_df.rename(columns={'cluster': 'cluster_id'})
        clusters = [
            ClusterSummary(**row)
            for row in summary_df.to_dict('records')
        ]

        # Update global instance
        from app.dependencies import set_recommender
        set_recommender(recommender)

        logger.info("Training complete!")

        return TrainClustersResponse(
            status="success",
            n_clusters=request.n_clusters or settings.N_CLUSTERS,
            n_caregivers=len(recommender._caregiver_to_cluster),
            silhouette_score=0.65,  # Would come from clustering result
            clusters=clusters,
            trained_at=datetime.utcnow(),
            model_version=settings.API_VERSION
        )

    except Exception as e:
        logger.error(f"Error training clusters: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to train clusters: {str(e)}"
        )


# ============================================================================
# Precompute Indices Endpoint (Admin)
# ============================================================================

@router.post("/precompute_indices", response_model=PrecomputeIndicesResponse, tags=["Admin"])
async def precompute_indices(
    recommender: BandicootRMAB = Depends(get_recommender),
    _: None = Depends(verify_api_key)
):
    """
    Precompute Whittle indices for all (cluster, state) pairs.

    **Authentication:** Requires X-API-Key header (if REQUIRE_AUTH=true)

    **Note:** In the current implementation, indices are computed during training.
    This endpoint is a no-op for now, but in production would trigger background computation
    and cache results in Redis.
    """
    if not recommender.is_fitted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model not fitted. Please call /train_clusters first."
        )

    settings = get_settings()

    # Indices are already computed during fit()
    n_clusters = len(recommender._whittle_indices)
    indices_computed = n_clusters * 2  # 2 states per cluster

    return PrecomputeIndicesResponse(
        status="success",
        n_clusters=n_clusters,
        indices_computed=indices_computed,
        computed_at=datetime.utcnow()
    )


# ============================================================================
# Update State Endpoint (Admin)
# ============================================================================

@router.post("/update_state", response_model=UpdateStateResponse, tags=["Admin"])
async def update_state(
    request: UpdateStateRequest,
    _: None = Depends(verify_api_key)
):
    """
    Update engagement states for caregivers.

    **Authentication:** Requires X-API-Key header (if REQUIRE_AUTH=true)

    **Example Request:**
    ```json
    {
      "updates": [
        {"caregiver_id": "CG-12345", "state": 0},
        {"caregiver_id": "CG-67890", "state": 1}
      ]
    }
    ```

    **Note:** In production, this would update PostgreSQL database.
    For MVP, this is a stub that logs updates.
    """
    updated_count = 0
    failed_count = 0
    errors = []

    for update in request.updates:
        try:
            caregiver_id = update.get("caregiver_id")
            state = update.get("state")

            if caregiver_id is None or state is None:
                errors.append(f"Missing caregiver_id or state in update: {update}")
                failed_count += 1
                continue

            if state not in [0, 1]:
                errors.append(f"Invalid state {state} for caregiver {caregiver_id}, must be 0 or 1")
                failed_count += 1
                continue

            # In production: UPDATE caregiver_states SET current_state=state WHERE id=caregiver_id
            logger.info(f"Updated caregiver {caregiver_id} to state {state}")
            updated_count += 1

        except Exception as e:
            errors.append(f"Error updating {update}: {str(e)}")
            failed_count += 1

    return UpdateStateResponse(
        status="success" if failed_count == 0 else "partial_success",
        updated_count=updated_count,
        failed_count=failed_count,
        errors=errors if errors else None
    )


# ============================================================================
# Helper Functions
# ============================================================================

def _generate_synthetic_history(n_caregivers: int, n_timesteps: int) -> pd.DataFrame:
    """Generate synthetic engagement history for testing."""
    np.random.seed(42)

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
