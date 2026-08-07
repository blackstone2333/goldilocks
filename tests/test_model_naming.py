#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "goldilocks" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from model_naming import model_display_label, model_name_suffix, visible_task_name


def main() -> None:
    cases = {
        "gpt-5.6-sol": ("sol", "Sol"),
        "gpt-5.6-terra": ("terra", "Terra"),
        "gpt-5.6-luna": ("luna", "Luna"),
        "gpt-5.3-codex-spark": ("spark", "Spark"),
        "deepseek-ai/DeepSeek-V4-Flash": (
            "deepseek-v4-flash",
            "DeepSeek V4 Flash",
        ),
        "moonshotai/Kimi-K2.5": ("kimi-k2-5", "Kimi K2.5"),
        "qwen/Qwen3-Coder-Flash": ("qwen3-coder-flash", "Qwen3 Coder Flash"),
        "provider/GLM-5.2-Air": ("glm-5-2-air", "GLM 5.2 Air"),
    }
    for model, (suffix, label) in cases.items():
        assert model_name_suffix(model) == suffix, model
        assert model_display_label(model) == label, model

    assert visible_task_name(
        "fast__api_review_deepseek-v4-flash",
        "deepseek-ai/DeepSeek-V4-Flash",
    ) == "fast__api_review_deepseek-v4-flash"
    assert visible_task_name(
        "fast__api_review_deepseek-v4-flash",
        "moonshotai/Kimi-K2.5",
    ) == "fast__api_review_kimi-k2-5"
    print("Goldilocks dynamic model naming contract passed.")


if __name__ == "__main__":
    main()
