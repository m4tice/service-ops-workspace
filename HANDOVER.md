# Workspace Handover

Updated: 2026-11-22

> **Continuity Note:** Ongoing workspace state and session handoff are maintained by the **Schaltmeister** agent (`.github/agents/schaltmeister.agent.md`) inside [.github/workspace-context.md](.github/workspace-context.md). In a new VS Code workspace or Copilot CLI session, select Schaltmeister and prompt `continue` rather than manually updating this file.

## Purpose

This repository is the operations control plane for independently maintained MCP servers and web backends. Service code, releases, dependencies, and tests belong in each service's own Git repository. This workspace owns the registry, checkout lifecycle, isolated setup, launch/status commands, generated MCP client configuration, and operations documentation.

Start with the [README](README.md) for a quick overview and the [User Guide](docs/USER_GUIDE.md) for operator procedures. Requirements and architecture are in [docs/](docs/README.md).

## Current Snapshot

- The registry at [repositories.toml](repositories.toml) contains comments only; there are no registered services.
- The current [.vscode/mcp.json](.vscode/mcp.json) has an empty `servers` object.
- `src/` contains only its explanatory README; no service checkout is currently managed there.
- `examples/` contains local reference MCP implementations. `mcp_template/` is the MCP starter contract. Neither is automatically registered or synchronized.
- The root `.venv` is for workspace management and tests. Managed checkouts get their own `.venv` and editable install.

## Registry Contract

New entries use `[[services]]` in `repositories.toml`. Each service has a unique safe `name`, Git `url`, unique TCP `port`, and `type` of `mcp` or `web`. The manager clones the remote's `main` branch to `src/<name>`.

MCP entries omit `command`; the manager launches the checkout's `mcp-server` executable with `MCP_HOST=127.0.0.1`, `MCP_PORT=<port>`, and `MCP_TRANSPORT=http`. The generated MCP endpoint is `http://127.0.0.1:<port>/mcp`.

Web entries require a TOML string-array `command`. It is passed as argv without a shell. The manager resolves `python`/`python3` or installed executables from the service `.venv`, substitutes `{host}` and `{port}` within arguments, and sets generic `HOST` and `PORT` environment variables. An optional absolute `health_path` enables an HTTP GET check from `status`.

Legacy `[[servers]]` entries are still parsed as MCP services. Avoid mixing legacy and new tables in the same registry. See the [README examples](README.md#register-a-service) for TOML samples.

## Commands

Install the workspace package and development tools with `python3 -m pip install -e ".[dev]"` inside the root `.venv`. The CLI is `mcp-workspace`.

```bash
mcp-workspace sync
mcp-workspace setup
mcp-workspace status
mcp-workspace run <name>
mcp-workspace run-all
.venv/bin/python -m pytest
```

`sync` clones missing repositories and fast-forwards existing checkouts only when they are clean, on `main`, and have the expected origin. It refuses unsafe states and does not delete removed checkouts. `setup` syncs first, then creates each service environment and editable-installs that checkout. `run` and `run-all` are foreground operations; Ctrl+C stops the process or group.

`sync` and `setup` regenerate `.vscode/mcp.json` from MCP services only. Treat that file as generated output; web services are intentionally excluded.

## Implementation Map

- [workspace_manager/registry.py](workspace_manager/registry.py): TOML parsing, `ManagedService`, and registry validation.
- [workspace_manager/repositories.py](workspace_manager/repositories.py): safe Git sync, MCP config generation, TCP/HTTP checks, and process launching.
- [workspace_manager/cli.py](workspace_manager/cli.py): `mcp-workspace` commands and per-service environment setup.
- [tests/test_tools.py](tests/test_tools.py): registry, local Git clone, launch, status, health-check, and config coverage.
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md): detailed setup and operations guide.
- [docs/SOFTWARE_REQUIREMENTS.md](docs/SOFTWARE_REQUIREMENTS.md) and [docs/SYSTEM_AND_DESIGN_REQUIREMENTS.md](docs/SYSTEM_AND_DESIGN_REQUIREMENTS.md): behavior and architecture requirements.

## Verification and Boundaries

The manager test suite last passed with 10 tests using `.venv/bin/python -m pytest`. Pylance reported no errors in the changed Python files. Re-run these checks after changes; no service-level integration check is possible until a service is registered and its remote is available.

`run-all` is a convenience foreground process coordinator, not a daemon or production supervisor. TCP status is not protocol validation. A configured web health path is only a shallow HTTP check. The manager does not configure authentication, TLS, firewall policy, or nginx. Keep listeners local unless deployment controls are deliberately provided.

The workspace directory was not available as a Git worktree during the previous validation, so Git diff/history checks were unavailable. Do not initialize, commit, or restructure version control as part of routine handover without confirming that is desired.

## Suggested Next Steps

1. Add approved MCP or web repositories to `repositories.toml`, assigning unique ports and keeping credentials out of the file.
2. Run `mcp-workspace sync`, review each checkout, then run `mcp-workspace setup`.
3. Use `mcp-workspace status` and launch one service before using `run-all`.
4. For a web service, confirm its command binds to the provided host/port and that its health path responds successfully.
5. Consider Windows CI, broader invalid-registry tests, and service-specific integration checks as the registry becomes populated.