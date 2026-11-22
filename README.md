# Service Operations Workspace

This repository is the control plane for MCP servers and web backends maintained in separate Git repositories. It is for the **workspace maintainer**, not for developing service features. Each service maintainer owns their repository's code, dependencies, tests, and `main` branch. One person may perform both roles, but the responsibilities and environments stay separate. The root `.venv` is for workspace management only; each checkout under `src/` gets its own `.venv` and dependencies.

## Set up the workspace

Use Python 3.11 or newer:

```bash
python3 -m venv .venv
```

macOS/Linux:

```bash
.venv/bin/python -m pip install -e ".[dev]"
```

Windows PowerShell:

```powershell
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Activate the workspace environment before using the `mcp-workspace` command.

macOS/Linux: `source .venv/bin/activate`

Windows PowerShell: `.venv\Scripts\Activate.ps1`

The editable install registers the `mcp-workspace` CLI from the root `pyproject.toml`. If you do not activate the environment, invoke `.venv/bin/mcp-workspace` on macOS/Linux or `.venv\Scripts\mcp-workspace.exe` on Windows. The manager uses Python's standard library and the `git` executable; it does not install FastMCP into the workspace environment.

If migrating from the earlier monorepo layout, recreate the existing root `.venv` once; it may still contain FastMCP and server dependencies from the old setup.

## Register a service

The workspace maintainer registers a service after its maintainer has published a Git repository. MCP services follow `mcp_template`; web services provide an argv-style startup command.

MCP example:

```toml
[[services]]
name = "my-time-server"
type = "mcp"
url = "https://github.com/your-org/my-time-server.git"
port = 8101
```

Web example (FastAPI with Uvicorn):

```toml
[[services]]
name = "my-api"
type = "web"
url = "https://github.com/your-org/my-api.git"
port = 8201
command = ["python", "-m", "uvicorn", "app.main:app", "--host", "{host}", "--port", "{port}"]
health_path = "/health"
```

Names and ports must be unique. The manager clones the `main` branch into `src/<name>/` and installs each repository into its own `.venv`. Web commands are argument arrays, not shell strings; `{host}` and `{port}` are replaced with the configured localhost address and port. `health_path` is optional and enables an HTTP GET check in `status`. Legacy `[[servers]]` entries remain accepted as MCP services; new entries should use `[[services]]`.

## Commands

```bash
mcp-workspace sync
mcp-workspace setup
mcp-workspace status [name ...]
mcp-workspace start <name> [name ...]
mcp-workspace start-all
mcp-workspace stop <name> [name ...]
mcp-workspace stop-all
mcp-workspace run my-time-server
mcp-workspace run-all
```

`sync` clones missing repositories and fast-forwards clean checkouts from `origin/main`. It refuses to update a checkout with local changes, a different origin, or a branch other than `main`; it never deletes checkouts removed from the registry. `setup` syncs first, then creates each server's `.venv` and installs that checkout in editable mode. `status` reports each checkout's branch, working-tree state, whether its configured local port accepts connections, optional web HTTP health, and any tracked background PID; pass one or more names to inspect specific services. `start` and `start-all` launch services in the background with tracked PIDs and logs under `.workspace_runtime/`; `stop` and `stop-all` terminate tracked background services cleanly. `run <name>` launches one configured server in the foreground, and `run-all` starts every registered server in one foreground command (press Ctrl+C to stop them all). Launch commands require setup first.

The manager regenerates `.vscode/mcp.json` from MCP services only, using the configured local HTTP ports and `/mcp` endpoint. Web services are launched and monitored by the workspace but are not emitted as MCP endpoints. Keep services bound to localhost behind nginx unless the deployment has appropriate authentication and network controls. Nginx configuration belongs in this workspace; service source and dependencies belong in each service repository.

## Template and examples

`mcp_template/` is the starting structure for new server repositories. Existing time, geolocation, and gambling implementations are kept in `examples/` as reference examples; they are not automatically cloned or updated because no upstream Git URLs have been configured for them. The examples share their own environment and are separate from the control-plane `.venv`.

## Validate the control plane

```bash
.venv/bin/python -m pytest
```

## Documentation

See [HANDOVER.md](HANDOVER.md) for the workspace status and agent handoff. See [docs/](docs/README.md) for maintainer requirements, system design, software requirements, and the user guide. Workspace changes are recorded in [CHANGELOG.md](CHANGELOG.md).