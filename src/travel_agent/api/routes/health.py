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

    # Determine OpenAI configuration status based on provider
    if settings.llm_provider == "azure_openai":
        openai_configured = bool(
            settings.azure_openai_api_key
            and settings.azure_openai_endpoint
            and settings.azure_openai_deployment_name
        )
    else:
        openai_configured = bool(settings.openai_api_key)

    return HealthResponse(
        status="healthy",
        version=__version__,
        amadeus_configured=bool(
            settings.amadeus_client_id and settings.amadeus_client_secret
        ),
        openai_configured=openai_configured,
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
