"""Tests for the logging configuration."""

import json
import logging

import pytest

from onsite_floor.core.logging import configure_logging
from onsite_floor.core.settings import Settings

pytestmark = pytest.mark.usefixtures("restore_logging")


def lines(capsys: pytest.CaptureFixture[str]) -> list[str]:
    """Return the non-empty lines written to stderr so far."""
    return [line for line in capsys.readouterr().err.splitlines() if line]


def test_text_format(capsys: pytest.CaptureFixture[str]) -> None:
    """In text mode a record is one readable line with level, logger name and message."""
    configure_logging(Settings(log_format="text", log_level="INFO"))

    logging.getLogger("onsite_floor.demo").info("hello %s", "world")

    [line] = lines(capsys)
    assert "INFO" in line
    assert "onsite_floor.demo: hello world" in line, f"unexpected text line: {line!r}"


def test_json_format(capsys: pytest.CaptureFixture[str]) -> None:
    """In JSON mode a record is one parsable JSON object with the main fields."""
    configure_logging(Settings(log_format="json", log_level="INFO"))

    logging.getLogger("onsite_floor.demo").info("hello %s", "world")

    [line] = lines(capsys)
    payload = json.loads(line)
    assert payload["level"] == "INFO"
    assert payload["logger"] == "onsite_floor.demo"
    assert payload["message"] == "hello world"
    assert "time" in payload, "JSON log must carry a timestamp"


def test_json_format_includes_traceback(capsys: pytest.CaptureFixture[str]) -> None:
    """`logger.exception` adds the traceback to the JSON object, so errors are not reduced to a message."""
    configure_logging(Settings(log_format="json", log_level="INFO"))

    try:
        raise ValueError("boom")
    except ValueError:
        logging.getLogger("onsite_floor.demo").exception("something failed")

    [line] = lines(capsys)
    assert "ValueError: boom" in json.loads(line)["exception"]


def test_level_filters_records(capsys: pytest.CaptureFixture[str]) -> None:
    """Records below the configured level are dropped."""
    configure_logging(Settings(log_format="text", log_level="WARNING"))
    logger = logging.getLogger("onsite_floor.demo")

    logger.info("quiet")
    logger.warning("loud")

    [line] = lines(capsys)
    assert "loud" in line, "WARNING must pass"
    assert "quiet" not in line, "INFO must be filtered out at WARNING level"


def test_repeated_configuration_does_not_duplicate_output(capsys: pytest.CaptureFixture[str]) -> None:
    """Configuring twice must not stack handlers, otherwise every line would be printed twice."""
    settings = Settings(log_format="text", log_level="INFO")
    configure_logging(settings)
    configure_logging(settings)

    logging.getLogger("onsite_floor.demo").info("once")

    assert len(lines(capsys)) == 1, "a record must be written exactly once"


def test_uvicorn_loggers_use_the_shared_handler(capsys: pytest.CaptureFixture[str]) -> None:
    """Uvicorn's own handlers are removed, so its records come out in our format."""
    configure_logging(Settings(log_format="json", log_level="INFO"))

    logging.getLogger("uvicorn.error").info("server message")

    [line] = lines(capsys)
    assert json.loads(line)["logger"] == "uvicorn.error", "uvicorn records must go through our formatter"


def test_level_applies_to_uvicorn_too(capsys: pytest.CaptureFixture[str]) -> None:
    """Uvicorn pins its own loggers to INFO, so our level must be applied to them explicitly."""
    configure_logging(Settings(log_format="text", log_level="WARNING"))

    logging.getLogger("uvicorn.access").info("request line")

    assert lines(capsys) == [], "INFO from uvicorn must be silenced at WARNING level"
