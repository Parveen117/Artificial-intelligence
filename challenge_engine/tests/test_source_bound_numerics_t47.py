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


def load_math() -> dict:
    return json.loads((ROOT / "examples" / "math_challenge.json").read_text(encoding="utf-8"))


def exact_leaf(node_id: str, value: str, lower: str | None = None, upper: str | None = None) -> dict:
    lower = value if lower is None else lower
    upper = value if upper is None else upper
    return {
        "id": node_id,
        "kind": "exact_contract",
        "value": value,
        "interval": {"lower": lower, "upper": upper},
    }


def op_node(node_id: str, op: str, deps: list[str], lower: str, upper: str) -> dict:
    return {
        "id": node_id,
        "kind": "op",
        "op": op,
        "deps": deps,
        "interval": {"lower": lower, "upper": upper},
    }


def source_cert(nodes: list[dict], root: str, threshold: str = "4/5", tail: dict | None = None) -> dict:
    return {
        "protocol": "source-bound-proof-carrying-numerics-v1",
        "source_model": "exact_expression_v1",
        "nodes": nodes,
        "root": root,
        "tail": {"rule": "zero"} if tail is None else tail,
        "threshold": threshold,
    }


class SourceBoundNumericsT47Tests(unittest.TestCase):
    def test_exact_dag_certifies(self):
        c = load_math()
        c["source_bound_numerics"] = source_cert([
            exact_leaf("a", "1/3"),
            exact_leaf("b", "1/6"),
            op_node("root", "add", ["a", "b"], "1/2", "1/2"),
        ], "root")
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "CERTIFIED")
        self.assertTrue(r["source_bound_numerics_summary"]["proof_bearing"])
        self.assertEqual(r["source_bound_numerics_summary"]["final_upper"], "1/2")

    def test_wider_verified_root_derives_radius(self):
        c = load_math()
        c["source_bound_numerics"] = source_cert([
            exact_leaf("a", "1/3"),
            exact_leaf("b", "1/6"),
            op_node("root", "add", ["a", "b"], "49/100", "51/100"),
        ], "root")
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "CERTIFIED")
        self.assertEqual(r["source_bound_numerics_summary"]["arithmetic_radius"], "1/100")

    def test_forged_narrow_node_fails(self):
        c = load_math()
        c["source_bound_numerics"] = source_cert([
            exact_leaf("a", "1/3"),
            exact_leaf("b", "1/6"),
            op_node("root", "add", ["a", "b"], "49/100", "49/100"),
        ], "root")
        self.assertEqual(evaluate_challenge(c)["result"], "FAILED")

    def test_division_interval_containing_zero_fails(self):
        c = load_math()
        c["source_bound_numerics"] = source_cert([
            exact_leaf("one", "1"),
            exact_leaf("zero", "0", "-1", "1"),
            op_node("root", "div", ["one", "zero"], "-10", "10"),
        ], "root")
        self.assertEqual(evaluate_challenge(c)["result"], "FAILED")

    def test_duplicate_node_id_invalid(self):
        c = load_math()
        c["source_bound_numerics"] = source_cert([
            exact_leaf("a", "1"),
            exact_leaf("a", "2"),
        ], "a")
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_forward_dependency_or_cycle_invalid(self):
        c = load_math()
        c["source_bound_numerics"] = source_cert([
            op_node("a", "neg", ["b"], "-1", "1"),
            op_node("b", "neg", ["a"], "-1", "1"),
        ], "a")
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_unsupported_source_model_is_incomplete(self):
        c = load_math()
        cert = source_cert([exact_leaf("root", "1/2")], "root")
        cert["source_model"] = "external_backend_claim"
        c["source_bound_numerics"] = cert
        self.assertEqual(evaluate_challenge(c)["result"], "INCOMPLETE")

    def test_geometric_tail_is_recomputed(self):
        c = load_math()
        c["source_bound_numerics"] = source_cert([
            exact_leaf("root", "7/10"),
            exact_leaf("first", "1/100"),
            exact_leaf("ratio", "1/2"),
        ], "root", tail={
            "rule": "geometric_tail",
            "first_omitted_node": "first",
            "ratio_upper_node": "ratio",
        })
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "CERTIFIED")
        self.assertEqual(r["source_bound_numerics_summary"]["analytic_tail"], "1/50")
        self.assertEqual(r["source_bound_numerics_summary"]["final_upper"], "18/25")

    def test_bad_geometric_ratio_fails(self):
        c = load_math()
        c["source_bound_numerics"] = source_cert([
            exact_leaf("root", "1/2"),
            exact_leaf("first", "1/100"),
            exact_leaf("ratio", "1"),
        ], "root", tail={
            "rule": "geometric_tail",
            "first_omitted_node": "first",
            "ratio_upper_node": "ratio",
        })
        self.assertEqual(evaluate_challenge(c)["result"], "FAILED")

    def test_exact_threshold_equality_fails_strict_claim(self):
        c = load_math()
        c["source_bound_numerics"] = source_cert([exact_leaf("root", "4/5")], "root")
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "FAILED")
        self.assertEqual(r["source_bound_numerics_summary"]["classification"], "EXACT_BOUNDARY_FAIL")

    def test_uncertain_boundary_touch_is_incomplete(self):
        c = load_math()
        c["source_bound_numerics"] = source_cert([
            exact_leaf("root", "79/100", "79/100", "4/5"),
        ], "root")
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "INCOMPLETE")
        self.assertEqual(r["source_bound_numerics_summary"]["classification"], "INCOMPLETE_BOUNDARY")

    def test_legacy_ball_no_longer_certifies(self):
        c = load_math()
        c["arithmetic_certificate"] = {
            "kind": "ball",
            "center": "0.70",
            "radius": "0.01",
            "analytic_tail": "0.01",
            "threshold": "0.80",
        }
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "INCOMPLETE")
        self.assertFalse(r["arithmetic_summary"]["proof_bearing"])

    def test_legacy_exact_zero_tail_still_certifies(self):
        c = load_math()
        c["arithmetic_certificate"] = {
            "kind": "exact_rational",
            "numerator": "7",
            "denominator": "10",
            "analytic_tail": "0",
            "threshold": "4/5",
        }
        self.assertEqual(evaluate_challenge(c)["result"], "CERTIFIED")

    def test_legacy_exact_nonzero_tail_is_incomplete(self):
        c = load_math()
        c["arithmetic_certificate"] = {
            "kind": "exact_rational",
            "numerator": "7",
            "denominator": "10",
            "analytic_tail": "1/100",
            "threshold": "4/5",
        }
        self.assertEqual(evaluate_challenge(c)["result"], "INCOMPLETE")

    def test_legacy_exact_boundary_is_failed_not_open(self):
        c = load_math()
        c["arithmetic_certificate"] = {
            "kind": "exact_decimal",
            "value": "0.8",
            "analytic_tail": "0",
            "threshold": "0.8",
        }
        self.assertEqual(evaluate_challenge(c)["result"], "FAILED")

    def test_source_bound_and_legacy_arithmetic_are_mutually_exclusive(self):
        c = load_math()
        c["source_bound_numerics"] = source_cert([exact_leaf("root", "1/2")], "root")
        c["arithmetic_certificate"] = {
            "kind": "exact_decimal", "value": "0.5", "analytic_tail": "0", "threshold": "0.8"
        }
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_genesis_commits_implementation_fingerprint(self):
        c = load_math()
        r = evaluate_challenge(c)
        fingerprint = r["implementation_manifest_sha256"]
        self.assertEqual(len(fingerprint), 64)
        self.assertEqual(r["challenge_genesis"]["contract"]["implementation_manifest_sha256"], fingerprint)

    def test_genesis_pin_round_trip_after_fingerprint(self):
        c = load_math()
        first = evaluate_challenge(copy.deepcopy(c))
        c["genesis"] = {"expected_hash": first["challenge_genesis"]["genesis_hash"]}
        self.assertEqual(evaluate_challenge(c)["result"], "CERTIFIED")

    def test_capabilities_publish_t47_protocol(self):
        caps = capabilities()
        self.assertEqual(caps["source_bound_numerics_protocol"], "source-bound-proof-carrying-numerics-v1")
        self.assertEqual(caps["legacy_approximate_arithmetic_without_source_proof"], "INCOMPLETE")
        self.assertEqual(caps["strict_exact_threshold_equality"], "FAILED")
        self.assertEqual(len(caps["implementation_manifest_sha256"]), 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
