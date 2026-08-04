"""Regression guard: every tool is registered, named in English, and documented.

This exists specifically to catch a regression back to the project's
original all-Portuguese public API (tool names, parameters) during future
changes.
"""

from __future__ import annotations

import re
from typing import Any

import mcp_redmine.tools  # noqa: F401  (import registers every tool)
from mcp_redmine.app import mcp

EXPECTED_TOOL_COUNT = 73

# A conservative list of Portuguese function-name fragments that must never
# reappear in a tool name.
PORTUGUESE_FRAGMENTS = (
    "listar",
    "criar",
    "excluir",
    "atualizar",
    "detalhar",
    "usuario",
    "projeto",
    "assunto",
    "anexar",
    "buscar",
    "papel",
)

NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def _registered_tools() -> dict[str, Any]:
    # FastMCP has no public API to list registered tools by name; reach into
    # the tool manager instead.
    return mcp._tool_manager._tools


def test_expected_number_of_tools_is_registered() -> None:
    assert len(_registered_tools()) == EXPECTED_TOOL_COUNT


def test_every_tool_name_is_ascii_snake_case() -> None:
    for name in _registered_tools():
        assert NAME_PATTERN.match(name), f"{name!r} is not ASCII snake_case"


def test_no_tool_name_contains_portuguese_fragments() -> None:
    for name in _registered_tools():
        for fragment in PORTUGUESE_FRAGMENTS:
            message = f"{name!r} contains Portuguese fragment {fragment!r}"
            assert fragment not in name, message


def test_every_tool_has_a_docstring() -> None:
    for name, tool in _registered_tools().items():
        assert tool.description, f"{name!r} has no description/docstring"
