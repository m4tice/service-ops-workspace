# Workspace Context

> Concise, agent-maintained state for seamless continuation across VS Code workspaces and Copilot CLI sessions. Update only when workspace capabilities, active focus, or key architectural decisions change—never dump chat transcripts.

## Workspace Identity
- **Role:** Operations and monitoring control plane (`mcp-workspace`) for external MCP servers (`type = "mcp"`) and web backends (`type = "web"`).
- **Boundaries:** Root `.venv` runs `workspace_manager` and `pytest` only; managed services clone `main` into `src/<name>/` with isolated `.venv` environments; `.vscode/mcp.json` is generated for MCP services only.

## Current Capabilities
- Registry validation (`repositories.toml`), non-destructive Git `sync`, isolated `setup`, foreground `run` / `run-all`, tracked background `start` / `start-all` / `stop` / `stop-all` (`.workspace_runtime/`), and `status [name ...]` (branch, worktree cleanliness, localhost TCP check, optional web HTTP `health_path`, tracked PID).
- AI foundation (`service-ops` custom agent + skills under `.github/skills/`) shared across VS Code Chat and Copilot CLI.

## Active Focus & Recent Decisions
- Established `service-ops` agent and modular skills (`workspace-continuity`, `refresh-workspace-context`, `service-operations`, `service-setup`, `workspace-development`) on `feat/ai-foundation` so new workspaces/sessions can resume directly without writing new handover docs.
- Registry `repositories.toml` currently has 0 registered services (comments only).

## Next Logical Steps
1. Register initial MCP or web repositories in `repositories.toml` and run `mcp-workspace setup`.
2. Verify service startup (`mcp-workspace start <name>` and `mcp-workspace status`) against real checkouts.
