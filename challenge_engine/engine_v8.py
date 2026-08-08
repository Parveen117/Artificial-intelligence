#!/usr/bin/env python3
"""Morphism-first Dynamic RNKE integration layer.

The native verified object is an admissible morphism ``a: x -> y``. A notation
such as ``S_t -> S_{t+1}`` is a connector presentation, not a required clocked
ontology. Static Genesis freezes rules, authority and comparison law; mutable
state and the candidate morphism belong to evaluation lineage.

A locally admitted action is never executable when global RNKE closure fails.
Successful recognition prepares an atomic connector realization whose state
update must commit before an external side effect is released.
"""
from __future__ import annotations

from typing import Any

try:
    from . import engine_v7 as _v7
    from .engine_v7 import *  # noqa: F401,F403
    from .dynamic_transition import (
        PROTOCOL as DYNAMIC_TRANSITION_PROTOCOL,
        NATIVE_PRIMITIVE,
        ACCEPTING_RESULTS,
        prepare_agent_action_transition,
        validator_manifest_sha256 as dynamic_validator_manifest_sha256,
    )
except ImportError:
    import engine_v7 as _v7
    from engine_v7 import *  # noqa: F401,F403
    from dynamic_transition import (
        PROTOCOL as DYNAMIC_TRANSITION_PROTOCOL,
        NATIVE_PRIMITIVE,
        ACCEPTING_RESULTS,
        prepare_agent_action_transition,
        validator_manifest_sha256 as dynamic_validator_manifest_sha256,
    )

ENGINE_VERSION = _v7.ENGINE_VERSION
SCHEMA_VERSION = _v7.SCHEMA_VERSION
MORPHISM_EVALUATION_FIELDS = {"action", "request_nonce", "approval", "proposal_context", "committed_state"}


def _morphic_authority_declaration(action_authorization: Any) -> Any:
    """Freeze authority/rules while leaving the candidate arrow and state dynamic."""
    if not isinstance(action_authorization, dict):
        return action_authorization
    return {
        key: value
        for key, value in action_authorization.items()
        if key not in MORPHISM_EVALUATION_FIELDS
    }


