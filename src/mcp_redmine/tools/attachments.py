"""Issue attachments."""

from __future__ import annotations

from typing import Any

from mcp_redmine.app import get_client, tool
from mcp_redmine.errors import RedmineError, redmine_error_message
from mcp_redmine.format import dumps
from mcp_redmine.uploads import upload_file


@tool
def attach_file_to_issue(
    issue_id: int,
    file_path: str,
    description: str = "",
    comment: str = "",
    file_name: str = "",
) -> str:
    """Attach a local file to an issue.

    Uploads the file and links it to the issue right after — the two steps
    Redmine's API requires, in a single call.

    The path is resolved on the machine running this MCP server.

    Args:
        issue_id: issue ID.
        file_path: full path of the file on the server's machine.
        description: attachment description, shown next to its name.
        comment: note to add to the history along with the attachment.
        file_name: display name in Redmine (empty = use the file's own name).
    """
    client = get_client()

    try:
        token, name, content_type = upload_file(client, file_path, file_name)
    except RedmineError as exc:
        return f"Upload error: {redmine_error_message(exc)}"

    attachment = {"token": token, "filename": name, "content_type": content_type}
    if description:
        attachment["description"] = description

    issue: dict[str, Any] = {"uploads": [attachment]}
    if comment:
        issue["notes"] = comment

    try:
        client.request("PUT", f"/issues/{issue_id}.json", json={"issue": issue})
    except RedmineError as exc:
        return (
            f"Upload of '{name}' succeeded, but linking it to issue "
            f"#{issue_id} failed: {redmine_error_message(exc)}. The token "
            "will expire on its own."
        )

    # The PUT returns 204 with no body, so the attachment's ID only shows up
    # by re-reading the issue. Without it there's no way to call
    # get_attachment or delete_attachment on it later.
    attachment_id = None
    try:
        after = client.request("GET", f"/issues/{issue_id}.json?include=attachments")
        candidates = [
            a
            for a in after.get("issue", {}).get("attachments", [])
            if a.get("filename") == name
        ]
        if candidates:
            attachment_id = max(candidates, key=lambda a: a["id"])["id"]
    except RedmineError:
        pass  # the attachment is there; we just couldn't confirm its ID

    return dumps(
        {
            "issue": issue_id,
            "attachment_id": attachment_id,
            "name": name,
            "content_type": content_type,
            "note": None
            if attachment_id
            else "attachment created, but could not re-read its ID — use get_issue",
        }
    )


@tool
def get_attachment(attachment_id: int) -> str:
    """Show an attachment's details: name, size, type, author, and download URL.

    Args:
        attachment_id: attachment ID (shown in get_issue, in the
            'attachments' list).
    """
    data = get_client().request("GET", f"/attachments/{attachment_id}.json")
    a = data.get("attachment", {})
    return dumps(
        {
            "id": a.get("id"),
            "name": a.get("filename"),
            "size_bytes": a.get("filesize"),
            "content_type": a.get("content_type"),
            "description": a.get("description"),
            "author": a.get("author", {}).get("name"),
            "created_on": a.get("created_on"),
            "url": a.get("content_url"),
        }
    )


@tool
def update_attachment(
    attachment_id: int, file_name: str = "", description: str = ""
) -> str:
    """Rename an attachment or change its description, without re-uploading it.

    Available since Redmine 5.0; older versions respond with 404.

    Args:
        attachment_id: attachment ID.
        file_name: new display name (empty = leave alone).
        description: new description (empty = leave alone).
    """
    payload = {}
    if file_name:
        payload["filename"] = file_name
    if description:
        payload["description"] = description

    if not payload:
        return (
            f"Nothing to update on attachment #{attachment_id}: no field was provided."
        )

    get_client().request(
        "PATCH", f"/attachments/{attachment_id}.json", json={"attachment": payload}
    )
    return f"Attachment #{attachment_id} updated ({', '.join(sorted(payload))})."


@tool
def delete_attachment(attachment_id: int) -> str:
    """Permanently delete an attachment. The file is removed from the server's disk.

    Args:
        attachment_id: attachment ID.
    """
    get_client().request("DELETE", f"/attachments/{attachment_id}.json")
    return f"Attachment #{attachment_id} deleted."
