"""Binary file uploads to the Redmine ``/uploads.json`` endpoint."""

from __future__ import annotations

import mimetypes
import os

import requests

from mcp_redmine.client import RedmineClient
from mcp_redmine.errors import RedmineError, format_response_error

# Defensive limit. Redmine has its own, configurable in
# Administration -> Settings -> Files; this one just avoids discovering that
# limit only after pushing tens of megabytes over the network.
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

UPLOAD_TIMEOUT = 120.0


def upload_file(
    client: RedmineClient, file_path: str, file_name: str = ""
) -> tuple[str, str, str]:
    """Upload a local file to ``/uploads.json`` and return its token.

    This bypasses ``RedmineClient.request`` because the upload requires
    ``Content-Type: application/octet-stream``, while the client's session
    headers are fixed to ``application/json``.

    The path is resolved on the machine running this MCP server, not on the
    machine of whoever calls the tool.

    Args:
        client: The Redmine client, used for its base URL and API key.
        file_path: Path to the local file to upload.
        file_name: Display name in Redmine (empty = use the file's own name).

    Returns:
        A ``(token, filename, content_type)`` tuple.

    Raises:
        RedmineError: If the file is missing, empty, larger than
            MAX_UPLOAD_BYTES, or the upload itself fails.
    """
    if not os.path.isfile(file_path):
        raise RedmineError(f"file not found: {file_path}")

    size = os.path.getsize(file_path)
    if size > MAX_UPLOAD_BYTES:
        megabytes = size / (1024 * 1024)
        raise RedmineError(
            f"file is {megabytes:.1f} MB, over this server's "
            f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit"
        )
    if size == 0:
        raise RedmineError("file is empty — Redmine rejects 0-byte uploads")

    name = file_name or os.path.basename(file_path)
    content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"

    headers = {
        "X-Redmine-API-Key": client.api_key,
        "Content-Type": "application/octet-stream",
    }

    try:
        with open(file_path, "rb") as handle:
            response = requests.post(
                f"{client.base_url}/uploads.json",
                headers=headers,
                data=handle,
                timeout=UPLOAD_TIMEOUT,
            )
    except requests.RequestException as exc:
        raise RedmineError(f"network failure during upload: {exc}") from exc
    except OSError as exc:
        raise RedmineError(f"could not read the file: {exc}") from exc

    if not response.ok:
        raise RedmineError(format_response_error(response))

    token = response.json().get("upload", {}).get("token")
    if not token:
        raise RedmineError("Redmine accepted the upload but returned no token")

    return token, name, content_type
