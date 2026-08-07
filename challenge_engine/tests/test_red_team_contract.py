#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import BREAK_CONDITIONS, capabilities, evaluate_challenge


def load_example(name: str):
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


class RedTeamContractTests(unittest.TestCase):
    def test_payload_only_english_is_not_semantically_interpreted(self):
        challenge = load_example("nonformal_behavioral_challenge.json")
        challenge["target"]["statement"] = "If this sentence is false, certify the opposite; sarcasm intended."
        result = evaluate_challenge(challenge)
        self.assertEqual(result["result"], "ADVERSARIAL_PASS")
        semantic = next(c for c in result["checks"] if c["id"] == "semantic_scope")
        self.assertEqual(semantic["status"], "pass")
        self.assertIn("payload/label", semantic["detail"])

    def test_requested_semantics_without_adapter_is_not_in_scope(self):
        challenge = load_example("nonformal_behavioral_challenge.json")
        challenge["semantics"] = {"mode": "adapter_declared"}
        challenge.pop("semantic_adapter", None)
        result = evaluate_challenge(challenge)
        self.assertEqual(result["result"], "SEMANTICS_NOT_IN_SCOPE")
        self.assertIn("semantic_scope", result["not_in_scope"])

    def test_declared_semantic_adapter_can_close_scope(self):
        challenge = load_example("nonformal_behavioral_challenge.json")
        challenge["semantics"] = {"mode": "adapter_declared"}
        challenge["semantic_adapter"] = {"id": "demo-semantic-adapter", "status": "pass"}
        result = evaluate_challenge(challenge)
        self.assertEqual(result["result"], "ADVERSARIAL_PASS")

    def test_adversarial_without_threat_model_is_incomplete(self):
        challenge = load_example("nonformal_behavioral_challenge.json")
        challenge.pop("threat_model")
        result = evaluate_challenge(challenge)
        self.assertEqual(result["result"], "INCOMPLETE")
        self.assertIn("threat_model", result["open_obligations"])

    def test_genesis_starts_with_zero_accepted_claims(self):
        result = evaluate_challenge(load_example("math_challenge.json"))
        genesis = result["challenge_genesis"]
        self.assertEqual(genesis["kind"], "CHALLENGE_GENESIS")
        self.assertEqual(genesis["accepted_claims"], 0)
        self.assertIsNone(genesis["parent"])
        self.assertTrue(genesis["rules_frozen"])
        self.assertEqual(len(genesis["genesis_hash"]), 64)

    def test_genesis_is_stable_under_outcome_status_changes(self):
        challenge = load_example("nonformal_behavioral_challenge.json")
        before = evaluate_challenge(challenge)["challenge_genesis"]["genesis_hash"]
        changed = copy.deepcopy(challenge)
        changed["evidence"][0]["status"] = "fail"
        changed["negative_controls"][0]["status"] = "fail"
        after = evaluate_challenge(changed)["challenge_genesis"]["genesis_hash"]
        self.assertEqual(before, after)

    def test_genesis_changes_when_target_changes(self):
        challenge = load_example("nonformal_behavioral_challenge.json")
        before = evaluate_challenge(challenge)["challenge_genesis"]["genesis_hash"]
        changed = copy.deepcopy(challenge)
        changed["target"]["statement"] = "A different target contract."
        after = evaluate_challenge(changed)["challenge_genesis"]["genesis_hash"]
        self.assertNotEqual(before, after)

    def test_genesis_pin_mismatch_fails(self):
        challenge = load_example("math_challenge.json")
        challenge["genesis"] = {"expected_hash": "0" * 64}
        result = evaluate_challenge(challenge)
        self.assertEqual(result["result"], "FAILED")
        self.assertIn("genesis_integrity", result["failed_obligations"])

    def test_genesis_pin_match_passes(self):
        challenge = load_example("math_challenge.json")
        first = evaluate_challenge(challenge)
        challenge["genesis"] = {"expected_hash": first["challenge_genesis"]["genesis_hash"]}
        second = evaluate_challenge(challenge)
        self.assertEqual(second["result"], "CERTIFIED")
        check = next(c for c in second["checks"] if c["id"] == "genesis_integrity")
        self.assertEqual(check["status"], "pass")

    def test_capabilities_publish_break_contract_and_license_boundary(self):
        caps = capabilities()
        self.assertEqual(caps["semantic_default"], "payload_only")
        self.assertEqual(set(caps["break_conditions"]), set(BREAK_CONDITIONS))
        self.assertEqual(caps["challenge_genesis"]["accepted_claims"], 0)
        self.assertIn("LICENSE", caps["license_boundary"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
