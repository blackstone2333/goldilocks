# Trigger evaluation

`trigger-cases.jsonl` defines the expected route and process budget before v0.2 implementation. Run each behavioral arm in a fresh context that contains only system-format skills and the arm under test.

## Isolation used for the pilot

- Bundled Codex CLI: `/Applications/ChatGPT.app/Contents/Resources/codex`
- Temporary `HOME` and `CODEX_HOME`
- Goldilocks skill symlinked as the only non-system skill
- Plugins, memories, rules, and multi-agent mode disabled
- Ephemeral, read-only execution

The CLI prompt inspection confirmed that Superpowers, Ponytail, Grill, qclaw, user skills, and user plugins were absent. The model-visible skill set contained only system format skills plus `goldilocks:goldilocks` for the Goldilocks arm.

## Result policy

- `PASS`: expected quality and process budget were met.
- `FAIL`: an observable quality, triggering, token, latency, authority, or proportionality contract was missed.
- A new engine or thin entry may be implemented only when a valid behavioral or static capability FAIL names it in `gap_engines` or `gap_entries`.
- One pilot failure is a RED candidate, not a final wording decision. Reproduce wording changes with a no-skill control and at least five fresh runs before GREEN.

Raw CLI thread IDs and token usage are recorded for behavioral runs in `results/red-baseline.jsonl`; deterministic missing-surface failures may use a static audit without a thread ID. Total and cached input tokens are kept separate because cached context still measures loaded context but may have different billing and latency effects.
