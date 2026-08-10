# Codex CLI root-gate visibility versus Skill invocation

## Status

Root cause confirmed and public default-branch metadata repaired on 2026-08-10: the affected user installed Goldilocks only as a global standalone Skill, and the GitHub default branch still disabled implicit invocation even though the Alpha plugin enabled it.

The v0.5.0 local release candidate now resolves the remaining packaging gap: Bootstrap explicitly
prefers `native_plugin` for detected Codex CLI/Desktop hosts and treats portable Skills as fallback.
Its focused contract and the complete 17-test suite pass.

## Symptom

A Codex CLI user running Goldilocks `0.5.0` saw `goldilocks` in the turn's Skill catalog but not in the visible list of invoked Skills. The responding model described this as a missed invocation while specialist frontend and motion Skills were selected.

## Confirmed evidence

- Tag `v0.5.0-alpha.2` sets `policy.allow_implicit_invocation: true`.
- Before the fix, both GitHub `main` and tag `v0.4.2` set `policy.allow_implicit_invocation: false`; a standalone Skill installed from the default branch therefore required explicit `$goldilocks` invocation.
- GitHub `main` now sets `policy.allow_implicit_invocation: true` at commit `a521ea170fa2bb56eb9bf2dbc2e453a22acbd3d4` (verified by a fresh repository file read). The immutable `v0.4.2` tag remains historical and unchanged.
- GitHub `main` also previously described Goldilocks as "Use only when explicitly asked", which contradicted implicit invocation. Commit `57a5d34c52f8b8b7a21baa76d2f2a4b0291ca200` now front-loads automatic executable development/project routing while retaining the silent Direct exit.
- Its `SKILL.md` description admits any executable work and explicitly names implicit invocation.
- Official OpenAI documentation says Codex initially sees only each Skill's name and description; implicit activation is a semantic choice when the prompt matches, not a mandatory load. Descriptions may be shortened under the Skill-list context budget, and trigger words should be front-loaded.
- The Alpha native plugin's `UserPromptSubmit` Hook injects the zero-cost root gate before specialist Skills. A fresh synthetic prompt returned the expected gate context.
- `tests/test_recovery_hook.py` and `tests/test_v03_contract.py` passed when run directly, including implicit-policy and gate-injection contracts.
- Direct intentionally does not load the full `SKILL.md`, create workflow state, or announce a route. Therefore no visible Goldilocks Skill badge is expected for many clear tasks even when the Hook-delivered gate ran.

## Causal split

1. **Visibility-only case:** the native Hook ran, selected Direct, and a specialist Skill then performed the work. The missing Goldilocks badge is expected and behavior is correct.
2. **Confirmed packaging defect:** the user installed Goldilocks as a standalone cross-platform Skill from GitHub `main`, whose metadata still had `allow_implicit_invocation: false` while the Alpha package had already switched to `true`.
3. **Remaining enforcement gap:** even with implicit invocation enabled, standalone Skill activation is semantic and best-effort; without the plugin Hook it can still lose to a more specific specialist Skill.
4. **Repaired selector contradiction:** the stable default-branch description explicitly restricted use to named invocation. The default branch now front-loads the executable-task trigger; fresh install behavior still requires a new Codex session to reload the Skill catalog.

The later environment confirmation establishes case 2. A model's retrospective statement that it "forgot" remains insufficient by itself, but the absence of any always-loaded instruction surface explains why the root gate was optional.

## Exact distinguishing test

For Codex CLI or Desktop, start from a portable-only installation and run the one-time `goldilocks-bootstrap` plan. The plan must identify Codex, recommend the native Plugin, include the locked Plugin installation actions, and remain partial until the Plugin plus four native Agent templates pass `--check`. After successful handoff and a new task, verify the root-gate Hook is present. Portable-only activation remains the fallback control, not the preferred Codex result.

## Bounded solution

