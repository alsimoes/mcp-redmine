"""Read-only reference data.

Covers issue statuses, priorities, trackers, custom fields, and document
categories.
"""

from __future__ import annotations

from mcp_redmine.app import get_client, tool
from mcp_redmine.format import dumps


@tool
def list_statuses_and_priorities() -> str:
    """List the issue statuses and priority levels available on this instance."""
    client = get_client()
    statuses = client.request("GET", "/issue_statuses.json")
    priorities = client.request("GET", "/enumerations/issue_priorities.json")
    return dumps(
        {
            "statuses": statuses.get("issue_statuses", []),
            "priorities": priorities.get("issue_priorities", []),
        }
    )


@tool
def list_trackers() -> str:
    """List the instance's trackers (issue types), with their IDs.

    IDs vary per instance — use this tool before create_issue instead of
    assuming Redmine's default values.
    """
    data = get_client().request("GET", "/trackers.json")
    trackers = [{"id": t["id"], "name": t["name"]} for t in data.get("trackers", [])]
    return dumps(trackers)


@tool
def list_custom_fields() -> str:
    """List the custom fields visible through the API.

    Each entry has an ID, format, and what it applies to. Needed to fill in
    'custom_fields' in create_issue and update_issue.

    Requires the API key's user to be an administrator.
    """
    data = get_client().request("GET", "/custom_fields.json")
    fields = [
        {
            "id": f["id"],
            "name": f["name"],
            "format": f.get("field_format"),
            "applies_to": f.get("customized_type"),
            "required": f.get("is_required"),
            "possible_values": f.get("possible_values"),
        }
        for f in data.get("custom_fields", [])
    ]
    return dumps(fields)


@tool
def list_document_categories() -> str:
    """List the instance's document categories, with their IDs.

    These belong to the Documents module; if it's disabled for a project, the
    list still exists but has no practical use there.
    """
    data = get_client().request("GET", "/enumerations/document_categories.json")
    return dumps(data.get("document_categories", []))
