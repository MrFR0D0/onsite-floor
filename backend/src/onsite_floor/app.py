"""FastAPI application factory."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from onsite_floor.core.logging import configure_logging
from onsite_floor.core.settings import Settings, get_settings

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application.

    Args:
        settings: Configuration to use. Loaded from the environment when omitted.

    Returns:
        A ready-to-serve application instance.
    """
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        """Configure logging when the server starts and say goodbye when it stops."""
        configure_logging(settings)
        logger.info("onsite-floor started (log level: %s, format: %s)", settings.log_level, settings.log_format)
        yield
        logger.info("onsite-floor stopped")

    app = FastAPI(title="onsite-floor", debug=settings.fastapi_debug_mode, lifespan=lifespan)
    app.state.settings = settings

    @app.get("/api/health", tags=["system"])
    async def health() -> dict[str, str]:
        """Report that the service is up."""
        return {"status": "ok"}

    return app


app = create_app()
