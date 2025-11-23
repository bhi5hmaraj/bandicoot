"""
Pydantic models for API requests and responses.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# Request Models
# ============================================================================

class RecommendRequest(BaseModel):
    """Request for caregiver recommendations."""

    budget: int = Field(..., ge=1, description="Number of caregivers to recommend")
    caregiver_ids: Optional[List[str]] = Field(
        None,
        description="Optional list of caregiver IDs to consider. If None, uses all active caregivers."
    )
    current_states: Optional[List[int]] = Field(
        None,
        description="Current state for each caregiver (0=Responsive, 1=Unresponsive). Must match caregiver_ids length."
    )
    filter_district: Optional[str] = Field(
        None,
        description="Optional district filter (e.g., 'Bihar-Patna')"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "budget": 100,
                "filter_district": "Bihar-Patna"
            }
        }


class UpdateStateRequest(BaseModel):
    """Request to update caregiver engagement states."""

    updates: List[Dict[str, Any]] = Field(
        ...,
        description="List of state updates, each with caregiver_id and state"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "updates": [
                    {"caregiver_id": "CG-12345", "state": 0},
                    {"caregiver_id": "CG-67890", "state": 1}
                ]
            }
        }


class TrainClustersRequest(BaseModel):
    """Request to train clustering model."""

    n_clusters: Optional[int] = Field(
        20,
        ge=2,
        le=100,
        description="Number of clusters to create"
    )
    min_observations: Optional[int] = Field(
        10,
        ge=1,
        description="Minimum observations required for MDP estimation"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "n_clusters": 20,
                "min_observations": 10
            }
        }


# ============================================================================
# Response Models
# ============================================================================

class CaregiverRecommendation(BaseModel):
    """Single caregiver recommendation."""

    caregiver_id: str = Field(..., description="Caregiver unique identifier")
    priority_score: float = Field(..., description="Whittle index (priority score)")
    current_state: str = Field(..., description="Current engagement state")
    cluster_id: int = Field(..., description="Assigned cluster ID")
    reason: Optional[str] = Field(None, description="Human-readable explanation")

    class Config:
        json_schema_extra = {
            "example": {
                "caregiver_id": "CG-12345",
                "priority_score": 0.87,
                "current_state": "Unresponsive",
                "cluster_id": 5,
                "reason": "High risk of dropout, responsive to interventions"
            }
        }


class RecommendationMetadata(BaseModel):
    """Metadata about recommendation generation."""

    total_evaluated: int = Field(..., description="Total caregivers evaluated")
    budget: int = Field(..., description="Requested budget")
    generated_at: datetime = Field(..., description="Timestamp of generation")
    model_version: str = Field(..., description="Model version used")

    class Config:
        json_schema_extra = {
            "example": {
                "total_evaluated": 150000,
                "budget": 100,
                "generated_at": "2025-11-23T10:30:00Z",
                "model_version": "v1.0.0"
            }
        }


class RecommendResponse(BaseModel):
    """Response with caregiver recommendations."""

    recommendations: List[CaregiverRecommendation] = Field(
        ...,
        description="List of recommended caregivers, sorted by priority (descending)"
    )
    metadata: RecommendationMetadata = Field(..., description="Generation metadata")


class ClusterSummary(BaseModel):
    """Summary statistics for a single cluster."""

    cluster_id: int
    n_caregivers: int
    w_responsive: float = Field(..., description="Whittle index for Responsive state")
    w_unresponsive: float = Field(..., description="Whittle index for Unresponsive state")
    retention_R: float = Field(..., description="P(R→R | passive)")
    recovery_U: float = Field(..., description="P(U→R | passive)")


class TrainClustersResponse(BaseModel):
    """Response after training clustering model."""

    status: str = Field(..., description="Training status")
    n_clusters: int = Field(..., description="Number of clusters created")
    n_caregivers: int = Field(..., description="Number of caregivers clustered")
    silhouette_score: float = Field(..., description="Clustering quality metric")
    clusters: List[ClusterSummary] = Field(..., description="Summary of each cluster")
    trained_at: datetime = Field(..., description="Training timestamp")
    model_version: str = Field(..., description="Model version")


class PrecomputeIndicesResponse(BaseModel):
    """Response after precomputing Whittle indices."""

    status: str = Field(..., description="Computation status")
    n_clusters: int = Field(..., description="Number of clusters processed")
    indices_computed: int = Field(..., description="Number of (cluster, state) pairs")
    computed_at: datetime = Field(..., description="Computation timestamp")


class UpdateStateResponse(BaseModel):
    """Response after updating caregiver states."""

    status: str = Field(..., description="Update status")
    updated_count: int = Field(..., description="Number of states updated successfully")
    failed_count: int = Field(..., description="Number of failed updates")
    errors: Optional[List[str]] = Field(None, description="Error messages if any")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    model_loaded: bool = Field(..., description="Whether recommender model is loaded")
    timestamp: datetime = Field(..., description="Current server time")


class ErrorResponse(BaseModel):
    """Error response."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
