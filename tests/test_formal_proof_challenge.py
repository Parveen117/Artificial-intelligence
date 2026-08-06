from __future__ import annotations

import json
import unittest
from dataclasses import asdict
from pathlib import Path

from formal_proof_challenge.verifier import tamper_one_step, verify_proof

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "formal_proof_challenge" / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FormalProofGateTests(unittest.TestCase):
    def test_valid_arithmetic_is_certified(self) -> None:
        cert = verify_proof(load("valid_arithmetic.json"))
        self.assertEqual(cert.status, "VALID_PROOF")
        self.assertTrue(cert.all_steps_licensed)
        self.assertTrue(cert.target_match)
        self.assertEqual(cert.error_count, 0)

    def test_valid_modus_ponens_is_certified(self) -> None:
        self.assertEqual(verify_proof(load("valid_modus_ponens.json")).status, "VALID_PROOF")

    def test_false_arithmetic_is_rejected(self) -> None:
        cert = verify_proof(load("false_arithmetic.json"))
        self.assertEqual(cert.status, "REJECTED")
        self.assertIn("ARITHMETIC_MISMATCH", {error["code"] for error in cert.errors})

    def test_unsupported_lemma_is_rejected(self) -> None:
        cert = verify_proof(load("unsupported_lemma.json"))
        self.assertEqual(cert.status, "REJECTED")
        self.assertIn("UNSUPPORTED_LEMMA", {error["code"] for error in cert.errors})

    def test_circular_proof_is_rejected(self) -> None:
        cert = verify_proof(load("circular_proof.json"))
        self.assertEqual(cert.status, "REJECTED")
        self.assertFalse(cert.dependency_graph_acyclic)
        self.assertIn("CIRCULAR_DEPENDENCY", {error["code"] for error in cert.errors})

    def test_target_mismatch_is_rejected(self) -> None:
        cert = verify_proof(load("target_mismatch.json"))
        self.assertEqual(cert.status, "REJECTED")
        self.assertIn("TARGET_MISMATCH", {error["code"] for error in cert.errors})

    def test_unknown_syntax_fails_closed(self) -> None:
        proof = load("valid_arithmetic.json")
        proof["steps"][0]["rule"] = "MAGIC"
        cert = verify_proof(proof)
        self.assertEqual(cert.status, "REJECTED")
        self.assertFalse(cert.admitted_syntax)
        self.assertEqual(cert.errors[0]["code"], "PARSE_NOT_ADMITTED")

    def test_missing_premise_is_rejected(self) -> None:
        proof = load("valid_modus_ponens.json")
        proof["steps"][2]["premises"] = ["S1", "S404"]
        cert = verify_proof(proof)
        self.assertEqual(cert.status, "REJECTED")
        self.assertIn("MISSING_PREMISE", {error["code"] for error in cert.errors})

    def test_tamper_one_step_breaks_valid_arithmetic(self) -> None:
        proof = load("valid_arithmetic.json")
        tampered = tamper_one_step(proof)
        self.assertEqual(verify_proof(proof).status, "VALID_PROOF")
        self.assertEqual(verify_proof(tampered).status, "REJECTED")

    def test_certificate_is_deterministic(self) -> None:
        proof = load("valid_modus_ponens.json")
        self.assertEqual(asdict(verify_proof(proof)), asdict(verify_proof(proof)))

    def test_equality_transitivity(self) -> None:
        proof = {
            "version": "1.0.0",
            "proof_id": "eq-transitivity",
            "assumptions": [
                {"op": "eq", "left": "x", "right": "y"},
                {"op": "eq", "left": "y", "right": "z"}
            ],
            "target": {"op": "eq", "left": "x", "right": "z"},
            "steps": [
                {"id": "S1", "rule": "ASSUMPTION", "premises": [], "conclusion": {"op": "eq", "left": "x", "right": "y"}},
                {"id": "S2", "rule": "ASSUMPTION", "premises": [], "conclusion": {"op": "eq", "left": "y", "right": "z"}},
                {"id": "S3", "rule": "EQ_TRANSITIVITY", "premises": ["S1", "S2"], "conclusion": {"op": "eq", "left": "x", "right": "z"}}
            ],
            "conclusion_step": "S3"
        }
        self.assertEqual(verify_proof(proof).status, "VALID_PROOF")


if __name__ == "__main__":
    unittest.main()
