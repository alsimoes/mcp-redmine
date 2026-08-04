"""Project wiki pages."""

from __future__ import annotations

from mcp_redmine.app import get_client, tool
from mcp_redmine.errors import RedmineError, redmine_error_message
from mcp_redmine.format import dumps
from mcp_redmine.uploads import upload_file


@tool
def list_wiki_pages(project_identifier: str) -> str:
    """List every wiki page of a project.

    Args:
        project_identifier: project identifier (e.g. 'my-project').
    """
    data = get_client().request(
        "GET", f"/projects/{project_identifier}/wiki/index.json"
    )
    pages = [
        {
            "title": p["title"],
            "version": p.get("version"),
            "updated_on": p.get("updated_on"),
            "parent": p.get("parent", {}).get("title") if p.get("parent") else None,
        }
        for p in data.get("wiki_pages", [])
    ]
    return dumps(pages)


@tool
def get_wiki_page(project_identifier: str, title: str, version: int = 0) -> str:
    """Read the content of a specific wiki page.

    Args:
        project_identifier: project identifier.
        title: page title (e.g. 'Home'). Case-sensitive, as in Redmine.
        version: version number to read (0 = most recent).
    """
    path = f"/projects/{project_identifier}/wiki/{title}.json"
    if version:
        path = f"/projects/{project_identifier}/wiki/{title}/{version}.json"
    data = get_client().request("GET", path)
    page = data.get("wiki_page", {})
    return dumps(
        {
            "title": page.get("title"),
            "text": page.get("text"),
            "version": page.get("version"),
            "author": page.get("author", {}).get("name"),
            "updated_on": page.get("updated_on"),
        }
    )


@tool
def create_or_update_wiki_page(
    project_identifier: str,
    title: str,
    text: str,
    comment: str = "",
    parent_page: str = "",
) -> str:
    """Create a new wiki page, or update an existing one.

    Redmine uses the same PUT endpoint for both cases.

    Args:
        project_identifier: project identifier.
        title: page title (e.g. 'Home').
        text: content in Markdown or Textile, depending on the instance's
            configuration (Administration -> Settings -> General -> Text
            formatting).
        comment: comment about the edit (shows up in the page's history).
        parent_page: title of the page that should become this one's parent,
            to nest it in the wiki index. Empty = leave the current nesting
            alone; on a new page, leaves it at the root.
    """
    payload = {"text": text, "comments": comment}
    if parent_page:
        payload["parent_title"] = parent_page

    get_client().request(
        "PUT",
        f"/projects/{project_identifier}/wiki/{title}.json",
        json={"wiki_page": payload},
    )

    nesting = f", nested under '{parent_page}'" if parent_page else ""
    return f"Wiki page '{title}' saved in '{project_identifier}'{nesting}."


@tool
def attach_file_to_wiki_page(
    project_identifier: str,
    title: str,
    file_path: str,
    comment: str = "",
    file_name: str = "",
) -> str:
    """Attach a file to an existing wiki page.

    The page's text is preserved: this tool reads the current content and
    rewrites it together with the attachment, because Redmine's endpoint
    replaces the whole page.

    The path is resolved on the machine running this MCP server.

    Args:
        project_identifier: project identifier.
        title: title of the page that will receive the attachment.
        file_path: full path of the file on the server's machine.
        comment: edit comment, shown in the page's history.
        file_name: display name (empty = use the file's own name).
    """
    client = get_client()

    try:
        current = client.request(
            "GET", f"/projects/{project_identifier}/wiki/{title}.json"
        )
    except RedmineError as exc:
        return f"Error reading page '{title}': {redmine_error_message(exc)}"

    current_text = current.get("wiki_page", {}).get("text", "")

    try:
        token, name, content_type = upload_file(client, file_path, file_name)
    except RedmineError as exc:
        return f"Upload error: {redmine_error_message(exc)}"

    payload = {
        "text": current_text,
        "comments": comment or f"Added attachment '{name}'",
        "uploads": [{"token": token, "filename": name, "content_type": content_type}],
    }

    try:
        client.request(
            "PUT",
            f"/projects/{project_identifier}/wiki/{title}.json",
            json={"wiki_page": payload},
        )
    except RedmineError as exc:
        return (
            f"Upload of '{name}' succeeded, but linking it to page "
            f"'{title}' failed: {redmine_error_message(exc)}. The token "
            "will expire on its own."
        )

    return f"'{name}' ({content_type}) attached to page '{title}'."


@tool
def delete_wiki_page(project_identifier: str, title: str) -> str:
    """Delete a wiki page (and its sub-pages, per Redmine's default behavior).

    Args:
        project_identifier: project identifier.
        title: title of the page to delete.
    """
    get_client().request("DELETE", f"/projects/{project_identifier}/wiki/{title}.json")
    return f"Wiki page '{title}' deleted from '{project_identifier}'."
