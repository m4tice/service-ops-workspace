---
name: service-setup
description: "Register, synchronize, and provision a new MCP server or web backend in repositories.toml. Use when asked to add, onboard, register, or set up a new backend or MCP server."
argument-hint: "<name> <git-url> [mcp|web] [port]"
---

# Service Setup

Safely register a new MCP server or web backend in `repositories.toml`, synchronize its `main` branch into `src/<name>`, provision its isolated `.venv`, and verify readiness.

## When to Use
- "Set up a new backend or MCP server."
- "Register `<repo-url>` on port 8105."
- Re-running provisioning (`setup`) after adding or updating registered repositories.

## Procedure

### 1. Collect & Validate Registry Inputs
1. Read `repositories.toml` to inspect existing service names and assigned ports.
2. Ensure you have required fields (ask concisely if any are missing):
   - `name`: unique, filesystem-safe slug (`[A-Za-z0-9._-]+`, e.g., `billing-api`).
   - `type`: `"mcp"` or `"web"`.
   - `url`: clean HTTPS or SSH Git URL (`https://...` or `git@...`). **Never accept or write embedded credentials/tokens.** Remind that the remote repository must have a `main` branch and a `pyproject.toml`.
   - `port`: unique TCP port (`1..65535`) not already used in `repositories.toml` (convention: `81xx` for MCP, `82xx` for web, unless specified).
   - For `type = "web"`:
     - `command`: non-empty TOML string array executed without a shell (e.g., `["python", "-m", "uvicorn", "app.main:app", "--host", "{host}", "--port", "{port}"]`).
     - `health_path` (optional): absolute path starting with `/` (e.g., `"/health"`).
   - For `type = "mcp"`: omit `command` and `health_path` (uses standard `mcp-server` entrypoint and generates `http://127.0.0.1:<port>/mcp`).

### 2. Update `repositories.toml`
Append a clean `[[services]]` block to `repositories.toml`. Do **not** manually edit `.vscode/mcp.json`.

### 3. Synchronize & Provision
1. Confirm before running `setup` if the user only asked to draft the configuration; otherwise run:
   ```bash
   .venv/bin/mcp-workspace setup
   ```
   (`setup` automatically runs `sync` first, regenerates `.vscode/mcp.json` for MCP services, creates `src/<name>/.venv`, and runs `pip install --editable` inside that isolated environment.)
2. If `sync` or `setup` fails:
   - Missing `pyproject.toml` or `mcp-server` entrypoint: report clearly as a service-repository contract issue (do not install service packages into root `.venv`).
   - Dirty checkout / non-`main` branch / origin mismatch: report the exact safety refusal and let the user decide before touching `src/<name>`.

### 4. Verify & Optional Launch
1. Run `.venv/bin/mcp-workspace status <name>` to confirm `branch=main` and `worktree=clean`.
2. Ask if the user wants to start the newly provisioned service now (`.venv/bin/mcp-workspace start <name>`).
