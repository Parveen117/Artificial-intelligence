import copy
import json
import unittest
from pathlib import Path

from challenge_engine.action_gate import action_sha256, evaluate_action_authorization
from challenge_engine.strict_json import loads_strict


ROOT = Path(__file__).resolve().parents[2]


def contract_for(action):
    bound = copy.deepcopy(action)
    action_hash = action_sha256(bound)
    return {
        "protocol": "proof-before-action-v1",
        "principal": "human:red-team-owner",
        "agent": "agent:red-team-candidate",
        "action": copy.deepcopy(action),
        "request_nonce": "red-team-request-0001",
        "committed_state": {
            "epoch": 7,
            "revoked_grant_ids": [],
            "used_request_nonces": [],
        },
        "delegations": [
            {
                "id": "red-team-root",
                "parent_id": None,
                "issuer": "human:red-team-owner",
                "subject": "agent:red-team-candidate",
                "tool": bound["tool"],
                "operation": bound["operation"],
                "resource": bound["resource"],
                "action_sha256": action_hash,
                "valid_from_epoch": 0,
                "valid_until_epoch": 10,
            }
        ],
        "terminal_grant_id": "red-team-root",
        "confirmation_required": False,
    }


class IndependentProofBeforeActionRedTeam(unittest.TestCase):
    """Attack properties not covered by the original directed mutation campaign."""

    def assertNotExecutable(self, contract, label):
        result = evaluate_action_authorization(contract)
        self.assertNotEqual(result["decision"], "ADMIT", (label, result))
        self.assertFalse(result["executable"], (label, result))
        return result

    def test_negative_zero_cannot_reuse_positive_zero_authority(self):
        authorized = {
            "tool": "numeric.execute",
            "operation": "apply",
            "resource": "register:sign-sensitive",
            "parameters": {"value": 0.0},
        }
        contract = contract_for(authorized)
        contract["action"]["parameters"]["value"] = -0.0
        self.assertNotExecutable(contract, "positive-zero authority reused for negative zero")

    def test_float_cannot_reuse_integer_typed_authority(self):
        authorized = {
            "tool": "schema.execute",
            "operation": "apply_integer",
            "resource": "counter:one",
            "parameters": {"value": 1},
        }
        contract = contract_for(authorized)
        contract["action"]["parameters"]["value"] = 1.0
        self.assertNotExecutable(contract, "integer authority reused by float representation")

    def test_non_roundtrippable_decimal_cannot_be_executable(self):
        action = loads_strict(
            '{"tool":"payment.synthetic","operation":"set_amount",'
            '"resource":"wallet:synthetic","parameters":{"amount":9007199254740993.0}}'
        )
        self.assertNotExecutable(
            contract_for(action),
            "declared decimal differs from float-compatible runtime carrier",
        )

    def test_unsafe_cross_runtime_integer_cannot_be_executable(self):
        action = {
            "tool": "payment.synthetic",
            "operation": "set_amount",
            "resource": "wallet:synthetic",
            "parameters": {"amount": 9007199254740993},
        }
        self.assertNotExecutable(
            contract_for(action),
            "integer exceeds the universally safe JSON integer range",
        )

    def test_oversized_request_nonce_fails_closed(self):
        action = {
            "tool": "gmail.send",
            "operation": "send_message",
            "resource": "mailbox:synthetic",
            "parameters": {},
        }
        contract = contract_for(action)
        contract["request_nonce"] = "n" * 65537
        self.assertNotExecutable(contract, "unbounded request nonce")

    def test_oversized_replay_state_fails_closed(self):
        action = {
            "tool": "gmail.send",
            "operation": "send_message",
            "resource": "mailbox:synthetic",
            "parameters": {},
        }
        contract = contract_for(action)
        contract["committed_state"]["used_request_nonces"] = [
            f"used-{index:05d}" for index in range(10001)
        ]
        self.assertNotExecutable(contract, "unbounded replay-state list")

    def test_public_fixture_exercises_replay_control(self):
        manifest = json.loads(
            (ROOT / "red_team_challenge" / "CHALLENGE_MANIFEST.json").read_text(encoding="utf-8")
        )
        fixture = json.loads((ROOT / manifest["baseline_fixture"]).read_text(encoding="utf-8"))
        state = fixture["action_authorization"]["committed_state"]
        self.assertTrue(
            state.get("used_request_nonces"),
            "published replay_escape track is inert when the frozen used-nonce set is empty",
        )

    def test_public_fixture_exercises_confirmation_control(self):
        manifest = json.loads(
            (ROOT / "red_team_challenge" / "CHALLENGE_MANIFEST.json").read_text(encoding="utf-8")
        )
        fixture = json.loads((ROOT / manifest["baseline_fixture"]).read_text(encoding="utf-8"))
        authority = fixture["action_authorization"]
        self.assertIs(
            authority.get("confirmation_required"),
            True,
            "approval is advertised as a mutable attack field but is ignored by the current public fixture",
        )
        self.assertIsInstance(authority.get("approval"), dict)


if __name__ == "__main__":
    unittest.main()
