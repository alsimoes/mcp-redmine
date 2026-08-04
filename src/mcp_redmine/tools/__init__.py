"""Import every tool submodule so its @tool-decorated functions register.

Nothing here is meant to be imported directly — the submodules register
themselves with the shared FastMCP instance (mcp_redmine.app.mcp) as a side
effect of being imported. This module exists purely to trigger that import
in one place, from mcp_redmine.app.main().
"""

from mcp_redmine.tools import (
    attachments,
    categories,
    groups,
    issue_relations,
    issues,
    memberships,
    metadata,
    news,
    project_files,
    projects,
    roles,
    search,
    time_entries,
    users,
    versions,
    wiki,
)

__all__ = [
    "attachments",
    "categories",
    "groups",
    "issue_relations",
    "issues",
    "memberships",
    "metadata",
    "news",
    "project_files",
    "projects",
    "roles",
    "search",
    "time_entries",
    "users",
    "versions",
    "wiki",
]
