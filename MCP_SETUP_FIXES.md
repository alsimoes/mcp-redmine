# MCP Server Setup Fixes

## Issues Found in Logs

### Issue 1: Early Import Error (July 28)
**Error:** `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`

**Root Cause:** The MCP SDK dependencies were not installed in the Python virtual environment at that time.

**Status:** ✅ **FIXED** — The venv now has MCP 1.29.0 with FastMCP support installed.

---

### Issue 2: Missing Entry Point File (Aug 2-4)
**Error:** `can't open file 'C:\\dev\\repos\\mcp-redmine\\server.py': [Errno 2] No such file or directory`

**Root Cause:** The MCP client (Claude Desktop) was configured to run `python.exe server.py`, but this file didn't exist. The actual entry point is:
- `src/mcp_redmine/app.py` (where `main()` is defined)
- Invoked via `__main__.py` with `python -m mcp_redmine`

**Status:** ✅ **FIXED** — Created `/server.py` as a bridge that delegates to the proper entry point.

---

## Solution Overview

### File Created: `server.py`
A simple wrapper script at the repository root that:
1. Adds `src/` to Python's module search path
2. Imports and calls `mcp_redmine.app:main()`
3. Works with the client's direct invocation pattern

This allows the MCP client to invoke the server using:
```
python.exe C:\dev\repos\mcp-redmine\server.py
```

Instead of needing:
```
python.exe -m mcp_redmine
```

### Architecture (After Fix)

```
Client invocation:
  python.exe C:\dev\repos\mcp-redmine\server.py
              ↓
  server.py (bridge)
              ↓
  src/mcp_redmine/app.py:main()
              ↓
  mcp_redmine/tools/* (FastMCP tools)
```

---

## Configuration Files

### `.mcp.json` (Recommended)
The repository contains `.mcp.json` which defines the proper invocation:
```json
{
  "mcpServers": {
    "redmine": {
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_redmine"],
      "env": {
        "REDMINE_URL": "${REDMINE_URL}",
        "REDMINE_API_KEY": "${REDMINE_API_KEY}",
        "REDMINE_TIMEOUT": "${REDMINE_TIMEOUT:-15}"
      }
    }
  }
}
```

This is ideal for:
- Local development (using `uv` for dependency management)
- Docker/containerized deployments
- Environments with `uv` installed

### Client Configuration (Claude Desktop)
If using Claude Desktop, the MCP server can be configured in your `claude_desktop_config.json`:

**Option A (Using Python directly):**
```json
{
  "mcpServers": {
    "redmine": {
      "command": "python",
      "args": ["-m", "mcp_redmine"],
      "env": {
        "REDMINE_URL": "https://your-redmine-instance.com",
        "REDMINE_API_KEY": "your_api_key_here",
        "REDMINE_TIMEOUT": "15"
      }
    }
  }
}
```

**Option B (Using the bridge entry point):**
```json
{
  "mcpServers": {
    "redmine": {
      "command": "python",
      "args": ["C:\\dev\\repos\\mcp-redmine\\server.py"],
      "env": {
        "REDMINE_URL": "https://your-redmine-instance.com",
        "REDMINE_API_KEY": "your_api_key_here",
        "REDMINE_TIMEOUT": "15"
      }
    }
  }
}
```

---

## Verification

The setup is correct when:

1. ✅ `server.py` exists in the repo root
2. ✅ `src/mcp_redmine/` contains the actual implementation
3. ✅ MCP SDK is installed: `mcp>=1.0.0,<2.0.0`
4. ✅ Server starts without import errors
5. ✅ Tools are registered and listed by the MCP client

---

## Why This Design

1. **Backward Compatibility:** Supports both invocation patterns (direct `server.py` and `python -m`)
2. **Proper Package Structure:** Keeps implementation in `src/` (PEP 517 compliant)
3. **No Code Duplication:** Bridge simply delegates to the real entry point
4. **Clear Entry Point:** `app.py:main()` is the single source of truth

---

## If Issues Persist

If the server still won't start after these fixes:

1. **Verify Environment Variables:**
   ```
   set REDMINE_URL=https://your-redmine-instance.com
   set REDMINE_API_KEY=your_api_key_here
   ```

2. **Test the Server Directly:**
   ```
   python C:\dev\repos\mcp-redmine\server.py
   ```

3. **Check Virtual Environment:**
   ```
   python -m pip install -e C:\dev\repos\mcp-redmine
   python -m pip install "mcp[cli]>=1.0.0,<2.0.0"
   ```

4. **Review Logs:**
   The MCP client logs (from Claude Desktop) will show the exact error if startup fails.

