# Changelog

Notable changes to the service operations workspace are recorded here. Service feature releases belong in their respective service repositories.

The workspace maintainer owns this changelog. Service maintainers record feature changes in their own repositories.

## Unreleased

- Added the `service-ops` custom agent, `.github/copilot-instructions.md`, `.github/workspace-context.md` continuity state, and five Agent Skills (`workspace-continuity`, `refresh-workspace-context`, `service-operations`, `service-setup`, `workspace-development`) for VS Code Chat and Copilot CLI.
- Added tracked background lifecycle commands (`start`, `start-all`, `stop`, `stop-all`) and named `status` filtering to `mcp-workspace`.
- Added typed MCP and web service registry entries, configurable web commands, optional HTTP health checks, and MCP-only VS Code config generation.
- Reframed the root project as an MCP server monitoring and operations control plane.
- Added a registry-driven workflow for cloning and fast-forwarding independent server repositories from `main`.
- Added per-server environment setup, foreground launch, TCP endpoint status, and generated VS Code MCP configuration.
- Added `mcp-workspace run-all` for foreground startup and coordinated shutdown of registered servers.
- Reserved `src/` for managed Git checkouts and preserved the original sample servers under `examples/`.
- Added maintainer-focused use case, system/design, software requirement, and user guide documentation.
- Clarified workspace maintainer and MCP server maintainer responsibilities across workspace documentation.
