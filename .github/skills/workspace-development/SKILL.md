---
name: workspace-development
description: "Develop, refactor, test, and document control-plane features in workspace_manager. Use when implementing new CLI commands, registry validations, health checks, bug fixes, or documentation updates for this workspace."
argument-hint: "<feature or bug description>"
---

# Workspace Development

Maintain and extend the `service-ops-workspace` control plane cleanly while preserving strict isolation between the workspace manager and managed services.

## When to Use
- Adding or modifying `mcp-workspace` CLI commands, registry schema, sync/process logic, or health checks.
- Fixing bugs or improving cross-platform (macOS / Windows) behavior in `workspace_manager/`.
- Updating control-plane requirements and operator documentation.

## Architectural Guardrails
- **Standard-library control plane**: Keep `workspace_manager` lightweight (stdlib + `git` CLI) unless the user explicitly approves adding a root dependency in `pyproject.toml`. Never add FastMCP or service runtime libraries to root `pyproject.toml`.
- **Cross-platform paths & processes**: Account for both POSIX (`.venv/bin`, signals/sessions) and Windows (`.venv/Scripts`, `.exe`, `CREATE_NEW_PROCESS_GROUP` / `taskkill`).
- **No shell injection**: Launch commands as argument arrays (`shell=False`), never interpolated shell strings.
- **Non-destructive Git**: Never auto-delete checkouts in `src/` or overwrite dirty/non-`main` service worktrees.

## Procedure
1. **Inspect Impacted Modules**:
   - `workspace_manager/registry.py` — TOML schema parsing & validation (`ManagedService`).
   - `workspace_manager/repositories.py` — Git sync, `.vscode/mcp.json` generation, TCP/HTTP status, foreground/background process management.
   - `workspace_manager/cli.py` — `mcp-workspace` argument parsing & command dispatch.
2. **Implement & Add Unit Tests**:
   - Add or update focused unit tests in `tests/test_tools.py` using `tmp_path` and `monkeypatch` (avoid network dependencies in tests).
3. **Run Validation**:
   - Execute `.venv/bin/python -m pytest` and ensure all tests pass with zero errors.
4. **Keep Docs & Context Aligned**:
   - Update `README.md`, `docs/USER_GUIDE.md`, `docs/SOFTWARE_REQUIREMENTS.md`, and `CHANGELOG.md` (`## Unreleased`) when CLI behavior or contracts change.
   - Run the `refresh-workspace-context` workflow to update `.github/workspace-context.md` if workspace capabilities or active focus changed.
