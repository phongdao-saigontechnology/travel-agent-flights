"""Entry point for the Travel Agent API."""

import uvicorn

from travel_agent.config import get_settings


def main():
    """Run the Travel Agent API server."""
    settings = get_settings()
    uvicorn.run(
        "travel_agent.api.app:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
