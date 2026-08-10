# Cowork MCP Setup for mcp-redmine

## Configuration

The Redmine MCP server can be configured in Cowork in one of two ways. Both
assume the package is installed — either `pip install mcp-redmine-rest` or, from
a clone, `pip install -e .` inside the virtual environment.

Replace `<repo>` below with the full path to your clone (for example
`C:\dev\repos\mcp-redmine`).

### Option 1: Using the console script (Recommended)

**Command:**
```
mcp-redmine-rest
```

**Arguments:** none

**Environment Variables:**
```
REDMINE_URL=<your-redmine-url>
REDMINE_API_KEY=<your-api-key>
REDMINE_TIMEOUT=15
```

If Cowork cannot find the executable on the `PATH`, point `Command` at it
directly — with a virtual environment that is
`<repo>\venv\Scripts\mcp-redmine-rest.exe`.

### Option 2: Using module invocation

**Command:**
```
<repo>\venv\Scripts\python.exe
```

**Arguments:**
```
-m mcp_redmine
```

**Environment Variables:**
```
REDMINE_URL=<your-redmine-url>
REDMINE_API_KEY=<your-api-key>
REDMINE_TIMEOUT=15
```

`PYTHONPATH` is not needed when the package is installed in that interpreter.
Set `PYTHONPATH=<repo>\src` only if you are running straight from a clone
without installing it.

## Troubleshooting

If the server fails to start:
1. Confirm the command and arguments match one of the two options above — this
   server has no standalone launcher script to point at, only the console
   script and `python -m mcp_redmine`.
2. Verify the environment variables are set; the server exits immediately with
   `REDMINE_URL and REDMINE_API_KEY must be set` when they are missing.
3. Restart Cowork after making configuration changes.

## Verifying the Setup

Test from a terminal:
```cmd
cd <repo>
set REDMINE_URL=http://your-redmine-instance
set REDMINE_API_KEY=your-api-key
venv\Scripts\python.exe -m mcp_redmine
```

The server waits for MCP messages on stdin/stdout, so no output is the expected
result — a configuration error would have printed instead. Press Ctrl+C to stop.
