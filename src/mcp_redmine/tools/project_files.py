"""Project files: artifacts published under a project's Files tab."""

from __future__ import annotations

from typing import Any

from mcp_redmine.app import get_client, tool
from mcp_redmine.errors import RedmineError, redmine_error_message
from mcp_redmine.format import dumps
from mcp_redmine.uploads import upload_file


@tool
def list_project_files(project_identifier: str) -> str:
    """List the files published under a project's Files tab.

    Not to be confused with issue attachments: these are project-level
    artifacts — builds, installers, documents — optionally tied to a version.

    Args:
        project_identifier: project identifier.
    """
    data = get_client().request("GET", f"/projects/{project_identifier}/files.json")
    files = [
        {
            "id": f["id"],
            "name": f.get("filename"),
            "size_bytes": f.get("filesize"),
            "content_type": f.get("content_type"),
            "description": f.get("description"),
            "version": (f.get("version") or {}).get("name"),
            "downloads": f.get("downloads"),
            "url": f.get("content_url"),
        }
        for f in data.get("files", [])
    ]
    return dumps(files)


@tool
def upload_project_file(
    project_identifier: str,
    file_path: str,
    description: str = "",
    version_id: int = 0,
    file_name: str = "",
) -> str:
    """Publish a file under a project's Files tab.

    The path is resolved on the machine running this MCP server.

    Args:
        project_identifier: project identifier.
        file_path: full path of the file on the server's machine.
        description: description shown in the listing.
        version_id: ties the file to a version (0 = none).
        file_name: display name (empty = use the file's own name).
    """
    client = get_client()

    try:
        token, name, content_type = upload_file(client, file_path, file_name)
    except RedmineError as exc:
        return f"Upload error: {redmine_error_message(exc)}"

    payload: dict[str, Any] = {
        "token": token,
        "filename": name,
        "content_type": content_type,
    }
    if description:
        payload["description"] = description
    if version_id:
        payload["version_id"] = version_id

    try:
        client.request(
            "POST", f"/projects/{project_identifier}/files.json", json={"file": payload}
        )
    except RedmineError as exc:
        return (
            f"Upload of '{name}' succeeded, but publishing it to "
            f"'{project_identifier}' failed: {redmine_error_message(exc)}. "
            "The token will expire on its own."
        )

    return (
        f"'{name}' ({content_type}) published in the files of '{project_identifier}'."
    )
