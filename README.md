<p align="center">
  <img src="plugins/goldilocks/assets/logo.png" width="176" alt="A warm bowl of porridge, the Goldilocks logo">
</p>

<h1 align="center">Goldilocks</h1>

<p align="center"><strong>Not too much process. Not too little rigor. Just right.</strong></p>

<p align="center">
  <a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.3.2-D4A72C" alt="Version 0.3.2">
  <img src="https://img.shields.io/badge/Three_Bears-27%2F27_passed-2ea44f" alt="Three Bears: 27 of 27 Goldilocks cells passed">
  <a href="https://skills.sh/blackstone2333/goldilocks/goldilocks"><img src="https://skills.sh/b/blackstone2333/goldilocks" alt="Install from skills.sh"></a>
  <img src="https://img.shields.io/badge/license-MIT-2563eb" alt="MIT License">
</p>

Goldilocks is a Codex workflow plugin built around the **Just-Necessary Principle**:

> Use the minimum process that preserves a constant quality, safety, authorization, and verification floor.

It provides a Superpowers-compatible workflow surface without requiring every task to pay for the entire workflow stack. Brainstorming, plans, TDD, debugging, worktrees, delegation, review, verification, branch finishing, and skill authoring remain available; each is loaded only when the task earns it.

## Why Goldilocks

- **Dynamic depth:** clear work gets a constant-time Direct-versus-delegate check; complex work receives only the useful management layers.
- **Progressive disclosure:** thirteen compatibility entries route into six shared engines instead of duplicating fourteen long procedures.
- **Native and reuse first:** inspect the project, standard library, established helpers, and proven libraries before inventing new machinery.
- **Decision-frontier questions:** ask only when an answer can materially change the end state, safety, scope, or authorization.
- **Ideas without scope creep:** useful adjacent ideas are preserved for later rather than silently expanding the current task.
- **Evidence before completion:** confidence, old test output, and agent reports never replace fresh evidence for material claims.
- **Hierarchical delegation:** Lead can dispatch execution contracts directly to Fast or give a bounded domain to Standard, which may organize its own Fast workers.
- **Quota-weighted economics:** optimize scarce, high-multiplier model usage and critical-path time while keeping total raw tokens inside a reasonable envelope.
- **Execution memory:** reuse a verified route for recurring task shapes after checking its invalidators instead of paying for the same orchestration decision twice.
- **Real Codex worker routes:** native subagents use explicit host-supported models; eligible Fast work can use the packaged `codex exec` GPT-5.3-Codex-Spark adapter when Spark is missing from the native model list.
- **Quiet update awareness:** the native Codex plugin checks at most once per day, stays silent when current or offline, and reports a newer release once without changing an active task.

## What Goldilocks actually does

Goldilocks is an adaptive router, not a mandatory waterfall. It inspects the repository and the task, activates only the workflow engines that remove real risk, and keeps the acceptance standard constant even when the process depth changes.

| Situation | Goldilocks behavior | Durable output when useful |
|---|---|---|
| Tiny, well-bounded change | Quickly compare Lead Direct with one Fast contract; use whichever finishes and verifies sooner | Usually none |
| Unclear feature or product decision | Align on the end state, material trade-offs, constraints, and acceptance before implementation | Compact spec or decision record when the choice must survive the session |
| Bug with an unknown cause | Reproduce, trace, test hypotheses, identify the root cause, then patch | Reusable debug lesson when recurrence is plausible |
| Multi-step implementation | Create only the necessary plan, prefer existing project patterns and libraries, then execute in coherent units | Plan, work packet, handoff, or project map when continuity requires it |
| Multiple independent units | Build the ready graph; use Lead→Fast or Lead→Standard→Fast while each layer reviews its own scope | Worker and domain evidence plus Lead integration, not parallel-document noise |
| Critical or externally consequential action | Require explicit authorization, Lead ownership, stronger evidence, and independent review where appropriate | Approval and verification evidence |
| Useful idea outside current scope | Preserve it without silently expanding the current task | Deferred-ideas entry |

