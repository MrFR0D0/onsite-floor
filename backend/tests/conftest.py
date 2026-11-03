"""Shared fixtures."""

import logging
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from onsite_floor.app import create_app
from onsite_floor.core.settings import Settings


@pytest.fixture
def client() -> TestClient:
    """A test client for a fresh application with explicit, environment-independent settings."""
    app = create_app(Settings(fastapi_debug_mode=False))
    return TestClient(app)


@pytest.fixture
def restore_logging() -> Iterator[None]:
    """Undo any logging configuration a test applies, so other tests are not affected.

    The state of every logger that exists before the test is saved and restored afterwards,
    so new libraries need no changes here. Loggers created during the test go back to defaults.
    """

    def all_loggers() -> list[logging.Logger]:
        known = [item for item in logging.root.manager.loggerDict.values() if isinstance(item, logging.Logger)]
        return [logging.root, *known]

    saved = {logger: (logger.handlers[:], logger.level, logger.propagate, logger.disabled) for logger in all_loggers()}
    disable_level = logging.root.manager.disable
    yield
    for logger in all_loggers():
        handlers, level, propagate, disabled = saved.get(logger, ([], logging.NOTSET, True, False))
        logger.handlers[:] = handlers
        logger.setLevel(level)
        logger.propagate = propagate
        logger.disabled = disabled
    logging.disable(disable_level)
