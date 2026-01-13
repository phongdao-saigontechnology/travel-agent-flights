"""Health check routes."""

from fastapi import APIRouter

from travel_agent import __version__
from travel_agent.config import get_settings
from travel_agent.models.api import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check the health status of the API.

    Returns configuration status for required services.
    """
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version=__version__,
        amadeus_configured=bool(
            settings.amadeus_client_id and settings.amadeus_client_secret
        ),
        openai_configured=bool(settings.openai_api_key),
    )


@router.get("/")
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "name": "Travel Agent API",
        "version": __version__,
        "description": "LangGraph-powered travel agent with Amadeus API integration",
        "docs": "/docs",
        "health": "/health",
    }