### Execution and decision flow

```mermaid
flowchart TD
    A["Task arrives"] --> B["Inspect repository, authority, risk, existing methods and verified execution patterns"]
    B --> C{"Fast make-or-delegate check"}

    C -- "Lead finishes sooner" --> D["Lead Direct<br/>Minimum coherent change"]
    C -- "Contract is ready" --> K["Fast worker or parallel Fast workers"]
    C -- "Domain judgment remains" --> T["Standard domain owner"]
    C -- "End state unclear" --> E["Align<br/>Material decisions and acceptance"]
    C -- "Root cause unknown" --> F["Diagnose<br/>Reproduce, trace, test hypotheses"]
    C -- "Multi-step or risky" --> G["Build<br/>Spec and plan only as needed"]
    C -- "Critical or external effect" --> H["Explicit authorization<br/>Lead ownership + stronger review"]

    E --> G
    F --> G
    H --> G
    G --> I["Freeze shared decisions, interfaces and acceptance"]
    I --> J{"Cheapest useful organization?"}
    J -- "Execution contract" --> K
    J -- "Bounded domain" --> T
    J -- "Critical or inseparable" --> L["Lead owns the core"]
    T --> U{"Can Standard externalize the remaining decisions?"}
    U -- "Yes" --> K
    U -- "No" --> V["Standard implements or escalates"]

    K --> W{"Is the selected Fast model available on this route?"}
    W -- "Native host advertises it" --> X["Native worker<br/>Explicit model, bounded context"]
    W -- "Spark is CLI-only" --> Y["Packaged codex exec worker<br/>GPT-5.3-Codex-Spark"]
    W -- "No eligible worker" --> V

    D --> M["Produce fresh acceptance evidence<br/>Tests, review, browser/device checks or targeted verification"]
    X --> M
    Y --> M
    V --> M
    L --> M
    M --> N{"Acceptance passes?"}
    N -- "No" --> O["Return to the relevant engine and iterate"]
    O --> M
    N -- "Yes" --> P["Evidence integrates upward<br/>Lead runs the combined gate"]

    P --> Q{"Will this knowledge matter later?"}
    Q -- "Yes" --> R["Keep only useful spec/plan/handoff, debug lesson, verified execution pattern, deferred idea or changelog"]
    Q -- "No" --> S["Complete without workflow residue"]
    R --> S
```

The invariant is the acceptance floor, not who typed the code. Fast describes low residual discretion after decomposition, not a small original task. Standard describes bounded domain judgment, not medium file count. Lead owns user intent, shared decisions, conflicts, and final quality; it implements only when Direct delivery or an inseparable core makes that cheaper than delegation.

### Hierarchical orchestration in v0.3

Goldilocks treats an agent team like a small company. The user sets direction and accepts the result. Lead acts as product, technical, and project leadership. Standard owns a domain and can turn its decisions into Fast execution contracts. Fast implements and runs focused checks but cannot delegate further.

The hierarchy is dynamic rather than mandatory. A tiny task may stay with Lead or go to one Fast worker. A medium task may go directly to Fast, to Standard, or remain local. A large project can use several Standard domain owners, each coordinating independent Fast work, before evidence integrates upward. There is no fixed worker count: useful concurrency is bounded by the ready dependency graph, host capacity, isolation, integration risk, and reviewer throughput.

Codex routing is equally dynamic. Goldilocks uses native subagents when the host advertises the selected model. If the native host omits Spark while the installed CLI still supports it, `dispatch_codex_worker.py` launches a contract-only `codex exec -m gpt-5.3-codex-spark` worker in the assigned repository or worktree. The adapter disables plugins, apps, MCP servers, and further delegation for that worker, keeps the configured provider and repository instructions, and never silently falls back to Lead.

The routing objective is not minimum raw tokens at any cost. Quality and authority are hard gates; total raw tokens remain bounded; among valid routes Goldilocks minimizes quota-weighted expensive usage and the wall-clock critical path. A route may use slightly more low-coefficient or separately metered worker tokens when it materially reduces scarce Lead usage without increasing defects or review debt.

