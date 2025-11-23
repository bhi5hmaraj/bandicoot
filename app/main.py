"""
Bandicoot RMAB API - Main application.

FastAPI service for caregiver intervention recommendations using
Restless Multi-Armed Bandits (RMAB).
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import time

from app.config import get_settings
from app.api import routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown events."""
    settings = get_settings()

    # Startup
    logger.info("=" * 60)
    logger.info(f"Starting {settings.API_TITLE} v{settings.API_VERSION}")
    logger.info("=" * 60)
    logger.info(f"Authentication: {'ENABLED' if settings.REQUIRE_AUTH else 'DISABLED'}")
    logger.info(f"Model Config: n_clusters={settings.N_CLUSTERS}, gamma={settings.GAMMA}")
    logger.info("=" * 60)

    yield

    # Shutdown
    logger.info("Shutting down Bandicoot RMAB API")


# Create FastAPI app
settings = get_settings()
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware (configure for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and their processing time."""
    start_time = time.time()

    # Log incoming request
    logger.info(f"→ {request.method} {request.url.path}")

    # Process request
    response = await call_next(request)

    # Log response
    process_time = time.time() - start_time
    logger.info(
        f"← {request.method} {request.url.path} "
        f"[{response.status_code}] {process_time:.3f}s"
    )

    # Add custom header with processing time
    response.headers["X-Process-Time"] = f"{process_time:.3f}"

    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions gracefully."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "detail": str(exc) if settings.LOG_LEVEL == "DEBUG" else None
        }
    )


# Include API routes
app.include_router(routes.router, prefix="/api/v1")


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "service": settings.API_TITLE,
        "version": settings.API_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
