# User Guide

This guide is for the **workspace maintainer** (MCP platform operator). It covers repository registration and operations, not feature development inside managed services. Each **service maintainer** owns their repository's source, dependencies, tests, and releases. One contributor may fill both roles, but should keep the workspace and service repositories and environments separate.

The MCP host/client is the consumer of running endpoints, not a maintainer role. Nginx is owned by the workspace maintainer unless an **infrastructure operator** has been assigned that responsibility.

## Prerequisites

- Python 3.11 or newer.
- Git available on `PATH`.
- Read access to each registered remote. Configure HTTPS credentials or SSH keys through Git as usual; do not put credentials in `repositories.toml`.

## Install the Workspace Manager

From the workspace root, create the control-plane environment:

macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Activate the environment for subsequent commands:

macOS/Linux: `source .venv/bin/activate`

Windows PowerShell: `.venv\Scripts\Activate.ps1`

The editable install creates the `mcp-workspace` command from the root `pyproject.toml`. Without activation, invoke `.venv/bin/mcp-workspace` on macOS/Linux or `.venv\Scripts\mcp-workspace.exe` on Windows.

If migrating from the previous combined-server layout, recreate the old root `.venv` once so it no longer contains server dependencies. This environment should contain workspace management and test tools only.

## Register a Service

Edit root `repositories.toml` and add one entry per service. MCP example:

```toml
[[services]]
name = "my-time-server"
type = "mcp"
url = "https://github.com/your-org/my-time-server.git"
port = 8101
```

Web example using FastAPI and Uvicorn:

```toml
[[services]]
name = "my-api"
type = "web"
url = "https://github.com/your-org/my-api.git"
port = 8201
command = ["python", "-m", "uvicorn", "app.main:app", "--host", "{host}", "--port", "{port}"]
health_path = "/health"
```

Use a unique, filesystem-safe name and unused port. Use an HTTPS or SSH Git URL and a remote `main` branch. Every repository needs a `pyproject.toml`. MCP repositories follow the `mcp_template` contract and install `mcp-server`; web repositories declare a command as an array of arguments. The manager executes it without a shell, replaces `{host}` and `{port}` within arguments, and resolves `python`/`python3` or installed commands from that service's `.venv`. `health_path` is an optional absolute URL path checked with HTTP GET by `status`.

The registry supports SSH clone URLs such as `git@github.com:your-org/my-time-server.git`. Do not add tokens, passwords, or private key material to this file.
Existing `[[servers]]` entries are still read as MCP services, but new entries should use `[[services]]` with an explicit `type`.

## Synchronize Repositories

Run from the root:

```bash
mcp-workspace sync
```

This clones missing repositories to `src/<name>` and fast-forwards existing checkouts from `origin/main`. Existing checkouts must have the expected origin, be on `main`, and have no local changes. If sync refuses, inspect that repository and resolve the state deliberately; the manager will not reset, stash, switch branches, or delete it for you.

A registry entry removed from `repositories.toml` is no longer managed or listed in the generated MCP config, but the checkout and `.venv` remain on disk. Remove them manually only after confirming they contain no work you need.

## Set Up Service Environments

```bash
mcp-workspace setup
```

Setup synchronizes first. For each repository it creates `src/<name>/.venv` if needed and installs that project's `pyproject.toml` in editable mode. A service dependency change should be made in that service repository and installed there; it should not be added to the workspace root dependencies.

## Check Status

```bash
mcp-workspace status
```

Status reports whether a repository is cloned, its current branch and working-tree state, and whether a TCP connection can be made to its configured localhost port. For web services with `health_path`, it also sends an HTTP GET and reports whether the response is successful. This is a shallow health check, not a feature-level validation. MCP services receive only a TCP check; use the MCP Inspector or another MCP client for protocol-level validation.

## Run a Service

Start one server per terminal:

```bash
mcp-workspace run my-time-server
```

For MCP services, the manager launches `mcp-server` in the foreground with `MCP_HOST=127.0.0.1`, its registry `MCP_PORT`, and `MCP_TRANSPORT=http`. For web services, it runs the configured command from the service checkout with `HOST=127.0.0.1` and `PORT=<configured-port>`; command arguments may use `{host}` and `{port}` placeholders. Stop it with Ctrl+C. The manager does not daemonize or restart service processes.

To start every registered service together, after running `mcp-workspace setup`, use:

```bash
mcp-workspace run-all
```

Each service runs as a child process with its own configured port. Console output is inherited and may interleave. Press Ctrl+C to stop the group. If one service exits unexpectedly, the manager stops the others and reports the failure. Run `mcp-workspace status` in another terminal to check TCP availability and configured web health paths.

## VS Code and Nginx

`mcp-workspace sync` and `mcp-workspace setup` regenerate `.vscode/mcp.json` from MCP services only. Treat it as generated output; edit `repositories.toml` to change managed MCP endpoints. The generated URLs use `http://127.0.0.1:<port>/mcp`. Web backends are not added to the MCP client configuration.

Nginx is maintained separately and is not configured or controlled by this tool. Keep server listeners on localhost unless there is a specific deployment need. If nginx fronts a server, verify its upstream port and MCP HTTP behavior, protect external access with the deployment's authentication and TLS policy, and keep logs/PID/cache files separate from tracked nginx configuration.

## Troubleshooting

- **`git` not found:** install Git and ensure the executable is on `PATH` in the shell that runs the manager.
- **Authentication or clone failure:** verify the remote URL and test Git access outside the manager. Never paste credentials into the registry.
- **Local changes prevent sync:** review and commit, stash, or otherwise preserve them before retrying. Sync intentionally does not discard work.
- **Origin or branch mismatch:** confirm the registry URL and checkout's `origin`; the manager only updates branch `main`.
- **Command not found:** run `mcp-workspace setup`; verify MCP projects define `mcp-server` or the web command names an installed executable or `python`/`python3`.
- **Endpoint offline:** confirm the service process started with the registered port and bound to `127.0.0.1`; inspect the service's own logs.
- **VS Code endpoint is stale:** run `mcp-workspace sync` to regenerate the MCP config from the registry.
- **Nginx returns errors:** check nginx's upstream, access/error logs, and forwarding configuration. Workspace status checks the local server port, not nginx.