def _morphic_genesis(challenge: dict[str, Any], base_result: dict[str, Any]) -> dict[str, Any]:
    """Rebuild Genesis around morphism law rather than mutable state coordinates."""
    if base_result.get("package") != _v7.AGENT_ACTION_PACKAGE and "action_authorization" not in challenge:
        return base_result["challenge_genesis"]

    canonicalize = _v7._v6._v5._v4._canonicalize
    sha256 = _v7._v6._v5._v4._sha256
    contract = canonicalize(dict(base_result["challenge_genesis"]["contract"]))
    contract["native_transition_primitive"] = NATIVE_PRIMITIVE
    contract["external_clock_required"] = False
    contract["action_authority_rules"] = canonicalize(
        _morphic_authority_declaration(challenge.get("action_authorization"))
    )
    contract["morphism_evaluation_fields"] = sorted(MORPHISM_EVALUATION_FIELDS)
    # Compatibility alias for readers/clients of the first dynamic draft.
    contract["action_evaluation_fields"] = sorted(MORPHISM_EVALUATION_FIELDS)
    contract["dynamic_transition_protocol"] = DYNAMIC_TRANSITION_PROTOCOL
    contract["dynamic_state_semantics"] = {
        "native_object": "admissible morphism a:x->y",
        "connector_state_notation": "S_before -> S_after",
        "state_field": "action_authorization.committed_state",
        "state_is_genesis_rule": False,
        "clock_required": False,
        "commit_mode": "compare_and_swap",
        "external_side_effect_after_atomic_commit_only": True,
    }
    contract["presentation_covariance_semantics"] = {
        "canonical_json_is_base_independence": False,
        "canonical_json_role": "deterministic connector serialization",
        "cross_presentation_invariance_requires_adapter": True,
        "invariant_target": "recognition closure / residual under a proved covariance map",
    }
    contract["factorwise_closure_semantics"] = {
        "endpoint_only_closure_sufficient": False,
        "residue_cancellation_allowed_to_hide_failed_factor": False,
        "every_mandatory_factor_must_close": True,
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
        "meaning": "immutable recognition/authority/morphism law before candidate evaluation; clock labels and mutable state are presentation/lineage data",
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
    payload["native_transition_primitive"] = NATIVE_PRIMITIVE
    digest = _v7._v6._v5._v4._sha256(payload)
    return {
        **payload,
        "hash_algorithm": "sha256",
        "evaluation_hash": digest,
        "meaning": "hash-bound evaluation outcome plus connector realization of one admitted native morphism",
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

    # Re-evaluate the Genesis pin using morphism-first semantics. Mutable state
    # is lineage, not a fixed rule. A time-like field is not automatically a
    # removable clock: e.g. an authorization epoch is semantic if validity uses it.
    checks = [
        item for item in base_result.get("checks", [])
        if item.get("id") != "genesis_integrity"
    ]
    genesis = _morphic_genesis(challenge, base_result)
    genesis_check = _v7._v6._v5._genesis_pin_check(challenge, genesis)
    checks = _v7._v6._v5._replace_check(checks, genesis_check)
    result_name = _v7._v6._v5._recompute_result(base_result.get("mode"), checks)

    action_summary = base_result.get("action_authorization_summary")
    action_decision = base_result.get("action_decision")

    # RSC-style factorwise law: one closed factor cannot cancel another failed
    # mandatory factor. Local ADMIT never overrides failed global recognition.
    globally_closed = result_name in ACCEPTING_RESULTS
    recognition_executable = action_decision == "ADMIT" and globally_closed

    dynamic_summary = prepare_agent_action_transition(
        challenge.get("action_authorization"),
        action_summary,
        global_result=result_name,
        genesis_hash=genesis["genesis_hash"],
    )
    commit_ready = recognition_executable and dynamic_summary.get("commit_ready") is True

    unresolved_factor_ids = [
        x.get("id") for x in checks
        if x.get("status") in {"fail", "invalid", "open", "blocked"}
    ]

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
        "native_transition_primitive": NATIVE_PRIMITIVE,
        "external_clock_required": False,
        "action_executable": recognition_executable,
        "dynamic_transition_protocol": DYNAMIC_TRANSITION_PROTOCOL,
        "dynamic_transition": dynamic_summary,
        "dynamic_commit_ready": commit_ready,
        "external_side_effect_ready": False,
        "factorwise_closure": {
            "required": True,
            "closed": globally_closed,
            "unresolved_factor_ids": unresolved_factor_ids,
            "endpoint_cancellation_not_accepted": True,
        },
        "dynamic_execution_rule": "recognition admits a morphism; connector must atomically realize its certified source-to-target state update before external side effect",
        "dynamic_composition_rule": "every mandatory factor closes; local or endpoint closure cannot hide another failed residue",
        "dynamic_state_rule": "committed_state is a connector presentation in lineage, not the native morphism or a frozen Genesis rule",
        "clock_independence_rule": "the native morphism and closure do not require a clock; normalized rates or time labels are optional presentations",
        "base_independence_rule": "cross-presentation closure invariance requires a declared covariance/faithfulness adapter; canonical JSON alone is not base independence",
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
        "native_transition_primitive": NATIVE_PRIMITIVE,
        "external_clock_required": False,
        "connector_transition_presentation": "S_before -> S_after",
        "dynamic_genesis_rule": "freeze recognition/authority/morphism law; keep candidate and mutable state in evaluation lineage",
        "dynamic_commit_mode": "compare_and_swap",
        "dynamic_atomicity_rule": "external side effect only after successful atomic connector-state commit",
        "dynamic_composition_rule": "every mandatory factor closes; local ADMIT never overrides failed global recognition",
        "clock_independence_rule": "clock labels and normalized rates are optional presentations of an already-declared morphism",
        "base_independence_rule": "representation covariance must be proved by an adapter; deterministic JSON hashing is only serialization normalization",
        "dynamic_transition_validator_manifest_sha256": dynamic_validator_manifest_sha256(),
    })
    return base
