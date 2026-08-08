#!/usr/bin/env python3
"""Morphism-first Dynamic RNKE transition primitives.

The native verified object is an admissible morphism ``a: x -> y``. A notation
such as ``S_t -> S_{t+1}``, a timestamp, epoch, block height, JSON object, basis,
or database row is a presentation of that morphism, not its primitive identity.

Recognition prepares a representation-bound transition certificate. A stateful
connector may then realize that admitted morphism by an atomic compare-and-swap
(CAS) from the certified source-state representation to the certified target
representation. A clock is not required by this module.

Base/presentation independence is not inferred from canonical JSON. It requires
a separately declared covariance/faithfulness adapter proving that two
presentations represent the same native morphism. Canonical JSON supplies only
deterministic serialization inside this connector presentation.

The in-memory store below is a deterministic test/reference connector. It is
not a distributed database or production persistence layer.
"""
from __future__ import annotations

import copy
import hashlib
import json
import string
import threading
from typing import Any

PROTOCOL = "dynamic-rnke-transition-v1"
NATIVE_PRIMITIVE = "admissible_morphism"
COMMIT_MODE = "compare_and_swap"
ACCEPTING_RESULTS = {"OBSERVED", "ADVERSARIAL_PASS", "CERTIFIED"}
_HEX = set(string.hexdigits)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_json(value: Any) -> str:
    """Deterministic hash for this JSON presentation, not a universal native identity."""
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _is_hex64(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in _HEX for ch in value)


def validator_manifest_sha256() -> str:
    return sha256_json({
        "protocol": PROTOCOL,
        "native_primitive": NATIVE_PRIMITIVE,
        "clock_required": False,
        "commit_mode": COMMIT_MODE,
        "recognition_rule": "every mandatory factor closes; endpoint or local closure cannot cancel an open factor",
        "state_rule": "mutable state is evaluation lineage, not a frozen Genesis rule",
        "presentation_rule": "state hashes and CAS are connector representations of the admitted morphism",
        "base_independence_rule": "cross-presentation invariance requires a declared covariance/faithfulness adapter",
        "serialization_rule": "canonical JSON gives deterministic bytes only; it is not a proof of coordinate independence",
        "atomicity_rule": "commit iff current_state_hash equals certified source-state representation hash",
        "certificate_rule": "connector must pin the exact transition certificate digest emitted by RNKE evaluation",
        "replay_rule": "successful CAS changes state representation, so a duplicate certificate becomes stale",
        "decision_states": ["ADMIT", "REJECT", "INCOMPLETE", "INVALID"],
    })


def _recognition_decision(result: str) -> str:
    if result in ACCEPTING_RESULTS:
        return "ADMIT"
    if result == "INCOMPLETE":
        return "INCOMPLETE"
    if result == "INVALID":
        return "INVALID"
    return "REJECT"


