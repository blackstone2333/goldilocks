---
name: using-git-worktrees
description: Use when feature work needs isolation, concurrent branches must not share state, a dirty baseline must be protected, or the user explicitly requests a git worktree.
---

# Using Git Worktrees

Read the isolation section of [orchestrate.md](../goldilocks/references/orchestrate.md). Detect host-provided isolation first, audit branch and dirty state, and create a worktree only when protection exceeds setup and merge cost. Prefer native tooling and established ignored locations. Preserve user changes and record integration and cleanup ownership. Never create duplicate isolation or automatically delete a worktree or branch.
