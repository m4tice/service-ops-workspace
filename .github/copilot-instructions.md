# Service Operations Workspace Guidelines

## Purpose and Role Boundaries
- This repository is the **control plane** for independently maintained MCP servers and web backends.
- Service feature code, dependencies, and releases live in each service's own Git repository (cloned into `src/<name>`), never in this workspace.
- Keep the root `.venv` strictly for `workspace_manager` and its tests. Each managed checkout under `src/<name>/` uses its own `.venv`.
- `examples/` and `mcp_template/` are reference/starter material only and are not auto-registered.

## Key Files and Generated Artifacts
- `repositories.toml`: authoritative registry of `[[services]]` (`type = "mcp"` or `"web"`, unique `name`, Git `url`, unique `port`, plus `command` and optional `health_path` for `web`). Never store credentials or tokens here.
- `.vscode/mcp.json`: **generated** by `mcp-workspace sync` and `mcp-workspace setup` from MCP services only. Never hand-edit it.
- `.workspace_runtime/`: untracked local PID state (`processes.json`) and logs (`logs/<name>.log`) for background `start`/`stop` commands.
- `.github/workspace-context.md`: concise, agent-maintained working context for seamless session/workspace handoff (avoids manual `HANDOVER.md` churn).

## Core Commands
- Run control-plane CLI via `.venv/bin/mcp-workspace` (or `mcp-workspace` when `.venv` is activated):
  - `sync`, `setup`, `status [name ...]`, `start <name ...>`, `start-all`, `stop <name ...>`, `stop-all`, `run <name>`, `run-all`
- Validate control-plane changes with `.venv/bin/python -m pytest`.

## Safety Rules
- `sync` only fast-forwards clean checkouts on `main` matching `origin`; never auto-reset, force-checkout, or delete removed checkouts in `src/`.
- Be honest about health checks: `status` checks TCP reachability (plus shallow HTTP GET when `health_path` is set on `web` services), not full MCP protocol handshakes.
- Ask for confirmation before state-changing operations on services (`setup`, `start`, `start-all`, `stop`, `stop-all`) unless the user explicitly requested execution.
- See `docs/README.md` and `docs/USER_GUIDE.md` for detailed architecture and operator procedures.
