---
name: goldilocks-diagnostics
description: Use only when the user explicitly asks to generate or export a Goldilocks diagnostic report.
---

# Goldilocks diagnostics

When the user says “生成最近 7 天的 Goldilocks 中文诊断报告”, resolve the
currently enabled `goldilocks` source with `codex plugin list --json`, then run that
source's local, read-only exporter. It never calls a model or network and emits only
aggregate counts and evidence state. Do not search the cache: older Goldilocks versions
may remain there.

```bash
python3 <enabled-goldilocks-source>/scripts/diagnostic_report.py --days 7 --lang zh --output goldilocks-diagnostic.md
```

If more than one local state directory exists, ask for or pass the intended directory:

```bash
python3 <enabled-goldilocks-source>/scripts/diagnostic_report.py --data-dir /path/to/goldilocks-data --sessions-dir ~/.codex/sessions --days 7 --lang en --output goldilocks-diagnostic.md
```

The report is safe to share for Beta feedback: it excludes raw prompts, project and file contents, secrets, and transcript content. Missing data or old schemas are reported as **evidence insufficient**, never treated as a failure.
