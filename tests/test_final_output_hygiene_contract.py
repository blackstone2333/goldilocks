#!/usr/bin/env python3

"""Guard the optional accepted-state final-output hygiene contract."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
SKILL = PLUGIN / "skills" / "goldilocks" / "SKILL.md"
REFERENCE = PLUGIN / "skills" / "goldilocks" / "references" / "final-output-hygiene.md"
NOTICE = PLUGIN / "THIRD_PARTY_NOTICES.md"


def main() -> None:
    root = SKILL.read_text(encoding="utf-8")
    reference = REFERENCE.read_text(encoding="utf-8")
    notice = NOTICE.read_text(encoding="utf-8")

    assert "[final-output-hygiene.md](references/final-output-hygiene.md)" in root
    assert "仅在方案被否或纠正、会话很长/compact/delegated、多交付表面" in root
    assert len(root.split()) <= 650, "always-loaded root Skill must remain compact"

    for required in (
        "accepted, verified current state",
        "authoritative baseline",
        "title, opening, filename, comment/docstring, test name, log entry, README, commit/PR/release text, and handoff",
        "synonyms, parenthetical contrasts",
        "real baseline removal, migration, API compatibility, and security or legal audit facts",
        "external actions already performed, including partial failure",
        "user-owned and concurrent pre-existing changes",
        "one ordinary repair",
        "Logs record observed state, cause, and events",
        "README text describes current product behavior, not session history",
    ):
        assert required in reference, required

    for required in (
        "https://github.com/LB623/no-negative-echo",
        "LB623",
        "MIT",
        "5ba55a4217568e94f22414cb5bbcde4b51c37995",
        "independent, narrowed rewrite",
        "does not copy the upstream scanner or installer",
        "Permission is hereby granted, free of charge",
    ):
        assert required in notice, required

    assert not list(PLUGIN.rglob("*scanner*"))
    assert not list(PLUGIN.rglob("*final-output*agent*"))
    assert "Do not add a freeze, scanner, automatic agent" in reference
    assert REFERENCE.is_file() and NOTICE.is_file(), "reference and notice ship in the plugin tree"

    print("Goldilocks final-output hygiene contract passed.")


if __name__ == "__main__":
    main()
