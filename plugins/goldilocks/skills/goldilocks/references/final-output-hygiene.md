# Final-output hygiene

Use this reference only when the root Skill's trigger is present. It keeps a final deliverable anchored to accepted, verified current state without hiding material history.

## One baseline per surface

Before writing each relevant surface, choose its authoritative baseline: the accepted verified state for a final answer, the current repository state for README and code comments, the executed event record for a log, and the actual external result for a commit, PR, release, or handoff. Write the title, opening, filename, comment/docstring, test name, log entry, README, commit/PR/release text, and handoff from that baseline.

Session proposals that were not adopted, and user corrections, are control information. They guide the result but are not deliverable facts. Do not reintroduce them through synonyms, parenthetical contrasts, or “no X version” framing. State the accepted result directly.

Examples: name a test for the behavior it verifies, a log for the observed event and cause, and a README for the product as it is now. A final answer starts with the delivered outcome and decisive evidence, not the conversational path to it.

## Preserve facts that remain material

Hygiene is not deletion or concealment. Retain, in the appropriate surface:

- real baseline removal, migration, API compatibility, and security or legal audit facts;
- an explicitly requested comparison;
- external actions already performed, including partial failure and their actual results;
- unresolved risks, limitations, and follow-up ownership; and
- user-owned and concurrent pre-existing changes.

When a previous state must be mentioned, use the authoritative factual baseline (for example, a migration's source and target schema or an executed release result), not the rejected wording or the correction dialogue. If the fact is uncertain, say so rather than smoothing it away.

## Minimum-sufficient pass

For an ordinary task, review each changed, relevant output surface once before finalizing. Do not add a freeze, scanner, automatic agent, full artifact bundle, or repeated cleanup loop. Escalate only when a concrete high-risk or strong-contamination case passes Goldilocks's existing gain/risk gate; otherwise use the normal one ordinary repair and rerun only failed or affected checks.

Logs record observed state, cause, and events. They do not turn emphasized user wording, prohibited terms, or chat corrections into runtime facts. README text describes current product behavior, not session history. Keep source comments and docstrings similarly factual and local.
