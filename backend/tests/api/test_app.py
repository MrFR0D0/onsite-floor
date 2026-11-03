"""Tests for the application factory `create_app`."""

import pytest
from fastapi.testclient import TestClient

from onsite_floor.app import create_app
from onsite_floor.core.settings import Settings


def test_create_app_uses_given_settings() -> None:
    """The factory applies the settings it receives and exposes them as `app.state.settings`.

    Tests pass their own settings this way, and features will read them from `app.state`.
    """
    settings = Settings(fastapi_debug_mode=True)

    app = create_app(settings)

    assert app.debug is True, "create_app must pass the debug flag from settings to FastAPI"
    assert app.state.settings is settings, "Settings must be reachable through app.state.settings"


@pytest.mark.usefixtures("restore_logging")
def test_startup_configures_logging(capsys: pytest.CaptureFixture[str]) -> None:
    """When the server starts, logging is configured and the first line says so.

    The `with` block makes TestClient run the startup and shutdown phases, as a real server does.
    """
    with TestClient(create_app(Settings(fastapi_debug_mode=False, log_level="INFO", log_format="text"))):
        pass

    output = capsys.readouterr().err
    assert "onsite_floor.app: onsite-floor started" in output, "startup must log through the configured handler"
    assert "onsite-floor stopped" in output, "shutdown must be logged too"
