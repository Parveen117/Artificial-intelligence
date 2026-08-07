#!/usr/bin/env python3
"""Compatibility-safe final wrapper for malformed direct API inputs."""
from __future__ import annotations

from typing import Any

try:
    from . import engine_v3 as _v3
    from .engine_v3 import *  # noqa: F401,F403
except ImportError:
    import engine_v3 as _v3
    from engine_v3 import *  # noqa: F401,F403

ENGINE_VERSION = _v3.ENGINE_VERSION
SCHEMA_VERSION = _v3.SCHEMA_VERSION


def _invalid_direct_result(challenge: Any, detail: str) -> dict[str, Any]:
    cid = challenge.get("challenge_id") if isinstance(challenge, dict) else None
    package = challenge.get("package") if isinstance(challenge, dict) and isinstance(challenge.get("package"), str) else None
    mode = challenge.get("mode") if isinstance(challenge, dict) and isinstance(challenge.get("mode"), str) else None
    return {
        "engine_version": ENGINE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "challenge_id": cid,
        "package": package,
        "mode": mode,
        "result": "INVALID",
        "formal_promotion": False,
        "challenge_genesis": None,
        "challenge_evaluation": None,
        "checks": [{"id": "json_domain", "status": "invalid", "detail": detail}],
        "open_obligations": [],
        "failed_obligations": [],
        "blocked_obligations": [],
        "invalid_contract_fields": ["json_domain"],
        "not_in_scope": [],
        "parser_boundary": "Malformed/non-finite direct API values are rejected as INVALID; raw connector JSON additionally rejects duplicate keys and NaN/Infinity tokens.",
    }


def evaluate_challenge(challenge: Any) -> dict[str, Any]:
    try:
        return _v3.evaluate_challenge(challenge)
    except ChallengeError as exc:
        return _invalid_direct_result(challenge, str(exc))
