"""Tests for how settings are loaded and validated."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from onsite_floor.core.settings import Settings, get_settings


def test_defaults_when_nothing_is_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without any environment variable or `.env` file, `debug` is off."""
    monkeypatch.delenv("ONSITE_FLOOR_DEBUG", raising=False)

    settings = Settings(_env_file=None)

    assert settings.debug is False, "debug must default to False when nothing is configured"


def test_reads_environment_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    """A variable with the `ONSITE_FLOOR_` prefix fills the matching field."""
    monkeypatch.setenv("ONSITE_FLOOR_DEBUG", "true")

    settings = Settings(_env_file=None)

    assert settings.debug is True, "ONSITE_FLOOR_DEBUG from the environment must be applied"


def test_reads_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Values from a `.env` file are used when no environment variable is set."""
    monkeypatch.delenv("ONSITE_FLOOR_DEBUG", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("ONSITE_FLOOR_DEBUG=true\n")

    settings = Settings(_env_file=env_file)

    assert settings.debug is True, "A value from the .env file must be applied"


def test_environment_variable_overrides_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Priority rule: a real environment variable wins over the same key in `.env`.

    This lets a server override local file values without editing the file.
    """
    env_file = tmp_path / ".env"
    env_file.write_text("ONSITE_FLOOR_DEBUG=true\n")
    monkeypatch.setenv("ONSITE_FLOOR_DEBUG", "false")

    settings = Settings(_env_file=env_file)

    assert settings.debug is False, "A real environment variable must win over the .env file"


def test_rejects_invalid_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """A value that cannot be read as a boolean stops startup with a validation error.

    A typo in configuration should fail loudly at launch, not surprise us later.
    """
    monkeypatch.setenv("ONSITE_FLOOR_DEBUG", "maybe")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_get_settings_is_cached() -> None:
    """`get_settings` reads the environment once and returns the same object afterwards."""
    get_settings.cache_clear()

    assert get_settings() is get_settings(), "get_settings must return the same cached object"
