from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from formal_proof_challenge.finality import (
    ZERO_HASH,
    FormalProofFinalityLedger,
    audit_proof_certificate,
    build_ecl_decision,
    build_public_receipt,
    digest,
    tamper_receipt,
    verify_ledger,
    verify_receipt,
)
from formal_proof_challenge.verifier import verify_proof

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "formal_proof_challenge" / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def make_certificate(*, valid: bool, proof_id: str = "proof-1", code: str = "ARITHMETIC_MISMATCH"):
    errors = () if valid else ({"code": code, "message": "test rejection", "step_id": "S1"},)
    unsigned = {
        "version": "1.0.0",
        "engine": "FormalProofGate",
        "rule_set_id": "formal-proof-gate-finite-calculus-v1",
        "rule_set_hash": digest({"rules": "test"}),
        "proof_id": proof_id,
        "proof_hash": digest({"proof_id": proof_id, "valid": valid}),
        "dependency_graph_hash": digest({"S1": []}),
        "admitted_syntax": True,
        "dependency_graph_acyclic": True,
        "all_steps_licensed": valid,
        "conclusion_step": "S1",
        "target_match": valid,
        "status": "VALID_PROOF" if valid else "REJECTED",
        "error_count": len(errors),
        "errors": errors,
    }
    return {**unsigned, "certificate_hash": digest(unsigned)}


class FormalProofFinalityTests(unittest.TestCase):
    def test_valid_fixture_seals_as_commit(self) -> None:
        certificate = asdict(verify_proof(load("valid_arithmetic.json")))
        decision = build_ecl_decision(certificate)
        self.assertEqual(decision["action"], "COMMIT")
        receipt = build_public_receipt(certificate)
        audit = verify_receipt(receipt, expected_previous_entry_hash=ZERO_HASH)
        self.assertTrue(audit.ok, audit.errors)

    def test_rejected_fixture_seals_as_reject_audit(self) -> None:
        certificate = asdict(verify_proof(load("false_arithmetic.json")))
        decision = build_ecl_decision(certificate)
        self.assertEqual(decision["action"], "REJECT")
        self.assertIn("ARITHMETIC_MISMATCH", decision["rejection_codes"])
        receipt = build_public_receipt(certificate)
        self.assertTrue(verify_receipt(receipt, expected_previous_entry_hash=ZERO_HASH).ok)

    def test_valid_proof_certificate_audit(self) -> None:
        self.assertTrue(audit_proof_certificate(make_certificate(valid=True)).ok)

    def test_forged_valid_status_is_rejected(self) -> None:
        certificate = make_certificate(valid=False)
        unsigned = dict(certificate)
        unsigned.pop("certificate_hash")
        unsigned["status"] = "VALID_PROOF"
        unsigned["certificate_hash"] = digest(unsigned)
        decision = build_ecl_decision(unsigned)
        self.assertEqual(decision["action"], "REJECT")
        self.assertIn("VALID_STATUS_WITH_OPEN_PROOF_OBLIGATION", decision["rejection_codes"])

    def test_receipt_tamper_is_detected(self) -> None:
        receipt = build_public_receipt(make_certificate(valid=True))
        audit = verify_receipt(tamper_receipt(receipt), expected_previous_entry_hash=ZERO_HASH)
        self.assertFalse(audit.ok)
        self.assertIn("PROOF_CERTIFICATE_HASH_MISMATCH", audit.errors)

    def test_iel_state_tamper_is_detected(self) -> None:
        receipt = build_public_receipt(make_certificate(valid=False))
        receipt["iel_entry"]["state_after"]["E"] += 1
        audit = verify_receipt(receipt, expected_previous_entry_hash=ZERO_HASH)
        self.assertFalse(audit.ok)
        self.assertIn("IEL_ENTRY_HASH_MISMATCH", audit.errors)
        self.assertIn("IEL_ENTROPY_TRANSITION_MISMATCH", audit.errors)

    def test_two_receipt_chain_is_valid(self) -> None:
        first = build_public_receipt(make_certificate(valid=True, proof_id="p1"))
        second = build_public_receipt(
            make_certificate(valid=False, proof_id="p2"),
            previous_entry_hash=first["iel_entry"]["entry_hash"],
            state_before=first["iel_entry"]["state_after"],
        )
        audit = verify_ledger([first, second])
        self.assertTrue(audit.ok, audit.errors)
        self.assertEqual(audit.final_state["theta"], 2)

    def test_duplicate_receipt_is_replay(self) -> None:
        certificate = make_certificate(valid=True)
        first = build_public_receipt(certificate)
        duplicate = build_public_receipt(
            certificate,
            previous_entry_hash=first["iel_entry"]["entry_hash"],
            state_before=first["iel_entry"]["state_after"],
        )
        audit = verify_ledger([first, duplicate])
        self.assertFalse(audit.ok)
        self.assertTrue(any("REPLAY_DETECTED" in error for error in audit.errors))

    def test_file_ledger_rejects_replay_without_append(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            ledger = FormalProofFinalityLedger(path)
            certificate = make_certificate(valid=True)
            self.assertEqual(ledger.seal_certificate(certificate)["status"], "SEALED")
            self.assertEqual(ledger.seal_certificate(certificate)["status"], "REPLAY_REJECTED")
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 1)

    def test_file_ledger_refuses_append_after_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            ledger = FormalProofFinalityLedger(path)
            self.assertEqual(ledger.seal_certificate(make_certificate(valid=True, proof_id="p1"))["status"], "SEALED")
            row = json.loads(path.read_text(encoding="utf-8"))
            row["iel_entry"]["state_after"]["E"] += 1
            path.write_text(json.dumps(row) + "\n", encoding="utf-8")
            result = ledger.seal_certificate(make_certificate(valid=True, proof_id="p2"))
            self.assertEqual(result["status"], "LEDGER_TAMPER_DETECTED")
            self.assertFalse(result["appended"])

    def test_rule_set_change_breaks_iel_invariant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = FormalProofFinalityLedger(Path(tmp) / "ledger.jsonl")
            first = make_certificate(valid=True, proof_id="p1")
            self.assertEqual(ledger.seal_certificate(first)["status"], "SEALED")
            changed = make_certificate(valid=True, proof_id="p2")
            unsigned = dict(changed)
            unsigned.pop("certificate_hash")
            unsigned["rule_set_hash"] = digest({"rules": "changed"})
            changed = {**unsigned, "certificate_hash": digest(unsigned)}
            self.assertEqual(ledger.seal_certificate(changed)["status"], "INVARIANT_MISMATCH")

    def test_receipt_build_is_deterministic_at_fixed_state(self) -> None:
        certificate = make_certificate(valid=True)
        self.assertEqual(build_public_receipt(certificate), build_public_receipt(certificate))


if __name__ == "__main__":
    unittest.main()
