# Stop Hook token receipt was invisible

## Symptom

Per-turn token baselines and receipt hashes existed, but users did not see a usage line after completed tasks.

After the first local fix, short Direct tasks displayed `Usage: Sol 0 ... total 0 tokens` even though the task consumed tokens.

Later multi-model tasks displayed only Sol even after a Terra child completed; nested Luna work was also at risk of omission.

## Root cause

The Stop Hook returned the receipt as `systemMessage`. Codex Desktop executed and recorded the Hook result but did not render that field as normal assistant text.

The pre-final `--current` query has a second host-ordering boundary: Codex appends the `token_count` record for the model call that invoked the query only after the tool returns. If no earlier model checkpoint exists in the turn, the latest cumulative total still equals the prompt baseline and the calculated delta is zero. In the reproduced task, the query printed zero at `04:07:26.410Z`; the next record at the same timestamp then added 161,739 input and 473 output tokens, and the completed turn delta was 324,747 tokens.

Native `SubagentStop` payloads do not currently include Token fields, so recent `executions` rows contain the correct Terra model and lifecycle but null usage. The child rollout identified by `agent_id` does contain cumulative `token_count` records. External Luna/Spark rows contain usage, but a Fast task created by a Standard child uses that child's session as `parent_session_id`; the old root-only query could not see it.

Observed fallback decisions may also store the child's `turn_id` rather than the parent's usage-baseline `turn_id`. Native ownership must therefore join by parent session plus `started_at >= baseline`, not by assumed turn-ID equality.

## Fix

`usage_reporter.py --current` now reads the active turn's existing local telemetry and emits one compact per-model Token line. The prompt contract asks Lead to run it once immediately before the final answer and append the output. It never estimates missing data or calls another model.

`PostCompact` now restores the same pre-final Usage instruction after every automatic or manual compaction. Previously it restored only continuity state, and stayed entirely silent without continuity debt; a long turn could therefore retain exact worker telemetry while forgetting to append the visible receipt.

A second recurrence exposed a different boundary. `usage_receipt_gate()` embedded the absolute path of the versioned plugin cache that generated the prompt. One live turn received the `0.4.5+codex.20260805165220` path at `10:44:54Z`; Codex replaced that cache with `0.5.0-alpha.1` at `10:49:11Z`; Lead ran the stale command at `10:51:16Z` and received `Errno 2`. There was no compaction, Lead did not forget the command, and mid-flight user steering remained in the same turn.

The injected command now asks `codex plugin list --json` for the currently enabled Goldilocks source at execution time, then runs that source's reporter. It contains no originating cache path. A local forwarding entry at the removed `0.4.5` path protects tasks that were already in flight when this fix was applied; it is compatibility state, not part of the distributable plugin.

An all-zero pre-final snapshot must be treated as unavailable and omitted. The exact completed total remains captured by the Stop Hook for audit, but current Codex Desktop does not expose a way for a plugin Hook to append that post-final value to the already-rendered assistant answer.

For completed native children, recover exact cumulative usage from the uniquely named child rollout and backfill the execution row. Traverse native child ownership before collecting external routes so Standard → Fast usage rolls up once to Lead.

## Verification

- `python3 tests/test_usage_reporter.py`
- `python3 tests/test_recovery_hook.py`
- The recovery regression covers compaction with no ledger, continuity debt without a ledger, and an active ledger.
- The cache-switch regression executes a previously generated prompt command after changing the active plugin root and proves it reaches the new reporter.
- The removed `0.4.5` command path successfully forwarded a live `--current` call to the enabled `0.5.0-alpha.1` source.
- Full contract suite and Skill validation.
- A real Terra child with null database telemetry recovered `2,774,123` input, `2,614,528` cached input, and `28,552` output tokens from its rollout, then backfilled the row with `missing=0`.
- A real historical Standard → Fast task produced one combined receipt containing both Terra and Luna.

## Limitation

The visible line is a lower-bound snapshot when earlier model checkpoints exist. On a one-call Direct answer, it is omitted rather than showing a false zero. Forcing exact post-final display would require another model turn or host UI support and is intentionally avoided.

## Do not repeat

- Do not add sleeps or polling: Codex does not append the invoking call's `token_count` until the tool returns.
- Do not run a second Lead turn merely to expose usage; that changes the usage being measured and spends more expensive tokens.
- Do not estimate the missing tail or relabel a stale zero delta as actual usage.
- Do not embed `Path(__file__)` or any versioned cache root in a command that may execute later in the turn; resolve the enabled plugin at execution time.

## Status

Included in `v0.5.0-alpha.1` for opt-in field testing. The regression covers stale snapshots, native child recovery, nested external aggregation, and dynamic model labels; the documented host-ordering limitation remains.
