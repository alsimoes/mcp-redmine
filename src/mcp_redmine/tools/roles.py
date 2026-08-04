"""Roles."""

from __future__ import annotations

from mcp_redmine.app import get_client, tool
from mcp_redmine.format import dumps


@tool
def list_roles() -> str:
    """List the instance's roles, with their IDs."""
    data = get_client().request("GET", "/roles.json")
    roles = [{"id": r["id"], "name": r["name"]} for r in data.get("roles", [])]
    return dumps(roles)


@tool
def get_role(role_id: int) -> str:
    """Show a role's details, including the full list of granted permissions.

    Useful for understanding why an operation is being refused, before trying
    again.

    Args:
        role_id: role ID (use list_roles).
    """
    data = get_client().request("GET", f"/roles/{role_id}.json")
    return dumps(data.get("role", {}))
