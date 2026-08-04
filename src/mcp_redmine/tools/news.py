"""Project and instance-wide news."""

from __future__ import annotations

from mcp_redmine.app import get_client, tool
from mcp_redmine.format import dumps


@tool
def list_news(project_identifier: str = "", limit: int = 25) -> str:
    """List news items.

    Args:
        project_identifier: restrict to a project (empty = all).
        limit: maximum number of news items.
    """
    path = "/news.json"
    if project_identifier:
        path = f"/projects/{project_identifier}/news.json"

    data = get_client().request("GET", path, params={"limit": limit})
    news = [
        {
            "id": n["id"],
            "title": n.get("title"),
            "summary": n.get("summary"),
            "author": n.get("author", {}).get("name"),
            "project": n.get("project", {}).get("name"),
            "created_on": n.get("created_on"),
        }
        for n in data.get("news", [])
    ]
    return dumps(news)


@tool
def get_news_item(news_id: int) -> str:
    """Show a news item's full text and comments.

    Args:
        news_id: news item ID (use list_news).
    """
    data = get_client().request(
        "GET", f"/news/{news_id}.json?include=comments,attachments"
    )
    return dumps(data.get("news", {}))


@tool
def create_news(
    project_identifier: str,
    title: str,
    description: str,
    summary: str = "",
) -> str:
    """Publish a news item in a project.

    News is visible to every project member and triggers an email
    notification according to the instance's configuration — not a silent
    draft.

    Args:
        project_identifier: project identifier.
        title: news title.
        description: news body.
        summary: summary line shown in the listing.
    """
    payload = {"title": title, "description": description}
    if summary:
        payload["summary"] = summary

    data = get_client().request(
        "POST", f"/projects/{project_identifier}/news.json", json={"news": payload}
    )

    if data:
        return dumps(data.get("news", {}))
    return f"News item '{title}' published in '{project_identifier}'."


@tool
def update_news(
    news_id: int,
    title: str = "",
    description: str = "",
    summary: str = "",
) -> str:
    """Update a published news item.

    Available since Redmine 5.1; older versions respond with 404.

    Args:
        news_id: news item ID.
        title: new title (empty = leave alone).
        description: new body (empty = leave alone).
        summary: new summary (empty = leave alone).
    """
    payload = {}
    if title:
        payload["title"] = title
    if description:
        payload["description"] = description
    if summary:
        payload["summary"] = summary

    if not payload:
        return f"Nothing to update on news item #{news_id}: no field was provided."

    get_client().request("PUT", f"/news/{news_id}.json", json={"news": payload})
    return f"News item #{news_id} updated ({', '.join(sorted(payload))})."


@tool
def delete_news(news_id: int) -> str:
    """Delete a news item. Available since Redmine 5.1.

    Args:
        news_id: news item ID.
    """
    get_client().request("DELETE", f"/news/{news_id}.json")
    return f"News item #{news_id} deleted."
