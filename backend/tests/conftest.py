"""Shared fixtures."""

import pytest
from fastapi.testclient import TestClient

from onsite_floor.app import create_app
from onsite_floor.core.settings import Settings


@pytest.fixture
def client() -> TestClient:
    """A test client for a fresh application with explicit, environment-independent settings."""
    app = create_app(Settings(debug=False))
    return TestClient(app)
