#!/usr/bin/env python3
"""Proof-carrying numerical provenance gate for mathematical hallucination detection.

A mathematical result is treated as overclaimed when its numerical certainty is
stronger than the admitted source trace proves. Participant-supplied radii,
analytic tails, or backend labels do not validate themselves.
"""
from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from typing import Any

try:
    from . import engine_v5 as _v5
    from .engine_v5 import *  # noqa: F401,F403
except ImportError:
    import engine_v5 as _v5
    from engine_v5 import *  # noqa: F401,F403

ENGINE_VERSION = _v5.ENGINE_VERSION
SCHEMA_VERSION = _v5.SCHEMA_VERSION
PROOF_NUMERIC_PROTOCOL = "proof-carrying-numeric-closure-v1"
MATH_HALLUCINATION_CLASS = "formal_numeric_overclaim"
ADMITTED_OPS = {"add", "sub", "mul", "neg", "div"}


def _ftext(q: Fraction) -> str:
    return str(q.numerator) if q.denominator == 1 else f"{q.numerator}/{q.denominator}"


def _interval(node: dict[str, Any], field: str) -> tuple[Fraction, Fraction]:
    raw = node.get(field)
    if not isinstance(raw, list) or len(raw) != 2:
        raise ValueError(f"{field} must be [lower, upper]")
    lo = _v5._v4._fraction_scalar(raw[0], f"{field}[0]")
    hi = _v5._v4._fraction_scalar(raw[1], f"{field}[1]")
    if lo > hi:
        raise ValueError(f"{field} lower must not exceed upper")
    return lo, hi


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def _sub(a, b):
    return (a[0] - b[1], a[1] - b[0])


def _mul(a, b):
    vals = (a[0]*b[0], a[0]*b[1], a[1]*b[0], a[1]*b[1])
    return min(vals), max(vals)


def _neg(a):
    return -a[1], -a[0]


def _div(a, b):
    if b[0] <= 0 <= b[1]:
        raise ZeroDivisionError("denominator enclosure contains zero")
    rec = (Fraction(1, b[1]), Fraction(1, b[0]))
    if rec[0] > rec[1]:
        rec = rec[1], rec[0]
    return _mul(a, rec)


def _canonical_op(op: str, deps: list[tuple[Fraction, Fraction]]):
    if op == "add" and len(deps) == 2:
        return _add(deps[0], deps[1])
    if op == "sub" and len(deps) == 2:
        return _sub(deps[0], deps[1])
    if op == "mul" and len(deps) == 2:
        return _mul(deps[0], deps[1])
    if op == "neg" and len(deps) == 1:
        return _neg(deps[0])
    if op == "div" and len(deps) == 2:
        return _div(deps[0], deps[1])
    raise ValueError("unsupported operation or arity")


def _subset(inner, outer) -> bool:
    return outer[0] <= inner[0] and inner[1] <= outer[1]


def _geometric_tail(first: Fraction, ratio: Fraction) -> Fraction:
    if first < 0 or ratio < 0 or ratio >= 1:
        raise ValueError("geometric tail requires first>=0 and 0<=ratio<1")
    return first / (1 - ratio)


