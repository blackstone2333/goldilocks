# Goldilocks v0.2.5 continuity smoke test

- Date: 2026-07-20
- Host: Codex CLI 0.145.0-alpha.18
- Model: GPT-5.3-Codex-Spark, low reasoning
- Plugin: `0.2.5+codex.20260720082836`
- Mode: fresh ephemeral context, read-only sandbox, vetted plugin hooks enabled for the run

## Scenario

The isolated repository contained `.goldilocks/ACTIVE.md` with:

- a stable handoff objective;
- an already-applied `QUESTION` steer;
- completed GitHub compaction research;
- one exact next action to read a local source file;
- explicit boundaries not to repeat the search or answer the steer again.

The fresh agent received only a generic request to continue and report the objective, prior-question status, action, release label, and do-not-repeat items.

## Result

Pass. The agent:

1. read `.goldilocks/ACTIVE.md` before acting;
2. preserved the original objective;
3. recognized the previous question as already applied and did not answer it again;
4. performed only the exact next action;
5. found release label `porridge-025`;
6. repeated the do-not-repeat boundary rather than reopening completed research;
7. made no file edits.

The run used 10,499 reported tokens. This number includes host startup and Skill-context overhead and has no matched baseline, so it is not a performance claim.

## Limits

This is one fresh-context recovery smoke test, not an automatic-compaction certification. It bypassed persisted hook trust after locally vetting the hook definition. Real validation still needs long-running projects, actual mid-turn auto-compaction, multiple consecutive compactions, steering delivered during tool execution, delayed-hook behavior, and comparisons with the hook disabled.
