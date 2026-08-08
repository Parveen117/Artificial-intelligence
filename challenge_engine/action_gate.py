#!/usr/bin/env python3
"""RNKE Proof-Before-Action authorization gate.

The model or agent may propose an action, but only an independently closed
capability/delegation contract may authorize execution. Natural-language
content is intentionally not an authority source in this protocol.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

PROTOCOL = "proof-before-action-v1"
MAX_DELEGATION_DEPTH = 16


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def action_sha256(action: dict[str, Any]) -> str:
    """Hash the exact executable action, including parameters."""
    return _sha256(action)


def validator_manifest_sha256() -> str:
    return _sha256({
        "protocol": PROTOCOL,
        "max_delegation_depth": MAX_DELEGATION_DEPTH,
        "authority_source": "declared capability/delegation chain only",
        "natural_language_authority": False,
        "grant_binding": ["tool", "operation", "resource", "action_sha256"],
        "state_checks": ["epoch", "revocation", "request_nonce_replay"],
        "confirmation_binding": ["approver", "action_sha256", "request_nonce"],
        "decision_states": ["ADMIT", "REJECT", "INCOMPLETE", "INVALID"],
    })


def _check(checks: list[dict[str, str]], check_id: str, status: str, detail: str) -> None:
    checks.append({"id": check_id, "status": status, "detail": detail})


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(_nonempty_string(x) for x in value) and len(set(value)) == len(value)


def _valid_epoch(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _decision(checks: list[dict[str, str]]) -> str:
    statuses = {x["status"] for x in checks}
    if "invalid" in statuses:
        return "INVALID"
    if "fail" in statuses:
        return "REJECT"
    if "open" in statuses:
        return "INCOMPLETE"
    return "ADMIT"


def evaluate_action_authorization(contract: Any) -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    if not isinstance(contract, dict):
        _check(checks, "contract", "invalid", "action_authorization must be an object")
        return _summary(None, checks)

    protocol = contract.get("protocol", PROTOCOL)
    if protocol != PROTOCOL:
        _check(checks, "protocol", "invalid", f"unsupported protocol: {protocol}")
    else:
        _check(checks, "protocol", "pass", PROTOCOL)

    principal = contract.get("principal")
    agent = contract.get("agent")
    if not _nonempty_string(principal):
        _check(checks, "principal", "invalid", "principal must be a non-empty string")
    else:
        _check(checks, "principal", "pass", principal)
    if not _nonempty_string(agent):
        _check(checks, "agent", "invalid", "agent must be a non-empty string")
    else:
        _check(checks, "agent", "pass", agent)

    action = contract.get("action")
    action_hash: str | None = None
    if not isinstance(action, dict):
        _check(checks, "action", "invalid", "action must be an object")
    else:
        bad = [k for k in ("tool", "operation", "resource") if not _nonempty_string(action.get(k))]
        if bad:
            _check(checks, "action", "invalid", f"action fields must be non-empty strings: {','.join(bad)}")
        elif "parameters" in action and not isinstance(action.get("parameters"), dict):
            _check(checks, "action", "invalid", "action.parameters must be an object when present")
        else:
            normalized_action = dict(action)
            normalized_action.setdefault("parameters", {})
            try:
                action_hash = action_sha256(normalized_action)
            except (TypeError, ValueError):
                _check(checks, "action", "invalid", "action must be canonical JSON without NaN/Infinity")
            else:
                action = normalized_action
                _check(checks, "action", "pass", f"exact action bound by sha256:{action_hash}")

    request_nonce = contract.get("request_nonce")
    if not _nonempty_string(request_nonce):
        _check(checks, "request_nonce", "invalid", "request_nonce must be a non-empty string")
    else:
        _check(checks, "request_nonce", "pass", request_nonce)

    state = contract.get("committed_state")
    epoch: int | None = None
    revoked: list[str] = []
    used_nonces: list[str] = []
    if not isinstance(state, dict):
        _check(checks, "committed_state", "invalid", "committed_state must be an object")
    else:
        epoch = state.get("epoch")
        if not _valid_epoch(epoch):
            _check(checks, "state_epoch", "invalid", "committed_state.epoch must be a nonnegative integer")
        else:
            _check(checks, "state_epoch", "pass", str(epoch))
        revoked = state.get("revoked_grant_ids", [])
        used_nonces = state.get("used_request_nonces", [])
        if not _string_list(revoked):
            _check(checks, "revocation_state", "invalid", "revoked_grant_ids must be a duplicate-free string list")
            revoked = []
        else:
            _check(checks, "revocation_state", "pass", f"revoked={len(revoked)}")
        if not _string_list(used_nonces):
            _check(checks, "replay_state", "invalid", "used_request_nonces must be a duplicate-free string list")
            used_nonces = []
        elif _nonempty_string(request_nonce) and request_nonce in used_nonces:
            _check(checks, "replay_guard", "fail", "request nonce already committed; replay rejected")
        else:
            _check(checks, "replay_guard", "pass", "request nonce is fresh in committed state")

    delegations = contract.get("delegations")
    terminal_id = contract.get("terminal_grant_id")
    grant_map: dict[str, dict[str, Any]] = {}
    structurally_valid = True
    if not isinstance(delegations, list) or not delegations:
        _check(checks, "delegations", "open", "at least one capability delegation is required")
        structurally_valid = False
    else:
        for i, grant in enumerate(delegations):
            if not isinstance(grant, dict):
                _check(checks, f"grant:{i}", "invalid", "grant must be an object")
                structurally_valid = False
                continue
            gid = grant.get("id")
            if not _nonempty_string(gid) or gid in grant_map:
                _check(checks, f"grant:{i}", "invalid", "grant id must be unique and non-empty")
                structurally_valid = False
                continue
            required_strings = ("issuer", "subject", "tool", "operation", "resource", "action_sha256")
            if any(not _nonempty_string(grant.get(k)) for k in required_strings):
                _check(checks, f"grant:{gid}", "invalid", "grant identity/scope/hash fields must be non-empty strings")
                structurally_valid = False
                continue
            parent_id = grant.get("parent_id")
            if parent_id is not None and not _nonempty_string(parent_id):
                _check(checks, f"grant:{gid}", "invalid", "parent_id must be null or a non-empty string")
                structurally_valid = False
                continue
            vf, vu = grant.get("valid_from_epoch"), grant.get("valid_until_epoch")
            if not _valid_epoch(vf) or not _valid_epoch(vu) or vf > vu:
                _check(checks, f"grant:{gid}", "invalid", "grant validity epochs must satisfy 0 <= from <= until")
                structurally_valid = False
                continue
            grant_map[gid] = grant
        if structurally_valid:
            _check(checks, "delegations", "pass", f"declared_grants={len(grant_map)}")

    if not _nonempty_string(terminal_id):
        _check(checks, "terminal_grant", "open", "terminal_grant_id is required")
    elif terminal_id not in grant_map:
        _check(checks, "terminal_grant", "open", "terminal_grant_id does not resolve")
    elif structurally_valid and action_hash is not None and _nonempty_string(principal) and _nonempty_string(agent) and epoch is not None:
        chain: list[dict[str, Any]] = []
        seen: set[str] = set()
        cursor = terminal_id
        chain_error: tuple[str, str] | None = None
        while cursor is not None:
            if cursor in seen:
                chain_error = ("invalid", "delegation cycle detected")
                break
            if len(chain) >= MAX_DELEGATION_DEPTH:
                chain_error = ("invalid", f"delegation depth exceeds {MAX_DELEGATION_DEPTH}")
                break
            grant = grant_map.get(cursor)
            if grant is None:
                chain_error = ("fail", f"missing parent grant: {cursor}")
                break
            seen.add(cursor)
            chain.append(grant)
            cursor = grant.get("parent_id")
        chain.reverse()

        if chain_error:
            _check(checks, "delegation_chain", chain_error[0], chain_error[1])
        elif not chain:
            _check(checks, "delegation_chain", "open", "no terminal delegation chain")
        else:
            root = chain[0]
            if root.get("parent_id") is not None or root.get("issuer") != principal:
                _check(checks, "delegation_root", "fail", "root grant must be issued directly by the declared principal")
            else:
                _check(checks, "delegation_root", "pass", principal)

            chain_ok = True
            for idx, grant in enumerate(chain):
                gid = grant["id"]
                if idx > 0:
                    parent = chain[idx - 1]
                    if grant.get("parent_id") != parent.get("id") or grant.get("issuer") != parent.get("subject"):
                        _check(checks, f"delegation_link:{gid}", "fail", "delegation issuer/parent continuity broken")
                        chain_ok = False
                    else:
                        _check(checks, f"delegation_link:{gid}", "pass", "issuer follows parent subject")
                scope_matches = (
                    grant.get("tool") == action.get("tool")
                    and grant.get("operation") == action.get("operation")
                    and grant.get("resource") == action.get("resource")
                    and grant.get("action_sha256") == action_hash
                )
                if not scope_matches:
                    _check(checks, f"grant_binding:{gid}", "fail", "grant does not bind the exact proposed action")
                    chain_ok = False
                else:
                    _check(checks, f"grant_binding:{gid}", "pass", "exact action binding closed")
                if gid in revoked:
                    _check(checks, f"grant_revocation:{gid}", "fail", "grant is revoked in committed state")
                    chain_ok = False
                else:
                    _check(checks, f"grant_revocation:{gid}", "pass", "grant not revoked")
                if not (grant["valid_from_epoch"] <= epoch <= grant["valid_until_epoch"]):
                    _check(checks, f"grant_epoch:{gid}", "fail", "grant is outside its committed validity epoch")
                    chain_ok = False
                else:
                    _check(checks, f"grant_epoch:{gid}", "pass", "grant valid at committed epoch")
            if chain[-1].get("subject") != agent:
                _check(checks, "terminal_subject", "fail", "terminal grant does not authorize the declared agent")
                chain_ok = False
            else:
                _check(checks, "terminal_subject", "pass", agent)
            _check(checks, "delegation_chain", "pass" if chain_ok else "fail", f"depth={len(chain)}")

    confirmation_required = contract.get("confirmation_required", False)
    if not isinstance(confirmation_required, bool):
        _check(checks, "confirmation_policy", "invalid", "confirmation_required must be Boolean")
    elif not confirmation_required:
        _check(checks, "confirmation_policy", "pass", "no separate confirmation required by declared contract")
    else:
        approval = contract.get("approval")
        if not isinstance(approval, dict):
            _check(checks, "human_confirmation", "open", "exact-action human confirmation is required")
        elif action_hash is None or not _nonempty_string(request_nonce) or not _nonempty_string(principal):
            _check(checks, "human_confirmation", "open", "cannot validate approval until action/principal/nonce close")
        else:
            ok = (
                approval.get("status") == "approved"
                and approval.get("approver") == principal
                and approval.get("action_sha256") == action_hash
                and approval.get("request_nonce") == request_nonce
            )
            if ok:
                _check(checks, "human_confirmation", "pass", "approval is bound to principal, exact action, and request nonce")
            else:
                _check(checks, "human_confirmation", "fail", "approval does not bind the exact proposed action/principal/nonce")

    return _summary(action_hash, checks)


def _summary(action_hash: str | None, checks: list[dict[str, str]]) -> dict[str, Any]:
    decision = _decision(checks)
    return {
        "protocol": PROTOCOL,
        "decision": decision,
        "executable": decision == "ADMIT",
        "action_sha256": action_hash,
        "checks": checks,
        "open_obligations": [x["id"] for x in checks if x["status"] == "open"],
        "failed_obligations": [x["id"] for x in checks if x["status"] == "fail"],
        "invalid_fields": [x["id"] for x in checks if x["status"] == "invalid"],
        "validator_manifest_sha256": validator_manifest_sha256(),
        "authority_rule": "Natural-language content may propose an action but cannot enlarge authority.",
    }
