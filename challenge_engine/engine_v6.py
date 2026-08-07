#!/usr/bin/env python3
"""Theorem-47 source-bound proof-carrying numerical hardening.

This layer closes the trust gap left by v4/v5: a participant-supplied radius or
analytic tail does not become proof-bearing merely because it is syntactically
well formed.  The proof-bearing T47 subset is an exact rational interval DAG
with an admitted formal source model and verifier-derived tail.  Legacy exact
rational/decimal singleton certificates with zero analytic tail remain exact;
legacy approximate certificates are held open unless migrated to T47.
"""
from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from pathlib import Path
from typing import Any

try:
    from . import engine_v5 as _v5
    from .engine_v5 import *  # noqa: F401,F403
except ImportError:
    import engine_v5 as _v5
    from engine_v5 import *  # noqa: F401,F403

ENGINE_VERSION = _v5.ENGINE_VERSION
SCHEMA_VERSION = _v5.SCHEMA_VERSION
SOURCE_BOUND_NUMERICS_PROTOCOL = "source-bound-proof-carrying-numerics-v1"
SOURCE_BOUND_SOURCE_MODEL = "exact_expression_v1"
MAX_TRACE_NODES = 256
ADMITTED_OPS = {"add", "sub", "mul", "neg", "div"}
ADMITTED_TAIL_RULES = {"zero", "geometric_tail"}


def _frac(value: Any, field: str) -> Fraction:
    return _v5._v4._fraction_scalar(value, field)


def _fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _canonicalize(value: Any) -> Any:
    return _v5._v4._canonicalize(value)


def _sha256(value: Any) -> str:
    return _v5._v4._sha256(value)


def _implementation_manifest() -> dict[str, Any]:
    root = Path(__file__).resolve().parent
    paths = [
        root / "strict_json.py",
        root / "engine.py",
        root / "engine_v4.py",
        root / "engine_v5.py",
        root / "engine_v6.py",
        root / "schema" / "challenge.schema.json",
    ]
    paths.extend(sorted((root / "packages").glob("*.json")))
    files: dict[str, str] = {}
    for path in paths:
        rel = path.relative_to(root).as_posix()
        files[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "protocol": SOURCE_BOUND_NUMERICS_PROTOCOL,
        "engine_version": ENGINE_VERSION,
        "files": files,
        "admitted_source_models": [SOURCE_BOUND_SOURCE_MODEL],
        "admitted_operations": sorted(ADMITTED_OPS),
        "admitted_tail_rules": sorted(ADMITTED_TAIL_RULES),
        "max_trace_nodes": MAX_TRACE_NODES,
        "meaning": "integrity fingerprint of the parser/validator implementation used to interpret this Challenge Genesis",
    }


def _implementation_fingerprint() -> str:
    return _sha256(_implementation_manifest())


def _parse_interval(value: Any, field: str) -> tuple[Fraction, Fraction]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object with lower and upper")
    if "lower" not in value or "upper" not in value:
        raise ValueError(f"{field} requires lower and upper")
    lower = _frac(value.get("lower"), f"{field}.lower")
    upper = _frac(value.get("upper"), f"{field}.upper")
    if lower > upper:
        raise ValueError(f"{field}.lower must not exceed upper")
    return lower, upper


def _contains(outer: tuple[Fraction, Fraction], inner: tuple[Fraction, Fraction]) -> bool:
    return outer[0] <= inner[0] and inner[1] <= outer[1]


def _interval_add(a: tuple[Fraction, Fraction], b: tuple[Fraction, Fraction]) -> tuple[Fraction, Fraction]:
    return a[0] + b[0], a[1] + b[1]


def _interval_sub(a: tuple[Fraction, Fraction], b: tuple[Fraction, Fraction]) -> tuple[Fraction, Fraction]:
    return a[0] - b[1], a[1] - b[0]


def _interval_mul(a: tuple[Fraction, Fraction], b: tuple[Fraction, Fraction]) -> tuple[Fraction, Fraction]:
    products = (a[0] * b[0], a[0] * b[1], a[1] * b[0], a[1] * b[1])
    return min(products), max(products)


def _interval_neg(a: tuple[Fraction, Fraction]) -> tuple[Fraction, Fraction]:
    return -a[1], -a[0]


