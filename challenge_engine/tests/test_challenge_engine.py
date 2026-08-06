#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import capabilities, evaluate_challenge


def load_example(name: str):
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


class ChallengeEngineTests(unittest.TestCase):
    def test_capabilities_default_math(self):
        caps = capabilities()
        self.assertEqual(caps["default_package"], "math")
        self.assertIn("security_audit", [p["package"] for p in caps["packages"]])

    def test_certified_math_example(self):
        result = evaluate_challenge(load_example("math_challenge.json"))
        self.assertEqual(result["result"], "CERTIFIED")
        self.assertTrue(result["formal_promotion"])

    def test_nonformal_adversarial_is_allowed(self):
        result = evaluate_challenge(load_example("nonformal_behavioral_challenge.json"))
        self.assertEqual(result["result"], "ADVERSARIAL_PASS")
        self.assertFalse(result["formal_promotion"])
        boundary = next(c for c in result["checks"] if c["id"] == "evidence_boundary")
        self.assertEqual(boundary["status"], "pass")

    def test_security_requires_declared_authorization(self):
        challenge = load_example("security_audit_challenge.json")
        challenge["scope"]["authorization"] = "missing"
        result = evaluate_challenge(challenge)
        self.assertEqual(result["result"], "BLOCKED_SCOPE")

    def test_certified_nonformal_only_is_incomplete(self):
        challenge = load_example("math_challenge.json")
        challenge["evidence"] = [{"id":"notes","type":"notes","status":"pass","formal":False}]
        result = evaluate_challenge(challenge)
        self.assertEqual(result["result"], "INCOMPLETE")
        self.assertIn("evidence_boundary", result["open_obligations"])

    def test_completion_without_error_cannot_promote(self):
        challenge = load_example("math_challenge.json")
        challenge["completion"] = {"enabled": True, "finite_upper": 0.2, "threshold": 1.0}
        result = evaluate_challenge(challenge)
        self.assertEqual(result["result"], "INCOMPLETE")
        self.assertIn("completion", result["open_obligations"])

    def test_completion_worst_case_failure(self):
        challenge = load_example("math_challenge.json")
        challenge["completion"] = {"enabled":True,"finite_upper":0.92,"completion_error":0.12,"threshold":1.0}
        result = evaluate_challenge(challenge)
        self.assertEqual(result["result"], "FAILED")
        self.assertIn("completion", result["failed_obligations"])

    def test_burden_above_one_fails(self):
        challenge = load_example("math_challenge.json")
        challenge["burden"] = {"beta": 1.01, "threshold": 1.0}
        result = evaluate_challenge(challenge)
        self.assertEqual(result["result"], "FAILED")
        self.assertIn("burden", result["failed_obligations"])

    def test_flow_visibility_cannot_revert(self):
        challenge = load_example("nonformal_behavioral_challenge.json")
        challenge["flow"]["probes"] = [
            {"order":0,"target_visible":False},
            {"order":1,"target_visible":True},
            {"order":2,"target_visible":False}
        ]
        result = evaluate_challenge(challenge)
        self.assertEqual(result["result"], "FAILED")
        self.assertIn("flow:recognition_monotonicity", result["failed_obligations"])

    def test_default_package_is_math(self):
        challenge = load_example("math_challenge.json")
        challenge.pop("package")
        result = evaluate_challenge(challenge)
        self.assertEqual(result["package"], "math")
        self.assertEqual(result["result"], "CERTIFIED")

    def test_negative_control_escape_fails(self):
        challenge = load_example("nonformal_behavioral_challenge.json")
        challenge["negative_controls"][0]["status"] = "fail"
        result = evaluate_challenge(challenge)
        self.assertEqual(result["result"], "FAILED")

    def test_open_required_obligation_holds(self):
        challenge = load_example("nonformal_behavioral_challenge.json")
        challenge["obligations"] = [x for x in challenge["obligations"] if x["id"] != "evidence"]
        result = evaluate_challenge(challenge)
        self.assertEqual(result["result"], "INCOMPLETE")
        self.assertIn("obligation:evidence", result["open_obligations"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
