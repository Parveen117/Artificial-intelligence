#!/usr/bin/env python3
"""FPG3 external anchor builder and verifier.

The anchor is a compact public checkpoint for the Formal Proof Gate receipt
ledger. It binds the admitted finite calculus, ECL policy, IEL invariant,
receipt count, action totals, receipt Merkle root, final IEL state, and ledger
head. Publishing the resulting JSON somewhere independent of the live app
makes later history replacement detectable against that retained checkpoint.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

ANCHOR_VERSION = "1.0.0"
ANCHOR_ID = "formal-proof-gate-external-anchor-v1"


@dataclass(frozen=True)
class AnchorVerification:
    ok: bool
    status: str
    error_count: int
    errors: Tuple[str, ...]
    anchor_hash: Optional[str]
    document_hash: Optional[str]
    receipt_count: Optional[int]
    last_entry_hash: Optional[str]


def _runtime() -> Dict[str, Any]:
    """Load FPG1/FPG2 runtime objects lazily for CLI and hosted use."""
    from .finality import (
        CRYPTO_BINDING_ID,
        ECL_POLICY_ID,
        IEL_LEDGER_ID,
        VERSION as FINALITY_VERSION,
        ZERO_HASH,
        FormalProofFinalityLedger,
        digest,
    )
    from .verifier import ALLOWED_RULES, RULE_SET_ID, VERSION as VERIFIER_VERSION

    return {
        "CRYPTO_BINDING_ID": CRYPTO_BINDING_ID,
        "ECL_POLICY_ID": ECL_POLICY_ID,
        "IEL_LEDGER_ID": IEL_LEDGER_ID,
        "FINALITY_VERSION": FINALITY_VERSION,
        "ZERO_HASH": ZERO_HASH,
        "FormalProofFinalityLedger": FormalProofFinalityLedger,
        "digest": digest,
        "ALLOWED_RULES": ALLOWED_RULES,
        "RULE_SET_ID": RULE_SET_ID,
        "VERIFIER_VERSION": VERIFIER_VERSION,
    }


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _is_hex64(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def _rule_set_hash(runtime: Mapping[str, Any]) -> str:
    return str(runtime["digest"]({
        "rule_set_id": runtime["RULE_SET_ID"],
        "rules": runtime["ALLOWED_RULES"],
        "version": runtime["VERIFIER_VERSION"],
    }))


def _ecl_policy_hash(runtime: Mapping[str, Any]) -> str:
    return str(runtime["digest"]({
        "policy_id": runtime["ECL_POLICY_ID"],
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
        "version": runtime["FINALITY_VERSION"],
    }))


def _invariant_hash(runtime: Mapping[str, Any], rule_set_hash: str, policy_hash: str) -> str:
    return str(runtime["digest"]({
        "ledger_id": runtime["IEL_LEDGER_ID"],
        "rule_set_id": runtime["RULE_SET_ID"],
        "rule_set_hash": rule_set_hash,
        "ecl_policy_hash": policy_hash,
        "version": runtime["FINALITY_VERSION"],
    }))


def _receipt_merkle_root(receipt_hashes: Sequence[str], digest_fn: Any) -> str:
    if not receipt_hashes:
        return str(digest_fn({"empty": "FORMAL_PROOF_RECEIPT_SET_V1"}))
    layer = [str(digest_fn({"leaf_index": i, "receipt_hash": value})) for i, value in enumerate(receipt_hashes)]
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [
            str(digest_fn({"left": layer[i], "right": layer[i + 1], "level": "FORMAL_PROOF_MERKLE_V1"}))
            for i in range(0, len(layer), 2)
        ]
    return layer[0]


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_external_anchor(
    ledger_path: str | Path,
    *,
    public_app_url: str = "",
    source_revision: str = "",
    observed_at_utc: Optional[str] = None,
) -> Dict[str, Any]:
    runtime = _runtime()
    ledger = runtime["FormalProofFinalityLedger"](ledger_path)
    receipts = ledger.receipts()
    audit = ledger.verify()
    if not audit.ok:
        raise ValueError("cannot anchor an invalid ledger: " + "; ".join(audit.errors))

    expected_rule_hash = _rule_set_hash(runtime)
    expected_policy_hash = _ecl_policy_hash(runtime)
    invariant_hash = _invariant_hash(runtime, expected_rule_hash, expected_policy_hash)

    action_counts = {"COMMIT": 0, "REJECT": 0}
    receipt_hashes = []
    for index, receipt in enumerate(receipts, start=1):
        receipt_hash = receipt.get("receipt_hash")
        if not _is_hex64(receipt_hash):
            raise ValueError(f"receipt {index} has no valid receipt_hash")
        receipt_hashes.append(str(receipt_hash))

        certificate = receipt.get("proof_certificate", {})
        decision = receipt.get("ecl_decision", {})
        binding = receipt.get("cryptographic_binding", {})
        if certificate.get("rule_set_id") != runtime["RULE_SET_ID"]:
            raise ValueError(f"receipt {index} uses a different rule_set_id")
        if certificate.get("rule_set_hash") != expected_rule_hash:
            raise ValueError(f"receipt {index} uses a different rule_set_hash")
        if decision.get("policy_hash") != expected_policy_hash:
            raise ValueError(f"receipt {index} uses a different ECL policy hash")
        if binding.get("binding_id") != runtime["CRYPTO_BINDING_ID"]:
            raise ValueError(f"receipt {index} uses a different crypto binding")
        action = str(decision.get("action", "UNKNOWN"))
        if action not in action_counts:
            raise ValueError(f"receipt {index} has unsupported action {action}")
        action_counts[action] += 1

    final_state = audit.final_state or {"I": invariant_hash, "E": 0, "theta": 0}
    if final_state.get("I") != invariant_hash:
        raise ValueError("ledger final IEL information invariant does not match the active calculus")
    if int(final_state.get("theta", -1)) != len(receipts):
        raise ValueError("ledger theta does not equal the receipt count")

    payload = {
        "version": ANCHOR_VERSION,
        "engine": "FormalProofExternalAnchor",
        "anchor_id": ANCHOR_ID,
        "ledger_id": runtime["IEL_LEDGER_ID"],
        "crypto_binding_id": runtime["CRYPTO_BINDING_ID"],
        "rule_set_id": runtime["RULE_SET_ID"],
        "rule_set_hash": expected_rule_hash,
        "ecl_policy_id": runtime["ECL_POLICY_ID"],
        "ecl_policy_hash": expected_policy_hash,
        "iel_invariant_hash": invariant_hash,
        "receipt_count": len(receipts),
        "action_counts": action_counts,
        "receipt_merkle_root": _receipt_merkle_root(receipt_hashes, runtime["digest"]),
        "last_entry_hash": audit.last_entry_hash,
        "final_state": final_state,
        "source_revision": source_revision,
        "public_app_url": public_app_url.rstrip("/"),
        "status": "ANCHORED_LEDGER" if receipts else "EMPTY_LEDGER_GENESIS",
    }
    anchor_hash = str(runtime["digest"](payload))
    document = {
        "anchor": payload,
        "anchor_hash": anchor_hash,
        "observed_at_utc": observed_at_utc or _now_utc(),
    }
    return {**document, "document_hash": str(runtime["digest"](document))}


def verify_external_anchor(anchor_document: Any) -> AnchorVerification:
    errors = []
    if not isinstance(anchor_document, Mapping):
        return AnchorVerification(False, "MALFORMED_ANCHOR", 1, ("ANCHOR_DOCUMENT_NOT_OBJECT",), None, None, None, None)

    candidate = dict(anchor_document)
    payload = candidate.get("anchor")
    if not isinstance(payload, Mapping):
        return AnchorVerification(False, "MALFORMED_ANCHOR", 1, ("ANCHOR_PAYLOAD_MISSING",), candidate.get("anchor_hash"), candidate.get("document_hash"), None, None)
    payload = dict(payload)

    runtime = _runtime()
    expected_rule_hash = _rule_set_hash(runtime)
    expected_policy_hash = _ecl_policy_hash(runtime)
    expected_invariant = _invariant_hash(runtime, expected_rule_hash, expected_policy_hash)

    if payload.get("version") != ANCHOR_VERSION:
        errors.append("ANCHOR_VERSION_MISMATCH")
    if payload.get("anchor_id") != ANCHOR_ID:
        errors.append("ANCHOR_ID_MISMATCH")
    if payload.get("rule_set_id") != runtime["RULE_SET_ID"]:
        errors.append("RULE_SET_ID_MISMATCH")
    if payload.get("rule_set_hash") != expected_rule_hash:
        errors.append("RULE_SET_HASH_MISMATCH")
    if payload.get("ecl_policy_id") != runtime["ECL_POLICY_ID"]:
        errors.append("ECL_POLICY_ID_MISMATCH")
    if payload.get("ecl_policy_hash") != expected_policy_hash:
        errors.append("ECL_POLICY_HASH_MISMATCH")
    if payload.get("iel_invariant_hash") != expected_invariant:
        errors.append("IEL_INVARIANT_HASH_MISMATCH")
    if payload.get("crypto_binding_id") != runtime["CRYPTO_BINDING_ID"]:
        errors.append("CRYPTO_BINDING_ID_MISMATCH")

    action_counts = payload.get("action_counts")
    receipt_count = payload.get("receipt_count")
    try:
        count = int(receipt_count)
        if count < 0:
            errors.append("RECEIPT_COUNT_NEGATIVE")
    except (TypeError, ValueError):
        count = -1
        errors.append("RECEIPT_COUNT_MALFORMED")
    if not isinstance(action_counts, Mapping):
        errors.append("ACTION_COUNTS_MALFORMED")
    else:
        try:
            total = int(action_counts.get("COMMIT", 0)) + int(action_counts.get("REJECT", 0))
            if total != count:
                errors.append("ACTION_COUNT_TOTAL_MISMATCH")
        except (TypeError, ValueError):
            errors.append("ACTION_COUNTS_MALFORMED")

    final_state = payload.get("final_state")
    if not isinstance(final_state, Mapping):
        errors.append("FINAL_STATE_MALFORMED")
    else:
        if final_state.get("I") != expected_invariant:
            errors.append("FINAL_STATE_INVARIANT_MISMATCH")
        try:
            if int(final_state.get("theta")) != count:
                errors.append("FINAL_STATE_THETA_MISMATCH")
            if int(final_state.get("E")) < 0:
                errors.append("FINAL_STATE_ENTROPY_NEGATIVE")
        except (TypeError, ValueError):
            errors.append("FINAL_STATE_VALUE_MALFORMED")

    for key in ("receipt_merkle_root", "last_entry_hash"):
        if not _is_hex64(payload.get(key)):
            errors.append(f"{key.upper()}_MALFORMED")

    claimed_anchor_hash = candidate.get("anchor_hash")
    expected_anchor_hash = str(runtime["digest"](payload))
    if claimed_anchor_hash != expected_anchor_hash:
        errors.append("ANCHOR_HASH_MISMATCH")

    claimed_document_hash = candidate.get("document_hash")
    unsigned_document = dict(candidate)
    unsigned_document.pop("document_hash", None)
    expected_document_hash = str(runtime["digest"](unsigned_document))
    if claimed_document_hash != expected_document_hash:
        errors.append("ANCHOR_DOCUMENT_HASH_MISMATCH")

    unique = tuple(dict.fromkeys(errors))
    return AnchorVerification(
        ok=not unique,
        status="VALID_EXTERNAL_ANCHOR" if not unique else "ANCHOR_TAMPER_OR_MISMATCH",
        error_count=len(unique),
        errors=unique,
        anchor_hash=str(claimed_anchor_hash) if claimed_anchor_hash is not None else None,
        document_hash=str(claimed_document_hash) if claimed_document_hash is not None else None,
        receipt_count=count if count >= 0 else None,
        last_entry_hash=str(payload.get("last_entry_hash")) if payload.get("last_entry_hash") is not None else None,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify a Formal Proof Gate external anchor")
    parser.add_argument("--ledger", type=Path, default=Path("formal_proof_public_receipts.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("latest-anchor.json"))
    parser.add_argument("--app-url", default="")
    parser.add_argument("--source-revision", default="")
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()

    if args.verify:
        payload = json.loads(args.verify.read_text(encoding="utf-8"))
        audit = asdict(verify_external_anchor(payload))
        print(json.dumps(audit, indent=2, sort_keys=True))
        return 0 if audit["ok"] else 2

    document = build_external_anchor(
        args.ledger,
        public_app_url=args.app_url,
        source_revision=args.source_revision,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "output": str(args.output),
        "anchor_hash": document["anchor_hash"],
        "document_hash": document["document_hash"],
        "receipt_count": document["anchor"]["receipt_count"],
        "last_entry_hash": document["anchor"]["last_entry_hash"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