Recurring routes can be stored as selective project execution patterns after combined verification. Future tasks reuse them only when subsystem, interfaces, risk, tools, billing channel, and acceptance still match. Plugin audit observations are local and concurrency-safe, but a worker stopping is never treated as verified success and internal routing history never enters the user-facing changelog.

Read the [v0.3 hierarchical orchestration design](docs/v0.3-hierarchical-orchestration.md) for the role boundaries, routing order, context policy, audit behavior, and release acceptance.

## Evidence: Goldilocks vs Superpowers

Goldilocks makes one deliberately narrow public claim: it is a more reliable and more efficient **Superpowers replacement** on the tested workflow surface. Two evaluations support that claim without mixing design scores with runtime measurements.

### Test 1 — instruction-level stress test

The original design evaluation ran eight isolated scenarios. Goldilocks was still named `just-necessary`, so this is architectural lineage evidence rather than release runtime evidence. The Goldilocks design averaged **98.9/100 versus 79.2/100**, led all eight scenarios, and used **86.2% less rule text**.

<p align="center">
  <img src="benchmarks/assets/instruction-stress-head-to-head.svg" width="960" alt="Instruction-level stress test: the Goldilocks predecessor leads Superpowers in all eight scenarios and uses 86.2 percent less rule text">
</p>

### Test 2 — real agentic certification

The `v0.2.2` certification build was tested on GPT-5.6 Terra at low reasoning across nine Baby/Mama/Papa tasks, three fresh isolated runs per task, and 27 attempts per workflow. The complete exploratory experiment contained 135 valid turns; the published replacement claim uses only the **54 Goldilocks/Superpowers head-to-head turns**.

<p align="center">
  <img src="benchmarks/assets/agentic-certification-head-to-head.svg" width="960" alt="Real agentic certification: Goldilocks delivered 27 of 27 attempts versus 8 of 27 for Superpowers and used less cost per successful delivery on every measured dimension">
</p>

Goldilocks delivered **27/27** attempts with 100% measured safety; Superpowers delivered **8/27** with 88.9% safety. Nineteen Superpowers attempts stopped before changing source code, so raw totals alone would reward non-delivery.

On the eight exact cells both workflows completed, Goldilocks used 30.6% fewer total tokens, 7.7% less time, 28.6% fewer tool calls, and 66.7% less Skill activity. It used 9.7% more uncached input on that slice—the one comparable efficiency measure it did not win. Charging every attempt and dividing by successful deliveries, Goldilocks used 61.2% fewer total tokens, 70.5% less uncached input, 60.4% less time, 55.4% fewer tool calls, and 89.8% less Skill activity.

Read the [two-test head-to-head report](benchmarks/GOLDILOCKS-VS-SUPERPOWERS.md), the [full runtime certification](benchmarks/three_bears/results/2026-07-18-terra-low-full-certification.md), the [benchmark methodology](benchmarks/three_bears/README.md), the [head-to-head data](benchmarks/three_bears/results/data/2026-07-18-terra-low-full/head-to-head.json), and the [complete per-cell audit data](benchmarks/three_bears/results/data/2026-07-18-terra-low-full/results.json).

## Install

Install the complete Superpowers-compatible suite with the cross-platform `skills` CLI:

```bash
npx skills add blackstone2333/goldilocks --skill '*' --global --agent codex --yes
```

Replace `codex` with `claude-code`, `cursor`, `opencode`, `github-copilot`, or `gemini-cli` for another agent. To install only the self-contained Just-Necessary router, use `--skill goldilocks` instead.

Native Codex plugin:

```bash
codex plugin marketplace add blackstone2333/goldilocks
codex plugin add goldilocks@goldilocks-local
```

Native Claude Code plugin:

```bash
claude plugin marketplace add blackstone2333/goldilocks
claude plugin install goldilocks@goldilocks
```

Do not enable Goldilocks and Superpowers together. See the [complete installation guide](docs/installation.md) for project-local installs, updates, platform IDs, and compatibility details.