def _interval_div(a: tuple[Fraction, Fraction], b: tuple[Fraction, Fraction]) -> tuple[Fraction, Fraction]:
    if b[0] <= 0 <= b[1]:
        raise ZeroDivisionError("source-bound denominator enclosure contains zero")
    reciprocal = (min(Fraction(1, 1) / b[0], Fraction(1, 1) / b[1]), max(Fraction(1, 1) / b[0], Fraction(1, 1) / b[1]))
    return _interval_mul(a, reciprocal)


def _canonical_operation(op: str, deps: list[tuple[Fraction, Fraction]]) -> tuple[Fraction, Fraction]:
    if op == "add" and len(deps) == 2:
        return _interval_add(deps[0], deps[1])
    if op == "sub" and len(deps) == 2:
        return _interval_sub(deps[0], deps[1])
    if op == "mul" and len(deps) == 2:
        return _interval_mul(deps[0], deps[1])
    if op == "neg" and len(deps) == 1:
        return _interval_neg(deps[0])
    if op == "div" and len(deps) == 2:
        return _interval_div(deps[0], deps[1])
    raise ValueError(f"unsupported operation or arity: {op}/{len(deps)}")


def _verify_trace(cert: dict[str, Any]) -> tuple[str, str, dict[str, tuple[Fraction, Fraction]], tuple[Fraction, Fraction] | None]:
    source_model = cert.get("source_model")
    if source_model != SOURCE_BOUND_SOURCE_MODEL:
        return "open", f"unsupported source model {source_model!r}; only {SOURCE_BOUND_SOURCE_MODEL} is proof-bearing in this release", {}, None

    nodes = cert.get("nodes")
    root_id = cert.get("root")
    if not isinstance(nodes, list) or not nodes:
        return "invalid", "source_bound_numerics.nodes must be a nonempty list", {}, None
    if len(nodes) > MAX_TRACE_NODES:
        return "invalid", f"source_bound_numerics.nodes exceeds protocol limit {MAX_TRACE_NODES}", {}, None
    if not isinstance(root_id, str) or not root_id:
        return "invalid", "source_bound_numerics.root is required", {}, None

    all_ids: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            return "invalid", f"source_bound_numerics.nodes[{index}] must be an object", {}, None
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            return "invalid", f"source_bound_numerics.nodes[{index}].id is required", {}, None
        if node_id in all_ids:
            return "invalid", f"duplicate source-bound node id: {node_id}", {}, None
        all_ids.add(node_id)

    seen: dict[str, tuple[Fraction, Fraction]] = {}
    for index, node in enumerate(nodes):
        node_id = node["id"]
        try:
            declared = _parse_interval(node.get("interval"), f"source_bound_numerics.nodes[{index}].interval")
        except ValueError as exc:
            return "invalid", str(exc), {}, None

        kind = node.get("kind")
        if kind == "exact_contract":
            if "value" not in node:
                return "invalid", f"exact_contract node {node_id} requires value", {}, None
            try:
                q = _frac(node.get("value"), f"source_bound_numerics.nodes[{index}].value")
            except ValueError as exc:
                return "invalid", str(exc), {}, None
            if not _contains(declared, (q, q)):
                return "fail", f"exact source value for {node_id} is outside its declared interval", {}, None
            seen[node_id] = declared
            continue

        if kind != "op":
            return "open", f"unsupported source-bound node class {kind!r}; external/backend claims require an admitted source validator", {}, None

        op = node.get("op")
        deps = node.get("deps")
        if op not in ADMITTED_OPS or not isinstance(deps, list):
            return "invalid", f"node {node_id} has unsupported operation or malformed deps", {}, None
        if any(not isinstance(dep, str) or dep not in seen for dep in deps):
            return "invalid", f"node {node_id} dependency is missing, forward-referenced, or cyclic", {}, None
        try:
            canonical = _canonical_operation(op, [seen[dep] for dep in deps])
        except ZeroDivisionError as exc:
            return "fail", str(exc), {}, None
        except ValueError as exc:
            return "invalid", str(exc), {}, None
        if not _contains(declared, canonical):
            return "fail", f"node {node_id} interval is narrower than verifier-computed enclosure [{_fraction_text(canonical[0])},{_fraction_text(canonical[1])}]", {}, None
        seen[node_id] = declared

    if root_id not in seen:
        return "invalid", "source_bound_numerics.root does not identify a verified node", {}, None
    return "pass", "source-bound exact-expression DAG verified", seen, seen[root_id]


