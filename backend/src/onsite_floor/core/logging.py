"""Logging configuration shared by the whole application."""

import json
import logging
import logging.config
from datetime import UTC, datetime
from typing import Any

from onsite_floor.core.settings import Settings

TEXT_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"

# Loggers that uvicorn configures for itself. We strip their own handlers so that their records
# travel to the root logger, and we give them our level, because uvicorn pins its own (INFO).
_UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


class JsonFormatter(logging.Formatter):
    """Render every log record as a single line of JSON, convenient for log collectors."""

    def format(self, record: logging.LogRecord) -> str:
        """Convert a log record into a JSON string.

        Args:
            record: The record to render.

        Returns:
            One JSON object with time, level, logger name and message (plus the traceback when present).
        """
        payload: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(settings: Settings) -> None:
    """Set up logging for the whole process according to the settings.

    Calling it again replaces the previous configuration instead of stacking handlers on top of it.

    Args:
        settings: Source of the log level and the output format.
    """
    formatter: dict[str, Any] = {"()": JsonFormatter} if settings.log_format == "json" else {"format": TEXT_FORMAT}
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"default": formatter},
            "handlers": {
                "console": {"class": "logging.StreamHandler", "formatter": "default", "stream": "ext://sys.stderr"},
            },
            "root": {"level": settings.log_level, "handlers": ["console"]},
            "loggers": {
                name: {"handlers": [], "propagate": True, "level": settings.log_level} for name in _UVICORN_LOGGERS
            },
        }
    )
