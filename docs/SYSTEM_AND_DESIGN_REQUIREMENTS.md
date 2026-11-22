# System and Design Requirements

## System Context

The workspace is a lightweight control plane around separately versioned MCP server and web backend repositories. It does not contain managed services as a shared application.

The two core human roles are the workspace maintainer, who operates this control plane, and the service maintainer, who develops and releases an individual service. A single contributor may perform both roles. MCP hosts/clients and Git hosting are system actors; nginx/infrastructure ownership is a separate optional role only when delegated.

```text
Workspace repository
  repositories.toml -> service types, commands, health paths, clone/update policy, names, ports
  workspace_manager -> sync, setup, status, run, MCP config generation
  .venv -> workspace manager and its development tools only
  src/<service-name> -> independent Git checkout and service-owned .venv
  nginx/ -> operator-maintained proxy configuration, when needed

MCP client -> localhost or nginx -> MCP endpoint at /mcp
Web client -> localhost or nginx -> configured web backend
```

## Repository Boundaries

- The workspace repository owns the registry, manager, documentation, tests, and operational configuration.
- Each directory under `src/` is an independent Git checkout. Its history, dependencies, tests, and runtime environment are owned by that service repository.
- `mcp_template/` defines the expected server integration contract. It is a scaffold, not a runtime dependency shared by deployed servers.
- `examples/` contains reference implementations and is not a registered or managed server repository.
- The workspace `.venv` must not install FastMCP or server application dependencies. Each server gets `src/<name>/.venv` from its own project metadata.

## Role Ownership

- The workspace maintainer owns `repositories.toml`, `workspace_manager`, workspace documentation and tests, generated MCP client configuration, and any workspace-level nginx configuration.
- The service maintainer owns the repository, its feature code, dependencies, tests, releases, and conformance to the launch contract.
- The Git hosting provider supplies remote repository content; it is not responsible for local environment setup.
- MCP hosts/clients consume server capabilities; they are not operated by this workspace manager.
- An infrastructure operator may own nginx, TLS, firewall, and host-level policy when these tasks are delegated. Otherwise they remain workspace-maintainer responsibilities.

## Control-Plane Components

- `repositories.toml` is the authoritative list of server names, Git URLs, and local HTTP ports.
- `workspace_manager.registry` validates service types, names, URLs, commands, health paths, and port uniqueness before operations.
- `workspace_manager.repositories` performs Git operations, TCP and optional HTTP health checks, launches service processes, and writes MCP-only `.vscode/mcp.json` configuration.
- `workspace_manager.cli` provides the `mcp-workspace` command.
- `.vscode/mcp.json` is generated output. Registry edits, not manual JSON edits, are the supported way to change managed endpoints.

## Operating Requirements

- Python 3.11 or newer is required by the workspace manager.
- Git must be installed and available on `PATH`; access to private repositories must already be configured using the user's normal Git credential or SSH-agent mechanism.
- Supported operator environments are macOS and Windows. Python virtual environment executable paths differ by OS; the manager handles those path differences.
- Repository names must be safe directory names and unique. Ports must be valid TCP ports and unique within the registry.
- Each remote must expose a branch named `main`. The manager does not configure alternate branches.
- Every registered repository must contain `pyproject.toml`. MCP services install a console command named `mcp-server`; web services declare an argv command in the registry.
- MCP services must honor `MCP_HOST`, `MCP_PORT`, and `MCP_TRANSPORT=http`, and expose Streamable HTTP at `/mcp` to match generated configuration. Web commands can use `{host}` and `{port}` argument placeholders; an optional `health_path` enables an HTTP GET status check.

## Network and Deployment Design

- Managed services bind to `127.0.0.1` by default; MCP launches also force HTTP transport. Web launches expose `HOST` and `PORT` environment values and substitute matching command placeholders.
- `status` checks TCP availability for all services. For web services with `health_path`, it also performs an HTTP GET and reports the HTTP result; it does not validate feature behavior or service identity.
- Nginx configuration is maintained separately in the workspace and is not generated or reloaded by the manager. If nginx is used, it should proxy to the correct localhost port and preserve the MCP HTTP behavior required by the chosen deployment.
- Do not expose a server directly to an untrusted network without authentication, TLS where appropriate, and network controls. The manager does not provide those controls.
- Sync is intentionally non-destructive: dirty trees, origin mismatches, and non-`main` branches are refused; removed registry entries are not deleted from disk.

## Design Decisions

- Use a plain TOML registry instead of embedding repository URLs in Python code.
- Clone each repository directly under `src/<name>`; do not use Git submodules because the workspace's workflow is explicitly to maintain independent working checkouts and fetch each repository's `main` branch.
- Use one root environment for operations and one environment per server to prevent dependency coupling.
- Keep server processes in the foreground for predictable logs and Ctrl+C shutdown. `run-all` supervises the command lifetime of its child processes and stops the group on interruption or unexpected exit; it is not a daemon, restart policy, or boot-time service manager.
- Generate local MCP configuration from the registry so port assignments and client endpoints do not drift.
