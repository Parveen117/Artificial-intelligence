#!/usr/bin/env python3
"""Dynamic RNKE integration layer.

The verified object is treated as a proposed state transition. Static Genesis
freezes rules/authority; mutable committed state belongs to evaluation lineage.
A locally admitted action is never executable when global RNKE closure fails.
A successful recognition prepares an atomic CAS transition certificate whose
state update must commit before an external side effect is released.
"""
from __future__ import annotations

from typing import Any

try:
    from . import engine_v7 as _v7
    from .engine_v7 import *  # noqa: F401,F403
    from .dynamic_transition import (
        PROTOCOL as DYNAMIC_TRANSITION_PROTOCOL,
        ACCEPTING_RESULTS,
        prepare_agent_action_transition,
        validator_manifest_sha256 as dynamic_validator_manifest_sha256,
    )
except ImportError:
    import engine_v7 as _v7
    from engine_v7 import *  # noqa: F401,F403
    from dynamic_transition import (
        PROTOCOL as DYNAMIC_TRANSITION_PROTOCOL,
        ACCEPTING_RESULTS,
        prepare_agent_action_transition,
        validator_manifest_sha256 as dynamic_validator_manifest_sha256,
    )

ENGINE_VERSION = _v7.ENGINE_VERSION
SCHEMA_VERSION = _v7.SCHEMA_VERSION
DYNAMIC_ACTION_FIELDS = {"action", "request_nonce", "approval", "proposal_context", "committed_state"}


def _dynamic_authority_declaration(action_authorization: Any) -> Any:
    """Freeze authority/rules while leaving S_t and candidate fields dynamic."""
    if not isinstance(action_authorization, dict):
        return action_authorization
    return {
        key: value
        for key, value in action_authorization.items()
        if key not in DYNAMIC_ACTION_FIELDS
    }


def _dynamic_genesis(challenge: dict[str, Any], base_result: dict[str, Any]) -> dict[str, Any]:
    """Rebuild Genesis so mutable state is not mistaken for a fixed rule."""
    if base_result.get("package") != _v7.AGENT_ACTION_PACKAGE and "action_authorization" not in challenge:
        return base_result["challenge_genesis"]

    canonicalize = _v7._v6._v5._v4._canonicalize
    sha256 = _v7._v6._v5._v4._sha256
    contract = canonicalize(dict(base_result["challenge_genesis"]["contract"]))
    contract["action_authority_rules"] = canonicalize(
        _dynamic_authority_declaration(challenge.get("action_authorization"))
    )
    contract["action_evaluation_fields"] = sorted(DYNAMIC_ACTION_FIELDS)
    contract["dynamic_transition_protocol"] = DYNAMIC_TRANSITION_PROTOCOL
    contract["dynamic_state_semantics"] = {
        "state_field": "action_authorization.committed_state",
        "state_is_genesis_rule": False,
        "commit_mode": "compare_and_swap",
        "external_side_effect_after_atomic_commit_only": True,
    }
    contract["dynamic_transition_validator_manifest_sha256"] = dynamic_validator_manifest_sha256()
    digest = sha256(contract)
    return {
        "kind": "CHALLENGE_GENESIS",
        "hash_algorithm": "sha256",
        "genesis_hash": digest,
        "parent": None,
        "accepted_claims": 0,
        "rules_frozen": True,
        "meaning": "immutable rules/authority before dynamic candidate evaluation; S_t and proposed transition remain lineage inputs",
        "contract": contract,
    }


def _extended_evaluation_record(
    challenge: dict[str, Any],
    result: dict[str, Any],
    genesis: dict[str, Any],
    dynamic_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    base = _v7._v6._v5._v4._evaluation_record(challenge, result, genesis)
    if not isinstance(dynamic_summary, dict):
        return base
    payload = {
        key: value
        for key, value in base.items()
        if key not in {"hash_algorithm", "evaluation_hash", "meaning"}
    }
    payload["dynamic_transition_certificate_sha256"] = dynamic_summary.get("certificate_sha256")
    digest = _v7._v6._v5._v4._sha256(payload)
    return {
        **payload,
        "hash_algorithm": "sha256",
        "evaluation_hash": digest,
        "meaning": "hash-bound evaluation outcome plus prepared dynamic transition under frozen rules and dynamic state lineage",
    }


def evaluate_challenge(challenge: Any) -> dict[str, Any]:
    if not isinstance(challenge, dict):
        return _v7.evaluate_challenge(challenge)

    base_result = _v7.evaluate_challenge(challenge)
    if base_result.get("challenge_genesis") is None:
        return base_result

    is_agent_action = base_result.get("package") == _v7.AGENT_ACTION_PACKAGE or "action_authorization" in challenge
    if not is_agent_action:
        return base_result

    # Re-evaluate the Genesis pin using dynamic semantics. The v7 pin included
    # committed_state in the frozen authority object, which is intentionally no
    # longer correct once S_t is a first-class dynamic object.
    checks = [
        item for item in base_result.get("checks", [])
        if item.get("id") != "genesis_integrity"
    ]
    genesis = _dynamic_genesis(challenge, base_result)
    genesis_check = _v7._v6._v5._genesis_pin_check(challenge, genesis)
    checks = _v7._v6._v5._replace_check(checks, genesis_check)
    result_name = _v7._v6._v5._recompute_result(base_result.get("mode"), checks)

    action_summary = base_result.get("action_authorization_summary")
    action_decision = base_result.get("action_decision")

    # Composition law: a local ADMIT never overrides failed global recognition.
    globally_closed = result_name in ACCEPTING_RESULTS
    recognition_executable = action_decision == "ADMIT" and globally_closed

    dynamic_summary = prepare_agent_action_transition(
        challenge.get("action_authorization"),
        action_summary,
        global_result=result_name,
        genesis_hash=genesis["genesis_hash"],
    )
    commit_ready = recognition_executable and dynamic_summary.get("commit_ready") is True

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
        "action_executable": recognition_executable,
        "dynamic_transition_protocol": DYNAMIC_TRANSITION_PROTOCOL,
        "dynamic_transition": dynamic_summary,
        "dynamic_commit_ready": commit_ready,
        "external_side_effect_ready": False,
        "dynamic_execution_rule": "recognition prepares transition; connector must atomically CAS S_t to S_{t+1} before releasing external side effect",
        "dynamic_composition_rule": "local ADMIT AND global RNKE closure are both necessary; failed global recognition cannot execute",
        "dynamic_state_rule": "committed_state is dynamic lineage, not a frozen Genesis rule",
        "dynamic_transition_validator_manifest_sha256": dynamic_validator_manifest_sha256(),
    })
    base_result["challenge_evaluation"] = _extended_evaluation_record(
        challenge, base_result, genesis, dynamic_summary
    )
    return base_result


def capabilities() -> dict[str, Any]:
    base = _v7.capabilities()
    base.update({
        "dynamic_transition_protocol": DYNAMIC_TRANSITION_PROTOCOL,
        "dynamic_state_object": "S_t -> S_{t+1}",
        "dynamic_genesis_rule": "freeze rules/authority; keep committed state in evaluation lineage",
        "dynamic_commit_mode": "compare_and_swap",
        "dynamic_atomicity_rule": "external side effect only after successful atomic state commit",
        "dynamic_composition_rule": "local ADMIT never overrides failed global recognition",
        "dynamic_transition_validator_manifest_sha256": dynamic_validator_manifest_sha256(),
    })
    return base
