"""Tests for the Paninian elision-ledger gates."""
import copy
import unittest

from ai_trust_enablement.paninian_elision_ledger import (
    ADMIT, INCOMPLETE, REJECT, certificate, verify_frame,
)

GOOD = {
    "frame_id": "t",
    "authorities": ["retrieval:corpus-v3"],
    "evidence": [
        {"id": "e1", "authority": "retrieval:corpus-v3", "elided": False, "induces": ["o1"]},
        {"id": "e2", "authority": "retrieval:corpus-v3", "elided": True, "induces": ["o2"]},
    ],
    "obligations": [
        {"id": "o1", "discharged_by": "e1"},
        {"id": "o2", "discharged_by": None, "carried": True},
    ],
    "controls": [{"id": "c1", "passes": True, "passes_under_mutation": False}],
    "claims": [{"id": "k1", "requires": ["o1", "o2"]}],
}


class TestElisionLedger(unittest.TestCase):
    def test_clean_frame_admits(self):
        self.assertEqual(verify_frame(GOOD).verdict, ADMIT)

    def test_pruning_evidence_without_ledger_is_rejected(self):
        """The core failure mode: context pruning drops the item and its obligation."""
        f = copy.deepcopy(GOOD)
        f["obligations"] = [o for o in f["obligations"] if o["id"] != "o2"]
        v = verify_frame(f)
        self.assertEqual(v.verdict, REJECT)
        self.assertTrue(any(r.code == "obligation_lost_with_elision" for r in v.reasons))

    def test_carried_obligation_keeps_the_frame_alive(self):
        f = copy.deepcopy(GOOD)
        f["obligations"][1]["carried"] = False
        self.assertEqual(verify_frame(f).verdict, REJECT)
        f["obligations"][1]["carried"] = True
        self.assertEqual(verify_frame(f).verdict, ADMIT)

    def test_discharger_itself_elided_is_rejected(self):
        f = copy.deepcopy(GOOD)
        f["obligations"][1] = {"id": "o2", "discharged_by": "e2", "carried": False}
        v = verify_frame(f)
        self.assertEqual(v.verdict, REJECT)
        self.assertTrue(any(r.code == "discharger_elided" for r in v.reasons))

    def test_vacuous_control_is_rejected(self):
        f = copy.deepcopy(GOOD)
        f["controls"][0]["passes_under_mutation"] = True
        v = verify_frame(f)
        self.assertEqual(v.verdict, REJECT)
        self.assertIn("c1", v.vacuous_controls)

    def test_control_without_mutation_is_incomplete_not_admit(self):
        f = copy.deepcopy(GOOD)
        del f["controls"][0]["passes_under_mutation"]
        self.assertEqual(verify_frame(f).verdict, INCOMPLETE)

    def test_undeclared_authority_is_incomplete(self):
        f = copy.deepcopy(GOOD)
        del f["evidence"][0]["authority"]
        v = verify_frame(f)
        self.assertEqual(v.verdict, INCOMPLETE)
        self.assertIn("e1", v.undeclared_authorities)

    def test_authority_outside_declared_set_is_incomplete(self):
        f = copy.deepcopy(GOOD)
        f["evidence"][0]["authority"] = "tool:unlisted"
        self.assertEqual(verify_frame(f).verdict, INCOMPLETE)

    def test_certificate_hash_is_stable_and_content_sensitive(self):
        a = certificate(GOOD)["certificate_hash"]
        b = certificate(copy.deepcopy(GOOD))["certificate_hash"]
        self.assertEqual(a, b)
        f = copy.deepcopy(GOOD)
        f["obligations"][1]["carried"] = False
        self.assertNotEqual(a, certificate(f)["certificate_hash"])

    def test_sutra_index_carries_the_new_rules(self):
        from ai_trust_enablement.paninian_meta_engine import derive
        self.assertEqual(derive("1.1.62").rule_id, "1.1.62")
        self.assertEqual(derive("1.3.9").operator, "zero_map")


if __name__ == "__main__":
    unittest.main()
