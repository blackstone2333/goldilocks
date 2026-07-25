# Goldilocks v0.3.2 Dual Codex Routing Evidence

Date: 2026-07-25  
Scope: route correctness only; no end-to-end performance claim

## Failure reproduced

- Native `collaboration.spawn_agent` rejected `model="gpt-5.3-codex-spark"` before starting a child and advertised only `gpt-5.6-sol` and `gpt-5.6-terra`.
- Existing v0.3.1 Hook data contained no planned decisions for real `collaboration.spawn_agent` calls, while `SubagentStart` and `SubagentStop` observations still arrived.

## Historical route evidence

- Structured session logs contain 22 child sessions with `originator="codex_exec"`, CLI `0.144.0-alpha.4`, and `turn_context.model="gpt-5.3-codex-spark"`.
- A recovered worker script used the exact command `/Applications/ChatGPT.app/Contents/Resources/codex exec -m gpt-5.3-codex-spark <contract>`.
- A direct 2026-07-25 probe through the bundled Codex `0.146.0-alpha.3.1` returned `SPARK_OK` from that exact model.

## v0.3.2 deterministic checks

```text
python3 tests/test_agent_routing_hook.py
Goldilocks v0.3.2 agent routing hook contract passed.

python3 tests/test_codex_worker.py
Goldilocks external Codex Fast worker contract passed.

python3 tests/test_recovery_hook.py
Goldilocks recovery hook contract passed.
```

These checks cover explicit native models, the namespaced tool name, Fast leaf behavior, unplanned-Sol soft return, safe stdin briefing, disabled worker delegation/plugins/apps/MCP, sandbox limits, result collection, and unchanged failure propagation.

## Real packaged-adapter probe

Command shape:

```text
python3 plugins/goldilocks/skills/goldilocks/scripts/dispatch_codex_worker.py \
  --workdir . \
  --task-name fast__route_probe \
  --task-file <read-only-probe-contract> \
  --reasoning-effort low \
  --sandbox read-only
```

Observed runtime:

- Codex CLI: `0.145.0` from the active PATH
- model: `gpt-5.3-codex-spark`
- provider: configured custom provider
- reasoning: low
- sandbox: read-only
- result: `GOLDILOCKS_SPARK_WORKER_OK`
- reported tokens: 8,417

The token observation is a routing constraint, not a benchmark: global Skill context still creates material fixed startup cost even after plugin/app/MCP and multi-agent disabling. External Spark is therefore unsuitable for tiny fragmented tasks unless quota-channel or parallel-time savings repay that overhead.

## Conclusion

The model remains available; native and CLI worker catalogs diverged on the observed host. v0.3.2 uses explicit native workers when supported and the packaged Spark CLI adapter otherwise. It never treats silent Sol inheritance or process exit as successful routing or final acceptance.
