"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Every field can be set through an environment variable with the `ONSITE_FLOOR_` prefix
    (for example `ONSITE_FLOOR_DEBUG=true`) or through a `.env` file in the working directory.
    """

    model_config = SettingsConfigDict(env_prefix="ONSITE_FLOOR_", env_file=".env", extra="ignore")

    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return the settings, reading the environment only once.

    Returns:
        The cached `Settings` instance.
    """
    return Settings()
