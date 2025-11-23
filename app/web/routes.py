"""
Web UI route handlers for Bandicoot RMAB Dashboard.

Serves HTML templates with server-side rendering using Jinja2.
"""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from app.dependencies import get_recommender
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    Render the main dashboard page.

    Shows quick stats, recommendation form, and recent recommendations.
    """
    try:
        recommender = get_recommender()
        settings = get_settings()

        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "model_loaded": recommender.is_fitted,
            "version": settings.API_VERSION,
            "page_title": "Dashboard"
        })
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": "Unable to load dashboard. Please try again.",
            "model_loaded": False
        })


@router.get("/model", response_class=HTMLResponse)
async def model_info(request: Request):
    """
    Render the model info page.

    Shows training status, cluster summary, and model metadata.
    """
    try:
        recommender = get_recommender()
        settings = get_settings()

        # Get cluster summary if model is trained
        clusters = []
        training_info = None

        if recommender.is_fitted:
            try:
                summary_df = recommender.get_cluster_summary()
                # Rename column to match template expectations
                summary_df = summary_df.rename(columns={'cluster': 'cluster_id'})
                clusters = summary_df.to_dict('records')

                # Get training metadata
                training_info = {
                    'n_caregivers': len(recommender.caregiver_ids),
                    'n_clusters': recommender.n_clusters,
                    'trained_at': 'N/A'  # TODO: Add timestamp tracking
                }
            except Exception as e:
                logger.warning(f"Could not get cluster summary: {e}")

        return templates.TemplateResponse("model.html", {
            "request": request,
            "model_loaded": recommender.is_fitted,
            "version": settings.API_VERSION,
            "clusters": clusters,
            "training_info": training_info,
            "page_title": "Model Info"
        })
    except Exception as e:
        logger.error(f"Model info error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": "Unable to load model information. Please try again.",
            "model_loaded": False
        })


@router.get("/settings", response_class=HTMLResponse)
async def settings(request: Request):
    """
    Render the settings page.

    Shows model parameters and system configuration.
    """
    try:
        recommender = get_recommender()
        config = get_settings()

        return templates.TemplateResponse("settings.html", {
            "request": request,
            "model_loaded": recommender.is_fitted,
            "version": config.API_VERSION,
            "config": config,
            "page_title": "Settings"
        })
    except Exception as e:
        logger.error(f"Settings error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": "Unable to load settings. Please try again.",
            "model_loaded": False
        })
