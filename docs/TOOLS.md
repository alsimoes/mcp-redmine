# Tool reference

Full reference for all 73 tools, grouped by resource. Parameter names match
Redmine's own REST API field names wherever one exists, so the
[Redmine REST API documentation](https://www.redmine.org/projects/redmine/wiki/Rest_api)
doubles as a reference for this server.

Conventions used throughout:

- **"Leave alone" sentinels** on update tools: `0` for IDs, empty string
  `""` for text and dates, `-1` for percentages and hours. There is no way to
  *clear* a field through these tools — blanking a date or removing an
  assignee has to be done in the Redmine web UI.
- IDs (tracker, priority, category, version, role, custom field...) vary per
  Redmine instance. Use the corresponding `list_*` / metadata tool instead of
  assuming default values from the documentation.
- File paths (`file_path` / `caminho_arquivo`-style parameters) are resolved
  **on the machine running this MCP server**, not on the machine of whoever
  is talking to the agent. For local setups that's the same machine; for a
  remote setup, it isn't.

## Issues

| Tool | Purpose |
|---|---|
| `list_issues` | List issues, with filters. |
| `get_issue` | Full detail of one issue, including history. |
| `create_issue` | Create a new issue in a project. |
| `update_issue` | Update any field of an issue, or add a comment. |
| `bulk_update_issues` | Apply the same change to several issues. |
| `delete_issue` | Permanently delete an issue. |
| `add_watcher` / `remove_watcher` | Manage watchers on an issue. |
| `update_journal_note` | Edit the text of a comment already posted. |

`list_issues` filters by tracker, category, version, assignee, author, parent
issue, subject text, date range, and custom field; sorts by any field; and
paginates with `limit` + `offset`. It can also run a saved query via
`query_id` — in that case Redmine ignores the other filters.

The response includes `total`, `returned`, `offset`, and `remaining`, so you
can tell whether more pages are needed without guessing.

`get_issue` includes attachments, relations, watchers, and subtasks, plus the
full history. History can be turned off with `include_history=False` for very
long issues.

`bulk_update_issues` exists because fixing the category on 30 issues
shouldn't cost 30 calls. It does not abort on the first error — it tries
every issue and returns each individual result. **There is no equivalent for
creation**: each issue has its own content, so batching creation wouldn't
save anything.

`create_issue` and `update_issue` accept, beyond the basics: `category_id`,
`fixed_version_id`, `assigned_to_id`, `parent_issue_id`, `start_date`,
`due_date`, `estimated_hours`, and `custom_fields`. `update_issue` also
accepts `done_ratio` and `description`.

`description` in `update_issue` **replaces** the whole description. To append
a note without losing what's already there, use `notes`, which becomes a
comment in the history instead.

`update_journal_note` uses `PUT /journals/:id.json`, marked **alpha** in
Redmine's documentation. If it responds 404, your version doesn't have this
endpoint. The ID it expects is the comment's (`journals[].id` from
`get_issue`), not the issue's.

## Issue relations

| Tool | Purpose |
|---|---|
| `list_issue_relations` | List an issue's relations, with each relation's ID. |
| `create_issue_relation` | Create a relation between two issues. |
| `delete_issue_relation` | Delete a relation by ID. |
| `chain_issues` | Chain a list of issues in sequence, one pair at a time. |

Accepted relation types: `relates`, `precedes`, `follows`, `blocks`,
`blocked`, `duplicates`, `duplicated`, `copied_to`, `copied_from`.

```
chain_issues(issue_ids=[22, 25, 49, 51], relation_type="precedes")
  → #22 precedes #25 precedes #49 precedes #51
```

`chain_issues` does not abort on the first error: it tries every pair and
returns each result. Safe to re-run — Redmine rejects a duplicate relation
with 422, which shows up as an error for that specific pair without
affecting the others.

> **Careful with `precedes` and `follows`**: in Redmine, these two are
> date-driven. Creating the relation **reschedules the following issue**,
> pushing its start date past the previous one's — in a long chain, the last
> issue ends up dozens of days out. If you only want to record ordering
> without touching the schedule, use `relates` instead. The `delay` parameter
> only affects these two relation types; it's ignored for the others.
>
> **Permission**: creating and deleting relations requires "Manage issue
> relations" on the role of the API key's user.