def _tail_bound(cert: dict[str, Any], intervals: dict[str, tuple[Fraction, Fraction]]) -> tuple[str, str, Fraction | None]:
    tail = cert.get("tail")
    if not isinstance(tail, dict):
        return "invalid", "source_bound_numerics.tail must be an object", None
    rule = tail.get("rule")
    if rule == "zero":
        return "pass", "zero analytic tail declared by exact-expression source model", Fraction(0)
    if rule != "geometric_tail":
        return "open", f"tail rule {rule!r} is not proof-bearing in this engine release", None

    first_id = tail.get("first_omitted_node")
    ratio_id = tail.get("ratio_upper_node")
    if not isinstance(first_id, str) or first_id not in intervals:
        return "invalid", "geometric_tail.first_omitted_node must reference a verified DAG node", None
    if not isinstance(ratio_id, str) or ratio_id not in intervals:
        return "invalid", "geometric_tail.ratio_upper_node must reference a verified DAG node", None
    first = intervals[first_id]
    ratio = intervals[ratio_id]
    if first[0] < 0:
        return "invalid", "geometric first-omitted magnitude enclosure must be nonnegative", None
    if ratio[0] < 0 or ratio[1] >= 1:
        return "fail", "geometric ratio enclosure must satisfy 0 <= q < 1", None
    tau = first[1] / (1 - ratio[1])
    return "pass", f"geometric tail recomputed as {_fraction_text(tau)}", tau


def _source_bound_check(challenge: dict[str, Any]) -> tuple[Check | None, dict[str, Any] | None]:
    if "source_bound_numerics" not in challenge:
        return None, None
    cert = challenge.get("source_bound_numerics")
    if not isinstance(cert, dict):
        return Check("source_bound_numerics", "invalid", "source_bound_numerics must be an object"), None
    if cert.get("protocol", SOURCE_BOUND_NUMERICS_PROTOCOL) != SOURCE_BOUND_NUMERICS_PROTOCOL:
        return Check("source_bound_numerics", "invalid", "unsupported source-bound numerics protocol"), None
    if "arithmetic_certificate" in challenge:
        return Check("source_bound_numerics", "invalid", "source_bound_numerics and legacy arithmetic_certificate are mutually exclusive"), None

    trace_status, trace_detail, intervals, root = _verify_trace(cert)
    if trace_status != "pass":
        return Check("source_bound_numerics", trace_status, trace_detail), {
            "protocol": SOURCE_BOUND_NUMERICS_PROTOCOL,
            "proof_bearing": False,
            "source_model": cert.get("source_model"),
            "trace_status": trace_status,
        }

    tail_status, tail_detail, tau = _tail_bound(cert, intervals)
    if tail_status != "pass" or tau is None:
        return Check("source_bound_numerics", tail_status, tail_detail), {
            "protocol": SOURCE_BOUND_NUMERICS_PROTOCOL,
            "proof_bearing": False,
            "source_model": cert.get("source_model"),
            "trace_status": trace_status,
            "tail_status": tail_status,
        }

    if "threshold" not in cert:
        return Check("source_bound_numerics", "invalid", "source_bound_numerics.threshold is required"), None
    try:
        threshold = _frac(cert.get("threshold"), "source_bound_numerics.threshold")
    except ValueError as exc:
        return Check("source_bound_numerics", "invalid", str(exc)), None

    assert root is not None
    final_lower = root[0] - tau
    final_upper = root[1] + tau
    if final_upper < threshold:
        status = "pass"
        detail = f"source-bound outward upper={_fraction_text(final_upper)} < threshold={_fraction_text(threshold)}"
        classification = "STRICT_PASS"
    elif final_lower >= threshold:
        status = "fail"
        if final_lower == final_upper == threshold:
            detail = "exact source-bound value equals threshold; strict inequality is false"
            classification = "EXACT_BOUNDARY_FAIL"
        else:
            detail = f"source-bound lower={_fraction_text(final_lower)} >= threshold={_fraction_text(threshold)}"
            classification = "STRICT_FAIL"
    else:
        status = "open"
        detail = f"source-bound enclosure [{_fraction_text(final_lower)},{_fraction_text(final_upper)}] touches/crosses threshold={_fraction_text(threshold)}"
        classification = "INCOMPLETE_BOUNDARY"

    summary = {
        "protocol": SOURCE_BOUND_NUMERICS_PROTOCOL,
        "source_model": SOURCE_BOUND_SOURCE_MODEL,
        "proof_bearing": True,
        "root": cert.get("root"),
        "root_lower": _fraction_text(root[0]),
        "root_upper": _fraction_text(root[1]),
        "arithmetic_radius": _fraction_text((root[1] - root[0]) / 2),
        "tail_rule": cert.get("tail", {}).get("rule"),
        "analytic_tail": _fraction_text(tau),
        "final_lower": _fraction_text(final_lower),
        "final_upper": _fraction_text(final_upper),
        "threshold": _fraction_text(threshold),
        "classification": classification,
        "implementation_manifest_sha256": _implementation_fingerprint(),
        "external_source_boundary": "proof is for the declared exact-expression source model; mapping an external physical/backend quantity into those exact leaves remains a package/connector obligation",
    }
    return Check("source_bound_numerics", status, detail), summary


