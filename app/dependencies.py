"""
FastAPI dependencies for authentication and dependency injection.
"""

from fastapi import Header, HTTPException, status, Depends
from typing import Optional, Annotated
from app.config import Settings, get_settings
from bandicoot.core.recommender import BandicootRMAB
import logging

logger = logging.getLogger(__name__)

# Global recommender instance (singleton pattern)
_recommender_instance: Optional[BandicootRMAB] = None


def get_recommender() -> BandicootRMAB:
    """
    Get or create the global recommender instance.

    This is a singleton to avoid loading the model multiple times.
    In production, this would load from saved model file or database.
    """
    global _recommender_instance

    if _recommender_instance is None:
        settings = get_settings()
        logger.info("Initializing BandicootRMAB instance...")
        _recommender_instance = BandicootRMAB(
            n_clusters=settings.N_CLUSTERS,
            gamma=settings.GAMMA,
            alpha=settings.ALPHA,
            min_observations=settings.MIN_OBSERVATIONS,
            random_state=settings.RANDOM_STATE
        )
        logger.info("BandicootRMAB instance created (not yet fitted)")

    return _recommender_instance


def reset_recommender():
    """Reset the global recommender instance (for testing or retraining)."""
    global _recommender_instance
    _recommender_instance = None
    logger.info("Recommender instance reset")


def set_recommender(recommender: BandicootRMAB):
    """Set the global recommender instance."""
    global _recommender_instance
    _recommender_instance = recommender
    logger.info(f"Recommender instance updated (fitted={recommender.is_fitted})")


async def verify_api_key(
    x_api_key: Annotated[Optional[str], Header()] = None,
    settings: Settings = Depends(get_settings)
) -> None:
    """
    Verify API key for protected endpoints.

    Args:
        x_api_key: API key from X-API-Key header
        settings: Application settings

    Raises:
        HTTPException: If authentication is required and key is invalid
    """
    if not settings.REQUIRE_AUTH:
        # Authentication disabled (development mode)
        return

    if settings.API_KEY is None:
        # No API key configured, but auth required
        logger.error("REQUIRE_AUTH=True but API_KEY not set in environment")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfiguration: authentication not properly configured"
        )

    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if x_api_key != settings.API_KEY:
        logger.warning(f"Invalid API key attempt: {x_api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )

    # Authentication successful
    return
