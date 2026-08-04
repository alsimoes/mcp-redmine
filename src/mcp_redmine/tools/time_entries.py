"""Time tracking: logging and querying time entries."""

from __future__ import annotations

from typing import Any

from mcp_redmine.app import get_client, tool
from mcp_redmine.format import dumps


@tool
def list_time_entries(
    project_identifier: str = "",
    issue_id: int = 0,
    user_id: str = "",
    start_date: str = "",
    end_date: str = "",
    limit: int = 50,
) -> str:
    """List time entries, with optional filters.

    Args:
        project_identifier: filter by project (identifier or id).
        issue_id: filter by a specific issue (0 = ignore this filter).
        user_id: filter by user; use 'me' for the API key's own user.
        start_date: minimum date, YYYY-MM-DD format.
        end_date: maximum date, YYYY-MM-DD format.
        limit: maximum number of entries returned.
    """
    params: dict[str, Any] = {"limit": limit}
    if project_identifier:
        params["project_id"] = project_identifier
    if issue_id:
        params["issue_id"] = issue_id
    if user_id:
        params["user_id"] = user_id
    if start_date:
        params["from"] = start_date
    if end_date:
        params["to"] = end_date

    data = get_client().request("GET", "/time_entries.json", params=params)
    entries = [
        {
            "id": e["id"],
            "issue_id": e.get("issue", {}).get("id"),
            "project": e.get("project", {}).get("name"),
            "user": e.get("user", {}).get("name"),
            "hours": e.get("hours"),
            "activity": e.get("activity", {}).get("name"),
            "comment": e.get("comments"),
            "date": e.get("spent_on"),
        }
        for e in data.get("time_entries", [])
    ]
    total_hours = sum(e["hours"] or 0 for e in entries)
    return dumps({"total_hours": total_hours, "entries": entries})


@tool
def get_time_entry(time_entry_id: int) -> str:
    """Show a time entry's details.

    Args:
        time_entry_id: time entry ID (use list_time_entries).
    """
    data = get_client().request("GET", f"/time_entries/{time_entry_id}.json")
    return dumps(data.get("time_entry", {}))


@tool
def log_time(
    hours: float,
    date: str,
    issue_id: int = 0,
    project_identifier: str = "",
    activity_id: int = 0,
    comment: str = "",
) -> str:
    """Log time spent, tied to either an issue or a project.

    Args:
        hours: amount of time worked (e.g. 2.5).
        date: date the work was done, YYYY-MM-DD format.
        issue_id: issue ID (use this OR project_identifier, not both).
        project_identifier: project identifier (if not tying this to a
            specific issue).
        activity_id: activity type ID (varies per instance; use
            list_time_entry_activities to see the options).
        comment: description of what was done.
    """
    if not issue_id and not project_identifier:
        return "Error: provide issue_id or project_identifier."

    entry: dict[str, Any] = {
        "hours": hours,
        "spent_on": date,
        "comments": comment,
    }
    if issue_id:
        entry["issue_id"] = issue_id
    if project_identifier:
        entry["project_id"] = project_identifier
    if activity_id:
        entry["activity_id"] = activity_id

    data = get_client().request(
        "POST", "/time_entries.json", json={"time_entry": entry}
    )
    return dumps(data.get("time_entry", {}))


@tool
def update_time_entry(
    time_entry_id: int,
    hours: float = 0,
    comment: str = "",
    activity_id: int = 0,
) -> str:
    """Update an existing time entry.

    Args:
        time_entry_id: ID of the time entry to update.
        hours: new hours value (0 = leave alone).
        comment: new comment (empty = leave alone).
        activity_id: new activity ID (0 = leave alone).
    """
    entry: dict[str, Any] = {}
    if hours:
        entry["hours"] = hours
    if comment:
        entry["comments"] = comment
    if activity_id:
        entry["activity_id"] = activity_id

    get_client().request(
        "PUT", f"/time_entries/{time_entry_id}.json", json={"time_entry": entry}
    )
    return f"Time entry #{time_entry_id} updated successfully."


@tool
def delete_time_entry(time_entry_id: int) -> str:
    """Delete a time entry by ID."""
    get_client().request("DELETE", f"/time_entries/{time_entry_id}.json")
    return f"Time entry #{time_entry_id} deleted successfully."


@tool
def list_time_entry_activities() -> str:
    """List the activity types available for logging time.

    For example: Development, Design, Support.
    """
    data = get_client().request("GET", "/enumerations/time_entry_activities.json")
    return dumps(data.get("time_entry_activities", []))
