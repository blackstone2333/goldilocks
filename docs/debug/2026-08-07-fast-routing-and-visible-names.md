# Fast routing and visible child names regressed

## Symptom

Recent child names retained `_terra` or `_sol` but inconsistently omitted the `fast__`, `standard__`, or `lead__` prefix. Recent native dispatch also selected Terra repeatedly without visibly considering Luna Fast.

Dynamic provider models were reduced to a family-only suffix such as `_deepseek` or `_kimi`, hiding variants such as DeepSeek V4 Flash or Kimi K2.5.

## Evidence

- Eleven recent native `spawn_agent` calls retained a model suffix; only four retained an explicit routing prefix.
- The current Hook matcher accepts `spawn_agent` and `collaboration.spawn_agent`, but not the host-qualified `functions.collaboration.spawn_agent` used by the current collaboration surface.
- The active host advertises native Goldilocks roles only for Terra Standard and Sol review. Luna/Spark remain external `codex-exec` routes.
- External audit rows prove Luna succeeded repeatedly, most recently on 2026-08-06, so absence from the native role list is not route failure.

## Root cause

The naming validator was correct, but its Hook matcher did not cover the current fully-qualified tool name, allowing calls to bypass prefix validation and suffix rewriting. Separately, Fast remained documented as an external adapter but was not made a first-class decision checkpoint; Lead could choose the immediately visible Terra role without explaining why Luna/Spark failed the quality gate.

The suffix helper deliberately returned the first recognized family and discarded every remaining version/variant token. The same helper was duplicated in native and external routing, making drift likely.

## Required fix

- Match `Agent`, `spawn_agent`, `collaboration.spawn_agent`, and `functions.collaboration.spawn_agent`.
- Require visible names in `<tier>__<semantic>_<model>` form.
- Evaluate each ready unit for Fast before Standard. If every delegated unit remains Terra, require a concise residual-judgment/tool/authority/acceptance reason; never force Fast when it is ineligible.
- Treat native-role absence as a transport choice, not `route_unavailable`, while the verified external adapter remains usable.
- Use one shared naming helper. Keep concise fixed OpenAI aliases, but preserve meaningful dynamic family/version/variant tokens, for example `_deepseek-v4-flash` and `_kimi-k2-5`.

## Do not repeat

- Do not create unverified native Luna/Spark role files merely to make them appear in the UI.
- Do not impose an agent quota or dispatch work whose briefing/review cost erases the benefit.
- Do not rely on Lead naming habits when Hook or injected context can express the contract.

## Verification

- All repository contract scripts pass, including 70 trigger cases.
- The installed Hook matcher covers `Agent`, `spawn_agent`, `collaboration.spawn_agent`, and `functions.collaboration.spawn_agent`.
- Installed recovery, orchestration, route-card, and Terra employee files exactly match the verified source.
- `git diff --check` passes.
- Dynamic naming tests cover DeepSeek V4 Flash, Kimi K2.5, Qwen3 Coder Flash, and GLM 5.2 Air; native and external routing share the same helper.

## Status

Included in `v0.5.0-alpha.1` for opt-in field testing. One fresh real multi-unit task remains necessary to observe the host UI name and actual Fast/Terra choice after Hook trust is renewed.
