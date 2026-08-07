#!/usr/bin/env python3
"""Theorem-46 exact finite-jet seam quotient adapter for Challenge Engine 1.2.0.

This layer deliberately implements only the proof-safe exact-polynomial subset
of the first-visible-jet seam quotient theorem. Raw algebraic division by zero
remains invalid. Approximate/remainder-bearing seam quotients are held open until
an admitted validator proves the required remainder and denominator-separation
bounds.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any

try:
    from . import engine_v4 as _v4
    from .engine_v4 import *  # noqa: F401,F403
except ImportError:
    import engine_v4 as _v4
    from engine_v4 import *  # noqa: F401,F403

ENGINE_VERSION = _v4.ENGINE_VERSION
SCHEMA_VERSION = _v4.SCHEMA_VERSION
SEAM_QUOTIENT_PROTOCOL = "first-visible-jet-seam-quotient-v1"


def _fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _parse_coefficients(values: Any, field: str) -> list[Fraction]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{field} must be a nonempty list")
    return [_v4._fraction_scalar(value, f"{field}[{i}]") for i, value in enumerate(values)]


def _first_visible(coefficients: list[Fraction]) -> int | None:
    for index, coefficient in enumerate(coefficients):
        if coefficient != 0:
            return index
    return None


def _seam_quotient_check(challenge: dict[str, Any]) -> tuple[Check | None, dict[str, Any] | None]:
    if "seam_quotient_certificate" not in challenge:
        return None, None

    cert = challenge.get("seam_quotient_certificate")
    if not isinstance(cert, dict):
        return Check("seam_quotient", "invalid", "seam_quotient_certificate must be an object"), None

    seam_id = cert.get("seam_id")
    if not isinstance(seam_id, str) or not seam_id.strip():
        return Check("seam_quotient", "invalid", "seam_id is required"), None

    relation = cert.get("relation", "finite_seam_quotient")
    if relation != "finite_seam_quotient":
        return Check("seam_quotient", "invalid", "only finite_seam_quotient is currently certified"), None

    model = cert.get("model")
    if model != "exact_polynomial_jet":
        return (
            Check(
                "seam_quotient",
                "open",
                "only exact_polynomial_jet is proof-bearing in this release; approximate/remainder-bearing seams require a validated Theorem-46 remainder adapter",
            ),
            {
                "protocol": SEAM_QUOTIENT_PROTOCOL,
                "seam_id": seam_id,
                "model": model,
                "classification": "INCOMPLETE_REMAINDER_VALIDATION",
                "proof_bearing": False,
            },
        )

    try:
        numerator = _parse_coefficients(cert.get("numerator_coefficients"), "seam_quotient_certificate.numerator_coefficients")
        denominator = _parse_coefficients(cert.get("denominator_coefficients"), "seam_quotient_certificate.denominator_coefficients")
    except ValueError as exc:
        return Check("seam_quotient", "invalid", str(exc)), None

    if numerator[0] != 0 or denominator[0] != 0:
        return (
            Check("seam_quotient", "invalid", "Theorem-46 seam quotient certificate is for a declared 0/0 endpoint; both constant coefficients must be zero"),
            None,
        )

    r_a = _first_visible(numerator)
    r_b = _first_visible(denominator)

    base_summary: dict[str, Any] = {
        "protocol": SEAM_QUOTIENT_PROTOCOL,
        "seam_id": seam_id,
        "model": model,
        "relation": relation,
        "numerator_order": r_a,
        "denominator_order": r_b,
        "proof_bearing": True,
    }

    if r_b is None:
        summary = {
            **base_summary,
            "classification": "INCOMPLETE_FLAT_OR_UNRESOLVED",
            "quotient": None,
            "proof_bearing": False,
        }
        return (
            Check(
                "seam_quotient",
                "open",
                "all declared denominator jets vanish; finite-jet theorem does not assign a quotient",
            ),
            summary,
        )

    if r_a is None:
        summary = {
            **base_summary,
            "classification": "FINITE_QUOTIENT_ZERO",
            "quotient": "0",
        }
        return Check("seam_quotient", "pass", "exact zero numerator polynomial over visible denominator gives seam quotient 0"), summary

    if r_a > r_b:
        summary = {
            **base_summary,
            "classification": "FINITE_QUOTIENT_ZERO",
            "quotient": "0",
        }
        return Check("seam_quotient", "pass", f"numerator first-visible order {r_a} exceeds denominator order {r_b}; seam quotient tends to 0"), summary

    if r_a < r_b:
        summary = {
            **base_summary,
            "classification": "DIVERGENT_NO_FINITE_QUOTIENT",
            "quotient": None,
        }
        return Check("seam_quotient", "fail", f"numerator first-visible order {r_a} is below denominator order {r_b}; no finite seam quotient exists"), summary

    leading_denominator = denominator[r_b]
    if leading_denominator == 0:
        return Check("seam_quotient", "invalid", "internal first-visible denominator invariant failed"), None

    quotient = numerator[r_a] / leading_denominator
    summary = {
        **base_summary,
        "classification": "FINITE_SEAM_QUOTIENT",
        "numerator_leading": _fraction_text(numerator[r_a]),
        "denominator_leading": _fraction_text(leading_denominator),
        "quotient": _fraction_text(quotient),
    }
    return (
        Check(
            "seam_quotient",
            "pass",
            f"common first-visible order {r_a}; exact seam quotient={_fraction_text(quotient)}",
        ),
        summary,
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


def _extended_genesis(challenge: dict[str, Any], base_result: dict[str, Any]) -> dict[str, Any]:
    if "seam_quotient_certificate" not in challenge:
        return base_result["challenge_genesis"]
    contract = _v4._canonicalize(dict(base_result["challenge_genesis"]["contract"]))
    contract["seam_quotient_protocol"] = SEAM_QUOTIENT_PROTOCOL
    contract["seam_quotient_certificate"] = _v4._canonicalize(challenge.get("seam_quotient_certificate"))
    digest = _v4._sha256(contract)
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
    if not isinstance(expected, str) or not _v4._v3._HEX64.fullmatch(expected.strip()):
        return Check("genesis_integrity", "invalid", "genesis.expected_hash must be a 64-character SHA-256 hex digest")
    actual = genesis["genesis_hash"]
    if expected.strip().lower() == actual:
        return Check("genesis_integrity", "pass", actual)
    return Check("genesis_integrity", "fail", f"expected {expected.strip().lower()}, computed {actual}")


def evaluate_challenge(challenge: Any) -> dict[str, Any]:
    if not isinstance(challenge, dict):
        return _v4.evaluate_challenge(challenge)

    base_result = _v4.evaluate_challenge(challenge)
    if base_result.get("challenge_genesis") is None:
        return base_result

    checks = [item for item in base_result.get("checks", []) if item.get("id") != "genesis_integrity"]
    seam_check, seam_summary = _seam_quotient_check(challenge)
    checks = _replace_check(checks, seam_check)

    genesis = _extended_genesis(challenge, base_result)
    checks = _replace_check(checks, _genesis_pin_check(challenge, genesis))
    result_name = _recompute_result(base_result.get("mode"), checks)

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
        "seam_quotient_protocol": SEAM_QUOTIENT_PROTOCOL,
        "seam_quotient_summary": seam_summary,
        "division_by_zero_boundary": "raw algebraic 1/0 and 0/0 are not assigned finite values; only a declared theorem-46 seam quotient can classify a vanishing-function ratio",
    })
    base_result["challenge_evaluation"] = _v4._evaluation_record(challenge, base_result, genesis)
    return base_result


def capabilities() -> dict[str, Any]:
    base = _v4.capabilities()
    base.update({
        "seam_quotient_protocol": SEAM_QUOTIENT_PROTOCOL,
        "seam_quotient_proof_bearing_model": "exact_polynomial_jet",
        "seam_quotient_approximate_model": "INCOMPLETE until a validated remainder/denominator-separation adapter is declared",
        "raw_division_by_zero": "INVALID / not redefined by seam quotient protocol",
    })
    return base
