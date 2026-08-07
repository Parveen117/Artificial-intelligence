#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import capabilities, evaluate_challenge
from engine_v4 import evaluate_challenge as evaluate_v4


def load_math() -> dict:
    return json.loads((ROOT / "examples" / "math_challenge.json").read_text(encoding="utf-8"))


def exact_cert(num, den, seam_id="demo-seam") -> dict:
    return {
        "seam_id": seam_id,
        "model": "exact_polynomial_jet",
        "relation": "finite_seam_quotient",
        "numerator_coefficients": num,
        "denominator_coefficients": den,
    }


class SeamQuotientTheorem46Tests(unittest.TestCase):
    def test_legacy_challenge_keeps_old_genesis(self):
        c = load_math()
        old = evaluate_v4(copy.deepcopy(c))
        new = evaluate_challenge(copy.deepcopy(c))
        self.assertEqual(new["result"], old["result"])
        self.assertEqual(new["challenge_genesis"]["genesis_hash"], old["challenge_genesis"]["genesis_hash"])

    def test_equal_order_exact_seam_quotient_certifies(self):
        c = load_math()
        c["seam_quotient_certificate"] = exact_cert([0, 0, "2"], [0, 0, "4"])
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "CERTIFIED")
        self.assertEqual(r["seam_quotient_summary"]["classification"], "FINITE_SEAM_QUOTIENT")
        self.assertEqual(r["seam_quotient_summary"]["quotient"], "1/2")

    def test_numerator_higher_order_gives_zero(self):
        c = load_math()
        c["seam_quotient_certificate"] = exact_cert([0, 0, 3], [0, 5])
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "CERTIFIED")
        self.assertEqual(r["seam_quotient_summary"]["classification"], "FINITE_QUOTIENT_ZERO")
        self.assertEqual(r["seam_quotient_summary"]["quotient"], "0")

    def test_denominator_higher_order_fails_finite_quotient_claim(self):
        c = load_math()
        c["seam_quotient_certificate"] = exact_cert([0, 3], [0, 0, 5])
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "FAILED")
        self.assertEqual(r["seam_quotient_summary"]["classification"], "DIVERGENT_NO_FINITE_QUOTIENT")

    def test_all_zero_denominator_jets_are_incomplete(self):
        c = load_math()
        c["seam_quotient_certificate"] = exact_cert([0, 0, 0], [0, 0, 0])
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "INCOMPLETE")
        self.assertEqual(r["seam_quotient_summary"]["classification"], "INCOMPLETE_FLAT_OR_UNRESOLVED")

    def test_visible_numerator_with_flat_denominator_is_incomplete(self):
        c = load_math()
        c["seam_quotient_certificate"] = exact_cert([0, 1], [0, 0, 0])
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "INCOMPLETE")

    def test_exact_zero_numerator_polynomial_gives_zero(self):
        c = load_math()
        c["seam_quotient_certificate"] = exact_cert([0, 0, 0], [0, 7])
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "CERTIFIED")
        self.assertEqual(r["seam_quotient_summary"]["quotient"], "0")

    def test_nonzero_endpoint_is_invalid_for_zero_over_zero_protocol(self):
        c = load_math()
        c["seam_quotient_certificate"] = exact_cert([1, 2], [0, 3])
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_missing_seam_id_is_invalid(self):
        c = load_math()
        cert = exact_cert([0, 1], [0, 1])
        cert["seam_id"] = ""
        c["seam_quotient_certificate"] = cert
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_approximate_model_is_incomplete_not_trusted(self):
        c = load_math()
        c["seam_quotient_certificate"] = {
            "seam_id": "approx-seam",
            "model": "analytic_with_validated_remainder",
            "numerator_coefficients": [0, 1],
            "denominator_coefficients": [0, 1],
            "claimed_remainder": "1e-30",
        }
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "INCOMPLETE")
        self.assertFalse(r["seam_quotient_summary"]["proof_bearing"])
        self.assertEqual(r["seam_quotient_summary"]["classification"], "INCOMPLETE_REMAINDER_VALIDATION")

    def test_zero_denominator_inside_rational_coefficient_is_invalid(self):
        c = load_math()
        c["seam_quotient_certificate"] = exact_cert([0, "1/2"], [0, "1/0"])
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_seam_certificate_changes_genesis(self):
        c1 = load_math()
        c2 = load_math()
        c1["seam_quotient_certificate"] = exact_cert([0, 2], [0, 4], "seam-a")
        c2["seam_quotient_certificate"] = exact_cert([0, 3], [0, 4], "seam-a")
        r1 = evaluate_challenge(c1)
        r2 = evaluate_challenge(c2)
        self.assertNotEqual(r1["challenge_genesis"]["genesis_hash"], r2["challenge_genesis"]["genesis_hash"])

    def test_seam_genesis_pin_round_trip(self):
        c = load_math()
        c["seam_quotient_certificate"] = exact_cert([0, 2], [0, 4])
        first = evaluate_challenge(copy.deepcopy(c))
        c["genesis"] = {"expected_hash": first["challenge_genesis"]["genesis_hash"]}
        self.assertEqual(evaluate_challenge(c)["result"], "CERTIFIED")

    def test_capabilities_publish_division_boundary(self):
        caps = capabilities()
        self.assertEqual(caps["seam_quotient_protocol"], "first-visible-jet-seam-quotient-v1")
        self.assertEqual(caps["seam_quotient_proof_bearing_model"], "exact_polynomial_jet")
        self.assertIn("INVALID", caps["raw_division_by_zero"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
