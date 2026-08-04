"""Issue categories within a project."""

from __future__ import annotations

from typing import Any

from mcp_redmine.app import get_client, tool
from mcp_redmine.format import dumps


@tool
def list_project_categories(project_identifier: str) -> str:
    """List a project's issue categories, with their IDs.

    Args:
        project_identifier: project identifier (e.g. 'my-project').
    """
    data = get_client().request(
        "GET", f"/projects/{project_identifier}/issue_categories.json"
    )
    categories = [
        {
            "id": c["id"],
            "name": c["name"],
            "default_assignee": c.get("assigned_to", {}).get("name"),
        }
        for c in data.get("issue_categories", [])
    ]
    return dumps(categories)


@tool
def create_project_category(
    project_identifier: str,
    name: str,
    assigned_to_id: int = 0,
) -> str:
    """Create an issue category in a project.

    Args:
        project_identifier: project identifier.
        name: category name (e.g. 'Infrastructure').
        assigned_to_id: user assigned by default to issues in this category
            (0 = none).
    """
    payload: dict[str, Any] = {"name": name}
    if assigned_to_id:
        payload["assigned_to_id"] = assigned_to_id

    data = get_client().request(
        "POST",
        f"/projects/{project_identifier}/issue_categories.json",
        json={"issue_category": payload},
    )
    return dumps(data.get("issue_category", {}))


@tool
def update_project_category(
    category_id: int,
    name: str = "",
    assigned_to_id: int = 0,
) -> str:
    """Update an issue category.

    Args:
        category_id: category ID (use list_project_categories).
        name: new name (empty = leave alone).
        assigned_to_id: new default assignee (0 = leave alone).
    """
    payload: dict[str, Any] = {}
    if name:
        payload["name"] = name
    if assigned_to_id:
        payload["assigned_to_id"] = assigned_to_id

    if not payload:
        return f"Nothing to update on category #{category_id}: no field was provided."

    get_client().request(
        "PUT",
        f"/issue_categories/{category_id}.json",
        json={"issue_category": payload},
    )
    return f"Category #{category_id} updated ({', '.join(sorted(payload))})."


@tool
def delete_project_category(category_id: int, reassign_to_id: int = 0) -> str:
    """Delete an issue category.

    Issues that used the category are left without one, unless you give
    another category to receive them.

    Args:
        category_id: ID of the category to delete.
        reassign_to_id: ID of the category that receives the orphaned issues
            (0 = leave them without a category).
    """
    path = f"/issue_categories/{category_id}.json"
    if reassign_to_id:
        path += f"?reassign_to_id={reassign_to_id}"

    get_client().request("DELETE", path)

    destination = (
        f", issues reassigned to category #{reassign_to_id}"
        if reassign_to_id
        else ", issues were left without a category"
    )
    return f"Category #{category_id} deleted{destination}."
