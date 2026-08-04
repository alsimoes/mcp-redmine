"""Environment-based configuration for the Redmine connection."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_TIMEOUT = 15.0


class ConfigurationError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    """Connection settings read from the environment.

    Attributes:
        url: Base URL of the Redmine instance, without a trailing slash.
        api_key: Redmine REST API key (My account > API access key).
        timeout: Per-request timeout in seconds.
    """

    url: str
    api_key: str
    timeout: float = DEFAULT_TIMEOUT


def load_settings() -> Settings:
    """Read and validate settings from the environment.

    Loading is deferred to call time (rather than done at import time) so the
    package stays importable — for tests, tooling, or introspection — without
    REDMINE_URL and REDMINE_API_KEY being set.

    Returns:
        The validated settings.

    Raises:
        ConfigurationError: If REDMINE_URL or REDMINE_API_KEY is missing, or
            if REDMINE_TIMEOUT is set but is not a positive number.
    """
    url = os.environ.get("REDMINE_URL", "").rstrip("/")
    api_key = os.environ.get("REDMINE_API_KEY", "")

    if not url or not api_key:
        raise ConfigurationError(
            "REDMINE_URL and REDMINE_API_KEY must be set in the environment. "
            "See .env.example, or the 'env' block of your MCP client's server "
            "configuration."
        )

    timeout = DEFAULT_TIMEOUT
    timeout_raw = os.environ.get("REDMINE_TIMEOUT", "")
    if timeout_raw:
        try:
            timeout = float(timeout_raw)
        except ValueError as exc:
            raise ConfigurationError(
                f"REDMINE_TIMEOUT must be a number, got {timeout_raw!r}."
            ) from exc
        if timeout <= 0:
            raise ConfigurationError("REDMINE_TIMEOUT must be greater than zero.")

    return Settings(url=url, api_key=api_key, timeout=timeout)
