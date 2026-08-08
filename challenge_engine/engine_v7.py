#!/usr/bin/env python3
"""RNKE Proof-Before-Action gate for agentic execution.

This layer treats an LLM/tool call as a proposal, never as authority. Execution
is admitted only when the declared capability chain, exact action binding,
committed-state freshness, revocation state, and any required human approval
close under the proof-before-action-v1 protocol.
"""
from __future__ import annotations

from typing import Any

try:
    from . import engine_v6 as _v6
    from .engine_v6 import *  # noqa: F401,F403
    from .action_gate import (
        PROTOCOL as PROOF_BEFORE_ACTION_PROTOCOL,
        evaluate_action_authorization,
        validator_manifest_sha256 as action_validator_manifest_sha256,
    )
except ImportError:
    import engine_v6 as _v6
    from engine_v6 import *  # noqa: F401,F403
    from action_gate import (
        PROTOCOL as PROOF_BEFORE_ACTION_PROTOCOL,
        evaluate_action_authorization,
        validator_manifest_sha256 as action_validator_manifest_sha256,
    )

ENGINE_VERSION = _v6.ENGINE_VERSION
SCHEMA_VERSION = _v6.SCHEMA_VERSION
AGENT_ACTION_PACKAGE = "agent_action"


def _action_check(challenge: dict[str, Any], package_name: str | None):
    has_contract = "action_authorization" in challenge
    if package_name != AGENT_ACTION_PACKAGE and not has_contract:
        return None, None
    if not has_contract:
        return (
            _v6.Check(
                "proof_before_action",
                "open",
                "agent_action package requires an action_authorization contract; proposal alone cannot authorize execution",
            ),
            None,
        )

    summary = evaluate_action_authorization(challenge.get("action_authorization"))
    decision = summary.get("decision")
    if decision == "ADMIT":
        status = "pass"
        detail = "exact authority/evidence chain closed; action may cross the RNKE execution boundary"
    elif decision == "REJECT":
        status = "fail"
        detail = "authority/evidence chain failed; action is rejected"
    elif decision == "INCOMPLETE":
        status = "open"
        detail = "authority/evidence chain is incomplete; action is not executable"
    else:
        status = "invalid"
        detail = "malformed proof-before-action contract"
    return _v6.Check("proof_before_action", status, detail), summary


def _extended_genesis(challenge: dict[str, Any], base_result: dict[str, Any]) -> dict[str, Any]:
    package_name = base_result.get("package")
    if package_name != AGENT_ACTION_PACKAGE and "action_authorization" not in challenge:
        return base_result["challenge_genesis"]
    contract = _v6._v5._v4._canonicalize(dict(base_result["challenge_genesis"]["contract"]))
    contract["proof_before_action_protocol"] = PROOF_BEFORE_ACTION_PROTOCOL
    contract["action_authorization"] = _v6._v5._v4._canonicalize(challenge.get("action_authorization"))
    contract["action_validator_manifest_sha256"] = action_validator_manifest_sha256()
    digest = _v6._v5._v4._sha256(contract)
    return {
        "kind": "CHALLENGE_GENESIS",
        "hash_algorithm": "sha256",
        "genesis_hash": digest,
        "parent": None,
        "accepted_claims": 0,
        "rules_frozen": True,
        "meaning": "immutable rules of engagement before candidate evaluation; no claim or action is accepted at genesis",
        "contract": contract,
    }


def evaluate_challenge(challenge: Any) -> dict[str, Any]:
    if not isinstance(challenge, dict):
        return _v6.evaluate_challenge(challenge)
    base_result = _v6.evaluate_challenge(challenge)
    if base_result.get("challenge_genesis") is None:
        return base_result

    checks = [
        item for item in base_result.get("checks", [])
        if item.get("id") not in {"genesis_integrity", "proof_before_action"}
    ]
    action_check, action_summary = _action_check(challenge, base_result.get("package"))
    checks = _v6._v5._replace_check(checks, action_check)

    genesis = _extended_genesis(challenge, base_result)
    checks = _v6._v5._replace_check(checks, _v6._v5._genesis_pin_check(challenge, genesis))
    result_name = _v6._v5._recompute_result(base_result.get("mode"), checks)
    action_decision = action_summary.get("decision") if isinstance(action_summary, dict) else None

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
        "proof_before_action_protocol": PROOF_BEFORE_ACTION_PROTOCOL,
        "action_decision": action_decision,
        "action_executable": action_decision == "ADMIT",
        "action_authorization_summary": action_summary,
        "action_validator_manifest_sha256": action_validator_manifest_sha256(),
        "agent_authority_boundary": "Natural-language/model output may propose an action but cannot enlarge the frozen authority contract.",
    })
    base_result["challenge_evaluation"] = _v6._v5._v4._evaluation_record(challenge, base_result, genesis)
    return base_result


def capabilities() -> dict[str, Any]:
    base = _v6.capabilities()
    base.update({
        "proof_before_action_protocol": PROOF_BEFORE_ACTION_PROTOCOL,
        "agent_action_package": AGENT_ACTION_PACKAGE,
        "action_decisions": ["ADMIT", "REJECT", "INCOMPLETE", "INVALID"],
        "llm_output_authority": False,
        "action_authority_rule": "proposal != authority; exact authority closure is required before execution",
        "action_validator_manifest_sha256": action_validator_manifest_sha256(),
    })
    return base
