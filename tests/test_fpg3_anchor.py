from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from formal_proof_challenge.anchor import build_external_anchor, verify_external_anchor
from formal_proof_challenge.finality import FormalProofFinalityLedger

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "formal_proof_challenge" / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FPG3AnchorTests(unittest.TestCase):
    def test_empty_ledger_anchor_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            anchor = build_external_anchor(Path(tmp) / "ledger.jsonl", observed_at_utc="2026-08-06T00:00:00+00:00")
            self.assertEqual(anchor["anchor"]["receipt_count"], 0)
            self.assertEqual(anchor["anchor"]["status"], "EMPTY_LEDGER_GENESIS")
            self.assertTrue(verify_external_anchor(anchor).ok)

    def test_commit_and_reject_are_counted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            ledger = FormalProofFinalityLedger(path)
            self.assertEqual(ledger.seal_proof(load("valid_arithmetic.json"))["status"], "SEALED")
            self.assertEqual(ledger.seal_proof(load("false_arithmetic.json"))["status"], "SEALED")
            anchor = build_external_anchor(path, public_app_url="https://example.test", source_revision="abc123")
            payload = anchor["anchor"]
            self.assertEqual(payload["receipt_count"], 2)
            self.assertEqual(payload["action_counts"], {"COMMIT": 1, "REJECT": 1})
            self.assertEqual(payload["final_state"]["theta"], 2)
            self.assertEqual(payload["public_app_url"], "https://example.test")
            self.assertTrue(verify_external_anchor(anchor).ok)

    def test_anchor_hash_is_stable_when_only_observation_time_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            first = build_external_anchor(path, observed_at_utc="2026-08-06T00:00:00+00:00")
            second = build_external_anchor(path, observed_at_utc="2026-08-07T00:00:00+00:00")
            self.assertEqual(first["anchor_hash"], second["anchor_hash"])
            self.assertNotEqual(first["document_hash"], second["document_hash"])

    def test_anchor_tamper_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            anchor = build_external_anchor(Path(tmp) / "ledger.jsonl")
            tampered = copy.deepcopy(anchor)
            tampered["anchor"]["receipt_count"] = 99
            audit = verify_external_anchor(tampered)
            self.assertFalse(audit.ok)
            self.assertIn("ACTION_COUNT_TOTAL_MISMATCH", audit.errors)
            self.assertIn("ANCHOR_HASH_MISMATCH", audit.errors)

    def test_invalid_ledger_cannot_be_anchored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            ledger = FormalProofFinalityLedger(path)
            ledger.seal_proof(load("valid_arithmetic.json"))
            row = json.loads(path.read_text(encoding="utf-8"))
            row["iel_entry"]["state_after"]["E"] += 1
            path.write_text(json.dumps(row) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                build_external_anchor(path)


if __name__ == "__main__":
    unittest.main()
