#!/usr/bin/env python3
"""Exact-rational / validated-enclosure hardening for Challenge Engine 1.2.0.

This layer preserves the audited v3 decision engine and adds a proof-bearing
numeric carrier. Connector decimal lexemes are recovered exactly before binary
rounding can influence threshold or canonical-hash decisions. Exact rationals
and finite decimals embed as zero-radius enclosures; directed intervals and
validated balls carry outward arithmetic uncertainty; analytic tails stay a
separate declared channel. Raw floating-point centres without an outward radius
remain non-proof-bearing.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from fractions import Fraction
import hashlib
import json
import math
from typing import Any

try:
    from . import engine_v3 as _v3
    from .engine_v3 import *  # noqa: F401,F403
    from .strict_json import exact_json_lexeme
except ImportError:
    import engine_v3 as _v3
    from engine_v3 import *  # noqa: F401,F403
    from strict_json import exact_json_lexeme

ENGINE_VERSION = _v3.ENGINE_VERSION
SCHEMA_VERSION = _v3.SCHEMA_VERSION
ARITHMETIC_PROTOCOL = "exact-rational-directed-enclosure-v1"
PARSER_CONTRACT = "strict-json-unique-keys-finite-numbers-exact-decimal-lexeme-v2"


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
        "arithmetic_protocol": ARITHMETIC_PROTOCOL,
        "parser_boundary": "Malformed/non-finite direct API values are rejected as INVALID; raw connector JSON additionally rejects duplicate keys and non-standard numeric tokens.",
    }


def _fraction_record(value: Fraction) -> dict[str, str]:
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _fraction_from_decimal_text(text: str) -> Fraction:
    try:
        value = Decimal(text.strip())
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError(f"invalid exact decimal: {text!r}") from exc
    if not value.is_finite():
        raise ValueError("exact decimal must be finite")
    return Fraction(value)


def _fraction_scalar(value: Any, field: str) -> Fraction:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a scalar number, not Boolean")
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{field} must be finite")
        token = exact_json_lexeme(value)
        return _fraction_from_decimal_text(token if token is not None else str(value))
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError(f"{field} must not be empty")
        if "/" in text:
            parts = text.split("/")
            if len(parts) != 2:
                raise ValueError(f"{field} has invalid rational spelling")
            try:
                numerator = int(parts[0].strip())
                denominator = int(parts[1].strip())
            except ValueError as exc:
                raise ValueError(f"{field} has invalid rational spelling") from exc
            if denominator == 0:
                raise ValueError(f"{field} denominator must be nonzero")
            return Fraction(numerator, denominator)
        return _fraction_from_decimal_text(text)
    raise ValueError(f"{field} must be an integer, finite decimal, or rational string")


def _declared_decimal(value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("not a finite numeric value")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("not a finite numeric value")
    token = exact_json_lexeme(value) if isinstance(value, float) else None
    return Decimal(token if token is not None else str(value))


def _canonicalize(value: Any) -> Any:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ChallengeError("non-finite number cannot enter canonical contract")
        token = exact_json_lexeme(value)
        if token is not None:
            return {"$exact_number": _fraction_record(_fraction_from_decimal_text(token))}
        return value
    if isinstance(value, list):
        return [_canonicalize(x) for x in value]
    if isinstance(value, dict):
        return {k: _canonicalize(v) for k, v in sorted(value.items())}
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _canonicalize(value), sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _collect_exact_connector_numbers(value: Any, path: str = "$") -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    if isinstance(value, float):
        token = exact_json_lexeme(value)
        if token is not None:
            out[path] = _fraction_record(_fraction_from_decimal_text(token))
        return out
    if isinstance(value, list):
        for i, item in enumerate(value):
            out.update(_collect_exact_connector_numbers(item, f"{path}[{i}]"))
    elif isinstance(value, dict):
        for key, item in value.items():
            out.update(_collect_exact_connector_numbers(item, f"{path}.{key}"))
    return out


def _replace_check(checks: list[dict[str, Any]], check: Check | None) -> list[dict[str, Any]]:
    if check is None:
        return checks
    out = [x for x in checks if x.get("id") != check.id]
    out.append({"id": check.id, "status": check.status, "detail": check.detail})
    return out


def _exact_burden_check(challenge: dict[str, Any]) -> Check | None:
    burden = challenge.get("burden")
    if "burden" not in challenge or not isinstance(burden, dict):
        return None
    try:
        beta = _declared_decimal(burden.get("beta"))
        threshold = _declared_decimal(burden.get("threshold", 1.0))
    except ValueError:
        return Check("burden", "invalid", "beta and threshold must be finite numeric values")
    if beta < 0:
        return Check("burden", "invalid", "beta must be nonnegative")
    if threshold <= 0:
        return Check("burden", "invalid", "threshold must be positive")
    reserve = threshold - beta
    if reserve > 0:
        return Check("burden", "pass", f"exact declared-value reserve={reserve}")
    if reserve == 0:
        return Check("burden", "open", "exact declared-value boundary saturation")
    return Check("burden", "fail", f"beta={beta} exceeds threshold={threshold}")


def _exact_completion_check(challenge: dict[str, Any]) -> Check | None:
    completion = challenge.get("completion")
    if "completion" not in challenge or not isinstance(completion, dict):
        return None
    enabled = completion.get("enabled", False)
    if not isinstance(enabled, bool):
        return Check("completion", "invalid", "completion.enabled must be Boolean")
    if not enabled:
        return None
    if completion.get("finite_upper") is None:
        return Check("completion", "open", "finite_upper is required")
    if completion.get("completion_error") is None:
        return Check("completion", "open", "completion_error is required; finite result alone cannot promote")
    try:
        finite_upper = _declared_decimal(completion.get("finite_upper"))
        error = _declared_decimal(completion.get("completion_error"))
        threshold = _declared_decimal(completion.get("threshold", 1.0))
    except ValueError:
        return Check("completion", "invalid", "completion values must be finite numeric values")
    if finite_upper < 0 or error < 0:
        return Check("completion", "invalid", "finite_upper and completion_error must be nonnegative")
    if threshold <= 0:
        return Check("completion", "invalid", "threshold must be positive")
    worst = finite_upper + error
    reserve = threshold - worst
    if reserve > 0:
        return Check("completion", "pass", f"exact declared-value worst={worst}; reserve={reserve}")
    if reserve == 0:
        return Check("completion", "open", f"exact declared-value worst reaches threshold {threshold}")
    return Check("completion", "fail", f"exact declared-value worst={worst} exceeds threshold={threshold}")


def _exact_flow_checks(challenge: dict[str, Any]) -> list[Check]:
    flow = challenge.get("flow")
    if not isinstance(flow, dict) or flow.get("enabled") is not True:
        return []
    checks: list[Check] = []
    bilateral = flow.get("bilateral")
    if isinstance(bilateral, dict):
        try:
            defect = _declared_decimal(bilateral.get("defect"))
            tolerance = _declared_decimal(bilateral.get("tolerance"))
        except ValueError:
            checks.append(Check("flow:bilateral_defect", "invalid", "finite defect and tolerance are required"))
        else:
            if tolerance < 0:
                checks.append(Check("flow:bilateral_defect", "invalid", "tolerance must be nonnegative"))
            elif abs(defect) <= tolerance:
                checks.append(Check("flow:bilateral_defect", "pass", f"exact |defect|={abs(defect)} <= {tolerance}"))
            else:
                checks.append(Check("flow:bilateral_defect", "fail", f"exact |defect|={abs(defect)} > {tolerance}"))
    if "remainder_bound" in flow:
        try:
            remainder = _declared_decimal(flow.get("remainder_bound"))
        except ValueError:
            checks.append(Check("flow:remainder_bound", "invalid", "remainder_bound must be finite"))
        else:
            checks.append(Check(
                "flow:remainder_bound", "pass" if remainder >= 0 else "invalid",
                f"exact remainder_bound={remainder}" if remainder >= 0 else "remainder_bound must be nonnegative",
            ))
    return checks


def _integer_component(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except (ValueError, AttributeError) as exc:
            raise ValueError(f"{field} must be an integer or integer string") from exc
    raise ValueError(f"{field} must be an integer or integer string")


def _descriptor_interval(item: dict[str, Any], label: str) -> tuple[Fraction, Fraction]:
    forms = sum([
        int("numerator" in item or "denominator" in item),
        int("value" in item),
        int("lower" in item or "upper" in item),
        int("center" in item or "radius" in item),
    ])
    if forms != 1:
        raise ValueError(f"{label} must declare exactly one enclosure form")
    if "numerator" in item or "denominator" in item:
        numerator = _integer_component(item.get("numerator"), f"{label}.numerator")
        denominator = _integer_component(item.get("denominator"), f"{label}.denominator")
        if denominator == 0:
            raise ValueError(f"{label}.denominator must be nonzero")
        q = Fraction(numerator, denominator)
        return q, q
    if "value" in item:
        q = _fraction_scalar(item.get("value"), f"{label}.value")
        return q, q
    if "lower" in item or "upper" in item:
        if "lower" not in item or "upper" not in item:
            raise ValueError(f"{label} interval requires both lower and upper")
        lower = _fraction_scalar(item.get("lower"), f"{label}.lower")
        upper = _fraction_scalar(item.get("upper"), f"{label}.upper")
        if lower > upper:
            raise ValueError(f"{label}.lower must not exceed upper")
        return lower, upper
    if "center" not in item or "radius" not in item:
        raise ValueError(f"{label} ball requires center and radius")
    center = _fraction_scalar(item.get("center"), f"{label}.center")
    radius = _fraction_scalar(item.get("radius"), f"{label}.radius")
    if radius < 0:
        raise ValueError(f"{label}.radius must be nonnegative")
    return center - radius, center + radius


def _check_independent_enclosures(cert: dict[str, Any]) -> Check | None:
    if "independent_enclosures" not in cert:
        return None
    items = cert.get("independent_enclosures")
    if not isinstance(items, list) or len(items) < 2:
        return Check("arithmetic_path_overlap", "invalid", "independent_enclosures requires at least two entries")
    seen: set[str] = set()
    intervals: list[tuple[Fraction, Fraction]] = []
    try:
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValueError(f"independent_enclosures[{index}] must be an object")
            eid = item.get("id")
            if not isinstance(eid, str) or not eid.strip():
                raise ValueError(f"independent_enclosures[{index}].id is required")
            if eid in seen:
                raise ValueError(f"duplicate independent enclosure id: {eid}")
            seen.add(eid)
            intervals.append(_descriptor_interval(item, f"independent_enclosures[{index}]"))
    except ValueError as exc:
        return Check("arithmetic_path_overlap", "invalid", str(exc))
    common_lower = max(lo for lo, _ in intervals)
    common_upper = min(hi for _, hi in intervals)
    if common_lower <= common_upper:
        return Check("arithmetic_path_overlap", "pass", f"common intersection=[{_fraction_text(common_lower)},{_fraction_text(common_upper)}]")
    return Check("arithmetic_path_overlap", "fail", "independent certified enclosures are disjoint; target identity, adapter, or enclosure must be wrong")


def _check_arithmetic_certificate(challenge: dict[str, Any]) -> tuple[Check | None, dict[str, Any] | None, Check | None]:
    if "arithmetic_certificate" not in challenge:
        return None, None, None
    cert = challenge.get("arithmetic_certificate")
    if not isinstance(cert, dict):
        return Check("arithmetic_certificate", "invalid", "arithmetic_certificate must be an object"), None, None
    kind = cert.get("kind")
    relation = cert.get("relation", "upper_below_threshold")
    allowed = {"exact_rational", "exact_decimal", "directed_interval", "ball", "raw_float"}
    if kind not in allowed:
        return Check("arithmetic_certificate", "invalid", f"unsupported arithmetic kind: {kind}"), None, None
    if relation != "upper_below_threshold":
        return Check("arithmetic_certificate", "invalid", "only upper_below_threshold is currently certified"), None, None
    if "analytic_tail" not in cert or "threshold" not in cert:
        return Check("arithmetic_certificate", "open", "analytic_tail and threshold must be declared explicitly"), None, _check_independent_enclosures(cert)

    try:
        tail = _fraction_scalar(cert.get("analytic_tail"), "arithmetic_certificate.analytic_tail")
        threshold = _fraction_scalar(cert.get("threshold"), "arithmetic_certificate.threshold")
        if tail < 0:
            raise ValueError("arithmetic_certificate.analytic_tail must be nonnegative")
        if kind == "exact_rational":
            numerator = _integer_component(cert.get("numerator"), "arithmetic_certificate.numerator")
            denominator = _integer_component(cert.get("denominator"), "arithmetic_certificate.denominator")
            if denominator == 0:
                raise ValueError("arithmetic_certificate.denominator must be nonzero")
            lower = upper = Fraction(numerator, denominator)
            radius = Fraction(0)
        elif kind == "exact_decimal":
            lower = upper = _fraction_scalar(cert.get("value"), "arithmetic_certificate.value")
            radius = Fraction(0)
        elif kind == "directed_interval":
            lower = _fraction_scalar(cert.get("lower"), "arithmetic_certificate.lower")
            upper = _fraction_scalar(cert.get("upper"), "arithmetic_certificate.upper")
            if lower > upper:
                raise ValueError("arithmetic_certificate.lower must not exceed upper")
            radius = (upper - lower) / 2
        else:
            center = _fraction_scalar(cert.get("center"), "arithmetic_certificate.center")
            if "radius" not in cert:
                if kind == "raw_float":
                    return (
                        Check("arithmetic_certificate", "open", "raw float is calibration only until an outward radius is supplied"),
                        {"kind": kind, "proof_bearing": False, "reason": "missing validated outward radius"},
                        _check_independent_enclosures(cert),
                    )
                raise ValueError("arithmetic_certificate.radius is required")
            radius = _fraction_scalar(cert.get("radius"), "arithmetic_certificate.radius")
            if radius < 0:
                raise ValueError("arithmetic_certificate.radius must be nonnegative")
            lower, upper = center - radius, center + radius
    except ValueError as exc:
        return Check("arithmetic_certificate", "invalid", str(exc)), None, _check_independent_enclosures(cert)

    outward_upper = upper + tail
    reserve = threshold - outward_upper
    if reserve > 0:
        status = "pass"
        detail = f"outward upper={_fraction_text(outward_upper)} < threshold={_fraction_text(threshold)}; reserve={_fraction_text(reserve)}"
    elif reserve == 0:
        status = "open"
        detail = f"outward upper reaches threshold={_fraction_text(threshold)}; strict promotion withheld"
    else:
        status = "fail"
        detail = f"outward upper={_fraction_text(outward_upper)} exceeds threshold={_fraction_text(threshold)}"
    summary = {
        "kind": kind,
        "relation": relation,
        "proof_bearing": True,
        "enclosure_lower": _fraction_text(lower),
        "enclosure_upper": _fraction_text(upper),
        "arithmetic_radius": _fraction_text(radius),
        "analytic_tail": _fraction_text(tail),
        "outward_upper": _fraction_text(outward_upper),
        "threshold": _fraction_text(threshold),
        "reserve": _fraction_text(reserve),
        "backend": cert.get("backend") if isinstance(cert.get("backend"), str) else None,
    }
    return Check("arithmetic_certificate", status, detail), summary, _check_independent_enclosures(cert)


def _new_genesis(original: dict[str, Any], base_result: dict[str, Any]) -> dict[str, Any]:
    contract = _canonicalize(dict(base_result["challenge_genesis"]["contract"]))
    contract["parser_contract"] = PARSER_CONTRACT
    contract["arithmetic_protocol"] = ARITHMETIC_PROTOCOL
    exact_numbers = _collect_exact_connector_numbers(original)
    if exact_numbers:
        contract["exact_numeric_declarations"] = exact_numbers
    if "arithmetic_certificate" in original:
        contract["arithmetic_certificate"] = _canonicalize(original.get("arithmetic_certificate"))
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


def _genesis_pin_check(original: dict[str, Any], genesis: dict[str, Any]) -> Check | None:
    pin = original.get("genesis")
    if pin is None:
        return None
    if not isinstance(pin, dict):
        return Check("genesis_integrity", "invalid", "genesis must be an object")
    if "expected_hash" not in pin:
        return None
    expected = pin.get("expected_hash")
    if not isinstance(expected, str) or not _v3._HEX64.fullmatch(expected.strip()):
        return Check("genesis_integrity", "invalid", "genesis.expected_hash must be a 64-character SHA-256 hex digest")
    actual = genesis["genesis_hash"]
    if expected.strip().lower() == actual:
        return Check("genesis_integrity", "pass", actual)
    return Check("genesis_integrity", "fail", f"expected {expected.strip().lower()}, computed {actual}")


def _evaluation_record(original: dict[str, Any], base_result: dict[str, Any], genesis: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(original)
    normalized.setdefault("package", base_result.get("package", "math"))
    normalized.setdefault("mode", base_result.get("mode"))
    normalized.setdefault("schema_version", SCHEMA_VERSION)
    normalized.setdefault("semantics", {"mode": "payload_only"})
    evaluation = normalized.get("evaluation") if isinstance(normalized.get("evaluation"), dict) else {}
    parent = evaluation.get("parent_hash")
    parent = parent.strip().lower() if isinstance(parent, str) and _v3._HEX64.fullmatch(parent.strip()) else None
    payload = {
        "kind": "CHALLENGE_EVALUATION",
        "engine_version": ENGINE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "genesis_hash": genesis["genesis_hash"],
        "input_sha256": _sha256(normalized),
        "parent_evaluation_hash": parent,
        "result": base_result["result"],
        "formal_promotion": base_result["formal_promotion"],
        "checks": base_result["checks"],
    }
    return {**payload, "hash_algorithm": "sha256", "evaluation_hash": _sha256(payload), "meaning": "hash-bound evaluation outcome under the frozen Challenge Genesis contract"}


def _evaluate_impl(challenge: dict[str, Any]) -> dict[str, Any]:
    base_result = _v3.evaluate_challenge(challenge)
    checks = [x for x in base_result.get("checks", []) if x.get("id") != "genesis_integrity"]
    checks = _replace_check(checks, _exact_burden_check(challenge))
    checks = _replace_check(checks, _exact_completion_check(challenge))
    for check in _exact_flow_checks(challenge):
        checks = _replace_check(checks, check)

    arithmetic_check, arithmetic_summary, overlap_check = _check_arithmetic_certificate(challenge)
    checks = _replace_check(checks, arithmetic_check)
    checks = _replace_check(checks, overlap_check)

    base_result["checks"] = checks
    genesis = _new_genesis(challenge, base_result)
    checks = _replace_check(checks, _genesis_pin_check(challenge, genesis))
    result_name = _v3._recompute_result(base_result.get("mode"), checks)
    base_result.update({
        "result": result_name,
        "formal_promotion": result_name == "CERTIFIED",
        "challenge_genesis": genesis,
        "checks": checks,
        "open_obligations": [x["id"] for x in checks if x.get("status") == "open"],
        "failed_obligations": [x["id"] for x in checks if x.get("status") == "fail"],
        "blocked_obligations": [x["id"] for x in checks if x.get("status") == "blocked"],
        "invalid_contract_fields": [x["id"] for x in checks if x.get("status") == "invalid"],
        "not_in_scope": [x["id"] for x in checks if x.get("status") == "not_in_scope"],
        "arithmetic_protocol": ARITHMETIC_PROTOCOL,
        "arithmetic_summary": arithmetic_summary,
        "parser_boundary": "Connector JSON rejects duplicate keys and non-standard numeric tokens; finite decimal lexemes are retained for exact declared-value decisions.",
        "numeric_boundary": "Exact rational/decimal values have zero arithmetic radius. Validated intervals/balls carry outward arithmetic radius. Analytic tail is separate and adds outward before threshold promotion.",
    })
    base_result["challenge_evaluation"] = _evaluation_record(challenge, base_result, genesis)
    return base_result


def evaluate_challenge(challenge: Any) -> dict[str, Any]:
    try:
        if not isinstance(challenge, dict):
            raise ChallengeError("challenge input must be a JSON object")
        return _evaluate_impl(challenge)
    except (ChallengeError, ValueError) as exc:
        return _invalid_direct_result(challenge, str(exc))


def capabilities() -> dict[str, Any]:
    base = _v3.capabilities()
    base.update({
        "arithmetic_protocol": ARITHMETIC_PROTOCOL,
        "exact_connector_decimal_lexeme": True,
        "proof_bearing_arithmetic_kinds": ["exact_rational", "exact_decimal", "directed_interval", "ball", "raw_float_with_validated_radius"],
        "raw_float_without_radius": "INCOMPLETE",
        "numeric_promotion_rule": "outward arithmetic upper + analytic tail < threshold",
        "independent_enclosure_check": "optional common-intersection requirement",
        "arbitrary_precision_contract": "use string-valued exact decimal/rational/enclosure fields",
    })
    return base
