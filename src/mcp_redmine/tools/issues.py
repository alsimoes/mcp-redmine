"""Issues: list, read, create, update, bulk update, delete.

Also covers watchers and comments, which operate on issue history.
"""

from __future__ import annotations

from typing import Any

from mcp_redmine.app import get_client, tool
from mcp_redmine.errors import RedmineError, redmine_error_message
from mcp_redmine.format import dumps


def _optional_issue_fields(
    category_id: int = 0,
    fixed_version_id: int = 0,
    assigned_to_id: int = 0,
    parent_issue_id: int = 0,
    start_date: str = "",
    due_date: str = "",
    done_ratio: int = -1,
    estimated_hours: float = -1.0,
    custom_fields: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the optional fields shared by create_issue and update_issue.

    Only fields that were actually provided are added to the payload — the
    sentinels (0, "", -1) mean "leave this field alone". That matters for
    update_issue in particular: sending a field with an empty value would
    clear the existing content in Redmine.

    Returns:
        The subset of the Redmine issue payload built from the given fields.
    """
    fields: dict[str, Any] = {}

    if category_id:
        fields["category_id"] = category_id
    if fixed_version_id:
        fields["fixed_version_id"] = fixed_version_id
    if assigned_to_id:
        fields["assigned_to_id"] = assigned_to_id
    if parent_issue_id:
        fields["parent_issue_id"] = parent_issue_id
    if start_date:
        fields["start_date"] = start_date
    if due_date:
        fields["due_date"] = due_date
    if done_ratio >= 0:
        fields["done_ratio"] = done_ratio
    if estimated_hours >= 0:
        fields["estimated_hours"] = estimated_hours
    if custom_fields:
        fields["custom_fields"] = [
            {"id": int(field_id), "value": value}
            for field_id, value in custom_fields.items()
        ]

    return fields


@tool
def list_issues(
    project_identifier: str = "",
    status: str = "open",
    limit: int = 25,
    tracker_id: int = 0,
    category_id: int = 0,
    fixed_version_id: int = 0,
    assigned_to_id: int = 0,
    author_id: int = 0,
    parent_issue_id: int = 0,
    subject_contains: str = "",
    created_after: str = "",
    created_before: str = "",
    updated_after: str = "",
    custom_fields: dict[str, str] | None = None,
    sort_by: str = "",
    offset: int = 0,
    query_id: int = 0,
) -> str:
    """List Redmine issues, with filters.

    Args:
        project_identifier: project identifier. Empty = all projects.
        status: 'open', 'closed', '*' (all), or the ID of a specific status.
        limit: maximum issues per page. Redmine caps this at 100.
        tracker_id: filter by tracker (use list_trackers).
        category_id: filter by category (use list_project_categories).
        fixed_version_id: filter by target version (use list_project_versions).
        assigned_to_id: filter by assignee.
        author_id: filter by who created the issue.
        parent_issue_id: return the subtasks of an issue.
        subject_contains: text contained in the subject (partial match).
        created_after: YYYY-MM-DD, issues created on or after this date.
        created_before: YYYY-MM-DD, issues created on or before this date.
        updated_after: YYYY-MM-DD, issues updated on or after this date.
        custom_fields: map of {field_id: value}, e.g. {"1": "8"}.
        sort_by: field and direction, e.g. 'priority:desc', 'updated_on:desc',
            'id:asc'. Several can be comma-separated.
        offset: how many issues to skip — use together with 'limit' to
            paginate.
        query_id: run a saved query (use list_saved_queries). When given, the
            other filters are ignored by Redmine.

    Returns:
        JSON with the total number of matching issues (not just this page),
        so it's possible to tell whether pagination is needed without
        guessing.
    """
    params: dict[str, Any] = {"limit": limit}

    if query_id:
        params["query_id"] = query_id
    else:
        params["status_id"] = status
        if tracker_id:
            params["tracker_id"] = tracker_id
        if category_id:
            params["category_id"] = category_id
        if fixed_version_id:
            params["fixed_version_id"] = fixed_version_id
        if assigned_to_id:
            params["assigned_to_id"] = assigned_to_id
        if author_id:
            params["author_id"] = author_id
        if parent_issue_id:
            params["parent_id"] = parent_issue_id
        if subject_contains:
            params["subject"] = f"~{subject_contains}"
        if created_after and created_before:
            params["created_on"] = f"><{created_after}|{created_before}"
        elif created_after:
            params["created_on"] = f">={created_after}"
        elif created_before:
            params["created_on"] = f"<={created_before}"
        if updated_after:
            params["updated_on"] = f">={updated_after}"
        if custom_fields:
            for field_id, value in custom_fields.items():
                params[f"cf_{field_id}"] = value

    if project_identifier:
        params["project_id"] = project_identifier
    if sort_by:
        params["sort"] = sort_by
    if offset:
        params["offset"] = offset

    data = get_client().request("GET", "/issues.json", params=params)

    issues = [
        {
            "id": i["id"],
            "subject": i["subject"],
            "tracker": i.get("tracker", {}).get("name"),
            "status": i["status"]["name"],
            "priority": i["priority"]["name"],
            "category": i.get("category", {}).get("name"),
            "version": i.get("fixed_version", {}).get("name"),
            "project": i["project"]["name"],
            "assigned_to": i.get("assigned_to", {}).get("name", "-"),
            "updated_on": i.get("updated_on"),
        }
        for i in data.get("issues", [])
    ]

    total = data.get("total_count", len(issues))
    returned = len(issues)
    remaining = max(0, total - offset - returned)

    return dumps(
        {
            "total": total,
            "returned": returned,
            "offset": offset,
            "remaining": remaining,
            "issues": issues,
        }
    )


@tool
def get_issue(issue_id: int, include_history: bool = True) -> str:
    """Return every detail of an issue.

    Includes the description, attachments, relations, watchers, and
    subtasks.

    Args:
        issue_id: issue ID.
        include_history: also fetch the comments and change log. Turn this
            off for long issues when only the current field values matter.
    """
    includes = ["attachments", "relations", "watchers", "children"]
    if include_history:
        includes.insert(0, "journals")

    data = get_client().request(
        "GET", f"/issues/{issue_id}.json?include={','.join(includes)}"
    )
    return dumps(data.get("issue", {}))


@tool
def bulk_update_issues(
    issue_ids: list[int],
    status_id: int = 0,
    notes: str = "",
    priority_id: int = 0,
    tracker_id: int = 0,
    category_id: int = 0,
    fixed_version_id: int = 0,
    assigned_to_id: int = 0,
    start_date: str = "",
    due_date: str = "",
    done_ratio: int = -1,
    estimated_hours: float = -1.0,
    custom_fields: dict[str, str] | None = None,
) -> str:
    """Apply the same change to several issues at once.

    Useful when the change is identical across issues — moving a batch of
    cards to a new status, fixing the category for a whole set, assigning a
    version. There is no equivalent for creation: each issue has its own
    content, so batching creation would not save anything.

    This does not abort on the first error: it tries every issue and reports
    each individual result.

    Every field besides issue_ids uses the same "leave alone" sentinels as
    update_issue: 0 for IDs, empty string for text and dates, -1 for
    percentage and hours.

    Args:
        issue_ids: IDs of the issues to change.
        status_id: new status ID (0 = leave alone).
        notes: comment appended to each issue's history.
        priority_id: new priority (0 = leave alone).
        tracker_id: new tracker (0 = leave alone).
        category_id: new category (0 = leave alone).
        fixed_version_id: new target version (0 = leave alone).
        assigned_to_id: new assignee (0 = leave alone).
        start_date: new start date, YYYY-MM-DD (empty = leave alone).
        due_date: new due date, YYYY-MM-DD (empty = leave alone).
        done_ratio: 0 to 100 (-1 = leave alone).
        estimated_hours: estimated effort in hours (-1 = leave alone).
        custom_fields: map of {field_id: value}, e.g. {"1": "5"}.
    """
    if not issue_ids:
        return "Provide at least one issue."

    fields: dict[str, Any] = {}
    if status_id:
        fields["status_id"] = status_id
    if notes:
        fields["notes"] = notes
    if priority_id:
        fields["priority_id"] = priority_id
    if tracker_id:
        fields["tracker_id"] = tracker_id

    fields.update(
        _optional_issue_fields(
            category_id=category_id,
            fixed_version_id=fixed_version_id,
            assigned_to_id=assigned_to_id,
            start_date=start_date,
            due_date=due_date,
            done_ratio=done_ratio,
            estimated_hours=estimated_hours,
            custom_fields=custom_fields,
        )
    )

    if not fields:
        return "Nothing to update: no field was provided."

    client = get_client()
    results, updated, failed = [], 0, 0
    for issue_id in issue_ids:
        try:
            client.request("PUT", f"/issues/{issue_id}.json", json={"issue": fields})
            results.append({"issue": issue_id, "result": "ok"})
            updated += 1
        except RedmineError as exc:
            results.append(
                {
                    "issue": issue_id,
                    "result": "error",
                    "detail": redmine_error_message(exc),
                }
            )
            failed += 1

    return dumps(
        {
            "applied_fields": sorted(k for k in fields if k != "notes"),
            "attempted": len(issue_ids),
            "updated": updated,
            "failed": failed,
            "details": results if failed else "all updated",
        }
    )


@tool
def create_issue(
    project_identifier: str,
    subject: str,
    description: str = "",
    tracker_id: int = 1,
    priority_id: int = 2,
    status_id: int = 0,
    category_id: int = 0,
    fixed_version_id: int = 0,
    assigned_to_id: int = 0,
    parent_issue_id: int = 0,
    start_date: str = "",
    due_date: str = "",
    estimated_hours: float = -1.0,
    custom_fields: dict[str, str] | None = None,
) -> str:
    """Create a new issue in Redmine.

    Args:
        project_identifier: project identifier (e.g. 'my-project').
        subject: issue title.
        description: detailed description.
        tracker_id: tracker ID (varies per instance; use list_trackers).
        priority_id: priority ID (use list_statuses_and_priorities).
        status_id: status ID (0 = use the workflow's initial status).
        category_id: category ID (use list_project_categories).
        fixed_version_id: target version ID (use list_project_versions).
        assigned_to_id: assignee's user ID.
        parent_issue_id: parent issue ID, to create this as a subtask.
        start_date: start date, YYYY-MM-DD format.
        due_date: due date, YYYY-MM-DD format.
        estimated_hours: estimated effort in hours (-1 = not provided).
        custom_fields: map of {field_id: value}, e.g. {"1": "5"}. Use
            list_custom_fields to discover the IDs.

    Every field besides project and subject is optional; anything not
    provided is left to the project's defaults.
    """
    payload = {
        "project_id": project_identifier,
        "subject": subject,
        "description": description,
        "tracker_id": tracker_id,
        "priority_id": priority_id,
    }
    if status_id:
        payload["status_id"] = status_id

    payload.update(
        _optional_issue_fields(
            category_id=category_id,
            fixed_version_id=fixed_version_id,
            assigned_to_id=assigned_to_id,
            parent_issue_id=parent_issue_id,
            start_date=start_date,
            due_date=due_date,
            estimated_hours=estimated_hours,
            custom_fields=custom_fields,
        )
    )

    data = get_client().request("POST", "/issues.json", json={"issue": payload})
    return dumps(data.get("issue", {}))


@tool
def update_issue(
    issue_id: int,
    status_id: int = 0,
    notes: str = "",
    subject: str = "",
    description: str = "",
    priority_id: int = 0,
    tracker_id: int = 0,
    category_id: int = 0,
    fixed_version_id: int = 0,
    assigned_to_id: int = 0,
    parent_issue_id: int = 0,
    start_date: str = "",
    due_date: str = "",
    done_ratio: int = -1,
    estimated_hours: float = -1.0,
    custom_fields: dict[str, str] | None = None,
) -> str:
    """Update an existing issue. Only changes the fields that are provided.

    Args:
        issue_id: ID of the issue to update.
        status_id: new status ID (0 = leave alone).
        notes: comment to add to the history (does not replace the
            description).
        subject: new title (empty = leave alone).
        description: new description — REPLACES the existing one entirely.
        priority_id: new priority (0 = leave alone).
        tracker_id: new tracker (0 = leave alone).
        category_id: new category (0 = leave alone).
        fixed_version_id: new target version (0 = leave alone).
        assigned_to_id: new assignee (0 = leave alone).
        parent_issue_id: new parent issue (0 = leave alone).
        start_date: new start date, YYYY-MM-DD (empty = leave alone).
        due_date: new due date, YYYY-MM-DD (empty = leave alone).
        done_ratio: 0 to 100 (-1 = leave alone).
        estimated_hours: estimated effort in hours (-1 = leave alone).
        custom_fields: map of {field_id: value}, e.g. {"1": "5"}.

    "Leave alone" sentinels: 0 for IDs, empty string for text and dates, -1
    for percentage and hours. There is no way to clear a field through this
    tool — to blank out a date or remove an assignee, use the Redmine web UI.
    """
    payload: dict[str, Any] = {}
    if status_id:
        payload["status_id"] = status_id
    if notes:
        payload["notes"] = notes
    if subject:
        payload["subject"] = subject
    if description:
        payload["description"] = description
    if priority_id:
        payload["priority_id"] = priority_id
    if tracker_id:
        payload["tracker_id"] = tracker_id

    payload.update(
        _optional_issue_fields(
            category_id=category_id,
            fixed_version_id=fixed_version_id,
            assigned_to_id=assigned_to_id,
            parent_issue_id=parent_issue_id,
            start_date=start_date,
            due_date=due_date,
            done_ratio=done_ratio,
            estimated_hours=estimated_hours,
            custom_fields=custom_fields,
        )
    )

    if not payload:
        return f"Nothing to update on #{issue_id}: no field was provided."

    get_client().request("PUT", f"/issues/{issue_id}.json", json={"issue": payload})

    changed = sorted(k for k in payload if k != "notes")
    summary = ", ".join(changed) if changed else "comment only"
    return f"Issue #{issue_id} updated successfully ({summary})."


@tool
def delete_issue(issue_id: int) -> str:
    """Permanently delete an issue.

    WARNING: this is irreversible and takes the issue's subtasks, time
    entries, and history with it. Redmine has no trash can. Prefer moving to
    a closed status (e.g. Cancelled) when the goal is only to take it off the
    board.

    Args:
        issue_id: ID of the issue to delete.
    """
    get_client().request("DELETE", f"/issues/{issue_id}.json")
    return f"Issue #{issue_id} permanently deleted."


@tool
def add_watcher(issue_id: int, user_id: int) -> str:
    """Add a watcher to an issue.

    Args:
        issue_id: issue ID.
        user_id: ID of the user to add as a watcher (use list_users).
    """
    get_client().request(
        "POST", f"/issues/{issue_id}/watchers.json", json={"user_id": user_id}
    )
    return f"User #{user_id} is now watching issue #{issue_id}."


@tool
def remove_watcher(issue_id: int, user_id: int) -> str:
    """Remove a watcher from an issue.

    Args:
        issue_id: issue ID.
        user_id: ID of the user to remove.
    """
    get_client().request("DELETE", f"/issues/{issue_id}/watchers/{user_id}.json")
    return f"User #{user_id} stopped watching issue #{issue_id}."


@tool
def update_journal_note(journal_id: int, text: str) -> str:
    """Edit the text of a comment already posted to an issue's history.

    The journal ID is the 'id' field of each entry in 'journals', visible via
    get_issue — not to be confused with the issue ID.

    This endpoint is marked alpha in the Redmine documentation and may not
    exist in older versions; a 404 usually means that.

    Args:
        journal_id: ID of the history entry (journal).
        text: new text for the comment.
    """
    get_client().request(
        "PUT", f"/journals/{journal_id}.json", json={"journal": {"notes": text}}
    )
    return f"Comment #{journal_id} updated."
