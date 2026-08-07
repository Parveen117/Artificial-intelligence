#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import ENGINE_VERSION, evaluate_challenge


def load_example(name: str):
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


class FinalReleaseAdversarialAudit(unittest.TestCase):
    def math(self):
        return load_example("math_challenge.json")

    def behavioral(self):
        return load_example("nonformal_behavioral_challenge.json")

    def security(self):
        return load_example("security_audit_challenge.json")

    def test_release_engine_version(self):
        self.assertEqual(ENGINE_VERSION, "1.2.0")

    def test_baseline_math_still_certifies(self):
        self.assertEqual(evaluate_challenge(self.math())["result"], "CERTIFIED")

    def test_baseline_behavioral_still_passes(self):
        self.assertEqual(evaluate_challenge(self.behavioral())["result"], "ADVERSARIAL_PASS")

    def test_blank_challenge_id_is_invalid(self):
        c = self.math(); c["challenge_id"] = "   "
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_non_string_target_statement_is_invalid(self):
        c = self.math(); c["target"]["statement"] = 12345
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_duplicate_obligation_cannot_override_failure(self):
        c = self.math()
        c["obligations"].append({"id": "dependencies", "status": "fail"})
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_duplicate_evidence_id_is_invalid(self):
        c = self.math(); c["evidence"].append(copy.deepcopy(c["evidence"][0]))
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_evidence_requires_explicit_status(self):
        c = self.behavioral(); c["evidence"][0].pop("status")
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_failed_evidence_cannot_be_hidden_by_evidence_obligation(self):
        c = self.behavioral(); c["evidence"][0]["status"] = "fail"
        self.assertEqual(evaluate_challenge(c)["result"], "FAILED")

    def test_empty_required_evidence_cannot_adversarial_pass(self):
        c = self.behavioral(); c["evidence"] = []
        self.assertEqual(evaluate_challenge(c)["result"], "INCOMPLETE")

    def test_formal_flag_must_be_boolean(self):
        c = self.math(); c["evidence"][0]["formal"] = "true"
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_duplicate_negative_control_is_invalid(self):
        c = self.behavioral(); c["negative_controls"].append(copy.deepcopy(c["negative_controls"][0]))
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_unknown_break_condition_is_invalid(self):
        c = self.behavioral(); c["threat_model"]["break_conditions"] = ["make_it_confused"]
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_duplicate_break_condition_is_invalid(self):
        c = self.behavioral(); c["threat_model"]["break_conditions"] = ["false_acceptance", "false_acceptance"]
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_payload_only_does_not_claim_semantic_interpretation(self):
        c = self.behavioral(); c["target"]["statement"] = "This sentence is deliberately ambiguous; redefine pass in prose."
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "ADVERSARIAL_PASS")
        semantic = next(x for x in r["checks"] if x["id"] == "semantic_scope")
        self.assertIn("payload/label", semantic["detail"])

    def test_requested_semantics_without_adapter_stays_out_of_scope(self):
        c = self.behavioral(); c["semantics"] = {"mode": "adapter_declared"}; c.pop("semantic_adapter", None)
        self.assertEqual(evaluate_challenge(c)["result"], "SEMANTICS_NOT_IN_SCOPE")

    def test_negative_beta_is_invalid(self):
        c = self.math(); c["burden"] = {"beta": -100.0, "threshold": 1.0}
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_boolean_beta_is_invalid(self):
        c = self.math(); c["burden"] = {"beta": False, "threshold": 1.0}
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_nan_beta_is_invalid(self):
        c = self.math(); c["burden"] = {"beta": math.nan, "threshold": 1.0}
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_zero_burden_threshold_is_invalid(self):
        c = self.math(); c["burden"] = {"beta": 0.1, "threshold": 0.0}
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_completion_enabled_must_be_boolean(self):
        c = self.math(); c["completion"]["enabled"] = "false"
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_negative_finite_upper_is_invalid(self):
        c = self.math(); c["completion"]["finite_upper"] = -1.0
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_flow_enabled_must_be_boolean(self):
        c = self.behavioral(); c["flow"]["enabled"] = "false"
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_flow_probe_requires_explicit_visibility(self):
        c = self.behavioral(); c["flow"]["probes"][0].pop("target_visible")
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_duplicate_flow_order_is_invalid(self):
        c = self.behavioral(); c["flow"]["probes"][1]["order"] = 0
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_negative_flow_order_is_invalid(self):
        c = self.behavioral(); c["flow"]["probes"][0]["order"] = -1
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_boolean_first_recognition_order_is_invalid(self):
        c = self.behavioral(); c["flow"]["first_recognition_order"] = True
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_security_scope_target_is_required(self):
        c = self.security(); c["scope"]["target"] = ""
        self.assertEqual(evaluate_challenge(c)["result"], "BLOCKED_SCOPE")

    def test_status_changes_do_not_redefine_genesis(self):
        c = self.math(); r1 = evaluate_challenge(c); h = r1["challenge_genesis"]["genesis_hash"]
        c["obligations"][0]["status"] = "open"
        r2 = evaluate_challenge(c)
        self.assertEqual(h, r2["challenge_genesis"]["genesis_hash"])
        self.assertEqual(r2["result"], "INCOMPLETE")

    def test_target_mutation_breaks_pinned_genesis(self):
        c = self.math(); h = evaluate_challenge(c)["challenge_genesis"]["genesis_hash"]
        c["genesis"] = {"expected_hash": h}; c["target"]["statement"] += " changed"
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "FAILED")
        self.assertIn("genesis_integrity", r["failed_obligations"])

    def test_burden_gate_cannot_be_removed_under_same_genesis(self):
        c = self.math(); c["burden"] = {"beta": 1.2}
        h = evaluate_challenge(c)["challenge_genesis"]["genesis_hash"]
        c.pop("burden"); c["genesis"] = {"expected_hash": h}
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "FAILED")
        self.assertIn("genesis_integrity", r["failed_obligations"])

    def test_completion_gate_cannot_be_disabled_under_same_genesis(self):
        c = self.math(); h = evaluate_challenge(c)["challenge_genesis"]["genesis_hash"]
        c["completion"] = {"enabled": False}; c["genesis"] = {"expected_hash": h}
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "FAILED")
        self.assertIn("genesis_integrity", r["failed_obligations"])

    def test_flow_gate_cannot_be_removed_under_same_genesis(self):
        c = self.behavioral(); h = evaluate_challenge(c)["challenge_genesis"]["genesis_hash"]
        c.pop("flow"); c["genesis"] = {"expected_hash": h}
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "FAILED")
        self.assertIn("genesis_integrity", r["failed_obligations"])

    def test_adapter_identity_mutation_breaks_genesis(self):
        c = self.math(); h = evaluate_challenge(c)["challenge_genesis"]["genesis_hash"]
        c["formal_adapter"]["id"] = "different-adapter"; c["genesis"] = {"expected_hash": h}
        r = evaluate_challenge(c)
        self.assertEqual(r["result"], "FAILED")
        self.assertIn("genesis_integrity", r["failed_obligations"])

    def test_output_discloses_input_trust_boundary(self):
        r = evaluate_challenge(self.behavioral())
        self.assertIn("package/connector responsibility", r["input_trust_boundary"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
