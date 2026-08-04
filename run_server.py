#!/usr/bin/env python3
"""Robust entry point for Redmine MCP server.

This script ensures the package is importable and delegates to the main app.
It handles path setup and environment configuration consistently.
"""

import sys
import os
from pathlib import Path

# Ensure src is in the path
repo_root = Path(__file__).parent
src_path = repo_root / "src"
sys.path.insert(0, str(src_path))

# Set up minimal environment defaults if needed
if "REDMINE_TIMEOUT" not in os.environ:
    os.environ["REDMINE_TIMEOUT"] = "15"

# Import and run the main app
from mcp_redmine.app import main

if __name__ == "__main__":
    main()