def prepare_dynamic_transition(
    *,
    state_before: Any,
    state_after: Any,
    transition_id: Any,
    payload_sha256: Any,
    genesis_hash: Any,
    recognition_result: str,
) -> dict[str, Any]:
    """Prepare one morphism realization after recognition, without committing it.

    ``state_before`` and ``state_after`` are connector presentations of the
    source and target of the arrow. No time coordinate is required.
    """
    errors: list[str] = []
    if not isinstance(state_before, dict):
        errors.append("state_before must be an object")
    if not isinstance(state_after, dict):
        errors.append("state_after must be an object")
    if not isinstance(transition_id, str) or not transition_id.strip():
        errors.append("transition_id must be a non-empty string")
    if not _is_hex64(payload_sha256):
        errors.append("payload_sha256 must be a 64-character hexadecimal digest")
    if not _is_hex64(genesis_hash):
        errors.append("genesis_hash must be a 64-character hexadecimal digest")

    if errors:
        return {
            "protocol": PROTOCOL,
            "native_primitive": NATIVE_PRIMITIVE,
            "clock_required": False,
            "decision": "INVALID",
            "commit_ready": False,
            "atomic_commit_required": True,
            "commit_mode": COMMIT_MODE,
            "errors": errors,
            "validator_manifest_sha256": validator_manifest_sha256(),
        }

    decision = _recognition_decision(recognition_result)
    before_hash = sha256_json(state_before)
    after_hash = sha256_json(state_after) if decision == "ADMIT" else None
    certificate: dict[str, Any] = {
        "protocol": PROTOCOL,
        "native_primitive": NATIVE_PRIMITIVE,
        "clock_required": False,
        "presentation_scope": "connector_json_state_v1",
        "base_independence_status": "representation_bound_unless_covariance_adapter_closes",
        "decision": decision,
        "commit_ready": decision == "ADMIT",
        "atomic_commit_required": True,
        "commit_mode": COMMIT_MODE,
        "transition_id": transition_id,
        "payload_sha256": payload_sha256.lower(),
        "genesis_hash": genesis_hash.lower(),
        "recognition_result": recognition_result,
        "source_state_representation_sha256": before_hash,
        "target_state_representation_sha256": after_hash,
        # Backward-compatible aliases used by the CAS reference connector.
        "state_before_sha256": before_hash,
        "state_after_sha256": after_hash,
        "state_after": copy.deepcopy(state_after) if decision == "ADMIT" else None,
        "validator_manifest_sha256": validator_manifest_sha256(),
    }
    certificate["certificate_sha256"] = sha256_json(certificate)
    return certificate


def prepare_agent_action_transition(
    action_authorization: Any,
    action_summary: Any,
    *,
    global_result: str,
    genesis_hash: str,
) -> dict[str, Any]:
    """Derive the morphism realization for ``proof-before-action-v1``.

    A successful action consumes its request nonce in the target state. This
    turns replay resistance into state evolution. The state update must still be
    CAS committed by the connector before the external side effect is released.

    The committed epoch used by the authorization contract is semantic state
    when grant validity depends on it. It is therefore not treated as a removable
    clock coordinate merely because it resembles time.
    """
    if not isinstance(action_authorization, dict) or not isinstance(action_summary, dict):
        return prepare_dynamic_transition(
            state_before={}, state_after={}, transition_id="invalid",
            payload_sha256="0" * 64, genesis_hash=genesis_hash,
            recognition_result="INVALID",
        )

    state_before = action_authorization.get("committed_state")
    nonce = action_authorization.get("request_nonce")
    payload_hash = action_summary.get("action_sha256")
    if not isinstance(state_before, dict):
        state_before = {}
    state_after = copy.deepcopy(state_before)

    used = state_after.get("used_request_nonces", [])
    if not isinstance(used, list):
        used = []
    if isinstance(nonce, str) and nonce and nonce not in used:
        used = list(used) + [nonce]
    state_after["used_request_nonces"] = used

    local_decision = action_summary.get("decision")
    effective_result = global_result
    if local_decision == "INCOMPLETE" and global_result in ACCEPTING_RESULTS:
        effective_result = "INCOMPLETE"
    elif local_decision in {"REJECT", "INVALID"} and global_result in ACCEPTING_RESULTS:
        effective_result = "FAILED" if local_decision == "REJECT" else "INVALID"

    return prepare_dynamic_transition(
        state_before=state_before,
        state_after=state_after,
        transition_id=nonce,
        payload_sha256=payload_hash,
        genesis_hash=genesis_hash,
        recognition_result=effective_result,
    )


class InMemoryAtomicStateStore:
    """Thread-safe reference CAS store for one connector presentation."""

    def __init__(self, initial_state: dict[str, Any]):
        if not isinstance(initial_state, dict):
            raise TypeError("initial_state must be an object")
        self._state = copy.deepcopy(initial_state)
        self._lock = threading.Lock()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._state)

    def state_sha256(self) -> str:
        with self._lock:
            return sha256_json(self._state)

    def compare_and_swap(self, expected_state_sha256: str, new_state: dict[str, Any]) -> bool:
        with self._lock:
            if sha256_json(self._state) != expected_state_sha256:
                return False
            self._state = copy.deepcopy(new_state)
            return True