def _legacy_arithmetic_trust_gate(challenge: dict[str, Any], base_result: dict[str, Any]) -> Check | None:
    cert = challenge.get("arithmetic_certificate")
    if not isinstance(cert, dict):
        return None
    current = next((item for item in base_result.get("checks", []) if item.get("id") == "arithmetic_certificate"), None)
    if current is None or current.get("status") in {"invalid", "fail"}:
        return None
    kind = cert.get("kind")
    try:
        tail = _frac(cert.get("analytic_tail"), "arithmetic_certificate.analytic_tail")
    except ValueError:
        return None

    if kind in {"exact_rational", "exact_decimal"} and tail == 0:
        summary = base_result.get("arithmetic_summary")
        if isinstance(summary, dict):
            try:
                lower = _frac(summary.get("enclosure_lower"), "arithmetic_summary.enclosure_lower")
                upper = _frac(summary.get("enclosure_upper"), "arithmetic_summary.enclosure_upper")
                threshold = _frac(summary.get("threshold"), "arithmetic_summary.threshold")
            except ValueError:
                return None
            if lower == upper == threshold:
                return Check("arithmetic_certificate", "fail", "exact value equals threshold; strict upper-below-threshold claim is false")
        return None

    return Check(
        "arithmetic_certificate",
        "open",
        "legacy approximate radius/tail is not proof-bearing under Theorem 47; migrate to source_bound_numerics so the verifier derives the enclosure/tail from an admitted source trace",
    )


def _replace_check(checks: list[dict[str, Any]], check: Check | None) -> list[dict[str, Any]]:
    if check is None:
        return checks
    out = [item for item in checks if item.get("id") != check.id]
    out.append({"id": check.id, "status": check.status, "detail": check.detail})
    return out


def _recompute_result(mode: str, checks: list[dict[str, Any]]) -> str:
    statuses = [item.get("status") for item in checks]
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


def _final_genesis(original: dict[str, Any], base_result: dict[str, Any]) -> dict[str, Any]:
    contract = _canonicalize(dict(base_result["challenge_genesis"]["contract"]))
    contract["implementation_manifest_sha256"] = _implementation_fingerprint()
    contract["implementation_manifest_protocol"] = SOURCE_BOUND_NUMERICS_PROTOCOL
    if "source_bound_numerics" in original:
        contract["source_bound_numerics"] = _canonicalize(original.get("source_bound_numerics"))
    digest = _sha256(contract)
    return {
        "kind": "CHALLENGE_GENESIS",
        "hash_algorithm": "sha256",
        "genesis_hash": digest,
        "parent": None,
        "accepted_claims": 0,
        "rules_frozen": True,
        "meaning": "immutable rules plus parser/validator implementation fingerprint before candidate evaluation; no claim is accepted at genesis",
        "contract": contract,
    }


