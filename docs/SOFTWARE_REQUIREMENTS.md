# Software Requirements

These requirements are for the workspace maintainer's control-plane software. MCP and web service maintainers own and test feature behavior in their own repositories; this workspace tests integration and operations only.

## Role Boundaries

- The **workspace maintainer** configures the registry and operates manager commands.
- The **service maintainer** supplies a repository that follows the launch contract; the workspace does not modify its feature code.
- The **MCP host/client** consumes endpoints but is not managed by the workspace software.
- An **infrastructure operator** is optional and owns nginx/deployment policy only when that responsibility is delegated.

## Functional Requirements

| ID | Requirement | Verification |
| --- | --- | --- |
| SWR-01 | The manager shall load typed service entries from root `repositories.toml`, while reading legacy `[[servers]]` entries as MCP services. | Registry parser tests and CLI invocation. |
| SWR-02 | The manager shall reject invalid or duplicate names, unsupported Git URLs, invalid ports, and duplicate ports. | Unit tests for invalid registry entries. |
| SWR-03 | `sync` shall clone missing repositories from branch `main` into `src/<name>`. | Integration test using a local Git remote. |
| SWR-04 | `sync` shall fast-forward only a clean checkout whose origin matches the registry and whose current branch is `main`. | Tests for clean update and refusal cases. |
| SWR-05 | `sync` shall not delete checkouts absent from the registry. | Review and test that no deletion operation occurs. |
| SWR-06 | `setup` shall synchronize first, then create a per-checkout `.venv` and install that checkout in editable mode. | Test or manual check with a template repository. |
| SWR-07 | `setup` shall fail clearly if a registered checkout has no `pyproject.toml`. | CLI test for missing project metadata. |
| SWR-08 | `run <name>` shall launch an MCP executable or a web service's argv command from its checkout, using localhost and its registered port without invoking a shell. | Unit test of process arguments/environment and local smoke test. |
| SWR-09 | `status` shall report clone state, branch, dirty/clean worktree, and TCP endpoint availability; web services may additionally configure an HTTP health path. | Unit tests for cloned, un-cloned, online, offline, healthy, and unhealthy cases. |
| SWR-10 | `sync` and `setup` shall regenerate `.vscode/mcp.json` for MCP services only, using HTTP `/mcp` URLs. | JSON generation and service-filtering tests. |
| SWR-11 | An empty registry shall be valid and produce an actionable message, not a failure. | CLI smoke test. |
| SWR-12 | Registry changes shall not cause automatic deletion of removed repositories or their environments. | Manual workflow test and code review. |
| SWR-13 | `run-all` shall start every registered, provisioned service with its own configured localhost port and stop the process group on Ctrl+C or unexpected child exit. | Unit test of process launch and cleanup; manual multi-service smoke test. |
| SWR-14 | `start`, `start-all`, `stop`, and `stop-all` shall manage tracked background service processes, prune stale PID records, and expose running PIDs through `status` (including named service filters). | Unit tests for background start/stop, idempotency, stale PID pruning, and CLI dispatch. |

## Quality Requirements

- **Isolation:** installing or updating a service must not install its dependencies into the root workspace environment or another service's environment.
- **Cross-platform operation:** paths and virtual-environment executables must work on macOS and Windows.
- **Safety:** synchronization must refuse local modifications, unexpected origins, and unexpected branches rather than reset or overwrite them.
- **Traceability:** repository identity and port assignment must be explicit in `repositories.toml`; generated configuration must be reproducible from that file.
- **Usability:** failures should identify the server and the corrective action where practical.
- **Minimal privileges:** Git credentials remain managed by Git/SSH and are never copied into the registry or generated MCP config.
- **Operational honesty:** TCP availability must not be presented as MCP protocol validation; an HTTP health path is only a shallow web application check.

## Acceptance Criteria

A maintainer can register MCP or web repositories, clone them from `main`, provision isolated environments, run them on registered localhost ports, inspect basic endpoint availability, and produce VS Code MCP configuration for MCP services without installing service dependencies into the root workspace environment. Local changes and unsafe checkout states are preserved and reported rather than overwritten.

## Current Implementation Notes

The workspace currently tests registry validation, clone behavior against a local Git remote, generated endpoint configuration, endpoint availability, and launch environment variables. Production-grade process supervision, MCP-level health checks, Windows CI, and nginx integration tests are not currently implemented.
