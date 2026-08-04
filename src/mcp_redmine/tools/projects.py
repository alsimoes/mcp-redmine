"""Projects: list, read, create, update, archive."""

from __future__ import annotations

from mcp_redmine.app import get_client, tool
from mcp_redmine.format import dumps


@tool
def list_projects() -> str:
    """List every project available in Redmine."""
    data = get_client().request("GET", "/projects.json?limit=100")
    projects = [
        {"id": p["id"], "name": p["name"], "identifier": p["identifier"]}
        for p in data.get("projects", [])
    ]
    return dumps(projects)


@tool
def get_project(project_identifier: str) -> str:
    """Show a project's details: description, enabled modules, trackers, and categories.

    Args:
        project_identifier: project identifier.
    """
    data = get_client().request(
        "GET",
        f"/projects/{project_identifier}.json"
        "?include=trackers,issue_categories,enabled_modules",
    )
    return dumps(data.get("project", {}))


@tool
def create_project(
    name: str,
    identifier: str,
    description: str = "",
    parent_project_id: int = 0,
    is_public: bool = False,
) -> str:
    """Create a project.

    Args:
        name: display name.
        identifier: URL identifier — lowercase letters, digits, and hyphens,
            immutable after creation.
        description: project description.
        parent_project_id: parent project ID, to create this as a subproject.
        is_public: whether it's visible to non-member users. The default here
            is private, more conservative than Redmine's own default.
    """
    payload = {"name": name, "identifier": identifier, "is_public": is_public}
    if description:
        payload["description"] = description
    if parent_project_id:
        payload["parent_id"] = parent_project_id

    data = get_client().request("POST", "/projects.json", json={"project": payload})
    return dumps(data.get("project", {}))


@tool
def update_project(
    project_identifier: str,
    name: str = "",
    description: str = "",
    homepage: str = "",
) -> str:
    """Update a project. Only changes the fields that are provided.

    The 'identifier' cannot be changed after creation — that's a Redmine
    limitation, not one of this server.

    Args:
        project_identifier: project identifier.
        name: new display name (empty = leave alone).
        description: new description (empty = leave alone).
        homepage: project URL (empty = leave alone).
    """
    payload = {}
    if name:
        payload["name"] = name
    if description:
        payload["description"] = description
    if homepage:
        payload["homepage"] = homepage

    if not payload:
        return f"Nothing to update on '{project_identifier}': no field was provided."

    get_client().request(
        "PUT", f"/projects/{project_identifier}.json", json={"project": payload}
    )
    return f"Project '{project_identifier}' updated ({', '.join(sorted(payload))})."


@tool
def archive_project(project_identifier: str, archive: bool = True) -> str:
    """Archive or unarchive a project.

    An archived project becomes read-only and disappears from listings,
    without losing anything. It's the reversible alternative to deletion,
    which this server deliberately does not expose — deletion is irreversible
    and takes issues, time entries, and wiki content with it. Deleting a
    project for real is a web UI operation.

    Args:
        project_identifier: project identifier.
        archive: True archives, False unarchives.
    """
    action = "archive" if archive else "unarchive"
    get_client().request("PUT", f"/projects/{project_identifier}/{action}.json")
    verb = "archived" if archive else "unarchived"
    return f"Project '{project_identifier}' {verb}."
