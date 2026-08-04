# Cowork MCP Setup for mcp-redmine

## Configuration

The Redmine MCP server can be configured in Cowork in one of two ways:

### Option 1: Using the run_server.py wrapper (Recommended)

**Command:**
```
C:\dev\repos\mcp-redmine\venv\Scripts\python.exe
```

**Arguments:**
```
run_server.py
```

**Environment Variables:**
```
REDMINE_URL=<your-redmine-url>
REDMINE_API_KEY=<your-api-key>
REDMINE_TIMEOUT=15
```

### Option 2: Using module invocation

**Command:**
```
C:\dev\repos\mcp-redmine\venv\Scripts\python.exe
```

**Arguments:**
```
-m mcp_redmine.app
```

**Environment Variables:**
```
REDMINE_URL=<your-redmine-url>
REDMINE_API_KEY=<your-api-key>
REDMINE_TIMEOUT=15
PYTHONPATH=C:\dev\repos\mcp-redmine\src
```

## Troubleshooting

If you see errors like "No such file or directory" for server.py:
1. Check that the command and args are set correctly (not pointing to server.py directly)
2. Ensure PYTHONPATH includes the src/ directory if using module invocation
3. Verify environment variables are set
4. Restart Cowork after making configuration changes

## Verifying the Setup

Test from a terminal:
```cmd
cd C:\dev\repos\mcp-redmine
set REDMINE_URL=http://your-redmine-instance
set REDMINE_API_KEY=your-api-key
venv\Scripts\python.exe run_server.py
```

The server should start and display initialization messages. Press Ctrl+C to stop.
