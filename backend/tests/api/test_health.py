"""Tests for the `/api/health` endpoint."""

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    """The health check answers 200 with a fixed `{"status": "ok"}` payload.

    Monitoring tools and Docker use this endpoint to learn that the service is alive.
    """
    response = client.get("/api/health")

    assert response.status_code == 200, "Health endpoint must answer with HTTP 200"
    assert response.json() == {"status": "ok"}, "Health check must report the service as ok"