## What ships

Goldilocks exposes the familiar workflow entry names needed to replace Superpowers:

| Need | Entry |
|---|---|
| Align on an uncertain end state | `brainstorming` |
| Produce or execute an implementation plan | `writing-plans`, `executing-plans` |
| Build with focused tests | `test-driven-development` |
| Diagnose before patching | `systematic-debugging` |
| Isolate or divide work | `using-git-worktrees`, `dispatching-parallel-agents`, `subagent-driven-development` |
| Request or process review | `requesting-code-review`, `receiving-code-review` |
| Prove completion and finish a branch | `verification-before-completion`, `finishing-a-development-branch` |
| Create or improve Skills | `writing-skills` |

The explicit `goldilocks` router replaces `using-superpowers`. It is intentionally not injected into every task, so trivial work can remain on the Direct path with zero workflow Skill reads.

The compatibility entries progressively disclose six shared engines:

1. **Align** — end state, material decisions, acceptance.
2. **Diagnose** — reproduction, trace, hypothesis, root cause.
3. **Build** — planning, focused TDD, coherent execution.
4. **Orchestrate** — worktrees, delegation, model routing, integration ownership.
5. **Prove** — review, verification, authorization, branch completion.
6. **Evolve** — idea capture, retrospection, and Skill improvement.

For work that must survive a session or be handed to another engineer, the engines share a small **Continuity Protocol**. It reuses the repository's existing docs layout when possible; otherwise it can keep a project structure map, compact work packet or split spec/plan/handoff, selective debug memory, verified execution patterns, deferred ideas, and a user-facing changelog. Direct tasks do not create workflow records by default, but can still create or update documentation when it is the deliverable or necessary for correctness. Internal execution memory stays separate from the release changelog. The protocol adds neither another visible Skill nor another engine.

