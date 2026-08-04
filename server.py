#!/usr/bin/env python3
"""Bridge entry point for MCP server.

This file exists to support clients that invoke the server via direct path
rather than using `python -m mcp_redmine`. The proper entry point is in
src/mcp_redmine/app.py:main(), invoked via __main__.py.

This bridge simply delegates to the correct entry point.
"""

import sys
from pathlib import Path

# Add src/ to the path so imports work correctly
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from mcp_redmine.app import main

if __name__ == "__main__":
    main()
