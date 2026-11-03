"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Every field can be set through an environment variable with the `ONSITE_FLOOR_` prefix
    (for example `ONSITE_FLOOR_FASTAPI_DEBUG_MODE=true`) or through a `.env` file in the working directory.
    """

    model_config = SettingsConfigDict(env_prefix="ONSITE_FLOOR_", env_file=".env", extra="ignore")

    fastapi_debug_mode: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["text", "json"] = "text"


@lru_cache
def get_settings() -> Settings:
    """Return the settings, reading the environment only once.

    Returns:
        The cached `Settings` instance.
    """
    return Settings()
