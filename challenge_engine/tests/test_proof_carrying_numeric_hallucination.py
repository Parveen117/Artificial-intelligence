import unittest

from challenge_engine.engine import evaluate_challenge, capabilities


def base_challenge():
    return {
        "schema_version": "1.0",
        "challenge_id": "proof-carrying-numeric-demo",
        "package": "math",
        "mode": "certified",
        "target": {"statement": "certify a strict numerical bound"},
        "evidence": [{"id": "formal", "kind": "formal", "status": "pass"}],
        "obligations": [{"id": "formal_support", "status": "pass"}],
        "formal_adapter": {"id": "exact-trace-adapter", "status": "pass"},
    }


def exact_trace(upper="3/4", threshold="4/5"):
    return {
        "protocol": "proof-carrying-numeric-closure-v1",
        "source_complete": True,
        "root": "root",
        "threshold": threshold,
        "tail": {"rule": "zero"},
        "nodes": [
            {"id": "a", "kind": "exact_contract", "value": "1/2", "interval": ["1/2", "1/2"]},
            {"id": "b", "kind": "exact_contract", "value": "1/4", "interval": ["1/4", "1/4"]},
            {"id": "root", "kind": "op", "op": "add", "deps": ["a", "b"], "interval": ["3/4", upper]},
        ],
    }


class ProofCarryingNumericHallucinationTests(unittest.TestCase):
    def test_exact_trace_certifies(self):
        c = base_challenge()
        c["proof_carrying_numeric"] = exact_trace()
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "CERTIFIED")
        self.assertEqual(r["proof_carrying_numeric_summary"]["classification"], "CERTIFIED_NUMERIC_CLOSURE")
        self.assertEqual(r["math_hallucination_class"], "formal_numeric_overclaim")

    def test_forged_narrow_root_fails(self):
        c = base_challenge()
        trace = exact_trace(upper="7/10")
        trace["nodes"][-1]["interval"] = ["7/10", "7/10"]
        c["proof_carrying_numeric"] = trace
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "FAILED")

    def test_zero_denominator_enclosure_fails(self):
        c = base_challenge()
        c["proof_carrying_numeric"] = {
            "source_complete": True,
            "root": "q",
            "threshold": "10",
            "nodes": [
                {"id": "n", "kind": "exact_contract", "value": "1", "interval": ["1", "1"]},
                {"id": "d", "kind": "exact_contract", "value": "0", "interval": ["-1", "1"]},
                {"id": "q", "kind": "op", "op": "div", "deps": ["n", "d"], "interval": ["-100", "100"]},
            ],
        }
        self.assertEqual(evaluate_challenge(c)["result"], "FAILED")

    def test_open_source_completeness_is_incomplete(self):
        c = base_challenge()
        trace = exact_trace()
        trace["source_complete"] = False
        c["proof_carrying_numeric"] = trace
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "INCOMPLETE")
        self.assertEqual(r["proof_carrying_numeric_summary"]["classification"], "INCOMPLETE_BLIND_DEPENDENCY")

    def test_exact_equality_fails_strict_claim(self):
        c = base_challenge()
        c["proof_carrying_numeric"] = exact_trace(threshold="3/4")
        self.assertEqual(evaluate_challenge(c)["result"], "FAILED")

    def test_uncertain_boundary_touch_is_incomplete(self):
        c = base_challenge()
        trace = exact_trace(upper="4/5", threshold="4/5")
        c["proof_carrying_numeric"] = trace
        self.assertEqual(evaluate_challenge(c)["result"], "INCOMPLETE")

    def test_geometric_tail_is_recomputed(self):
        c = base_challenge()
        trace = exact_trace(upper="3/4", threshold="1")
        trace["tail"] = {"rule": "geometric_tail", "first_omitted_upper": "1/100", "ratio_upper": "1/2"}
        c["proof_carrying_numeric"] = trace
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "CERTIFIED")
        self.assertEqual(r["proof_carrying_numeric_summary"]["analytic_tail"], "1/50")

    def test_unadmitted_tail_rule_is_incomplete(self):
        c = base_challenge()
        trace = exact_trace()
        trace["tail"] = {"rule": "participant_claim", "value": "0"}
        c["proof_carrying_numeric"] = trace
        self.assertEqual(evaluate_challenge(c)["result"], "INCOMPLETE")

    def test_legacy_ball_radius_cannot_self_certify(self):
        c = base_challenge()
        c["arithmetic_certificate"] = {
            "kind": "ball", "center": "0.7", "radius": "0.01", "analytic_tail": "0.01", "threshold": "0.8"
        }
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "INCOMPLETE")
        self.assertIn("proof_carrying_numeric", r["open_obligations"])

    def test_legacy_exact_zero_tail_stays_compatible(self):
        c = base_challenge()
        c["arithmetic_certificate"] = {
            "kind": "exact_rational", "numerator": "3", "denominator": "4", "analytic_tail": "0", "threshold": "4/5"
        }
        self.assertEqual(evaluate_challenge(c)["result"], "CERTIFIED")

    def test_capabilities_publish_math_hallucination_role(self):
        caps = capabilities()
        self.assertEqual(caps["proof_carrying_numeric_protocol"], "proof-carrying-numeric-closure-v1")
        self.assertEqual(caps["math_hallucination_numeric_class"], "formal_numeric_overclaim")
        self.assertEqual(len(caps["numeric_validator_manifest_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
