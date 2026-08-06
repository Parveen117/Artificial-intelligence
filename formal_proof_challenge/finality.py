#!/usr/bin/env python3
"""FPG2 public finality adapter for the Formal Proof Gate.

The adapter binds four separately verifiable objects:

1. FormalProofGate proof certificate.
2. ECL-style closure decision: COMMIT or REJECT.
3. IEL-style append-only audit transition with invariant information state.
4. SHA-256 receipt/chain binding with explicit tamper and replay checks.

It is deliberately a tamper-evident research adapter. It is not a digital
signature, trusted timestamp, identity proof, consensus protocol, or legal
notarization service.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import threading
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

ZERO_HASH = "0" * 64
VERSION = "1.0.0"
ECL_POLICY_ID = "formal-proof-gate-ecl-closure-policy-v1"
IEL_LEDGER_ID = "formal-proof-gate-iel-audit-ledger-v1"
CRYPTO_BINDING_ID = "formal-proof-gate-sha256-chain-v1"
_LEDGER_LOCK = threading.Lock()


@dataclass(frozen=True)
class ProofCertificateAudit:
    ok: bool
    status: str
    errors: Tuple[str, ...]
    claimed_hash: Optional[str]
    expected_hash: Optional[str]


@dataclass(frozen=True)
class ReceiptVerification:
    ok: bool
    status: str
    error_count: int
    errors: Tuple[str, ...]
    action: str
    receipt_hash: Optional[str]
    entry_hash: Optional[str]


@dataclass(frozen=True)
class LedgerVerification:
    ok: bool
    status: str
    checked: int
    error_count: int
    errors: Tuple[str, ...]
    last_entry_hash: str
    final_state: Optional[Dict[str, Any]]


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _mapping(value: Any) -> Dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return copy.deepcopy(dict(value))
    raise ValueError("value must be a dataclass or mapping")


def _is_hex64(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def _hash_without(payload: Mapping[str, Any], field: str) -> str:
    unsigned = copy.deepcopy(dict(payload))
    unsigned.pop(field, None)
    return digest(unsigned)


def audit_proof_certificate(certificate: Any) -> ProofCertificateAudit:
    errors: List[str] = []
    try:
        cert = _mapping(certificate)
    except ValueError as exc:
        return ProofCertificateAudit(False, "MALFORMED_PROOF_CERTIFICATE", (str(exc),), None, None)

    required = {
        "engine",
        "rule_set_id",
        "rule_set_hash",
        "proof_id",
        "proof_hash",
        "dependency_graph_hash",
        "admitted_syntax",
        "dependency_graph_acyclic",
        "all_steps_licensed",
        "target_match",
        "status",
        "error_count",
        "errors",
        "certificate_hash",
    }
    missing = sorted(required - set(cert))
    if missing:
        errors.append("PROOF_CERTIFICATE_FIELDS_MISSING:" + ",".join(missing))

    claimed = cert.get("certificate_hash")
    expected = _hash_without(cert, "certificate_hash") if not missing else None
    if not _is_hex64(claimed):
        errors.append("PROOF_CERTIFICATE_HASH_FORMAT_INVALID")
    elif expected != claimed:
        errors.append("PROOF_CERTIFICATE_HASH_MISMATCH")

    status = str(cert.get("status", "UNKNOWN"))
    raw_errors = cert.get("errors", ())
    if not isinstance(raw_errors, (list, tuple)):
        errors.append("PROOF_CERTIFICATE_ERRORS_MALFORMED")
        raw_errors = ()
    try:
        declared_error_count = int(cert.get("error_count", -1))
    except (TypeError, ValueError):
        declared_error_count = -1
        errors.append("PROOF_CERTIFICATE_ERROR_COUNT_MALFORMED")
    if declared_error_count != len(raw_errors):
        errors.append("PROOF_CERTIFICATE_ERROR_COUNT_MISMATCH")

    if status == "VALID_PROOF":
        closure_flags = (
            cert.get("admitted_syntax") is True,
            cert.get("dependency_graph_acyclic") is True,
            cert.get("all_steps_licensed") is True,
            cert.get("target_match") is True,
            len(raw_errors) == 0,
        )
        if not all(closure_flags):
            errors.append("VALID_STATUS_WITH_OPEN_PROOF_OBLIGATION")
    elif status != "REJECTED":
        errors.append("UNKNOWN_PROOF_STATUS")

    return ProofCertificateAudit(
        ok=not errors,
        status="VALID_PROOF_CERTIFICATE" if not errors else "INVALID_PROOF_CERTIFICATE",
        errors=tuple(errors),
        claimed_hash=str(claimed) if claimed is not None else None,
        expected_hash=expected,
    )


def _proof_error_codes(certificate: Mapping[str, Any]) -> Tuple[str, ...]:
    codes: List[str] = []
    raw_errors = certificate.get("errors", ())
    if isinstance(raw_errors, (list, tuple)):
        for error in raw_errors:
            if isinstance(error, Mapping):
                code = str(error.get("code", "UNKNOWN_REJECTION"))
            else:
                code = "MALFORMED_REJECTION"
            if code not in codes:
                codes.append(code)
    return tuple(codes)


def _ecl_policy_hash() -> str:
    return digest(
        {
            "policy_id": ECL_POLICY_ID,
            "commit_when": {
                "proof_certificate_audit": "ok",
                "status": "VALID_PROOF",
                "admitted_syntax": True,
                "dependency_graph_acyclic": True,
                "all_steps_licensed": True,
                "target_match": True,
                "error_count": 0,
            },
            "otherwise": "REJECT",
            "version": VERSION,
        }
    )


def build_ecl_decision(certificate: Any) -> Dict[str, Any]:
    cert = _mapping(certificate)
    audit = audit_proof_certificate(cert)
    proof_codes = list(_proof_error_codes(cert))
    proof_codes.extend(code for code in audit.errors if code not in proof_codes)

    try:
        error_count = int(cert.get("error_count", -1))
    except (TypeError, ValueError):
        error_count = -1
    closure_ready = bool(
        audit.ok
        and cert.get("status") == "VALID_PROOF"
        and cert.get("admitted_syntax") is True
        and cert.get("dependency_graph_acyclic") is True
        and cert.get("all_steps_licensed") is True
        and cert.get("target_match") is True
        and error_count == 0
    )
    action = "COMMIT" if closure_ready else "REJECT"
    classification = "FORMAL_PROOF_CLOSED" if closure_ready else "FORMAL_PROOF_OPEN_OR_INVALID"
    unsigned = {
        "version": VERSION,
        "engine": "FormalProofECLDecision",
        "policy_id": ECL_POLICY_ID,
        "policy_hash": _ecl_policy_hash(),
        "proof_certificate_hash": str(cert.get("certificate_hash", "")),
        "proof_id": str(cert.get("proof_id", "UNKNOWN")),
        "proof_status": str(cert.get("status", "UNKNOWN")),
        "proof_certificate_audit_ok": audit.ok,
        "closure_ready": closure_ready,
        "action": action,
        "classification": classification,
        "rejection_codes": tuple(proof_codes),
    }
    return {**unsigned, "decision_hash": digest(unsigned)}


def _invariant_hash(certificate: Mapping[str, Any], decision: Mapping[str, Any]) -> str:
    return digest(
        {
            "ledger_id": IEL_LEDGER_ID,
            "rule_set_id": certificate.get("rule_set_id"),
            "rule_set_hash": certificate.get("rule_set_hash"),
            "ecl_policy_hash": decision.get("policy_hash"),
            "version": VERSION,
        }
    )


def _entropy_delta(decision_hash: str, event_index: int) -> int:
    seed = digest({"decision_hash": decision_hash, "event_index": event_index, "ledger_id": IEL_LEDGER_ID})
    return 1 + (int(seed[-8:], 16) % 1_000_000)


def _genesis_state(invariant_hash: str) -> Dict[str, Any]:
    return {"I": invariant_hash, "E": 0, "theta": 0}


def _build_iel_entry(
    certificate: Mapping[str, Any],
    decision: Mapping[str, Any],
    previous_entry_hash: str,
    state_before: Mapping[str, Any],
) -> Dict[str, Any]:
    event_index = int(state_before["theta"]) + 1
    entropy_delta = _entropy_delta(str(decision["decision_hash"]), event_index)
    state_after = {
        "I": state_before["I"],
        "E": int(state_before["E"]) + entropy_delta,
        "theta": event_index,
    }
    payload_hash = digest({"proof_certificate": certificate, "ecl_decision": decision})
    unsigned = {
        "version": VERSION,
        "engine": "FormalProofIELAudit",
        "ledger_id": IEL_LEDGER_ID,
        "event_index": event_index,
        "audit_event": "FORMAL_PROOF_CLOSURE_DECISION",
        "proof_id": certificate.get("proof_id"),
        "proof_certificate_hash": certificate.get("certificate_hash"),
        "ecl_decision_hash": decision.get("decision_hash"),
        "action": decision.get("action"),
        "classification": decision.get("classification"),
        "rejection_codes": tuple(decision.get("rejection_codes", ())),
        "payload_hash": payload_hash,
        "previous_entry_hash": previous_entry_hash,
        "state_before": dict(state_before),
        "entropy_delta": entropy_delta,
        "state_after": state_after,
    }
    return {**unsigned, "entry_hash": digest(unsigned)}


def _replay_key(certificate: Mapping[str, Any]) -> str:
    return digest(
        {
            "rule_set_hash": certificate.get("rule_set_hash"),
            "proof_certificate_hash": certificate.get("certificate_hash"),
            "binding": "FORMAL_PROOF_REPLAY_KEY_V1",
        }
    )


def _build_crypto_binding(
    certificate: Mapping[str, Any],
    decision: Mapping[str, Any],
    entry: Mapping[str, Any],
) -> Dict[str, Any]:
    payload_hash = digest(
        {
            "proof_certificate": certificate,
            "ecl_decision": decision,
            "iel_entry": entry,
        }
    )
    return {
        "version": VERSION,
        "engine": "FormalProofCryptoBinding",
        "binding_id": CRYPTO_BINDING_ID,
        "algorithm": "SHA-256",
        "proof_certificate_hash": certificate.get("certificate_hash"),
        "ecl_decision_hash": decision.get("decision_hash"),
        "iel_entry_hash": entry.get("entry_hash"),
        "previous_entry_hash": entry.get("previous_entry_hash"),
        "receipt_payload_hash": payload_hash,
        "replay_key": _replay_key(certificate),
    }


def build_public_receipt(
    certificate: Any,
    *,
    previous_entry_hash: str = ZERO_HASH,
    state_before: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    cert = _mapping(certificate)
    decision = build_ecl_decision(cert)
    invariant_hash = _invariant_hash(cert, decision)
    before = dict(state_before) if state_before is not None else _genesis_state(invariant_hash)
    if before.get("I") != invariant_hash:
        raise ValueError("IEL invariant mismatch: rule set or ECL policy changed")
    entry = _build_iel_entry(cert, decision, previous_entry_hash, before)
    binding = _build_crypto_binding(cert, decision, entry)
    unsigned = {
        "version": VERSION,
        "engine": "FormalProofPublicReceipt",
        "proof_certificate": cert,
        "ecl_decision": decision,
        "iel_entry": entry,
        "cryptographic_binding": binding,
    }
    return {**unsigned, "receipt_hash": digest(unsigned)}


def verify_receipt(
    receipt: Any,
    *,
    expected_previous_entry_hash: Optional[str] = None,
    expected_state_before: Optional[Mapping[str, Any]] = None,
) -> ReceiptVerification:
    errors: List[str] = []
    try:
        candidate = _mapping(receipt)
    except ValueError as exc:
        return ReceiptVerification(False, "MALFORMED_RECEIPT", 1, (str(exc),), "UNKNOWN", None, None)

    cert = candidate.get("proof_certificate")
    decision = candidate.get("ecl_decision")
    entry = candidate.get("iel_entry")
    binding = candidate.get("cryptographic_binding")
    if not all(isinstance(value, Mapping) for value in (cert, decision, entry, binding)):
        return ReceiptVerification(False, "MALFORMED_RECEIPT", 1, ("RECEIPT_COMPONENT_MISSING",), "UNKNOWN", candidate.get("receipt_hash"), None)

    cert = dict(cert)
    decision = dict(decision)
    entry = dict(entry)
    binding = dict(binding)

    proof_audit = audit_proof_certificate(cert)
    errors.extend(proof_audit.errors)

    expected_decision = build_ecl_decision(cert)
    if canonical_json(decision) != canonical_json(expected_decision):
        errors.append("ECL_DECISION_MISMATCH")
    if decision.get("decision_hash") != _hash_without(decision, "decision_hash"):
        errors.append("ECL_DECISION_HASH_MISMATCH")

    if entry.get("entry_hash") != _hash_without(entry, "entry_hash"):
        errors.append("IEL_ENTRY_HASH_MISMATCH")
    if entry.get("proof_certificate_hash") != cert.get("certificate_hash"):
        errors.append("IEL_PROOF_HASH_BINDING_MISMATCH")
    if entry.get("ecl_decision_hash") != decision.get("decision_hash"):
        errors.append("IEL_DECISION_HASH_BINDING_MISMATCH")
    if entry.get("action") != decision.get("action"):
        errors.append("IEL_ACTION_BINDING_MISMATCH")
    if entry.get("payload_hash") != digest({"proof_certificate": cert, "ecl_decision": decision}):
        errors.append("IEL_PAYLOAD_HASH_MISMATCH")

    state_before = entry.get("state_before")
    state_after = entry.get("state_after")
    if not isinstance(state_before, Mapping) or not isinstance(state_after, Mapping):
        errors.append("IEL_STATE_MALFORMED")
    else:
        expected_invariant = _invariant_hash(cert, decision)
        if state_before.get("I") != expected_invariant or state_after.get("I") != expected_invariant:
            errors.append("IEL_INFORMATION_INVARIANT_MISMATCH")
        try:
            delta = int(entry.get("entropy_delta"))
            if delta <= 0:
                errors.append("IEL_ENTROPY_DELTA_NOT_POSITIVE")
            if int(state_after.get("E")) != int(state_before.get("E")) + delta:
                errors.append("IEL_ENTROPY_TRANSITION_MISMATCH")
            if int(state_after.get("theta")) != int(state_before.get("theta")) + 1:
                errors.append("IEL_EVENT_INDEX_TRANSITION_MISMATCH")
            if int(entry.get("event_index")) != int(state_after.get("theta")):
                errors.append("IEL_EVENT_INDEX_MISMATCH")
        except (TypeError, ValueError):
            errors.append("IEL_STATE_VALUE_MALFORMED")
        if expected_state_before is not None and canonical_json(state_before) != canonical_json(expected_state_before):
            errors.append("IEL_STATE_CONTINUITY_MISMATCH")

    if expected_previous_entry_hash is not None and entry.get("previous_entry_hash") != expected_previous_entry_hash:
        errors.append("CRYPTO_PREVIOUS_ENTRY_HASH_MISMATCH")

    expected_binding = _build_crypto_binding(cert, decision, entry)
    if canonical_json(binding) != canonical_json(expected_binding):
        errors.append("CRYPTO_BINDING_MISMATCH")

    claimed_receipt_hash = candidate.get("receipt_hash")
    expected_receipt_hash = _hash_without(candidate, "receipt_hash")
    if claimed_receipt_hash != expected_receipt_hash:
        errors.append("RECEIPT_HASH_MISMATCH")

    unique_errors = tuple(dict.fromkeys(errors))
    action = str(decision.get("action", "UNKNOWN"))
    return ReceiptVerification(
        ok=not unique_errors,
        status="VALID_RECEIPT" if not unique_errors else "TAMPER_DETECTED",
        error_count=len(unique_errors),
        errors=unique_errors,
        action=action,
        receipt_hash=str(claimed_receipt_hash) if claimed_receipt_hash is not None else None,
        entry_hash=str(entry.get("entry_hash")) if entry.get("entry_hash") is not None else None,
    )


def tamper_receipt(receipt: Any) -> Dict[str, Any]:
    """Deterministically alter one bound field without repairing its hashes."""
    out = _mapping(receipt)
    cert = out.get("proof_certificate")
    if isinstance(cert, dict) and cert.get("status") == "VALID_PROOF":
        cert["status"] = "REJECTED"
        out["tamper_note"] = "changed proof certificate status without recomputing bindings"
        return out
    entry = out.get("iel_entry")
    if isinstance(entry, dict) and isinstance(entry.get("state_after"), dict):
        entry["state_after"]["E"] = int(entry["state_after"].get("E", 0)) + 1
        out["tamper_note"] = "incremented IEL entropy state without recomputing bindings"
        return out
    out["receipt_hash"] = ZERO_HASH
    out["tamper_note"] = "replaced receipt hash"
    return out


def verify_ledger(receipts: Iterable[Any]) -> LedgerVerification:
    errors: List[str] = []
    previous_hash = ZERO_HASH
    expected_state: Optional[Dict[str, Any]] = None
    seen_replay_keys: set[str] = set()
    checked = 0

    for index, raw in enumerate(receipts, start=1):
        checked = index
        try:
            receipt = _mapping(raw)
        except ValueError as exc:
            errors.append(f"entry {index}: MALFORMED_RECEIPT:{exc}")
            continue
        if expected_state is None:
            cert = receipt.get("proof_certificate", {})
            decision = receipt.get("ecl_decision", {})
            if isinstance(cert, Mapping) and isinstance(decision, Mapping):
                expected_state = _genesis_state(_invariant_hash(cert, decision))
        verification = verify_receipt(
            receipt,
            expected_previous_entry_hash=previous_hash,
            expected_state_before=expected_state,
        )
        for error in verification.errors:
            errors.append(f"entry {index}: {error}")

        binding = receipt.get("cryptographic_binding", {})
        replay_key = str(binding.get("replay_key", "")) if isinstance(binding, Mapping) else ""
        if not replay_key:
            errors.append(f"entry {index}: REPLAY_KEY_MISSING")
        elif replay_key in seen_replay_keys:
            errors.append(f"entry {index}: REPLAY_DETECTED")
        else:
            seen_replay_keys.add(replay_key)

        entry = receipt.get("iel_entry", {})
        if isinstance(entry, Mapping):
            previous_hash = str(entry.get("entry_hash", previous_hash))
            state_after = entry.get("state_after")
            expected_state = dict(state_after) if isinstance(state_after, Mapping) else expected_state

    return LedgerVerification(
        ok=not errors,
        status="VALID_LEDGER" if not errors else "LEDGER_TAMPER_OR_REPLAY_DETECTED",
        checked=checked,
        error_count=len(errors),
        errors=tuple(errors),
        last_entry_hash=previous_hash if checked else ZERO_HASH,
        final_state=expected_state,
    )


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at line {line_no}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"ledger line {line_no} is not a JSON object")
        rows.append(value)
    return rows


def _append_jsonl(path: Path, receipt: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(canonical_json(receipt) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


class FormalProofFinalityLedger:
    def __init__(self, path: str | Path = "formal_proof_public_receipts.jsonl") -> None:
        self.path = Path(path)

    def receipts(self) -> List[Dict[str, Any]]:
        return _read_jsonl(self.path)

    def verify(self) -> LedgerVerification:
        try:
            return verify_ledger(self.receipts())
        except ValueError as exc:
            return LedgerVerification(False, "LEDGER_MALFORMED", 0, 1, (str(exc),), ZERO_HASH, None)

    def seal_certificate(self, certificate: Any) -> Dict[str, Any]:
        cert = _mapping(certificate)
        with _LEDGER_LOCK:
            try:
                existing = self.receipts()
            except ValueError as exc:
                return {
                    "status": "LEDGER_MALFORMED",
                    "appended": False,
                    "replay_detected": False,
                    "errors": [str(exc)],
                    "ledger_path": str(self.path),
                }

            before_audit = verify_ledger(existing)
            if not before_audit.ok:
                return {
                    "status": "LEDGER_TAMPER_DETECTED",
                    "appended": False,
                    "replay_detected": False,
                    "errors": list(before_audit.errors),
                    "ledger_path": str(self.path),
                }

            replay_key = _replay_key(cert)
            for receipt in existing:
                binding = receipt.get("cryptographic_binding", {})
                if isinstance(binding, Mapping) and binding.get("replay_key") == replay_key:
                    return {
                        "status": "REPLAY_REJECTED",
                        "appended": False,
                        "replay_detected": True,
                        "existing_receipt_hash": receipt.get("receipt_hash"),
                        "proof_certificate_hash": cert.get("certificate_hash"),
                        "ledger_path": str(self.path),
                        "ledger": asdict(before_audit),
                    }

            previous_hash = before_audit.last_entry_hash
            state_before = before_audit.final_state
            try:
                receipt = build_public_receipt(
                    cert,
                    previous_entry_hash=previous_hash,
                    state_before=state_before,
                )
            except ValueError as exc:
                return {
                    "status": "INVARIANT_MISMATCH",
                    "appended": False,
                    "replay_detected": False,
                    "errors": [str(exc)],
                    "ledger_path": str(self.path),
                }

            receipt_audit = verify_receipt(
                receipt,
                expected_previous_entry_hash=previous_hash,
                expected_state_before=state_before,
            )
            if not receipt_audit.ok:
                return {
                    "status": "RECEIPT_BUILD_FAILED",
                    "appended": False,
                    "replay_detected": False,
                    "errors": list(receipt_audit.errors),
                    "ledger_path": str(self.path),
                }

            _append_jsonl(self.path, receipt)
            after_audit = verify_ledger(existing + [receipt])
            return {
                "status": "SEALED" if after_audit.ok else "POST_APPEND_VERIFICATION_FAILED",
                "appended": after_audit.ok,
                "replay_detected": False,
                "action": receipt["ecl_decision"]["action"],
                "receipt": receipt,
                "receipt_verification": asdict(receipt_audit),
                "ledger": asdict(after_audit),
                "ledger_path": str(self.path),
            }

    def seal_proof(self, proof: Any) -> Dict[str, Any]:
        try:
            from .verifier import verify_proof
        except ImportError:
            from verifier import verify_proof
        return self.seal_certificate(verify_proof(proof))


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Seal Formal Proof Gate certificates into ECL/IEL public receipts")
    parser.add_argument("proof", nargs="?", type=Path)
    parser.add_argument("--ledger", type=Path, default=Path("formal_proof_public_receipts.jsonl"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--tamper-proof", action="store_true")
    parser.add_argument("--verify-ledger", action="store_true")
    parser.add_argument("--verify-receipt", type=Path)
    parser.add_argument("--tamper-receipt", type=Path)
    args = parser.parse_args()

    if args.verify_ledger:
        result = asdict(FormalProofFinalityLedger(args.ledger).verify())
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 2

    if args.verify_receipt:
        result = asdict(verify_receipt(_load_json(args.verify_receipt)))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 2

    if args.tamper_receipt:
        result = tamper_receipt(_load_json(args.tamper_receipt))
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
        return 0

    if args.proof is None:
        parser.error("proof is required unless a verification mode is selected")

    try:
        from .verifier import tamper_one_step
    except ImportError:
        from verifier import tamper_one_step
    proof = _load_json(args.proof)
    if args.tamper_proof:
        proof = tamper_one_step(proof)
    result = FormalProofFinalityLedger(args.ledger).seal_proof(proof)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result.get("status") == "SEALED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
