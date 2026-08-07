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
from strict_json import StrictJSONError, loads_strict


def load_example(name: str) -> dict:
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


class FinalParserLedgerAudit(unittest.TestCase):
    def test_baseline_math_still_certifies(self):
        self.assertEqual(evaluate_challenge(load_example("math_challenge.json"))["result"], "CERTIFIED")

    def test_baseline_nonformal_still_adversarial_passes(self):
        self.assertEqual(evaluate_challenge(load_example("nonformal_behavioral_challenge.json"))["result"], "ADVERSARIAL_PASS")

    def test_baseline_security_still_adversarial_passes(self):
        result = evaluate_challenge(load_example("security_audit_challenge.json"))
        self.assertEqual(result["result"], "ADVERSARIAL_PASS")
        toe = next(x for x in result["checks"] if x["id"] == "scope_toe_binding")
        self.assertEqual(toe["status"], "pass")

    def test_explicit_blank_package_does_not_silently_default(self):
        c = load_example("math_challenge.json")
        c["package"] = ""
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_explicit_null_package_does_not_silently_default(self):
        c = load_example("math_challenge.json")
        c["package"] = None
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_package_path_abuse_is_invalid(self):
        c = load_example("math_challenge.json")
        c["package"] = "../packages/math"
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_explicit_blank_mode_does_not_silently_default(self):
        c = load_example("math_challenge.json")
        c["mode"] = ""
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_explicit_boolean_mode_does_not_silently_default(self):
        c = load_example("math_challenge.json")
        c["mode"] = False
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_duplicate_top_level_json_key_is_rejected(self):
        with self.assertRaises(StrictJSONError):
            loads_strict('{"challenge_id":"x","challenge_id":"y","target":{"statement":"z"}}')

    def test_duplicate_nested_json_key_is_rejected(self):
        with self.assertRaises(StrictJSONError):
            loads_strict('{"challenge_id":"x","target":{"statement":"a","statement":"b"}}')

    def test_duplicate_mode_downgrade_trick_is_rejected(self):
        with self.assertRaises(StrictJSONError):
            loads_strict('{"challenge_id":"x","mode":"certified","mode":"exploratory","target":{"statement":"z"}}')

    def test_nan_token_is_rejected(self):
        with self.assertRaises(StrictJSONError):
            loads_strict('{"challenge_id":"x","target":{"statement":"z"},"burden":{"beta":NaN}}')

    def test_infinity_token_is_rejected(self):
        with self.assertRaises(StrictJSONError):
            loads_strict('{"challenge_id":"x","target":{"statement":"z"},"burden":{"beta":Infinity}}')

    def test_decimal_boundary_01_plus_07_is_not_false_pass(self):
        c = load_example("math_challenge.json")
        c["completion"] = {"enabled": True, "finite_upper": 0.1, "completion_error": 0.7, "threshold": 0.8}
        result = evaluate_challenge(c)
        self.assertEqual(result["result"], "INCOMPLETE")
        check = next(x for x in result["checks"] if x["id"] == "completion")
        self.assertEqual(check["status"], "open")

    def test_decimal_boundary_01_plus_02_is_not_roundoff_failure(self):
        c = load_example("math_challenge.json")
        c["completion"] = {"enabled": True, "finite_upper": 0.1, "completion_error": 0.2, "threshold": 0.3}
        result = evaluate_challenge(c)
        self.assertEqual(result["result"], "INCOMPLETE")
        check = next(x for x in result["checks"] if x["id"] == "completion")
        self.assertEqual(check["status"], "open")

    def test_decimal_strict_reserve_still_passes(self):
        c = load_example("math_challenge.json")
        c["completion"] = {"enabled": True, "finite_upper": 0.1, "completion_error": 0.69, "threshold": 0.8}
        self.assertEqual(evaluate_challenge(c)["result"], "CERTIFIED")

    def test_scoped_security_requires_target_toe(self):
        c = load_example("security_audit_challenge.json")
        c["target"].pop("toe")
        self.assertEqual(evaluate_challenge(c)["result"], "BLOCKED_SCOPE")

    def test_scoped_security_rejects_toe_scope_mismatch(self):
        c = load_example("security_audit_challenge.json")
        c["target"]["toe"] = "different-service"
        self.assertEqual(evaluate_challenge(c)["result"], "BLOCKED_SCOPE")

    def test_package_manifest_is_committed_in_genesis(self):
        r = evaluate_challenge(load_example("math_challenge.json"))
        digest = r["challenge_genesis"]["contract"]["package_manifest_sha256"]
        self.assertEqual(len(digest), 64)
        int(digest, 16)

    def test_capabilities_publish_strict_parser_and_manifest_hashes(self):
        caps = capabilities()
        self.assertTrue(caps["strict_json_input"])
        self.assertTrue(caps["package_manifest_committed_in_genesis"])
        for package in caps["packages"]:
            self.assertEqual(len(package["manifest_sha256"]), 64)

    def test_evaluation_record_is_hash_bound(self):
        r = evaluate_challenge(load_example("math_challenge.json"))
        ev = r["challenge_evaluation"]
        self.assertEqual(ev["genesis_hash"], r["challenge_genesis"]["genesis_hash"])
        self.assertEqual(len(ev["input_sha256"]), 64)
        self.assertEqual(len(ev["evaluation_hash"]), 64)

    def test_status_change_keeps_genesis_but_changes_evaluation_hash(self):
        c1 = load_example("nonformal_behavioral_challenge.json")
        c2 = copy.deepcopy(c1)
        c2["evidence"][0]["status"] = "fail"
        r1 = evaluate_challenge(c1)
        r2 = evaluate_challenge(c2)
        self.assertEqual(r1["challenge_genesis"]["genesis_hash"], r2["challenge_genesis"]["genesis_hash"])
        self.assertNotEqual(r1["challenge_evaluation"]["evaluation_hash"], r2["challenge_evaluation"]["evaluation_hash"])

    def test_rule_change_changes_genesis_and_evaluation_hash(self):
        c1 = load_example("math_challenge.json")
        c2 = copy.deepcopy(c1)
        c2["target"]["statement"] += " changed"
        r1 = evaluate_challenge(c1)
        r2 = evaluate_challenge(c2)
        self.assertNotEqual(r1["challenge_genesis"]["genesis_hash"], r2["challenge_genesis"]["genesis_hash"])
        self.assertNotEqual(r1["challenge_evaluation"]["evaluation_hash"], r2["challenge_evaluation"]["evaluation_hash"])

    def test_valid_parent_evaluation_hash_is_carried(self):
        first = evaluate_challenge(load_example("nonformal_behavioral_challenge.json"))
        parent = first["challenge_evaluation"]["evaluation_hash"]
        c = load_example("nonformal_behavioral_challenge.json")
        c["evaluation"] = {"parent_hash": parent}
        second = evaluate_challenge(c)
        self.assertEqual(second["challenge_evaluation"]["parent_evaluation_hash"], parent)

    def test_malformed_parent_evaluation_hash_is_invalid(self):
        c = load_example("nonformal_behavioral_challenge.json")
        c["evaluation"] = {"parent_hash": "not-a-hash"}
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_malformed_genesis_pin_is_invalid(self):
        c = load_example("math_challenge.json")
        c["genesis"] = {"expected_hash": "abc"}
        self.assertEqual(evaluate_challenge(c)["result"], "INVALID")

    def test_valid_genesis_pin_still_passes(self):
        c = load_example("math_challenge.json")
        first = evaluate_challenge(c)
        c["genesis"] = {"expected_hash": first["challenge_genesis"]["genesis_hash"]}
        self.assertEqual(evaluate_challenge(c)["result"], "CERTIFIED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
