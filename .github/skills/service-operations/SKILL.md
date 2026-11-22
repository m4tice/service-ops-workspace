---
name: service-operations
description: "Monitor, find, start, and stop registered MCP servers and web backends. Use when asked whether client/managed servers are online or healthy, to find matching servers, or to start/stop one, several, or all servers."
argument-hint: "[status | start | stop] [all | service names or filter]"
---

# Service Operations

Inspect health and manage the runtime lifecycle of registered MCP servers and web backends through `mcp-workspace`.

## When to Use
- "Are all the client/managed servers online or healthy?"
- "Find the time/api servers and start/stop them."
- "Start all servers" or "Stop all servers."
- Diagnosing why a registered service is offline or failing to start.

## Procedure

### 1. Discover & Match Services
1. Read `repositories.toml` to list all `[[services]]` (and any legacy `[[servers]]`).
2. If the registry is empty, report clearly that no services are registered in `repositories.toml` yet and offer to set one up via `service-setup`.
3. When the user gives partial names, types (`mcp` vs `web`), or descriptions (e.g., "find the geolocation and api servers"):
   - Match against `name`, `type`, `url`, and `command` in `repositories.toml`.
   - State the resolved exact service name(s) before mutating state. If ambiguous, ask the user to confirm the matched list.

### 2. Check Online & Health Status (Read-Only)
1. Run `.venv/bin/mcp-workspace status` (or `.venv/bin/mcp-workspace status <name ...>` for specific services).
2. Interpret and report results honestly for each service:
   - **`not cloned`**: Checkout missing under `src/<name>`; needs `mcp-workspace sync` / `setup`.
   - **`endpoint=online` / `offline`**: Whether `127.0.0.1:<port>` accepts TCP connections.
   - **`health=healthy` / `unhealthy(...)` / `not-configured`** (`web` only): Shallow HTTP GET result for `health_path`.
   - **`process=running(pid=...)`**: Tracked background process managed by `mcp-workspace start`. (If `endpoint=online` without `process=running`, note that an untracked/foreground process is listening on that port.)
   - **Important distinction**: For `mcp` services, `endpoint=online` confirms local TCP reachability, not a full MCP protocol handshake.

### 3. Start or Stop Services
1. **Confirmation check**: If the user explicitly requested starting or stopping specific/all services, proceed after verifying target names. If you are recommending a restart during troubleshooting, ask confirmation first.
2. Execute the background CLI command (do not block chat with foreground `run` unless requested):
   - Start specific: `.venv/bin/mcp-workspace start <name1> [name2 ...]`
   - Start all: `.venv/bin/mcp-workspace start-all`
   - Stop specific: `.venv/bin/mcp-workspace stop <name1> [name2 ...]`
   - Stop all: `.venv/bin/mcp-workspace stop-all`
3. Follow up immediately with `.venv/bin/mcp-workspace status [name ...]` to verify post-action endpoint/health state.
4. If a service fails to start or exits immediately, inspect `.workspace_runtime/logs/<name>.log` and report the root cause (e.g., missing `mcp-workspace setup`, port conflict, or missing command).
