# Model routing update — 2026-07-31

This note records the evidence and decisions behind Goldilocks v0.4.5. It updates current routing without rewriting the prices attached to older benchmark runs.

## Current OpenAI economics

Official standard short-context API rates, USD per 1M tokens:

| Model | Input | Cached input | Output | Goldilocks starting role |
|---|---:|---:|---:|---|
| GPT-5.6 Sol | $5.00 | $0.50 | $30.00 | Lead / Critical / final integration |
| GPT-5.6 Terra | $2.00 | $0.20 | $12.00 | Standard |
| GPT-5.6 Luna | $0.20 | $0.02 | $1.20 | Fast |

Luna is one tenth of Terra and four percent of Sol at each listed rate. Codex plan estimates also expose roughly ten times as many Luna messages as Terra messages. GPT-5.3-Codex-Spark remains useful where its separately metered Pro coding pool lowers opportunity cost, but that billing advantage does not make it the universal Fast route.

Sources: [OpenAI API pricing](https://developers.openai.com/api/docs/pricing), [Codex plan estimates](https://learn.chatgpt.com/docs/pricing), and [OpenAI workload guidance](https://developers.openai.com/tracks/building-agents#how-to-choose).

## v0.4.5 starting routes

- **Luna is the universal Fast baseline** for focused coding, tests, exploration, extraction, routing, automation, and bounded content production.
- **Spark is the optional code-quota specialist** for text-only deterministic coding batches whose separate allowance repays external startup cost.
- **Terra is the Standard baseline** when bounded work still needs material domain judgment, cross-file coordination, or local integration. A low-risk Standard-boundary unit with stable interfaces and decisive acceptance may probe Luna once; a quality miss upgrades to Terra.
- **Sol remains Lead** for intent, architecture, trust boundaries, Critical work, shared decisions, final integration, and combined acceptance.

Availability, tools, modality, privacy, authority, and the task-specific quality floor are hard gates before price. The classification is made after decomposition: Fast means low remaining discretion, not a small original task.

## Local activation audit

A privacy-preserving audit of recent Codex project sessions found that activation and execution had separated:

- the root Hook injected Goldilocks 10 times on July 28, 25 times on July 29, and 45 times on July 30;
- the three most recent substantial development projects used many local parallel tool batches, but dispatched no Goldilocks Luna, Terra, or Spark child;
- a later task did start two subagents, but both inherited Sol instead of taking explicit Fast or Standard routes;
- historical routing state contained stopped Spark, Luna, and Terra workers, proving the routes had worked earlier, while every `verified_passes` counter remained zero.

This is an operational audit, not a model-quality benchmark. It shows that the models were callable but the Lead often stopped after reading the thin root Skill, never entered `orchestrate.md`, and treated a worker stop as the end of the audit trail.

v0.4.5 therefore adds two controls without making all work orchestrated:

1. visibly multi-unit implementation must perform one constant-time make-or-delegate comparison before Lead edits; Direct is still valid when briefing and review cost more;
2. native worker stops remain observations until Lead reruns combined acceptance and records `verified_pass` or `verified_fail`. Only verified passes may seed reusable execution memory.

No private prompt text, source code, or acceptance text is stored. Gate records use hashes; the new outcome recorder stores only an evidence hash.
