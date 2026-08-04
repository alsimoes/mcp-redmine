"""Project membership: who belongs to a project, and with which roles."""

from __future__ import annotations

from mcp_redmine.app import get_client, tool
from mcp_redmine.format import dumps


@tool
def list_project_members(project_identifier: str) -> str:
    """List a project's members and each one's roles.

    Args:
        project_identifier: project identifier.
    """
    data = get_client().request(
        "GET", f"/projects/{project_identifier}/memberships.json?limit=100"
    )
    members = [
        {
            "membership_id": m["id"],
            "user_or_group": (m.get("user") or m.get("group") or {}).get("name"),
            "user_id": (m.get("user") or {}).get("id"),
            "roles": [role["name"] for role in m.get("roles", [])],
        }
        for m in data.get("memberships", [])
    ]
    return dumps(members)


@tool
def add_project_member(
    project_identifier: str,
    user_id: int,
    role_ids: list[int],
) -> str:
    """Add a user as a project member, with one or more roles.

    Args:
        project_identifier: project identifier.
        user_id: user ID (use list_users).
        role_ids: list of role IDs (use list_roles).
    """
    if not role_ids:
        return "Provide at least one role — a member with no role has no permissions."

    data = get_client().request(
        "POST",
        f"/projects/{project_identifier}/memberships.json",
        json={"membership": {"user_id": user_id, "role_ids": role_ids}},
    )
    return dumps(data.get("membership", {}))


@tool
def update_project_member(membership_id: int, role_ids: list[int]) -> str:
    """Replace a member's roles.

    The given list becomes the complete list — any role not in it is
    removed.

    Args:
        membership_id: membership ID (the 'membership_id' field in
            list_project_members), not the user's ID.
        role_ids: new, complete list of role IDs.
    """
    if not role_ids:
        return "Provide at least one role. To remove access, use remove_project_member."

    get_client().request(
        "PUT",
        f"/memberships/{membership_id}.json",
        json={"membership": {"role_ids": role_ids}},
    )
    return f"Membership #{membership_id} now has roles {role_ids}."


@tool
def remove_project_member(membership_id: int) -> str:
    """Remove a member from a project.

    The user loses access, but what they created remains — issues, comments,
    and time entries stay recorded under their name.

    Args:
        membership_id: membership ID (the 'membership_id' field in
            list_project_members), not the user's ID.
    """
    get_client().request("DELETE", f"/memberships/{membership_id}.json")
    return f"Membership #{membership_id} removed."
