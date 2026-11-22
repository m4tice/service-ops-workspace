---
name: refresh-workspace-context
description: "Update the durable agent-maintained workspace context file (.github/workspace-context.md) when features, capabilities, or project direction change. Use when asked to save/refresh workspace context or after completing a meaningful control-plane feature or architectural decision."
argument-hint: "[summary of new decision or focus]"
---

# Refresh Workspace Context

Keep `.github/workspace-context.md` accurate and compact so any future VS Code workspace or Copilot CLI session immediately understands the current nature and state of the project—eliminating manual `HANDOVER.md` maintenance.

## When to Use
- Explicitly invoked via `/refresh-workspace-context`.
- Automatically at the end of a task that changes workspace capabilities, CLI commands, architectural boundaries, or active development focus.
- **Do NOT use** for trivial Q&A, read-only health checks, or routine start/stop operations where project nature did not change.

## Procedure
1. **Gather Ground Truth**:
   - Read `.github/workspace-context.md`.
   - Check `CHANGELOG.md`, `repositories.toml`, and `git status -sb` to ensure facts match the codebase.
2. **Update `.github/workspace-context.md` In-Place**:
   - Keep the entire file concise (**under 45 lines**).
   - Maintain only four sections:
     1. `## Workspace Identity` (core role and unchanging boundaries)
     2. `## Current Capabilities` (actual implemented CLI commands, registry features, and agent skills)
     3. `## Active Focus & Recent Decisions` (current feature work, key design choices, and high-level registry state—no secrets or ephemeral PIDs)
     4. `## Next Logical Steps` (1–3 actionable follow-ups)
   - Replace obsolete bullets rather than appending chronological logs or conversation history.
3. **Report**: Briefly confirm what changed in `.github/workspace-context.md`.