When compaction or mid-flight steering threatens an active long task, Continuity can add one temporary `.goldilocks/ACTIVE.md` execution frontier. It keeps the stable objective, consumed steering, Done/In progress/Remaining, one exact next action, repository and verification state, a do-not-repeat boundary, and the terminal condition. Recovery reads this ledger and reconciles it with Git before continuing; repository evidence wins. The native Codex plugin also includes silent-by-default recovery hooks and an optional complete compaction-prompt asset. See [installation and Codex recovery setup](docs/installation.md#codex-continuity-recovery).

For multi-unit plans, a shared **Hierarchical Orchestration Protocol** first compares Direct execution with delegation. It can route a complete contract to Fast, assign a bounded domain to Standard, or let Standard organize Fast workers after local decisions are fixed. Selection uses a quality gate, quota-weighted subscription burn, a raw-token envelope, critical-path latency, confidence, recency, execution memory, and a Pareto shortlist. See the [dated model-routing survey](docs/model-routing-survey-2026-07-18.md) for the public seed; local evidence wins.

The native Codex plugin turns that protocol into an execution guard. Every native spawn declares `fast__`, `standard__`, or `lead__` and an explicit host-supported worker model; omitted models cannot silently inherit Lead. Fast cannot delegate further, while Standard may organize Fast inside its contract. A justified `lead__` handoff may inherit full history and the parent Lead model. The packaged Goldilocks Skill also carries `dispatch_codex_worker.py` for the verified case where native `collaboration.spawn_agent` does not advertise Spark but `codex exec` does. SQLite-backed audit remains concurrency-safe; ambiguous starts are recorded without stopping the wrong child, and an unplanned Sol child receives a soft return-to-owner check.

## Public model-routing seed

The following seed is dated **2026-07-18**. It is an advisory starting point for routing, not a permanent leaderboard or an instruction to call a named model blindly. Availability, tool access, context, modality, language, data policy, and task risk are hard gates; recent local evidence on the same repository and task shape overrides this public seed. Unlisted models remain eligible when they clear the same gates.

### Selection standard

1. Apply the hard gates above.
2. Reject candidates below the task-specific quality floor, even when they are free.
3. Estimate quality with a weighted geometric mean so a critical weakness cannot hide inside a high average: `Q = 100 × product(score_i ^ weight_i)`.
4. For subscriptions, estimate `QuotaBurn = Σ(usage × account coefficient × channel scarcity) + retries + review + integration`; keep raw tokens inside an evidence-based envelope.
5. Keep the quality/quota-burn/latency Pareto frontier. Use expected successful-delivery cost and the published logarithmic value score only as portable fallbacks when account-specific quota evidence is unavailable.

Subscription quota is treated as opportunity cost, not zero cost. A separate usage channel lowers cost but never lowers the quality or safety floor. Evidence confidence falls for stale data, mismatched versions or agent harnesses, small samples, missing domain evidence, and results that have not been reproduced locally.

### Task profiles and starting quality floors

| Profile | Default role | Floor | Evidence emphasized |
|---|---|---:|---|
| Mechanical edits | Fast | 65 | local acceptance, Aider edit correctness, format reliability, speed |
| Test authoring | Fast or Standard | 70 | local regression/mutation detection, SWE-bench, Terminal-Bench, edit correctness |
| Repository implementation | Standard | 75 | SWE-bench, Terminal-Bench, local repository success, edit correctness |
| Exploration | Fast | 60 | local summary usefulness, tool reliability, speed, context fit |
| Review and security | Lead | 85 | local defects caught, repository-agent evidence, reasoning and domain-security evidence |
| Frontend and multimodal | Standard or Lead | 75 | local visual acceptance, domain evidence, modality and tool reliability |

These are starting floors, not universal pass marks. Critical work is never assigned by value score alone. Tests may be written and run by a worker, but the Lead reviews their assertions and reruns the combined gate in the integrated workspace.

### Initial role map

| Role | Current seed | Lower-confidence candidates | Boundaries |
|---|---|---|---|
| Fast | GPT-5.3-Codex-Spark; GPT-5.6 Luna; Muse Spark 1.1; GLM-5.1 | MiniMax-M3; DeepSeek V4 Pro | Any complete execution contract with low residual discretion and deterministic acceptance; Fast is a leaf |
| Standard | GPT-5.6 Terra; Grok 4.5; GPT-5.6 Luna; Muse Spark 1.1; Claude Sonnet 5; Gemini 3 Pro; GLM-5.1 | Qwen3.7 Max | Bounded domain ownership, local design, worker coordination, and independently verifiable implementation |
| Lead | Claude Opus 4.8; Claude Fable 5; GPT-5.5 | Kimi K3 | User intent, architecture, Critical judgment, shared interfaces, conflict resolution, combined verification and final integration |

In Codex Pro, GPT-5.3-Codex-Spark is the first candidate for eligible Fast text-only work because its separate usage limit reduces opportunity cost. Eligibility is decided after Lead or Standard externalizes the material decisions, so large implementation volume can still become Fast-ready. Spark does **not** own architecture, ambiguous repository-wide changes, security or Critical decisions, vision/browser work, final review, or integration. Terra is the initial general Standard choice; Luna is the initial lower-risk, high-volume Standard/Fast choice. Current availability and verified local results override this seed.

### Comparable public data slice

This small slice contains models that had both a comparable Terminal-Bench 2.1 entry and an Artificial Analysis row at collection time. “Example value” is normalized to the best eligible row in this slice; it is **not** a universal model ranking.

| Model | Terminal-Bench 2.1 | TB reported cost | AA blended $/1M | AA end-to-end | Example value |
|---|---:|---:|---:|---:|---:|
| Grok 4.5 | 79.3% | $134.09 | $1.35 | 17.74s | 100.0 |
| Muse Spark 1.1 | 76.2% | $198.05 | $0.78 | 24.10s | 94.0 |
| Claude Opus 4.8 | 78.9% | $286.94 | $3.85 | 45.91s | 91.3 |
| GPT-5.6 Luna | 75.7% | $241.45 | $0.87 | 83.47s | 79.9 |
| Claude Fable 5 | 83.8% | $552.67 | $7.70 | 132.16s | 79.8 |
| GPT-5.6 Terra | 78.4% | $421.15 | $2.17 | 141.16s | 73.9 |
| Claude Sonnet 5 | 74.6% | $288.18 | $1.54 | 199.71s | 70.6 |
| GPT-5.5 | 83.1% | $2,059.19 | $4.35 | 72.62s | 61.8 |
| GLM-5.1 | 58.7% | $277.14 | $0.90 | 70.79s | 52.2 |

Grok 4.5's Terminal-Bench submission reported a `-9.0%` hack adjustment, so the registry applies a reliability penalty. Gemini 3 Pro had a comparable Terminal-Bench result but no matching current price row. Kimi K3, Qwen3.7 Max, MiniMax-M3, and DeepSeek V4 Pro had useful broad metrics but no comparable current Terminal-Bench row, so they remain bake-off candidates instead of scored winners.

The evidence set includes SWE-bench, Terminal-Bench, Aider Polyglot, LiveCodeBench, Artificial Analysis, official capability documentation, and provider pricing. Inspect the [machine-readable model registry](plugins/goldilocks/skills/goldilocks/assets/model-registry.json) and the [full survey with source links and limitations](docs/model-routing-survey-2026-07-18.md).

### Improve the seed

[Open an issue](https://github.com/blackstone2333/goldilocks/issues) when public or local evidence contradicts this map. Useful reports include the exact model/version/provider, task profile, agent harness and tools, reasoning level, sample count, pass rate, token or monetary cost, wall-clock latency, retries, review effort, and integration defects. Reproducible repository-local results are more valuable than another broad aggregate score.

See the [v0.3 hierarchical orchestration design](docs/v0.3-hierarchical-orchestration.md) and its [v0.2 capability-engine lineage](docs/v0.2-capability-trigger-engine.md).

## Validate locally

No model calls:

```bash
python3 tests/test_v03_contract.py
python3 tests/test_three_bears_contract.py
python3 tests/test_agent_routing_hook.py
python3 tests/test_recovery_hook.py
python3 tests/test_update_checker.py
python3 benchmarks/three_bears/run.py --selftest
```

Low-cost live smoke test:

```bash
python3 benchmarks/three_bears/run.py \
  --task baby-docs \
  --arms goldilocks,superpowers \
  --model gpt-5.6-terra \
  --reasoning low \
  --runs 1 \
  --workers 2
```

The full reproducible matrix is documented in [Three Bears](benchmarks/three_bears/README.md).

## Status and direction

Goldilocks is now at `v0.3.2`. It can replace Superpowers more efficiently on the tested surface, but hierarchical orchestration remains an architectural direction rather than a new performance certification. This release makes the company-style route executable in current Codex hosts by separating native workers from the packaged Spark CLI worker, without claiming a new end-to-end performance result. The published runtime certification remains the v0.2.2 result while real projects measure quality non-inferiority, Lead quota share, total raw-token change, wall-clock critical path, retries, and integration defects. See the [changelog](CHANGELOG.md); [issues and suggestions are welcome](https://github.com/blackstone2333/goldilocks/issues).

Next iterations will focus on:

- lowering Mama/Papa test and verification overhead without weakening quality gates;
- expanding the benchmark into larger repositories and additional languages;
- adding more repetitions before making broad public performance claims;
- validating nested Standard→Fast delegation, continuity, and execution-memory reuse on long-running projects;
- measuring raw-token change, quota-weighted Lead share, wall-clock critical path, retries, and integration defects;
- preserving Superpowers entry compatibility while keeping the Direct path truly direct.

## License and influences

Goldilocks is MIT licensed and developed by Charles Roc and contributors. It is an independent implementation influenced by Superpowers, Grill-style decision-frontier questioning, and Ponytail's reuse/native-first approach. Those projects do not endorse Goldilocks. See [Third-Party Notices](plugins/goldilocks/THIRD_PARTY_NOTICES.md).
