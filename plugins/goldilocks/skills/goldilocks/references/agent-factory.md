# Agent Factory

Use only when no fixed employee fits and the host advertises a cheaper candidate. It creates an external Fast leaf, not a native agent or Lead.

## Discover, then ask once

Resolve `../scripts/create_agent_profile.py`:

```bash
python3 <factory> discover --require-capability <coding|tools|text>
```

Discovery intersects `models_cache.json` with official rates; it calls no model and writes nothing. Keep candidates clearing quality, tool, context, and authority gates. Numeric comparison needs the active billing channel. Visibility does not prove allowance.

Before first preflight/create/use, name the model, pool, benefit, and preflight cost; ask yes/no. After explicit yes:

```bash
python3 <factory> authorize \
  --model <id> --billing-channel <channel> --authority explicit-user
```

Authorization is global until revoked. Do not re-ask for that pair. A new model/channel needs authorization. Decline or silence means fixed employees or Direct.

Revoke only on explicit instruction:

```bash
python3 <factory> revoke \
  --model <id> --billing-channel <channel> --authority explicit-user
```

## Create and dispatch

```bash
python3 <factory> create \
  --model <id> --billing-channel <channel> \
  --require-capability <capability> \
  --reasoning-effort medium --sandbox workspace-write
```

The factory rejects invisible models, absent/revoked authorization, stale or non-official creation prices, missing capabilities, overwrites, and unsafe sandboxes. After authorization it runs one minimal read-only preflight and writes a tamper-evident leaf profile in plugin data. Price expiry later disables automatic cost ranking but does not revoke use; every dispatch rechecks host visibility and authorization.

```bash
python3 <dispatch-script> \
  --workdir <repository-or-worktree> \
  --task-name fast__<name> \
  --task-file <contract.md> \
  --agent-profile <profile.json>
```

The profile pins model, effort, sandbox, environment, billing channel, authorization, and price snapshot. Conflicting overrides fail. The adapter records observed model, tokens, elapsed time, channel, and verification state. The dynamic worker remains a leaf and never silently replaces Lead.
