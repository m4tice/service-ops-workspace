---
name: workspace-continuity
description: "Resume work in a new VS Code workspace or Copilot CLI session without re-explaining the project. Use when asked to continue, resume, catch up, summarize current workspace status, or hand off between sessions."
argument-hint: "[optional focus area]"
---

# Workspace Continuity

Reconstruct accurate, up-to-date project and service state so the maintainer can immediately continue work in a fresh VS Code Chat or Copilot CLI session without writing or reading lengthy handover files.

## When to Use
- The user selects **Schaltmeister** in a new session/workspace and says "continue", "resume", "what's the status?", or "where did we leave off?"
- Before starting non-trivial feature work when current workspace context has not yet been checked in this session.

## Procedure
1. **Read Durable Working Context**: Read `.github/workspace-context.md` to understand current capabilities, recent architectural decisions, active focus, and planned next steps.
2. **Verify Against Live State**:
   - Inspect `repositories.toml` to see currently registered MCP and web services.
   - Run `git status -sb` and `git log -n 3 --oneline` to check active branch, uncommitted changes, and latest commits.
   - Run `.venv/bin/mcp-workspace status` (if `.venv` exists) to check clone state, endpoint availability, web health, and tracked PIDs.
3. **Reconcile Any Drift**: If live files, commits, or `repositories.toml` have advanced beyond `.github/workspace-context.md`, trust the live repository state and note the delta.
4. **Present a Concise Brief**:
   - **Branch & Worktree**: current Git branch and cleanliness.
   - **Registered Services**: count and online/offline/health summary (or note if none registered).
   - **Active Focus & Next Step**: 1–3 bullets on where work stands and what you are ready to do next.