- Prefer the native Plugin for every detected Codex host, including CLI and Desktop. It is the only package form that carries the Hook, Usage reporter, update check, and native Agent definitions together.
- Keep portable Skills as the compatibility path for other hosts and as a temporary Codex bootstrap source only when the Plugin was not installed initially. After native verification, hand off removal of duplicate Codex portable mappings.
- Treat `allow_implicit_invocation: true` as a required compatibility contract for both plugin and standalone Skill packaging, with a regression check against the public default-branch install source.
- Clarify in README that silent Direct normally has no Goldilocks badge.
- For the next experimental build, front-load the description with `Invoke before every executable task` and add an opt-in, minimal route/gate trace for field diagnosis instead of making all Direct tasks noisy.
- Do not force full `$goldilocks` invocation on every task: that would solve visibility by reintroducing the context and latency overhead Goldilocks is designed to avoid.

## Public installation contract

The user-approved README baseline is the published `main` narrative at commit `57a5d34`. The
v0.5.0 documentation may add verified behavior and release evidence, but it must preserve that
professional explanatory structure rather than replace it with a shortened promotional rewrite.
Install appears before benchmark results, with paths in this order: AI-assisted installation,
native Codex Plugin, native Claude Code Plugin, then portable Skills hosts. Codex CLI and Desktop
remain Plugin-first; Bootstrap remains a one-time install, upgrade, or repair Skill.

The final 2026-08-11 README regression gate checks that exact order in both languages. Fresh
verification passed all 17 repository `tests/test_*.py`, the root and Bootstrap Skill validators,
and `git diff --check`. The result badge was removed from the masthead so installation now precedes
every benchmark claim, not only the Evidence section.

### v0.5.0 feature visibility follow-up

**Symptom:** the workflow conflict and optional concurrency ceiling were correct but visually easy
to miss; Usage was buried inside the route-receipt section; Night Shift had only one sentence in
the model section; and the exact 12-row matrix was difficult to scan as a human-facing summary.

**Evidence:** the runtime and Agent guide already implement per-model Usage and distinguish Night
Shift as a delivery mode. The frozen aggregate ledger supplies exact time, Raw Token, and normalized
cost deltas for Direct, v0.4.2, and Superpowers. No new benchmark run is required.

**Disproven approaches:** the rejected short homepage removed too much product depth; a table-only
presentation is auditable but does not provide the requested at-a-glance comparison. Keep the full
table and add a derived chart rather than replacing evidence or inventing new results.

**Exact next test:** verify both READMEs contain localized GitHub Attention blocks, separate route
receipt/Usage/Night Shift level-two sections, the exact AI -> Codex -> Claude -> portable install
order, and localized chart assets whose labels and percentages match the frozen aggregate ledger;
then run all 17 repository tests, both Skill validators, and `git diff --check`.

**Related evidence:** public prose baseline `57a5d34`; current release ledger
`benchmarks/V050-RELEASE-EVIDENCE*.md`. **Do not repeat:** do not run another model matrix, do not
remove the 12-row table, and do not use `human-writing` for this revision.

Night Shift selection must also remain evidence-bounded. In the frozen complex reference, Luna Max
and Terra Medium both passed the complete quality gate; Luna Max used 1,275.764 s versus 249.043 s
(about 5.12x wall time, +412.27%) and an official-price proxy of $0.122976 versus $0.212937
(42.25% lower, not an actual bill).
Timing is observational on a shared provider. This supports a latency-for-price tradeoff, not a
claim that Luna is more token-efficient or universally better. Source:
`benchmarks/TERRA-LUNA-EFFORT-EVIDENCE.md`.

**Chart correction:** the first diverging-bar draft plotted Direct's +36.79% elapsed-time tradeoff
as the only large negative bar. Although numerically correct, it visually dominated the summary and
made the chart harder to read. Remove that one chart row. Preserve the exact Direct time delta in
the adjacent prose and the 12-row ledger so the tradeoff remains explicit and auditable. The chart
is now a savings-at-a-glance view, not a complete replacement for the ledger.

