"""FastAPI application factory."""

from fastapi import FastAPI

from onsite_floor.core.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application.

    Args:
        settings: Configuration to use. Loaded from the environment when omitted.

    Returns:
        A ready-to-serve application instance.
    """
    settings = settings or get_settings()
    app = FastAPI(title="onsite-floor", debug=settings.debug)
    app.state.settings = settings

    @app.get("/api/health", tags=["system"])
    async def health() -> dict[str, str]:
        """Report that the service is up."""
        return {"status": "ok"}

    return app


app = create_app()
