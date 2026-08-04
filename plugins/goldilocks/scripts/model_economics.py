#!/usr/bin/env python3

"""Shared official-rate and dynamic-agent profile helpers for Goldilocks."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ECONOMICS = (
    PLUGIN_ROOT
    / "skills"
    / "goldilocks"
    / "assets"
    / "model-economics.json"
)
PROFILE_SCHEMA_VERSION = 1


class EconomicsError(ValueError):
    """Raised when cost evidence is missing, stale, ambiguous, or invalid."""


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_timestamp(raw: object) -> datetime:
    if not isinstance(raw, str) or not raw.strip():
        raise EconomicsError("missing evidence timestamp")
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise EconomicsError(f"invalid evidence timestamp: {raw}") from error
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.expanduser().read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EconomicsError(f"could not read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise EconomicsError(f"JSON root must be an object: {path}")
    return value


def load_economics(path: Path = DEFAULT_ECONOMICS) -> dict[str, Any]:
    value = load_json(path)
    if value.get("schema_version") != 1:
        raise EconomicsError("unsupported model-economics schema")
    if not isinstance(value.get("models"), dict) or not isinstance(
        value.get("sources"), dict
    ):
        raise EconomicsError("model-economics registry lacks models or sources")
    return value


def model_ids_from_cache(path: Path) -> set[str]:
    value = load_json(path)
    models = value.get("models")
    if not isinstance(models, list):
        raise EconomicsError("models_cache.json lacks a models array")
    visible: set[str] = set()
    for model in models:
        if not isinstance(model, dict):
            continue
        identifier = model.get("slug") or model.get("id") or model.get("model")
        if isinstance(identifier, str) and identifier.strip():
            visible.add(identifier.strip())
    return visible


def available_channels(registry: dict[str, Any], model: str) -> list[str]:
    entry = registry["models"].get(model)
    if not isinstance(entry, dict):
        return []
    rates = entry.get("rates")
    if not isinstance(rates, list):
        return []
    return sorted(
        str(rate["billing_channel"])
        for rate in rates
        if isinstance(rate, dict) and isinstance(rate.get("billing_channel"), str)
    )


def pricing_snapshot(
    registry: dict[str, Any],
    model: str,
    billing_channel: str,
    *,
    require_current: bool = True,
    require_rankable: bool = True,
    clock: datetime | None = None,
) -> dict[str, Any]:
    entry = registry["models"].get(model)
    if not isinstance(entry, dict):
        raise EconomicsError(f"no official economics entry for model {model}")
    rates = entry.get("rates")
    if not isinstance(rates, list):
        raise EconomicsError(f"model {model} has no rate cards")
    matches = [
        rate
        for rate in rates
        if isinstance(rate, dict) and rate.get("billing_channel") == billing_channel
    ]
    if len(matches) != 1:
        channels = ", ".join(available_channels(registry, model)) or "none"
        raise EconomicsError(
            f"model {model} has no unique {billing_channel} rate; available: {channels}"
        )
    rate = matches[0]
    source_id = rate.get("source_id")
    source = registry["sources"].get(source_id)
    if not isinstance(source, dict) or source.get("kind") != "official":
        raise EconomicsError(f"rate {model}/{billing_channel} lacks an official source")
    expires_at = parse_timestamp(source.get("expires_at"))
    current = (clock or now_utc()).astimezone(timezone.utc) <= expires_at
    if require_current and not current:
        raise EconomicsError(
            f"official price for {model}/{billing_channel} expired at "
            f"{source.get('expires_at')}"
        )
    numeric = all(isinstance(rate.get(key), (int, float)) for key in ("input", "output"))
    rankable = bool(rate.get("rankable", True)) and numeric
    if require_rankable and not rankable:
        reason = rate.get("unknown_reason") or "numeric official rate is incomplete"
        raise EconomicsError(f"{model}/{billing_channel} is not cost-rankable: {reason}")
    return {
        "model": model,
        "provider": entry.get("provider"),
        "capabilities": list(entry.get("capabilities") or []),
        "billing_channel": billing_channel,
        "currency": rate.get("currency"),
        "unit": rate.get("unit"),
        "input": rate.get("input"),
        "cached_input": rate.get("cached_input"),
        "output": rate.get("output"),
        "conditions": rate.get("conditions") or {},
        "rankable": rankable and current,
        "price_current": current,
        "source": {
            "id": source_id,
            "url": source.get("url"),
            "kind": source.get("kind"),
            "retrieved_at": source.get("retrieved_at"),
            "expires_at": source.get("expires_at"),
        },
    }


def estimate_cost(
    snapshot: dict[str, Any],
    input_tokens: int | None,
    cached_input_tokens: int | None,
    output_tokens: int | None,
) -> dict[str, Any]:
    input_value = max(0, int(input_tokens or 0))
    cached_value = min(input_value, max(0, int(cached_input_tokens or 0)))
    output_value = max(0, int(output_tokens or 0))
    uncached_value = input_value - cached_value
    components = {
        "input": (uncached_value, snapshot.get("input")),
        "cached_input": (cached_value, snapshot.get("cached_input")),
        "output": (output_value, snapshot.get("output")),
    }
    unknown = [
        name
        for name, (tokens, rate) in components.items()
        if tokens > 0 and not isinstance(rate, (int, float))
    ]
    if unknown or not snapshot.get("price_current"):
        return {
            "status": "unknown",
            "unknown_components": unknown,
            "price_current": bool(snapshot.get("price_current")),
            "currency": snapshot.get("currency"),
            "billing_channel": snapshot.get("billing_channel"),
        }
    amount = sum(tokens * float(rate) for tokens, rate in components.values()) / 1_000_000
    return {
        "status": "estimated",
        "amount": round(amount, 12),
        "currency": snapshot.get("currency"),
        "billing_channel": snapshot.get("billing_channel"),
        "uncached_input_tokens": uncached_value,
        "cached_input_tokens": cached_value,
        "output_tokens": output_value,
    }


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sign_profile(profile: dict[str, Any]) -> dict[str, Any]:
    value = dict(profile)
    value.pop("integrity_sha256", None)
    value["integrity_sha256"] = hashlib.sha256(canonical_bytes(value)).hexdigest()
    return value


def verify_profile(profile: dict[str, Any]) -> None:
    if profile.get("schema_version") != PROFILE_SCHEMA_VERSION:
        raise EconomicsError("unsupported agent-profile schema")
    expected = str(profile.get("integrity_sha256") or "")
    unsigned = dict(profile)
    unsigned.pop("integrity_sha256", None)
    actual = hashlib.sha256(canonical_bytes(unsigned)).hexdigest()
    if not expected or expected != actual:
        raise EconomicsError("agent profile integrity check failed")
    authorization = profile.get("authorization")
    preflight = profile.get("preflight")
    if not isinstance(authorization, dict) or authorization.get("status") != "active":
        raise EconomicsError("agent profile lacks active explicit-user authorization")
    if not isinstance(preflight, dict) or preflight.get("status") != "passed":
        raise EconomicsError("agent profile has not passed read-only preflight")
    if profile.get("may_delegate") is not False:
        raise EconomicsError("dynamic agent profiles must remain leaves")
    if profile.get("sandbox") not in {"read-only", "workspace-write"}:
        raise EconomicsError("dynamic agent profile requests an unsafe sandbox")
