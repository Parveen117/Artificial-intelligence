#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import capabilities, evaluate_challenge
from strict_json import exact_json_lexeme, loads_strict


def load_math() -> dict:
    return json.loads((ROOT / "examples" / "math_challenge.json").read_text(encoding="utf-8"))


class ExactRationalBallArithmeticTests(unittest.TestCase):
    def test_connector_preserves_long_decimal_lexeme(self):
        value = loads_strict('{"x":0.123456789012345678901234567890123456789}')["x"]
        self.assertEqual(exact_json_lexeme(value), "0.123456789012345678901234567890123456789")

    def test_long_decimal_completion_boundary_is_exact(self):
        numbers = loads_strict(
            '{"finite_upper":0.123456789012345678901234567890,'
            '"completion_error":0.000000000000000000000000000010,'
            '"threshold":0.123456789012345678901234567900}'
        )
        c = load_math()
        c["completion"] = {"enabled": True, **numbers}
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "INCOMPLETE")
        check = next(x for x in r["checks"] if x["id"] == "completion")
        self.assertEqual(check["status"], "open")

    def test_equivalent_decimal_spellings_share_genesis_value(self):
        c1 = load_math()
        c2 = load_math()
        c1["completion"] = {"enabled": True, **loads_strict('{"finite_upper":0.1,"completion_error":0.69,"threshold":0.8}')}
        c2["completion"] = {"enabled": True, **loads_strict('{"finite_upper":0.10,"completion_error":0.690,"threshold":0.800}')}
        r1 = evaluate_challenge(c1)
        r2 = evaluate_challenge(c2)
        self.assertEqual(r1["challenge_genesis"]["genesis_hash"], r2["challenge_genesis"]["genesis_hash"])

    def test_genesis_exposes_exact_numeric_declarations(self):
        c = load_math()
        c["completion"] = {"enabled": True, **loads_strict('{"finite_upper":0.1,"completion_error":0.7,"threshold":0.8}')}
        r = evaluate_challenge(c)
        exact = r["challenge_genesis"]["contract"]["exact_numeric_declarations"]
        self.assertEqual(exact["$.completion.finite_upper"], {"numerator": "1", "denominator": "10"})
        self.assertEqual(exact["$.completion.threshold"], {"numerator": "4", "denominator": "5"})

    def test_exact_rational_certificate_passes(self):
        c = load_math()
        c["arithmetic_certificate"] = {
            "kind": "exact_rational",
            "numerator": "7",
            "denominator": "10",
            "analytic_tail": "1/100",
            "threshold": "4/5",
        }
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "CERTIFIED")
        self.assertEqual(r["arithmetic_summary"]["arithmetic_radius"], "0")

    def test_exact_decimal_arbitrary_precision_passes(self):
        c = load_math()
        c["arithmetic_certificate"] = {
            "kind": "exact_decimal",
            "value": "0.123456789012345678901234567890123456789",
            "analytic_tail": "0",
            "threshold": "0.123456789012345678901234567890123456790",
        }
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "CERTIFIED")
        self.assertTrue(r["arithmetic_summary"]["proof_bearing"])

    def test_ball_boundary_is_incomplete(self):
        c = load_math()
        c["arithmetic_certificate"] = {
            "kind": "ball",
            "center": "0.70",
            "radius": "0.05",
            "analytic_tail": "0.05",
            "threshold": "0.80",
        }
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "INCOMPLETE")
        check = next(x for x in r["checks"] if x["id"] == "arithmetic_certificate")
        self.assertEqual(check["status"], "open")

    def test_directed_interval_outward_failure(self):
        c = load_math()
        c["arithmetic_certificate"] = {
            "kind": "directed_interval",
            "lower": "0.79",
            "upper": "0.81",
            "analytic_tail": "0",
            "threshold": "0.80",
        }
        self.assertEqual(evaluate_challenge(c)["result"], "FAILED")

    def test_raw_float_without_radius_is_incomplete(self):
        c = load_math()
        c["arithmetic_certificate"] = {
            "kind": "raw_float",
            "center": "0.70",
            "analytic_tail": "0.01",
            "threshold": "0.80",
        }
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "INCOMPLETE")
        self.assertFalse(r["arithmetic_summary"]["proof_bearing"])

    def test_raw_float_with_validated_radius_can_close(self):
        c = load_math()
        c["arithmetic_certificate"] = {
            "kind": "raw_float",
            "center": "0.70",
            "radius": "0.01",
            "analytic_tail": "0.01",
            "threshold": "0.80",
        }
        self.assertEqual(evaluate_challenge(c)["result"], "CERTIFIED")

    def test_disjoint_independent_enclosures_fail(self):
        c = load_math()
        c["arithmetic_certificate"] = {
            "kind": "ball",
            "center": "0.50",
            "radius": "0.01",
            "analytic_tail": "0",
            "threshold": "0.80",
            "independent_enclosures": [
                {"id": "backend-a", "center": "0.500", "radius": "0.001"},
                {"id": "backend-b", "center": "0.510", "radius": "0.001"}
            ]
        }
        self.assertEqual(evaluate_challenge(c)["result"], "FAILED")

    def test_overlapping_independent_enclosures_pass(self):
        c = load_math()
        c["arithmetic_certificate"] = {
            "kind": "ball",
            "center": "0.50",
            "radius": "0.01",
            "analytic_tail": "0",
            "threshold": "0.80",
            "independent_enclosures": [
                {"id": "backend-a", "lower": "0.49", "upper": "0.51"},
                {"id": "backend-b", "center": "0.505", "radius": "0.01"}
            ]
        }
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "CERTIFIED")
        check = next(x for x in r["checks"] if x["id"] == "arithmetic_path_overlap")
        self.assertEqual(check["status"], "pass")

    def test_zero_denominator_is_invalid(self):
        c = load_math()
        c["arithmetic_certificate"] = {
            "kind": "exact_rational",
            "numerator": "1",
            "denominator": "0",
            "analytic_tail": "0",
            "threshold": "1",
        }
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_capabilities_publish_arithmetic_protocol(self):
        caps = capabilities()
        self.assertEqual(caps["arithmetic_protocol"], "exact-rational-directed-enclosure-v1")
        self.assertTrue(caps["exact_connector_decimal_lexeme"])
        self.assertEqual(caps["raw_float_without_radius"], "INCOMPLETE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