## Projects

| Tool | Purpose |
|---|---|
| `list_projects` | List every project. |
| `get_project` | Description, enabled modules, trackers, categories. |
| `create_project` | Create a project or subproject. |
| `update_project` | Name, description, and homepage. |
| `archive_project` | Archive or unarchive. |

`create_project` is **private** by default, more conservative than
Redmine's own default. `identifier` is immutable after creation — a Redmine
limitation, not this server's.

> **There is no `delete_project`, on purpose.** It's irreversible and takes
> issues, time entries, wiki content, and attachments with it.
> `archive_project` has the same practical effect — disappears from
> listings, becomes read-only — and is reversible. Deleting a project for
> real remains a web UI operation.

## Project members

| Tool | Purpose |
|---|---|
| `list_project_members` | Members and their roles. |
| `add_project_member` | Add a user with one or more roles. |
| `update_project_member` | Replace a member's list of roles. |
| `remove_project_member` | Remove a member from the project. |

These three work with the **membership ID**, not the user ID. It's the
`membership_id` field returned by `list_project_members`.

## Versions

| Tool | Purpose |
|---|---|
| `list_project_versions` | Versions (milestones) of a project, with IDs. |
| `create_project_version` | Create a version. |
| `update_version` | Rename, redate, or change a version's status. |
| `delete_version` | Delete a version. |

> Deleting a version leaves the issues that referenced it without a target
> version. To take a version out of circulation while preserving the link,
> use `update_version` with `status="closed"`.

## Categories

| Tool | Purpose |
|---|---|
| `list_project_categories` | Issue categories of a project, with IDs. |
| `create_project_category` | Create a category. |
| `update_project_category` | Rename or change the default assignee. |
| `delete_project_category` | Delete, optionally reassigning the issues. |

## Users and roles

| Tool | Purpose |
|---|---|
| `get_current_user` | Who owns the configured API key, and whether they're an admin. |
| `list_users` | List users, filterable by status and name. |
| `get_user` | Detail a user, with their projects and roles. |
| `create_user` | Create a user, with a Redmine-generated password. |
| `update_user` | Change data, lock, or unlock. |
| `update_my_account` | Change the data of the API key's own user. |
| `list_roles` | Roles on the instance, with IDs. |
| `get_role` | Permissions granted by a role. |

> **`create_user` does not accept a password parameter, on purpose.** The
> password is generated by Redmine and emailed to the person, so no
> credential ever passes through the conversation with the agent. To set a
> password manually, use the Redmine web UI.
>
> **There is no user deletion.** `update_user` with `status=3` locks access
> while preserving authorship of everything the person created. Deleting for
> real remains a web UI operation.

## Groups

| Tool | Purpose |
|---|---|
| `list_groups` | Groups on the instance. |
| `get_group` | Members and projects of a group. |
| `create_group` | Create a group, optionally with initial members. |
| `update_group` | Rename or replace the member list. |
| `delete_group` | Delete the group; users are unaffected. |
| `add_user_to_group` | Add a member without touching the rest. |
| `remove_user_from_group` | Remove a member. |

`update_group` with `user_ids` replaces the entire list — anyone not in it
is removed. To add one person, use `add_user_to_group` instead.

`list_users` requires an administrator. `get_current_user` works with any
key and is the most direct way to confirm which identity the agent is
operating under.

`get_role` is the shortcut for understanding a refusal: instead of retrying
blindly, check whether the permission actually exists on the role.

## Search and saved queries

| Tool | Purpose |
|---|---|
| `search` | Full-text search across issues, wiki, and news. |
| `list_saved_queries` | Saved queries (filters) visible to the user. |

`search` accepts restricting to a project, titles only, open issues only,
and choosing between requiring every word or any of them.

## Watchers, comments, and news

