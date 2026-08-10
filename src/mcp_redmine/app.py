"""FastMCP application: tool registration, error handling, and entry point."""

from __future__ import annotations

import sys
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from mcp.server.fastmcp import FastMCP

from mcp_redmine.client import RedmineClient
from mcp_redmine.config import ConfigurationError, load_settings
from mcp_redmine.errors import RedmineError, redmine_error_message

mcp = FastMCP("redmine")

F = TypeVar("F", bound=Callable[..., str])

_client: RedmineClient | None = None


def get_client() -> RedmineClient:
    """Return the process-wide Redmine client, creating it on first use.

    Creation is deferred so importing this package — for tests, tooling, or
    introspection — doesn't require REDMINE_URL and REDMINE_API_KEY to be set.

    Returns:
        The shared RedmineClient instance.

    Raises:
        ConfigurationError: If the required environment variables are unset.
    """
    global _client
    if _client is None:
        _client = RedmineClient(load_settings())
    return _client


def set_client(client: RedmineClient | None) -> None:
    """Override the process-wide client.

    Intended for tests, which inject a client backed by a mocked session
    instead of a real Redmine instance.

    Args:
        client: The client to use from now on, or None to reset so the next
            call to get_client() builds a fresh one from the environment.
    """
    global _client
    _client = client


def tool(func: F) -> F:
    """Register an MCP tool that turns Redmine failures into readable text.

    Wraps ``func`` so a RedmineError raised anywhere inside it becomes its
    message as an ordinary return value, instead of propagating as an
    exception, then registers the wrapped function with FastMCP. This
    replaces the try/except-and-format block that used to be repeated in
    nearly every tool.

    A handful of tools need to react differently to a failure partway through
    a multi-step operation (for example, reporting that a file upload
    succeeded but linking it to an issue failed). Those catch RedmineError
    themselves and return their own message, so this wrapper never sees it.

    Any other exception is a bug, not an expected Redmine failure, and is
    left to propagate so it surfaces instead of being silently swallowed.

    Args:
        func: The tool function to wrap and register.

    Returns:
        The wrapped function, already registered with FastMCP.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        try:
            return func(*args, **kwargs)
        except RedmineError as exc:
            return f"Error: {redmine_error_message(exc)}"

    mcp.tool()(wrapper)
    return wrapper  # type: ignore[return-value]


def main() -> None:
    """Entry point for the ``mcp-redmine-rest`` console script.

    Validates configuration eagerly so a misconfigured server fails fast with
    an actionable message, instead of starting up and letting every tool call
    fail later with a confusing network error.
    """
    try:
        load_settings()
    except ConfigurationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    import mcp_redmine.tools  # noqa: F401  (import registers every tool)

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
