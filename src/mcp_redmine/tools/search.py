"""Full-text search and saved queries."""

from __future__ import annotations

from typing import Any

from mcp_redmine.app import get_client, tool
from mcp_redmine.format import dumps


@tool
def search(
    query: str,
    project_identifier: str = "",
    titles_only: bool = False,
    open_issues_only: bool = False,
    all_words: bool = True,
    limit: int = 25,
) -> str:
    """Search for text across issues, wiki pages, news, and other Redmine objects.

    Args:
        query: text to search for.
        project_identifier: restrict to a project (empty = the whole
            instance).
        titles_only: search titles only, not the body.
        open_issues_only: restrict to open issues.
        all_words: require every word in the query; False = match any of
            them.
        limit: maximum number of results.
    """
    params: dict[str, Any] = {"q": query, "limit": limit}
    if titles_only:
        params["titles_only"] = 1
    if open_issues_only:
        params["open_issues"] = 1
    if all_words:
        params["all_words"] = 1

    path = "/search.json"
    if project_identifier:
        path = f"/projects/{project_identifier}/search.json"

    data = get_client().request("GET", path, params=params)

    results = [
        {
            "id": r.get("id"),
            "type": r.get("type"),
            "title": r.get("title"),
            "url": r.get("url"),
            "date": r.get("datetime"),
        }
        for r in data.get("results", [])
    ]
    return dumps({"total": data.get("total_count"), "results": results})


@tool
def list_saved_queries(project_identifier: str = "") -> str:
    """List the saved queries (filters) visible to the API key's user.

    Args:
        project_identifier: restrict to a project's queries (empty = all).
    """
    params: dict[str, Any] = {"limit": 100}
    if project_identifier:
        params["project_id"] = project_identifier

    data = get_client().request("GET", "/queries.json", params=params)
    queries = [
        {
            "id": q["id"],
            "name": q["name"],
            "is_public": q.get("is_public"),
            "project_id": q.get("project_id"),
        }
        for q in data.get("queries", [])
    ]
    return dumps(queries)
