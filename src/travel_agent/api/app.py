"""FastAPI application."""

from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from travel_agent import __version__
from travel_agent.api.routes import chat, health
from travel_agent.config import get_settings
from travel_agent.models.api import ErrorResponse

# Path to the demo directory (relative to project root)
DEMO_DIR = Path(__file__).parent.parent.parent.parent / "demo"

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Travel Agent API",
        description="LangGraph-powered travel agent chatbot with Amadeus API integration",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle uncaught exceptions."""
        logger.exception("unhandled_exception", path=request.url.path, error=str(exc))

        error_response = ErrorResponse(
            error="internal_server_error",
            message="An unexpected error occurred",
            details={"path": str(request.url.path)},
        )

        return JSONResponse(
            status_code=500,
            content=error_response.model_dump(),
        )

    # Include routers
    app.include_router(health.router)
    app.include_router(chat.router)

    # Serve demo page
    @app.get("/demo", include_in_schema=False)
    async def serve_demo():
        """Serve the demo chat interface."""
        return FileResponse(DEMO_DIR / "index.html")

    # Mount static files for demo assets (if any additional files are added)
    if DEMO_DIR.exists():
        app.mount("/demo/static", StaticFiles(directory=DEMO_DIR), name="demo-static")

    # Startup event
    @app.on_event("startup")
    async def startup_event():
        """Log startup information."""
        logger.info(
            "server_starting",
            version=__version__,
            host=settings.host,
            port=settings.port,
            amadeus_env=settings.amadeus_hostname,
        )

    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        """Clean up on shutdown."""
        logger.info("server_shutting_down")

    return app


# Create the app instance - will fail if settings are not configured
# This is intentional to fail fast on startup rather than at runtime
app = create_app()
