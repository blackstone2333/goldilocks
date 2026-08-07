#!/usr/bin/env python3

"""Stable, human-readable model labels and task-name suffixes."""

from __future__ import annotations

import re


FIXED_SUFFIXES = {
    "gpt-5.6-sol": "sol",
    "gpt-5.6-terra": "terra",
    "gpt-5.6-luna": "luna",
    "gpt-5.3-codex-spark": "spark",
}
FIXED_LABELS = {
    "gpt-5.6-sol": "Sol",
    "gpt-5.6-terra": "Terra",
    "gpt-5.6-luna": "Luna",
    "gpt-5.3-codex-spark": "Spark",
}
MODEL_FAMILIES = (
    "deepseek",
    "kimi",
    "qwen",
    "glm",
    "gemini",
    "grok",
    "fable",
    "opus",
    "sonnet",
    "haiku",
    "llama",
    "mistral",
    "minimax",
    "doubao",
    "sol",
    "terra",
    "luna",
    "spark",
)
FAMILY_LABELS = {
    "deepseek": "DeepSeek",
    "kimi": "Kimi",
    "qwen": "Qwen",
    "glm": "GLM",
    "gemini": "Gemini",
    "grok": "Grok",
    "fable": "Fable",
    "opus": "Opus",
    "sonnet": "Sonnet",
    "haiku": "Haiku",
    "llama": "Llama",
    "mistral": "Mistral",
    "minimax": "MiniMax",
    "doubao": "Doubao",
}
IGNORED_SUFFIX_TOKENS = {"latest", "preview"}
MAX_SUFFIX_LENGTH = 32
MODEL_SUFFIX_PATTERN = re.compile(
    r"(?:_|-)(?:"
    + "|".join(rf"{re.escape(family)}[a-z0-9]*" for family in MODEL_FAMILIES)
    + r")(?:-[a-z0-9]+)*$",
    re.IGNORECASE,
)


def slug_tokens(value: str) -> list[str]:
    return [
        token
        for token in re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-").split("-")
        if token
    ]


def family_for_token(token: str) -> str | None:
    for family in MODEL_FAMILIES:
        if token == family or (
            token.startswith(family) and token[len(family) :].isdigit()
        ):
            return family
    return None


def truncate_slug(tokens: list[str]) -> str:
    selected: list[str] = []
    for token in tokens:
        candidate = "-".join((*selected, token))
        if len(candidate) > MAX_SUFFIX_LENGTH:
            break
        selected.append(token)
    return "-".join(selected) or "model"


def model_name_suffix(model: str) -> str:
    normalized = model.strip().lower()
    if normalized in FIXED_SUFFIXES:
        return FIXED_SUFFIXES[normalized]

    tokens = slug_tokens(normalized)
    family_indexes = [
        index for index, token in enumerate(tokens) if family_for_token(token) is not None
    ]
    if family_indexes:
        tokens = tokens[family_indexes[-1] :]
    else:
        tokens = [
            token
            for token in tokens
            if token not in {"api", "model", "models", "latest", "preview"}
        ][-5:]
    tokens = [token for token in tokens if token not in IGNORED_SUFFIX_TOKENS]
    return truncate_slug(tokens)


def display_token(token: str) -> str:
    lowered = token.lower()
    for family, label in FAMILY_LABELS.items():
        if lowered == family:
            return label
        if lowered.startswith(family) and lowered[len(family) :].isdigit():
            return label + token[len(family) :]
    if re.fullmatch(r"[a-zA-Z]+\d+(?:\.\d+)*", token):
        return token.upper()
    return token[:1].upper() + token[1:]


def model_display_label(model: str) -> str:
    normalized = model.strip().lower()
    if normalized in FIXED_LABELS:
        return FIXED_LABELS[normalized]
    component = re.split(r"[/\\]", model.strip())[-1]
    tokens = [token for token in re.split(r"[-_\s]+", component) if token]
    if not tokens:
        return "Unknown model"
    return " ".join(display_token(token) for token in tokens)[:64]


def visible_task_name(task_name: str, model: str) -> str:
    normalized = task_name.strip().lower()
    suffix = model_name_suffix(model)
    exact = re.compile(rf"(?:_|-){re.escape(suffix)}$", re.IGNORECASE)
    base = exact.sub("", normalized)
    if base == normalized:
        base = MODEL_SUFFIX_PATTERN.sub("", normalized)
    return f"{base}_{suffix}"
