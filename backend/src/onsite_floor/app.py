"""FastAPI application factory."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Build and configure the FastAPI application.

    Returns:
        A ready-to-serve application instance.
    """
    app = FastAPI(title="onsite-floor")

    @app.get("/api/health", tags=["system"])
    async def health() -> dict[str, str]:
        """Report that the service is up."""
        return {"status": "ok"}

    return app


app = create_app()
