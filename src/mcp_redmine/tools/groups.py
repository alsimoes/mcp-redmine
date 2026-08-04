"""User groups."""

from __future__ import annotations

from typing import Any

from mcp_redmine.app import get_client, tool
from mcp_redmine.format import dumps


@tool
def list_groups() -> str:
    """List the instance's user groups. Requires administrator privileges."""
    data = get_client().request("GET", "/groups.json")
    groups = [{"id": g["id"], "name": g["name"]} for g in data.get("groups", [])]
    return dumps(groups)


@tool
def get_group(group_id: int) -> str:
    """Show a group's details: its members and the projects it belongs to.

    Args:
        group_id: group ID.
    """
    data = get_client().request(
        "GET", f"/groups/{group_id}.json?include=users,memberships"
    )
    return dumps(data.get("group", {}))


@tool
def create_group(name: str, user_ids: list[int] | None = None) -> str:
    """Create a user group.

    A group grants permissions to several people at once: add it as a
    project member and every member inherits the roles.

    Args:
        name: group name.
        user_ids: initial members' IDs (optional).
    """
    payload: dict[str, Any] = {"name": name}
    if user_ids:
        payload["user_ids"] = user_ids

    data = get_client().request("POST", "/groups.json", json={"group": payload})
    return dumps(data.get("group", {}))


@tool
def update_group(
    group_id: int, name: str = "", user_ids: list[int] | None = None
) -> str:
    """Update a group.

    Args:
        group_id: group ID.
        name: new name (empty = leave alone).
        user_ids: new, COMPLETE list of members — anyone not in it is removed
            from the group. To add one person without touching the rest, use
            add_user_to_group.
    """
    payload: dict[str, Any] = {}
    if name:
        payload["name"] = name
    if user_ids is not None:
        payload["user_ids"] = user_ids

    if not payload:
        return f"Nothing to update on group #{group_id}: no field was provided."

    get_client().request("PUT", f"/groups/{group_id}.json", json={"group": payload})
    return f"Group #{group_id} updated."


@tool
def delete_group(group_id: int) -> str:
    """Delete a group.

    The users themselves keep existing; they only lose the permissions that
    came from it.

    Args:
        group_id: group ID.
    """
    get_client().request("DELETE", f"/groups/{group_id}.json")
    return f"Group #{group_id} deleted."


@tool
def add_user_to_group(group_id: int, user_id: int) -> str:
    """Add a user to a group, without touching the other members.

    Args:
        group_id: group ID.
        user_id: user ID.
    """
    get_client().request(
        "POST", f"/groups/{group_id}/users.json", json={"user_id": user_id}
    )
    return f"User #{user_id} joined group #{group_id}."


@tool
def remove_user_from_group(group_id: int, user_id: int) -> str:
    """Remove a user from a group.

    Args:
        group_id: group ID.
        user_id: user ID.
    """
    get_client().request("DELETE", f"/groups/{group_id}/users/{user_id}.json")
    return f"User #{user_id} left group #{group_id}."
