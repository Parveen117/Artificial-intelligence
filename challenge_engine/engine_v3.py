#!/usr/bin/env python3
"""Final seal hardening layer for Challenge Engine 1.2.0.

This module preserves the audited v2 decision logic and tightens the remaining
connector/ledger boundaries: explicit package/mode selection, package-manifest
commitment, scoped TOE binding, decimal threshold comparisons, genesis pinning,
and a hash-bound evaluation record.
"""
from __future__ import annotations

from decimal import Decimal
import hashlib
import json
import math
import re
from typing import Any

try:
    from . import engine_v2 as _v2
    from .engine_v2 import *  # noqa: F401,F403
except ImportError:
    import engine_v2 as _v2
    from engine_v2 import *  # noqa: F401,F403

ENGINE_VERSION = _v2.ENGINE_VERSION
SCHEMA_VERSION = _v2.SCHEMA_VERSION
_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


def _canonical_bytes(value: Any) -> bytes:
    text = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return text.encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _validate_json_tree(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ChallengeError(f"non-finite number is not allowed at {path}")
        return
    if isinstance(value, list):
        for i, item in enumerate(value):
            _validate_json_tree(item, f"{path}[{i}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ChallengeError(f"JSON object key must be a string at {path}")
            _validate_json_tree(item, f"{path}.{key}")
        return
    raise ChallengeError(f"unsupported non-JSON value at {path}: {type(value).__name__}")


def available_packages() -> list[str]:
    return _v2.available_packages()


def load_package(name: str) -> dict[str, Any]:
    if not isinstance(name, str) or not name.strip():
        raise ChallengeError("package must be a non-empty string")
    if name not in available_packages():
        raise ChallengeError(f"unknown package: {name}")
    return _v2.load_package(name)


def _package_manifest_sha256(name: str) -> str:
    return _sha256(load_package(name))


def _decimal(value: Any) -> Decimal:
    if not _v2._is_number(value):
        raise ValueError("not a finite numeric value")
    return Decimal(str(value))


def _exact_burden_check(challenge: dict[str, Any]) -> Check | None:
    if "burden" not in challenge:
        return None
    burden = challenge.get("burden")
    if not isinstance(burden, dict):
        return None
    beta = burden.get("beta")
    threshold = burden.get("threshold", 1.0)
    if not _v2._is_number(beta) or _decimal(beta) < 0:
        return Check("burden", "invalid", "beta must be a nonnegative finite number")
    if not _v2._is_number(threshold) or _decimal(threshold) <= 0:
        return Check("burden", "invalid", "threshold must be a positive finite number")
    reserve = _decimal(threshold) - _decimal(beta)
    if reserve > 0:
        return Check("burden", "pass", f"beta={beta}; exact decimal reserve={reserve}")
    if reserve == 0:
        return Check("burden", "open", f"beta={beta}; exact decimal boundary saturation")
    return Check("burden", "fail", f"beta={beta} exceeds threshold={threshold}")


def _exact_completion_check(challenge: dict[str, Any]) -> Check | None:
    if "completion" not in challenge:
        return None
    completion = challenge.get("completion")
    if not isinstance(completion, dict):
        return None
    enabled = completion.get("enabled", False)
    if not isinstance(enabled, bool):
        return Check("completion", "invalid", "completion.enabled must be Boolean")
    if not enabled:
        return None
    u = completion.get("finite_upper")
    e = completion.get("completion_error")
    threshold = completion.get("threshold", 1.0)
    if not _v2._is_number(u):
        return Check("completion", "open", "finite_upper is required")
    if _decimal(u) < 0:
        return Check("completion", "invalid", "finite_upper must be nonnegative")
    if not _v2._is_number(e):
        return Check("completion", "open", "completion_error is required; finite result alone cannot promote")
    if _decimal(e) < 0:
        return Check("completion", "invalid", "completion_error must be nonnegative")
    if not _v2._is_number(threshold) or _decimal(threshold) <= 0:
        return Check("completion", "invalid", "threshold must be a positive finite number")
    worst = _decimal(u) + _decimal(e)
    margin = _decimal(threshold) - worst
    if margin > 0:
        return Check("completion", "pass", f"exact decimal finite_upper + error = {worst}; reserve={margin}")
    if margin == 0:
        return Check("completion", "open", f"exact decimal worst-case bound reaches threshold {threshold}")
    return Check("completion", "fail", f"exact decimal worst-case bound {worst} exceeds threshold {threshold}")


def _replace_check(checks: list[dict[str, Any]], new_check: Check | None) -> list[dict[str, Any]]:
    if new_check is None:
        return checks
    out = [x for x in checks if x.get("id") != new_check.id]
    out.append({"id": new_check.id, "status": new_check.status, "detail": new_check.detail})
    return out


def _selection(challenge: dict[str, Any]) -> tuple[str, dict[str, Any], str, list[Check]]:
    checks: list[Check] = []
    if "package" not in challenge:
        package_name = "math"
    else:
        requested = challenge.get("package")
        if not isinstance(requested, str) or not requested.strip() or requested not in available_packages():
            checks.append(Check("package", "invalid", "explicit package must name an installed package"))
            package_name = "math"
        else:
            package_name = requested
    package = load_package(package_name)

    if "mode" not in challenge:
        mode = package.get("default_mode", "exploratory")
    else:
        requested_mode = challenge.get("mode")
        if not isinstance(requested_mode, str) or requested_mode not in package.get("allowed_modes", []):
            checks.append(Check("mode_selection", "invalid", "explicit mode must be an allowed mode"))
            mode = package.get("default_mode", "exploratory")
        else:
            mode = requested_mode
    return package_name, package, mode, checks


def _scope_toe_check(challenge: dict[str, Any], package: dict[str, Any]) -> Check | None:
    if not package.get("requires_authorization", False):
        return None
    scope = challenge.get("scope")
    target = challenge.get("target")
    if not isinstance(scope, dict) or not isinstance(target, dict):
        return None
    scope_target = scope.get("target")
    toe = target.get("toe")
    if not isinstance(toe, str) or not toe.strip():
        return Check("scope_toe_binding", "blocked", "scoped packages require target.toe")
    if not isinstance(scope_target, str) or not scope_target.strip():
        return None
    if toe != scope_target:
        return Check("scope_toe_binding", "blocked", f"target.toe '{toe}' does not match authorized scope.target '{scope_target}'")
    return Check("scope_toe_binding", "pass", toe)


def _evaluation_parent_check(challenge: dict[str, Any]) -> Check | None:
    if "evaluation" not in challenge:
        return None
    evaluation = challenge.get("evaluation")
    if not isinstance(evaluation, dict):
        return Check("evaluation_parent", "invalid", "evaluation must be an object")
    parent = evaluation.get("parent_hash")
    if parent is None:
        return Check("evaluation_parent", "pass", "no parent evaluation declared")
    if not isinstance(parent, str) or not _HEX64.fullmatch(parent.strip()):
        return Check("evaluation_parent", "invalid", "evaluation.parent_hash must be a 64-character SHA-256 hex digest")
    return Check("evaluation_parent", "pass", parent.strip().lower())


def _new_genesis(base_result: dict[str, Any], package_name: str) -> dict[str, Any]:
    contract = dict(base_result["challenge_genesis"]["contract"])
    contract["package_manifest_sha256"] = _package_manifest_sha256(package_name)
    contract["parser_contract"] = "strict-json-unique-keys-finite-numbers-v1"
    digest = _sha256(contract)
    return {
        "kind": "CHALLENGE_GENESIS",
        "hash_algorithm": "sha256",
        "genesis_hash": digest,
        "parent": None,
        "accepted_claims": 0,
        "rules_frozen": True,
        "meaning": "immutable rules of engagement before candidate evaluation; no claim is accepted at genesis",
        "contract": contract,
    }


def _genesis_pin_check(challenge: dict[str, Any], genesis: dict[str, Any]) -> Check | None:
    pin = challenge.get("genesis")
    if pin is None:
        return None
    if not isinstance(pin, dict):
        return Check("genesis_integrity", "invalid", "genesis must be an object")
    if "expected_hash" not in pin:
        return None
    expected = pin.get("expected_hash")
    if not isinstance(expected, str) or not _HEX64.fullmatch(expected.strip()):
        return Check("genesis_integrity", "invalid", "genesis.expected_hash must be a 64-character SHA-256 hex digest")
    actual = genesis["genesis_hash"]
    if expected.strip().lower() == actual:
        return Check("genesis_integrity", "pass", actual)
    return Check("genesis_integrity", "fail", f"expected {expected.strip().lower()}, computed {actual}")


def _recompute_result(mode: str, checks: list[dict[str, Any]]) -> str:
    statuses = [x.get("status") for x in checks]
    if "invalid" in statuses:
        return "INVALID"
    if "blocked" in statuses:
        return "BLOCKED_SCOPE"
    if "not_in_scope" in statuses:
        return "SEMANTICS_NOT_IN_SCOPE"
    if "fail" in statuses:
        return "FAILED"
    if "open" in statuses:
        return "INCOMPLETE"
    if mode == "exploratory":
        return "OBSERVED"
    if mode == "adversarial":
        return "ADVERSARIAL_PASS"
    if mode == "certified":
        return "CERTIFIED"
    return "INVALID"


def _evaluation_record(normalized_input: dict[str, Any], genesis: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    input_hash = _sha256(normalized_input)
    evaluation = normalized_input.get("evaluation") if isinstance(normalized_input.get("evaluation"), dict) else {}
    parent = evaluation.get("parent_hash")
    parent = parent.strip().lower() if isinstance(parent, str) and _HEX64.fullmatch(parent.strip()) else None
    payload = {
        "kind": "CHALLENGE_EVALUATION",
        "engine_version": ENGINE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "genesis_hash": genesis["genesis_hash"],
        "input_sha256": input_hash,
        "parent_evaluation_hash": parent,
        "result": result["result"],
        "formal_promotion": result["formal_promotion"],
        "checks": result["checks"],
    }
    return {
        **payload,
        "hash_algorithm": "sha256",
        "evaluation_hash": _sha256(payload),
        "meaning": "hash-bound evaluation outcome under the frozen Challenge Genesis contract",
    }


def evaluate_challenge(challenge: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(challenge, dict):
        raise ChallengeError("challenge input must be a JSON object")
    _validate_json_tree(challenge)

    original = dict(challenge)
    package_name, package, mode, prechecks = _selection(original)

    base_input = dict(original)
    base_input["package"] = package_name
    base_input["mode"] = mode
    base_input.setdefault("schema_version", SCHEMA_VERSION)
    base_input.setdefault("semantics", {"mode": "payload_only"})
    # v3 verifies the stronger package-bound genesis itself.
    base_input.pop("genesis", None)

    base_result = _v2.evaluate_challenge(base_input)
    checks = list(base_result.get("checks", []))
    checks.extend({"id": c.id, "status": c.status, "detail": c.detail} for c in prechecks)

    toe_check = _scope_toe_check(base_input, package)
    if toe_check:
        checks.append({"id": toe_check.id, "status": toe_check.status, "detail": toe_check.detail})

    checks = _replace_check(checks, _exact_burden_check(base_input))
    checks = _replace_check(checks, _exact_completion_check(base_input))

    parent_check = _evaluation_parent_check(original)
    if parent_check:
        checks.append({"id": parent_check.id, "status": parent_check.status, "detail": parent_check.detail})

    base_result["checks"] = checks
    genesis = _new_genesis(base_result, package_name)
    pin_check = _genesis_pin_check(original, genesis)
    if pin_check:
        checks.append({"id": pin_check.id, "status": pin_check.status, "detail": pin_check.detail})

    result_name = _recompute_result(mode, checks)
    base_result.update({
        "engine_version": ENGINE_VERSION,
        "package": package_name,
        "mode": mode,
        "result": result_name,
        "formal_promotion": result_name == "CERTIFIED",
        "challenge_genesis": genesis,
        "checks": checks,
        "open_obligations": [x["id"] for x in checks if x.get("status") == "open"],
        "failed_obligations": [x["id"] for x in checks if x.get("status") == "fail"],
        "blocked_obligations": [x["id"] for x in checks if x.get("status") == "blocked"],
        "invalid_contract_fields": [x["id"] for x in checks if x.get("status") == "invalid"],
        "not_in_scope": [x["id"] for x in checks if x.get("status") == "not_in_scope"],
        "parser_boundary": "Connector JSON is strict: duplicate object keys and NaN/Infinity tokens are rejected before evaluation.",
        "replay_boundary": "The engine emits an evaluation hash and optional parent hash. Detecting reuse/replay across requests requires the connector or persistent ledger to remember prior evaluation hashes.",
    })

    normalized_input = dict(base_input)
    if "genesis" in original:
        normalized_input["genesis"] = original["genesis"]
    if "evaluation" in original:
        normalized_input["evaluation"] = original["evaluation"]
    base_result["challenge_evaluation"] = _evaluation_record(normalized_input, genesis, base_result)
    return base_result


def capabilities() -> dict[str, Any]:
    manifests = []
    for name in available_packages():
        manifest = dict(load_package(name))
        manifest["manifest_sha256"] = _package_manifest_sha256(name)
        manifests.append(manifest)
    base = _v2.capabilities()
    base.update({
        "engine_version": ENGINE_VERSION,
        "packages": manifests,
        "strict_json_input": True,
        "strict_json_contract": "unique object keys; standard finite JSON numbers only",
        "exact_threshold_arithmetic": "decimal-from-declared-number spelling for burden/completion decisions",
        "scoped_toe_binding": True,
        "package_manifest_committed_in_genesis": True,
        "evaluation_record": {"hash_algorithm": "sha256", "optional_parent_hash": True},
        "replay_boundary": "Cross-request replay detection is a connector/persistent-ledger responsibility.",
    })
    return base
