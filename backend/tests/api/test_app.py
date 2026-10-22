"""Tests for the application factory `create_app`."""

from onsite_floor.app import create_app
from onsite_floor.core.settings import Settings


def test_create_app_uses_given_settings() -> None:
    """The factory applies the settings it receives and exposes them as `app.state.settings`.

    Tests pass their own settings this way, and features will read them from `app.state`.
    """
    settings = Settings(debug=True)

    app = create_app(settings)

    assert app.debug is True, "create_app must pass the debug flag from settings to FastAPI"
    assert app.state.settings is settings, "Settings must be reachable through app.state.settings"
