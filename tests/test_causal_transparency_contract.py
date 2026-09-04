#!/usr/bin/env python3

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require(path: Path, *phrases: str) -> None:
    body = read(path)
    missing = [phrase for phrase in phrases if phrase not in body]
    assert not missing, f"{path.relative_to(ROOT)} lacks: {', '.join(missing)}"


def main() -> None:
    require(
        PLUGIN / "skills" / "goldilocks" / "SKILL.md",
        "Defect 报 evidence-backed CAUSE",
        "（或 unknown）",
        "fix 与当前 decisive verification evidence",
    )
    require(
        PLUGIN / "skills" / "goldilocks" / "references" / "diagnose.md",
        "diagnosis-driven fix",
        "evidence-backed cause",
        "explicitly unknown",
        "fix, and verification",
        "expand causal detail when the user asks",
    )
    require(
        PLUGIN / "skills" / "goldilocks" / "references" / "orchestrate.md",
        "defect handoffs",
        "evidence-backed `CAUSE`",
        "explicitly mark it unknown",
        "Expand causal detail when asked",
    )
    print("Goldilocks causal-transparency contract passed.")


if __name__ == "__main__":
    main()
