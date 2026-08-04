"""Error handling shared by every tool: turns Redmine failures into readable text."""

from __future__ import annotations

import requests

# Likely reasons by HTTP status, for readers without the Redmine docs open
# alongside.
HTTP_REASONS: dict[int, str] = {
    401: "invalid or missing API key",
    403: "not allowed to perform this operation, or the module is disabled "
    "for this project",
    404: "not found (check the ID, or this endpoint may not exist in this "
    "Redmine version)",
    409: "conflict — the resource was changed by someone else",
    422: "Redmine rejected the data during validation",
}


class RedmineError(RuntimeError):
    """A Redmine API call failed; the message is already human-readable."""


def format_response_error(response: requests.Response) -> str:
    """Turn a Redmine error response into a readable sentence.

    On validation failures Redmine returns ``{"errors": [...]}`` in the body,
    and that is where the real explanation lives — a blank required field, a
    circular relation, a nonexistent ID. When there is no useful body, fall
    back to the status code with the likely reason.

    Args:
        response: The failed response from Redmine.

    Returns:
        A one-line, human-readable description of the failure.
    """
    try:
        errors = response.json().get("errors")
        if errors:
            return "; ".join(str(error) for error in errors)
    except ValueError:
        pass

    reason = HTTP_REASONS.get(response.status_code)
    return f"HTTP {response.status_code}" + (f" — {reason}" if reason else "")


def redmine_error_message(exc: Exception) -> str:
    """Extract the readable message carried by an exception from the client.

    Args:
        exc: The exception caught around a Redmine API call. Usually a
            RedmineError, whose message is already readable, but this also
            handles a bare ``requests`` exception that still carries a
            ``response`` attribute.

    Returns:
        The message to show the caller.
    """
    response = getattr(exc, "response", None)
    if response is not None:
        return format_response_error(response)
    return str(exc)
