# Security

## Threat model

This server is a thin, faithful proxy to the Redmine REST API. It does not
decide what an agent is allowed to do — Redmine does, based on the
permissions of the user who owns the configured API key. That's a deliberate
design choice, not a limitation.

**Treat the API key exactly like a password.** It grants access equivalent
to the user who owns it: whatever that user can see or change through the
Redmine web UI, the agent can see or change through this server.

## The right way to limit an agent

**Limit the agent through Redmine, not through this server's code.**

1. Create a dedicated Redmine user for the agent.
2. Give that user a role with only the permissions you're comfortable
   granting — read-only on some projects, full access on others, whatever
   fits your case.
3. Use that user's API key to configure this server.

The server doesn't decide what's allowed; it forwards the call, and Redmine
is the one that refuses — with a readable message explaining that
permission was missing (see the error table in [README.md](README.md#error-messages)).

This is both safer and easier to audit than removing tools from the code:
the boundary lives in one place (Redmine's role/permission system), survives
updates to this server, and shows up in every issue's history with the name
of whoever acted — including the agent's dedicated user.

Two permissions worth thinking twice about before granting to an agent:

- **Delete issues.** There's no undo.
- **Administrator.** It unlocks instance-wide operations — creating and
  locking users, managing groups, reading every project.

## Deliberate omissions

Two operations that exist in the Redmine API are intentionally not exposed
as tools:

- **Deleting a project** — irreversible, and takes issues, time entries,
  wiki pages, and attachments down with it. Use `archive_project` instead:
  same practical effect (read-only, out of listings), fully reversible.
- **Deleting a user** — irreversible, and orphans or reattributes everything
  they authored. Use `update_user` with `status=3` to lock the account while
  preserving authorship history.

Deleting a project or a user for real remains a web UI operation, on
purpose — that's where confirmation is explicit and human.

`create_user` also never accepts a password as a parameter. Redmine
generates one and emails it directly to the person, so no credential ever
passes through the conversation with the agent.

## File paths

Tools that take a file path (`attach_file_to_issue`,
`attach_file_to_wiki_page`, `upload_project_file`) resolve that path **on
the machine running this MCP server**, not on the machine of whoever is
talking to the agent. For a local setup (Claude Desktop or Claude Code
running the server as a subprocess on your own machine) those are the same
machine. In a remote deployment, they are not — keep that in mind before
exposing this server to a client that isn't colocated with it.

## Network exposure

This server speaks MCP over stdio and makes outbound HTTPS/HTTP calls to
your configured `REDMINE_URL`. It does not open a network port itself. If
your Redmine instance is only reachable from a private network, the MCP
server needs to run somewhere with access to that network — which in
practice means a local Claude Desktop/Claude Code setup, not a browser-based
client with no path to your network.

## Reporting a vulnerability

If you find a security issue in this project, please open a
[GitHub issue](https://github.com/alsimoes/mcp-redmine/issues) marked
clearly as a security report, or contact the maintainer directly if the
issue is sensitive enough that public disclosure before a fix isn't
appropriate. Please don't include real Redmine URLs, API keys, or other
credentials in a report.