def commit_prepared_transition(
    store: InMemoryAtomicStateStore,
    certificate: Any,
    expected_certificate_sha256: Any,
) -> dict[str, Any]:
    """Atomically realize exactly the morphism certificate emitted by RNKE.

    ``expected_certificate_sha256`` is supplied by the trusted evaluation /
    connector path. This prevents a caller from replacing the target-state
    presentation and presenting the replacement as the morphism RNKE admitted.
    """
    if not isinstance(certificate, dict):
        return {"status": "INVALID", "committed": False, "reason": "certificate must be an object"}
    if not _is_hex64(expected_certificate_sha256):
        return {"status": "INVALID", "committed": False, "reason": "expected certificate digest is required"}
    if certificate.get("protocol") != PROTOCOL or certificate.get("native_primitive") != NATIVE_PRIMITIVE:
        return {"status": "INVALID", "committed": False, "reason": "unsupported dynamic morphism protocol"}
    if certificate.get("clock_required") is not False:
        return {"status": "INVALID", "committed": False, "reason": "native transition certificate must not require an external clock"}
    if certificate.get("commit_mode") != COMMIT_MODE or certificate.get("atomic_commit_required") is not True:
        return {"status": "INVALID", "committed": False, "reason": "atomic CAS contract is not closed"}
    if certificate.get("validator_manifest_sha256") != validator_manifest_sha256():
        return {"status": "INVALID", "committed": False, "reason": "dynamic validator manifest mismatch"}

    supplied_digest = certificate.get("certificate_sha256")
    body = {key: value for key, value in certificate.items() if key != "certificate_sha256"}
    computed_digest = sha256_json(body)
    if supplied_digest != computed_digest:
        return {"status": "INVALID", "committed": False, "reason": "transition certificate self-hash mismatch"}
    if supplied_digest != str(expected_certificate_sha256).lower():
        return {"status": "INVALID", "committed": False, "reason": "transition certificate is not the RNKE-evaluated certificate"}

    if certificate.get("decision") != "ADMIT" or certificate.get("commit_ready") is not True:
        return {"status": "NOT_COMMITTABLE", "committed": False, "reason": "recognition did not admit transition"}
    state_after = certificate.get("state_after")
    if not isinstance(state_after, dict):
        return {"status": "INVALID", "committed": False, "reason": "missing state_after"}
    if sha256_json(state_after) != certificate.get("target_state_representation_sha256"):
        return {"status": "INVALID", "committed": False, "reason": "target-state representation hash mismatch"}
    if certificate.get("state_after_sha256") != certificate.get("target_state_representation_sha256"):
        return {"status": "INVALID", "committed": False, "reason": "target-state compatibility alias mismatch"}
    if certificate.get("state_before_sha256") != certificate.get("source_state_representation_sha256"):
        return {"status": "INVALID", "committed": False, "reason": "source-state compatibility alias mismatch"}

    committed = store.compare_and_swap(certificate.get("source_state_representation_sha256"), state_after)
    receipt = {
        "kind": "RNKE_DYNAMIC_COMMIT_RECEIPT",
        "protocol": PROTOCOL,
        "native_primitive": NATIVE_PRIMITIVE,
        "status": "COMMITTED" if committed else "STALE_STATE",
        "committed": committed,
        "transition_id": certificate.get("transition_id"),
        "certificate_sha256": supplied_digest,
        "source_state_representation_sha256": certificate.get("source_state_representation_sha256"),
        "target_state_representation_sha256": certificate.get("target_state_representation_sha256") if committed else store.state_sha256(),
        # Backward-compatible receipt aliases.
        "state_before_sha256": certificate.get("source_state_representation_sha256"),
        "state_after_sha256": certificate.get("target_state_representation_sha256") if committed else store.state_sha256(),
    }
    receipt["receipt_sha256"] = sha256_json(receipt)
    return receipt