**Verified outcome:** both localized charts omit only the Direct time bar, preserve every positive
aggregate saving, and retain the Spark Luna-equivalent proxy note. The adjacent prose and exact
ledger still disclose Direct's +36.79% elapsed time. All 17 repository tests, both Skill validators,
both SVG XML checks, and `git diff --check` passed; final independent documentation review returned
SHIP.

**User-corrected chart contract:** a savings-percentage chart still makes the reader translate
percentages and can visually imply that the largest percentage is the strongest product. Replace it
with four solution rows (`v0.5.0`, `v0.4.2`, `Direct`, `Superpowers`) and three absolute-consumption
bars per row (elapsed seconds, Raw Token, normalized USD). Each metric uses its own linear scale with
the largest arm at 100%; bars are comparable only within that metric and must carry exact values.
This preserves Direct's shorter elapsed time while making Superpowers' larger absolute consumption
immediately visible. The exact 12-row ledger remains the audit source.

The user then approved a disclosed nonlinear display because the approximately order-of-magnitude
Superpowers outlier makes the other absolute bars too short on a linear axis. Labels remain exact
absolute totals. Bar length uses the same per-metric normalized transform
`log10(1 + 99 * value/max) / 2`, mapping zero to zero and each column maximum to full width. The
chart must call this a compressed log scale and must not present transformed lengths as percentages.

Final display contract: publish both views. The first chart uses the true per-metric linear ratio
`value/max` to preserve magnitude. The second uses the disclosed compressed-log transform to make
the three smaller arms readable. Both views show the same exact absolute labels, use no percentage
claims, preserve ordering, and retain the full 12-row ledger below.

**Verified final charts:** both languages now include the true linear view and the disclosed
compressed-log view. All four charts contain the four exact arm totals for elapsed time, Raw Token,
and normalized cost; no percentage appears in a chart. XML checks, Chrome-render visual inspection,
all 17 repository tests, both Skill validators, and `git diff --check` passed. Independent review
returned SHIP.

Hook trust is a separate host boundary. Bootstrap presents three choices after Plugin verification:
persistent trust through Codex's startup review, one-launch bypass with
`codex --dangerously-bypass-hook-trust` (all enabled Hooks), or no trust change. Bootstrap must
never write a trusted hash or execute the bypass without the user's choice.

Official Codex documentation independently confirms the boundary: Plugins package Skills and
optional lifecycle Hooks together; installing or enabling a Plugin does not trust non-managed
Hooks; trust is recorded against the current Hook-definition hash; `/hooks` reviews it; and
`--dangerously-bypass-hook-trust` runs enabled Hooks without persisted trust for one invocation.

## Localized receipt versus canonical audit

The visible orchestration receipt follows the user's primary language, including localized
`Reason/理由` and `Detail/详情` labels and a localized short reason. The machine-facing record is a
separate hidden HTML comment with fixed English field names and the original reason-code enum:
`lead_faster`, `shared_surface`, `critical_judgment`, `contract_not_ready`,
`route_unavailable`, `review_cost`, `parallel_gain`, or `quota_gain`.

Audit scripts parse only that canonical comment. They deliberately ignore the visible receipt, so
translation, wording changes, and localized labels cannot corrupt route statistics. Root Direct
still emits neither form. Focused verification on 2026-08-11 passed
`tests/test_route_auditor.py`, `tests/test_routing_rationale_audit.py`, and
`tests/test_v045_model_routing_contract.py`.

## Reference

- Official OpenAI documentation: <https://learn.chatgpt.com/docs/build-skills>
- Official global-instructions documentation: <https://learn.chatgpt.com/docs/agent-configuration/agents-md>
- Official Plugin packaging documentation: <https://developers.openai.com/plugins/build/plugins>
- Official Hook trust documentation: <https://learn.chatgpt.com/docs/hooks#review-and-trust-hooks>