| Tool | Purpose |
|---|---|
| `add_watcher` / `remove_watcher` | Add/remove a watcher on an issue. |
| `update_journal_note` | Edit the text of an already-posted comment. |
| `list_news` | List news, by project or instance-wide. |
| `get_news_item` | Full text, comments, and attachments. |
| `create_news` | Publish a news item in a project. |
| `update_news` | Edit a published news item. |
| `delete_news` | Delete a news item. |

> `create_news` triggers an email notification according to the instance's
> configuration — it's not a silent draft.
>
> `update_news` and `delete_news` are available starting with Redmine 5.1;
> older versions respond 404.

## Wiki

| Tool | Purpose |
|---|---|
| `list_wiki_pages` | All wiki pages of a project. |
| `get_wiki_page` | Read a page's content (older versions supported). |
| `create_or_update_wiki_page` | Create or update a page, with nesting. |
| `attach_file_to_wiki_page` | Attach a file to an existing page. |
| `delete_wiki_page` | Delete a wiki page. |

`create_or_update_wiki_page` accepts `parent_page` to nest the page under
another in the wiki index. Without it, a new page is created at the root.

`attach_file_to_wiki_page` re-reads the current text before writing, because
Redmine's endpoint replaces the entire page — attaching without that care
would wipe out the existing content.

> The Wiki module needs to be enabled for the project (Project settings →
> Modules → Wiki), and the corresponding REST permission needs to be active
> for your user/role.

## Time tracking

| Tool | Purpose |
|---|---|
| `list_time_entries` | Time entries with filters (project, issue, user, period), plus the total. |
| `get_time_entry` | Detail a specific entry. |
| `log_time` | Log time worked on an issue or project. |
| `update_time_entry` | Update an existing entry. |
| `delete_time_entry` | Delete an entry. |
| `list_time_entry_activities` | Activity types available (Development, Support, etc.). |

## Attachments

| Tool | Purpose |
|---|---|
| `attach_file_to_issue` | Upload a local file and link it to an issue. |
| `attach_file_to_wiki_page` | Same, for a wiki page (see Wiki above). |
| `get_attachment` | Name, size, type, author, and download URL. |
| `update_attachment` | Rename or change the description, without re-uploading. |
| `delete_attachment` | Permanently delete an attachment. |
| `list_project_files` | Files published under a project's Files tab. |
| `upload_project_file` | Publish a file in a project, optionally tied to a version. |

A project file is not an issue attachment: it's a project-level artifact —
builds, installers, documents — optionally linked to a version.

Redmine's API requires two steps for a file — `POST /uploads.json` to get a
token, then linking that token to the target. `attach_file_to_issue` and
`upload_project_file` do both in a single call. `attach_file_to_issue`
returns `attachment_id`, which Redmine's `PUT` doesn't — without it there
would be no way to call `get_attachment` or `delete_attachment` afterward.

`update_attachment` is available starting with Redmine 5.0; older versions
respond 404.

Uploads don't go through the shared JSON client, because they require
`Content-Type: application/octet-stream` while the rest of the API uses
JSON. Before touching the network, the server rejects a missing file, an
empty file (Redmine rejects 0-byte uploads), and a file over 50 MB — this
server's own limit, adjustable via `MAX_UPLOAD_BYTES` in
`mcp_redmine/uploads.py`. The MIME type is guessed from the file extension.

**`attach_file_to_issue`, `attach_file_to_wiki_page`, and
`upload_project_file` refuse every path unless `REDMINE_UPLOAD_ROOTS` is
configured** — uploads are disabled by default, as a defense against an
agent being steered into uploading a sensitive local file. See
[SECURITY.md](../SECURITY.md#file-uploads-prompt-injection-is-the-default-threat-model).

## Metadata (read-only)

| Tool | Purpose |
|---|---|
| `list_statuses_and_priorities` | Issue status and priority IDs on this instance. |
| `list_trackers` | Tracker (issue type) IDs. |
| `list_custom_fields` | IDs, format, and possible values of custom fields. |
| `list_document_categories` | Document module categories, with IDs. |

> `list_custom_fields` requires an **administrator** user — that's a Redmine
> restriction, not this server's. Without the privilege, it returns the
> error explaining why.

Trackers, issue statuses, priorities, and roles have no write endpoints in
the Redmine REST API — they're configurable only in Administration.
