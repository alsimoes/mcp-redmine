"""JSON formatting helper shared by every tool."""

from __future__ import annotations

import json
from typing import Any


def dumps(data: Any) -> str:
    """Serialize a value to indented JSON for a tool's return value.

    Args:
        data: Any JSON-serializable value.

    Returns:
        A pretty-printed JSON string.
    """
    return json.dumps(data, indent=2)
