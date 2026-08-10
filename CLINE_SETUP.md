# Setting up mcp-redmine with Cline (VS Code)

This server works with Cline with no modification at all. This guide covers
installing and configuring it for Cline in VS Code, on Windows and on
Linux/macOS alike.

For a shorter version, the README has a [Cline section](README.md#cline-vs-code).
If you want an agent to do the setup for you, point it at
[llms-install.md](llms-install.md).

## Prerequisites

- **Python 3.10+** installed and on the `PATH`
- **Redmine** with the REST API enabled: *Administration → Settings → API →
  "Enable REST web service"*
- A Redmine **API key**: *My account → API access key*
- **Cline** installed in VS Code

## Installing the server

Pick **one** of the three options below.

> **Mind the package name.** The distribution is **`mcp-redmine-rest`**, and the
> executable it installs is `mcp-redmine-rest`. The shorter `mcp-redmine` name
> on PyPI belongs to [an unrelated
> project](https://github.com/runekaagaard/mcp-redmine) — don't install that one
> expecting this server.

### Option A: uv tool install (recommended)

```bash
uv tool install mcp-redmine-rest
```

This installs the `mcp-redmine-rest` executable globally in the `uv`
environment.

### Option B: pip

```bash
pip install mcp-redmine-rest
```

### Option C: from source

```bash
git clone https://github.com/alsimoes/mcp-redmine.git
cd mcp-redmine

python3 -m venv venv && source venv/bin/activate    # Linux/Mac

pip install -e .
```

On Windows, use `py` and PowerShell rather than a Git Bash/WSL shell —
creating or recreating the venv from a Unix-style shell on Windows overwrites
`venv\pyvenv.cfg` with a Unix `home` path, and every subsequent launch of
`venv\Scripts\python.exe` fails with `No Python at '/usr/bin\python.exe'` (or
similar):

```powershell
git clone https://github.com/alsimoes/mcp-redmine.git
cd mcp-redmine

py -3 -m venv venv
.\venv\Scripts\Activate.ps1

pip install -e .
```

Using `cmd.exe` instead of PowerShell? Activate with
`venv\Scripts\activate.bat` after the `py -3 -m venv venv` step above.

---

## Configuring Cline

Cline keeps its MCP servers in a single settings file, and offers a UI that
edits that same file for you. Both routes are below.

> **In every snippet, replace `REDMINE_URL` and `REDMINE_API_KEY` with the real
> values for your Redmine instance.**

---

### Method 1 — the MCP settings file (recommended)

1. Open VS Code.
2. Press `Ctrl+Shift+P` and run **Cline: Open MCP Config File**, or click the
   gear next to "MCP Servers" in the Cline sidebar and choose *Configure MCP
   Servers*.
3. `cline_mcp_settings.json` opens. Add the block:

```json
{
  "mcpServers": {
    "redmine": {
      "command": "mcp-redmine-rest",
      "env": {
        "REDMINE_URL": "https://redmine.example.com",
        "REDMINE_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

4. Save the file and reload the window (`Ctrl+Shift+P` → *Developer: Reload
   Window*).

> **Where that file lives.** Prefer the palette command above — it opens the
> right file regardless of platform. If you need the path anyway, it depends on
> which Cline you are using:
>
> **Cline extension for VS Code**, under
> `.../User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`:
>
> | | |
> |---|---|
> | Windows | `%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\` |
> | macOS | `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/` |
> | Linux | `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/` |
>
> **Cline CLI / cline-core**, which keeps its own copy:
> `~/.cline/data/settings/cline_mcp_settings.json`.
>
> Editing the wrong one is the most common reason a server never shows up.

---

### Method 2 — the Add MCP Server UI

1. Click the Cline button in the VS Code sidebar.
2. Click the gear icon next to "MCP Servers".
3. Under "Installed", click **+ Add MCP Server**.
4. Fill in:

| Field | Value |
|---|---|
| Name | `redmine` |
| Command | `mcp-redmine-rest` (or `python`) |
| Args | (leave empty, or `-m mcp_redmine` if Command is `python`) |
| Env | `REDMINE_URL=https://redmine.example.com` |
| | `REDMINE_API_KEY=your_api_key_here` |

5. Click **Save** and check that the server comes up as "Connected".

This writes to the same `cline_mcp_settings.json` as Method 1.

---

### A note on `.mcp.json` and `.vscode/mcp.json`

**Cline does not auto-discover a workspace `.mcp.json`.** Its MCP configuration
is global, shared across every workspace — that is why both methods above edit
the same file. The two per-repository files belong to other tools:

| File | Read by | Versioned? |
|---|---|---|
| `.mcp.json` | Claude Code, at the workspace root | No — gitignored; copy it from [`.mcp.json.example`](.mcp.json.example) and fill in your own `REDMINE_URL`/`REDMINE_API_KEY` |
| `.vscode/mcp.json` | VS Code's own built-in MCP support | Yes — already generic, prompts you for the URL/key via VS Code's input UI |

You can keep one of those as your canonical definition and copy the server block
into `cline_mcp_settings.json`, but nothing will pick it up automatically.

---

## Ready-to-paste configurations

Pick the snippet matching how you installed the server.

### Installed with `uv tool install` (Option A)

```json
{
  "mcpServers": {
    "redmine": {
      "command": "mcp-redmine-rest",
      "env": {
        "REDMINE_URL": "https://redmine.example.com",
        "REDMINE_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

### Installed with `pip`, or from source, via the Python module

```json
{
  "mcpServers": {
    "redmine": {
      "command": "python",
      "args": ["-m", "mcp_redmine"],
      "env": {
        "REDMINE_URL": "https://redmine.example.com",
        "REDMINE_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

### From source, using `uv run`

```json
{
  "mcpServers": {
    "redmine": {
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_redmine"],
      "env": {
        "REDMINE_URL": "https://redmine.example.com",
        "REDMINE_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

### From source, with a virtual environment (absolute path)

Replace `/full/path/to/mcp-redmine` with the path to your clone. On Windows
that's `C:/full/path/to/mcp-redmine/venv/Scripts/python.exe`; forward slashes
work in JSON and save you from escaping backslashes.

```json
{
  "mcpServers": {
    "redmine": {
      "command": "/full/path/to/mcp-redmine/venv/bin/python",
      "args": ["-m", "mcp_redmine"],
      "env": {
        "REDMINE_URL": "https://redmine.example.com",
        "REDMINE_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

---

## Verifying it works

1. **Check Cline's output.** Open the *Output* panel (`Ctrl+Shift+U`) and pick
   **Cline** in the dropdown. The server should appear as connected, with no
   errors.

2. **Check the tools reach Redmine.** Ask Cline something simple:

   > List my Redmine projects

   If the tools loaded, Cline will reach for `list_projects` on its own. This
   matters more than the connection status: a server configured with a bad API
   key still connects, and only fails on the first call.

3. **Test from a terminal.** You can also start the server by hand to confirm
   the environment variables are right:

   ```bash
   # Windows (cmd):
   set REDMINE_URL=https://redmine.example.com
   set REDMINE_API_KEY=your_api_key_here
   mcp-redmine-rest
   ```

   The command takes no arguments — it starts the server and waits for MCP
   messages on stdin/stdout, so nothing happening is the expected result. A
   configuration problem would have printed an error instead. Press `Ctrl+C` to
   stop.

---

## Troubleshooting

### "REDMINE_URL and REDMINE_API_KEY must be set"

The environment variables aren't reaching the child process. Check that:

- the `env` block sits inside the server's own configuration;
- the JSON has no syntax errors (trailing commas, unbalanced quotes);
- you used literal values — `${VAR}`-style references are not reliably expanded.

### "No module named 'mcp.server.fastmcp'"

The `mcp[cli]` package isn't installed:

```bash
pip install "mcp[cli]>=1.0.0,<2.0.0"
```

### "No module named 'mcp_redmine'"

The `mcp-redmine-rest` package isn't installed in the Python that Cline is
calling.

- With `command: "python"`, confirm `pip install mcp-redmine-rest` ran against
  the **same** Python that's on VS Code's `PATH`.
- With a virtual environment, confirm the path to `python.exe` is right.

### The server shows up as "Disconnected"

Look for the error line in *Output* → **Cline**. The usual causes:

- **Wrong `command` path** — check the executable actually exists.
- **Python not on the `PATH`** — use an absolute path, e.g.
  `C:/Python310/python.exe`.
- **Firewall** — the server process needs network access to your Redmine URL.
- **401** — invalid API key, or the REST API is off in Redmine.

### Cline ignores the workspace's `.mcp.json`

That's expected — see [the note above](#a-note-on-mcpjson-and-vscodemcpjson).
Cline's MCP configuration is global; copy the server block into
`cline_mcp_settings.json`.

### 403 on specific tools

The API key belongs to a Redmine user without permission for that operation.
Use `get_role` to see what the user's role actually allows. Consider creating a
dedicated user with exactly the permissions you want to grant the agent — see
[SECURITY.md](SECURITY.md).

---

## The 73 tools

Once configured, Cline has access to every Redmine tool:

| Resource | Tools |
|---|---|
| Issues | `list_issues`, `get_issue`, `create_issue`, `update_issue`, `bulk_update_issues`, `delete_issue`, `add_watcher`, `remove_watcher`, `update_journal_note` |
| Issue relations | `list_issue_relations`, `create_issue_relation`, `delete_issue_relation`, `chain_issues` |
| Projects | `list_projects`, `get_project`, `create_project`, `update_project`, `archive_project` |
| Memberships | `list_project_members`, `add_project_member`, `update_project_member`, `remove_project_member` |
| Versions | `list_project_versions`, `create_project_version`, `update_version`, `delete_version` |
| Categories | `list_project_categories`, `create_project_category`, `update_project_category`, `delete_project_category` |
| Users | `get_current_user`, `list_users`, `get_user`, `create_user`, `update_user`, `update_my_account` |
| Groups | `list_groups`, `get_group`, `create_group`, `update_group`, `delete_group`, `add_user_to_group`, `remove_user_from_group` |
| Roles | `list_roles`, `get_role` |
| Wiki | `list_wiki_pages`, `get_wiki_page`, `create_or_update_wiki_page`, `attach_file_to_wiki_page`, `delete_wiki_page` |
| Time tracking | `list_time_entries`, `get_time_entry`, `log_time`, `update_time_entry`, `delete_time_entry`, `list_time_entry_activities` |
| Attachments | `attach_file_to_issue`, `get_attachment`, `update_attachment`, `delete_attachment` |
| Project files | `list_project_files`, `upload_project_file` |
| News | `list_news`, `get_news_item`, `create_news`, `update_news`, `delete_news` |
| Search | `search`, `list_saved_queries` |
| Metadata | `list_statuses_and_priorities`, `list_trackers`, `list_custom_fields`, `list_document_categories` |

For the full reference — signatures, parameters, and per-tool caveats — see
[docs/TOOLS.md](docs/TOOLS.md).

---

## Why it works with no adaptation

This server is built on the **standard MCP protocol** over stdio, which is
exactly what Cline implements. It depends on nothing specific to Claude Desktop.
Three things carry that compatibility:

1. **The official MCP SDK** — the server uses `mcp[cli]>=1.0.0`, the reference
   implementation of the protocol.
2. **Environment variables** — Cline supports the `env` block in an MCP server's
   configuration, the same way Claude Desktop does.
3. **stdio transport** — the server talks over stdin/stdout, with no WebSocket,
   HTTP, or proprietary transport involved.
