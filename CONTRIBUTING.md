# Contributing

Thanks for considering a contribution to mcp-redmine.

## Development setup

```bash
git clone https://github.com/alsimoes/mcp-redmine.git
cd mcp-redmine

python3 -m venv venv && source venv/bin/activate    # Linux/Mac

pip install -e ".[dev]"
```

On Windows, create the venv with `py` from PowerShell — not from a Git
Bash/WSL shell, which overwrites `venv\pyvenv.cfg` with a Unix `home` path
and breaks `venv\Scripts\python.exe` for every later Windows launch:

```powershell
git clone https://github.com/alsimoes/mcp-redmine.git
cd mcp-redmine

py -3 -m venv venv
.\venv\Scripts\Activate.ps1

pip install -e ".[dev]"
```

This installs the package in editable mode plus the development tools:
[pytest](https://docs.pytest.org/), [responses](https://github.com/getsentry/responses)
for mocking Redmine's HTTP API, [ruff](https://docs.astral.sh/ruff/) for
linting and formatting, and [mypy](https://mypy-lang.org/) for type checking.

## Running the checks

```bash
ruff check .              # lint
ruff format .             # format (or --check to only verify)
mypy src                  # strict type checking
pytest -q                 # test suite (no network access needed — HTTP is mocked)
```

All four run in CI on every pull request; please run them locally first.

## Project layout

```
src/mcp_redmine/
  app.py          # FastMCP instance, the @tool registration decorator, entry point
  client.py       # RedmineClient — thin wrapper over requests.Session
  config.py       # environment variable loading and validation
  errors.py       # RedmineError and Redmine response → readable message
  format.py       # JSON serialization helper shared by every tool
  uploads.py      # the two-step file upload flow (/uploads.json)
  tools/          # one module per Redmine resource; each function is a tool
tests/            # mirrors the structure above, HTTP mocked via `responses`
docs/TOOLS.md     # full tool reference
```

## Adding a new tool

1. Pick the `tools/*.py` module that matches the Redmine resource (or create
   a new one if it's a new resource).
2. Write the function, decorated with `@tool` from `mcp_redmine.app` (not
   `@mcp.tool()` directly — the decorator is what turns a `RedmineError` into
   a readable return value instead of a stack trace).
3. Use `get_client()` to make the request; let `RedmineError` propagate
   unless you need to react differently to a failure partway through a
   multi-step operation (see `attach_file_to_issue` for an example).
4. Follow the existing naming convention: `list_*` / `get_*` / `create_*` /
   `update_*` / `delete_*`, and prefer Redmine's own field names for
   parameters (`assigned_to_id`, not `assignee`).
5. Write a Google-style docstring — first line is a one-sentence summary,
   then an `Args:` section documenting every parameter. `ruff check` enforces
   this (pydocstyle rules).
6. Add type hints to every parameter and the return value; `mypy --strict`
   enforces this.
7. Add tests in the matching `tests/test_*.py`, mocking Redmine's response
   with `responses`.
8. Add the tool to the table in [docs/TOOLS.md](docs/TOOLS.md) and to the
   summary table in [README.md](README.md#available-tools).
9. Add an entry to [CHANGELOG.md](CHANGELOG.md) under "Unreleased".

## Commit style

Please write commit messages in English, in the imperative mood (e.g. "Add
`get_time_entry` tool", not "Added" or "Adds"). [Conventional Commits](https://www.conventionalcommits.org/)
prefixes (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`) are
welcome but not required.

## Pull requests

Please open an issue first for anything beyond a small fix, so we can agree
on the approach before you put in the work. Fill in the pull request
template's checklist — it mirrors the checks CI runs.
