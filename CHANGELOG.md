# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/) as
expressed through [PEP 440](https://peps.python.org/pep-0440/) version
identifiers.

## [Unreleased]

## [0.1.0] - 2026-07-31

First public release. This version reworks the project from a private,
Portuguese-language script into a packaged, English-language, tested project
suitable for public use.

### Changed

- **Every public identifier is now in English**: tool names, parameters, and
  JSON response keys. This is a breaking change for anyone who configured an
  MCP client against the earlier, private version of this server. The
  renaming follows a consistent pattern:

  | Old prefix (Portuguese) | New prefix (English) |
  |---|---|
  | `listar_*` | `list_*` |
  | `detalhar_*` | `get_*` |
  | `criar_*` | `create_*` |
  | `atualizar_*` | `update_*` |
  | `excluir_*` | `delete_*` |
  | `anexar_*` | `attach_*` / `upload_*` |
  | `buscar` | `search` |

  Parameters that map directly to a Redmine API field now use Redmine's own
  field name (e.g. `responsavel_id` → `assigned_to_id`). The full mapping is
  in the project's git history; the current names are documented in
  [docs/TOOLS.md](docs/TOOLS.md).
- Restructured the single-file `server.py` into an installable package
  (`src/mcp_redmine/`) with one module per Redmine resource under
  `tools/`.
- Centralized error handling into a `@tool` decorator, replacing the
  try/except-and-format block that used to be repeated in nearly every tool.
  A bug in a tool now propagates instead of being silently swallowed
  alongside expected Redmine failures.
- Replaced the fixed `ensure_ascii=False` JSON output with plain
  `json.dumps(..., indent=2)`, since responses are ASCII now.

### Fixed

- The server used to print a configuration error to stderr but keep running
  with an empty `REDMINE_URL`, so every tool call then failed with a
  confusing network error. It now validates configuration at startup and
  exits immediately with an actionable message.
- Docstrings were reformatted to comply with
  [PEP 257](https://peps.python.org/pep-0257/) (summary line immediately
  after the opening quotes, not after a blank line).

### Added

- Full type hints throughout (`mypy --strict`, [PEP 484](https://peps.python.org/pep-0484/)),
  with a `py.typed` marker ([PEP 561](https://peps.python.org/pep-0561/)).
- Packaging via `pyproject.toml`
  ([PEP 517](https://peps.python.org/pep-0517/),
  [PEP 518](https://peps.python.org/pep-0518/),
  [PEP 621](https://peps.python.org/pep-0621/)), with a `mcp-redmine`
  console script entry point.
- Test suite (`pytest` + `responses`), with no network access required.
- GitHub Actions CI: lint, format check, type check, and tests across Python
  3.10–3.13, plus a build/`twine check` job.
- `LICENSE` (MIT), `SECURITY.md`, `CONTRIBUTING.md`, `.env.example`, and
  `docs/TOOLS.md`.

### Removed

- References to the maintainer's private Redmine hostname and the stray,
  non-functional `setup.ps1`.

[Unreleased]: https://github.com/alsimoes/mcp-redmine/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/alsimoes/mcp-redmine/releases/tag/v0.1.0