def _proof_numeric_check(challenge: dict[str, Any]) -> tuple[Check | None, dict[str, Any] | None]:
    cert = challenge.get("proof_carrying_numeric")
    if cert is None:
        # Legacy approximate arithmetic claims remain visible, but are no longer
        # allowed to self-promote in certified mode.
        arithmetic = challenge.get("arithmetic_certificate")
        if isinstance(arithmetic, dict):
            kind = arithmetic.get("kind")
            tail = arithmetic.get("analytic_tail")
            exact_zero_tail = kind in {"exact_rational", "exact_decimal"} and str(tail).strip() in {"0", "0.0", "0/1"}
            if not exact_zero_tail:
                return (
                    Check("proof_carrying_numeric", "open", "numerical radius/tail requires an admitted source-bound proof trace; participant assertion is not self-validating"),
                    {"protocol": PROOF_NUMERIC_PROTOCOL, "classification": "INCOMPLETE_NUMERIC_PROVENANCE", "proof_bearing": False},
                )
        return None, None
    if not isinstance(cert, dict):
        return Check("proof_carrying_numeric", "invalid", "proof_carrying_numeric must be an object"), None
    if cert.get("protocol", PROOF_NUMERIC_PROTOCOL) != PROOF_NUMERIC_PROTOCOL:
        return Check("proof_carrying_numeric", "invalid", "unsupported proof-carrying numeric protocol"), None
    if cert.get("source_complete") is not True:
        return (
            Check("proof_carrying_numeric", "open", "source completeness/no-blindness obligation is not closed"),
            {"protocol": PROOF_NUMERIC_PROTOCOL, "classification": "INCOMPLETE_BLIND_DEPENDENCY", "proof_bearing": False},
        )

    nodes = cert.get("nodes")
    root_id = cert.get("root")
    if not isinstance(nodes, list) or not nodes or not isinstance(root_id, str) or not root_id:
        return Check("proof_carrying_numeric", "invalid", "nodes and root are required"), None

    seen: dict[str, tuple[Fraction, Fraction]] = {}
    ids: set[str] = set()
    try:
        for index, node in enumerate(nodes):
            if not isinstance(node, dict):
                raise ValueError(f"nodes[{index}] must be an object")
            node_id = node.get("id")
            if not isinstance(node_id, str) or not node_id or node_id in ids:
                raise ValueError("node ids must be unique nonempty strings")
            ids.add(node_id)
            declared = _interval(node, "interval")
            kind = node.get("kind")
            if kind == "exact_contract":
                value = _v5._v4._fraction_scalar(node.get("value"), f"nodes[{index}].value")
                if not (declared[0] <= value <= declared[1]):
                    return Check("proof_carrying_numeric", "fail", "exact source value is outside declared enclosure"), None
            elif kind == "op":
                op = node.get("op")
                deps = node.get("deps")
                if op not in ADMITTED_OPS or not isinstance(deps, list) or any(dep not in seen for dep in deps):
                    raise ValueError("unsupported operation, missing dependency, forward dependency, or cycle")
                try:
                    computed = _canonical_op(op, [seen[dep] for dep in deps])
                except ZeroDivisionError:
                    return Check("proof_carrying_numeric", "fail", "division enclosure contains zero"), None
                if not _subset(computed, declared):
                    return Check("proof_carrying_numeric", "fail", "declared enclosure is narrower than verifier-computed enclosure"), None
            else:
                return (
                    Check("proof_carrying_numeric", "open", f"unsupported source class: {kind}"),
                    {"protocol": PROOF_NUMERIC_PROTOCOL, "classification": "INCOMPLETE_SOURCE_VALIDATION", "proof_bearing": False},
                )
            seen[node_id] = declared
    except ValueError as exc:
        return Check("proof_carrying_numeric", "invalid", str(exc)), None

    if root_id not in seen:
        return Check("proof_carrying_numeric", "invalid", "root does not resolve to a verified node"), None
    root = seen[root_id]

    tail_spec = cert.get("tail", {"rule": "zero"})
    if not isinstance(tail_spec, dict):
        return Check("proof_carrying_numeric", "invalid", "tail must be an object"), None
    rule = tail_spec.get("rule", "zero")
    try:
        if rule == "zero":
            tail = Fraction(0)
        elif rule == "geometric_tail":
            first = _v5._v4._fraction_scalar(tail_spec.get("first_omitted_upper"), "tail.first_omitted_upper")
            ratio = _v5._v4._fraction_scalar(tail_spec.get("ratio_upper"), "tail.ratio_upper")
            tail = _geometric_tail(first, ratio)
        else:
            return (
                Check("proof_carrying_numeric", "open", "tail rule is not admitted by this engine version"),
                {"protocol": PROOF_NUMERIC_PROTOCOL, "classification": "INCOMPLETE_TAIL_VALIDATION", "proof_bearing": False},
            )
        threshold = _v5._v4._fraction_scalar(cert.get("threshold"), "proof_carrying_numeric.threshold")
    except ValueError as exc:
        return Check("proof_carrying_numeric", "invalid", str(exc)), None

    final_lower = root[0] - tail
    final_upper = root[1] + tail
    if final_upper < threshold:
        status = "pass"
        classification = "CERTIFIED_NUMERIC_CLOSURE"
        detail = f"source-bound outward upper={_ftext(final_upper)} < threshold={_ftext(threshold)}"
    elif final_lower >= threshold:
        status = "fail"
        classification = "STRICT_CLAIM_FALSE"
        detail = f"source-bound lower={_ftext(final_lower)} >= threshold={_ftext(threshold)}"
    else:
        status = "open"
        classification = "INCOMPLETE_THRESHOLD_CONTACT"
        detail = "verified enclosure touches/crosses the strict threshold with unresolved uncertainty"

    summary = {
        "protocol": PROOF_NUMERIC_PROTOCOL,
        "hallucination_class": MATH_HALLUCINATION_CLASS,
        "classification": classification,
        "proof_bearing": status == "pass",
        "root_interval": [_ftext(root[0]), _ftext(root[1])],
        "analytic_tail": _ftext(tail),
        "final_interval": [_ftext(final_lower), _ftext(final_upper)],
        "threshold": _ftext(threshold),
    }
    return Check("proof_carrying_numeric", status, detail), summary


