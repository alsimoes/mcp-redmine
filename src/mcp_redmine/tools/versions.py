"""Project versions (milestones)."""

from __future__ import annotations

from mcp_redmine.app import get_client, tool
from mcp_redmine.format import dumps

VALID_STATUSES = ("open", "locked", "closed")


@tool
def list_project_versions(project_identifier: str) -> str:
    """List a project's versions (milestones), with their IDs.

    Args:
        project_identifier: project identifier.
    """
    data = get_client().request("GET", f"/projects/{project_identifier}/versions.json")
    versions = [
        {
            "id": v["id"],
            "name": v["name"],
            "status": v.get("status"),
            "due_date": v.get("due_date"),
            "description": v.get("description"),
        }
        for v in data.get("versions", [])
    ]
    return dumps(versions)


@tool
def create_project_version(
    project_identifier: str,
    name: str,
    description: str = "",
    status: str = "open",
    due_date: str = "",
) -> str:
    """Create a version (milestone) in a project.

    Args:
        project_identifier: project identifier.
        name: version name (e.g. 'v0.1 - Identity').
        description: free-text description.
        status: 'open', 'locked', or 'closed'.
        due_date: version date, YYYY-MM-DD format.
    """
    if status not in VALID_STATUSES:
        return f"Invalid status: '{status}'. Use open, locked, or closed."

    payload = {"name": name, "status": status}
    if description:
        payload["description"] = description
    if due_date:
        payload["due_date"] = due_date

    data = get_client().request(
        "POST",
        f"/projects/{project_identifier}/versions.json",
        json={"version": payload},
    )
    return dumps(data.get("version", {}))


@tool
def update_version(
    version_id: int,
    name: str = "",
    description: str = "",
    status: str = "",
    due_date: str = "",
) -> str:
    """Update an existing version. Only changes the fields that are provided.

    Args:
        version_id: version ID (use list_project_versions).
        name: new name (empty = leave alone).
        description: new description (empty = leave alone).
        status: 'open', 'locked', or 'closed' (empty = leave alone). Closing a
            version removes it from the choices offered to new issues,
            without affecting the ones that already reference it.
        due_date: new date, YYYY-MM-DD (empty = leave alone).
    """
    if status and status not in VALID_STATUSES:
        return f"Invalid status: '{status}'. Use open, locked, or closed."

    payload = {}
    if name:
        payload["name"] = name
    if description:
        payload["description"] = description
    if status:
        payload["status"] = status
    if due_date:
        payload["due_date"] = due_date

    if not payload:
        return f"Nothing to update on version #{version_id}: no field was provided."

    get_client().request(
        "PUT", f"/versions/{version_id}.json", json={"version": payload}
    )
    return f"Version #{version_id} updated ({', '.join(sorted(payload))})."


@tool
def delete_version(version_id: int) -> str:
    """Delete a version. Issues that reference it are left without a target version.

    To take a version out of circulation without losing the historical link,
    prefer update_version with status='closed'.

    Args:
        version_id: ID of the version to delete.
    """
    get_client().request("DELETE", f"/versions/{version_id}.json")
    return f"Version #{version_id} deleted."