def _genesis_pin_check(original: dict[str, Any], genesis: dict[str, Any]) -> Check | None:
    pin = original.get("genesis")
    if pin is None:
        return None
    if not isinstance(pin, dict):
        return Check("genesis_integrity", "invalid", "genesis must be an object")
    expected = pin.get("expected_hash")
    if expected is None:
        return None
    if not isinstance(expected, str) or not _v5._v4._v3._HEX64.fullmatch(expected.strip()):
        return Check("genesis_integrity", "invalid", "genesis.expected_hash must be a 64-character SHA-256 hex digest")
    actual = genesis["genesis_hash"]
    if expected.strip().lower() == actual:
        return Check("genesis_integrity", "pass", actual)
    return Check("genesis_integrity", "fail", f"expected {expected.strip().lower()}, computed {actual}")


def evaluate_challenge(challenge: Any) -> dict[str, Any]:
    if not isinstance(challenge, dict):
        return _v5.evaluate_challenge(challenge)

    original = dict(challenge)
    base_input = dict(original)
    base_input.pop("genesis", None)
    base_result = _v5.evaluate_challenge(base_input)
    if base_result.get("challenge_genesis") is None:
        return base_result

    checks = [item for item in base_result.get("checks", []) if item.get("id") != "genesis_integrity"]
    checks = _replace_check(checks, _legacy_arithmetic_trust_gate(original, base_result))
    source_check, source_summary = _source_bound_check(original)
    checks = _replace_check(checks, source_check)

    genesis = _final_genesis(original, base_result)
    checks = _replace_check(checks, _genesis_pin_check(original, genesis))
    result_name = _recompute_result(base_result.get("mode"), checks)

    if isinstance(base_result.get("arithmetic_summary"), dict) and any(
        item.get("id") == "arithmetic_certificate" and item.get("status") == "open"
        for item in checks
    ):
        base_result["arithmetic_summary"] = {
            **base_result["arithmetic_summary"],
            "proof_bearing": False,
            "trust_status": "INCOMPLETE_SOURCE_VALIDATION",
        }

    base_result.update({
        "result": result_name,
        "formal_promotion": result_name == "CERTIFIED",
        "challenge_genesis": genesis,
        "checks": checks,
        "open_obligations": [item["id"] for item in checks if item.get("status") == "open"],
        "failed_obligations": [item["id"] for item in checks if item.get("status") == "fail"],
        "blocked_obligations": [item["id"] for item in checks if item.get("status") == "blocked"],
        "invalid_contract_fields": [item["id"] for item in checks if item.get("status") == "invalid"],
        "not_in_scope": [item["id"] for item in checks if item.get("status") == "not_in_scope"],
        "source_bound_numerics_protocol": SOURCE_BOUND_NUMERICS_PROTOCOL,
        "source_bound_numerics_summary": source_summary,
        "implementation_manifest_sha256": _implementation_fingerprint(),
        "numeric_trust_boundary": "a participant-supplied approximate radius or analytic tail is non-proof-bearing unless an admitted source-bound validator derives it; exact rational/decimal singleton values with zero tail remain exact",
    })
    base_result["challenge_evaluation"] = _v5._v4._evaluation_record(original, base_result, genesis)
    return base_result


def capabilities() -> dict[str, Any]:
    base = _v5.capabilities()
    base.update({
        "source_bound_numerics_protocol": SOURCE_BOUND_NUMERICS_PROTOCOL,
        "source_bound_source_model": SOURCE_BOUND_SOURCE_MODEL,
        "source_bound_operations": sorted(ADMITTED_OPS),
        "source_bound_tail_rules": sorted(ADMITTED_TAIL_RULES),
        "source_bound_max_trace_nodes": MAX_TRACE_NODES,
        "legacy_approximate_arithmetic_without_source_proof": "INCOMPLETE",
        "proof_bearing_arithmetic_kinds": [
            "exact_rational_with_zero_tail",
            "exact_decimal_with_zero_tail",
            "source_bound_proof_carrying_numerics",
        ],
        "strict_exact_threshold_equality": "FAILED",
        "implementation_manifest_sha256": _implementation_fingerprint(),
        "implementation_fingerprint_scope": "strict_json + engine compatibility/current numerical layers + schema + package manifests",
    })
    return base