def _implementation_manifest_hash() -> str:
    manifest = {
        "protocol": PROOF_NUMERIC_PROTOCOL,
        "hallucination_class": MATH_HALLUCINATION_CLASS,
        "source_classes": ["exact_contract"],
        "operations": sorted(ADMITTED_OPS),
        "tail_rules": ["zero", "geometric_tail"],
        "strict_boundary": "exact/verified enclosure semantics",
    }
    return hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _extended_genesis(challenge: dict[str, Any], base_result: dict[str, Any]) -> dict[str, Any]:
    if "proof_carrying_numeric" not in challenge:
        return base_result["challenge_genesis"]
    contract = _v5._v4._canonicalize(dict(base_result["challenge_genesis"]["contract"]))
    contract["proof_carrying_numeric_protocol"] = PROOF_NUMERIC_PROTOCOL
    contract["proof_carrying_numeric"] = _v5._v4._canonicalize(challenge.get("proof_carrying_numeric"))
    contract["numeric_validator_manifest_sha256"] = _implementation_manifest_hash()
    digest = _v5._v4._sha256(contract)
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


def evaluate_challenge(challenge: Any) -> dict[str, Any]:
    if not isinstance(challenge, dict):
        return _v5.evaluate_challenge(challenge)
    base_result = _v5.evaluate_challenge(challenge)
    if base_result.get("challenge_genesis") is None:
        return base_result

    checks = [item for item in base_result.get("checks", []) if item.get("id") not in {"genesis_integrity", "proof_carrying_numeric"}]
    proof_check, proof_summary = _proof_numeric_check(challenge)
    if proof_check is not None:
        checks = _v5._replace_check(checks, proof_check)

    genesis = _extended_genesis(challenge, base_result)
    checks = _v5._replace_check(checks, _v5._genesis_pin_check(challenge, genesis))
    result_name = _v5._recompute_result(base_result.get("mode"), checks)
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
        "proof_carrying_numeric_protocol": PROOF_NUMERIC_PROTOCOL,
        "math_hallucination_class": MATH_HALLUCINATION_CLASS,
        "proof_carrying_numeric_summary": proof_summary,
        "numeric_validator_manifest_sha256": _implementation_manifest_hash(),
    })
    base_result["challenge_evaluation"] = _v5._v4._evaluation_record(challenge, base_result, genesis)
    return base_result


def capabilities() -> dict[str, Any]:
    base = _v5.capabilities()
    base.update({
        "proof_carrying_numeric_protocol": PROOF_NUMERIC_PROTOCOL,
        "math_hallucination_numeric_class": MATH_HALLUCINATION_CLASS,
        "proof_carrying_numeric_source_classes": ["exact_contract"],
        "proof_carrying_numeric_operations": sorted(ADMITTED_OPS),
        "proof_carrying_numeric_tail_rules": ["zero", "geometric_tail"],
        "participant_asserted_radius_or_tail": "INCOMPLETE unless source-bound validator closes",
        "numeric_validator_manifest_sha256": _implementation_manifest_hash(),
    })
    return base
