#!/usr/bin/env python3
"""
Paninian Elision Ledger
=======================

Three verification gates that the existing Paninian layer did not carry, each
translated from a grammatical rule into a concrete failure mode of evidence-gated
AI systems. No dependencies; same canonical-JSON / SHA-256 certificate discipline
as the rest of `ai_trust_enablement`.

GATE 1 — ELISION LEDGER (1.1.62 `pratyayalope pratyayalaksanam`)
----------------------------------------------------------------
The grammatical rule: when an affix is elided, the operations it conditioned still
apply. Elision removes the element, not its effect.

The engineering failure it names: an agent's context is pruned, summarized,
compressed, or re-chunked between the moment a claim acquired its support and the
moment the claim is acted on. The supporting item disappears; the claim keeps the
authority it drew from that item. Every retrieval-augmented and long-horizon agent
stack does this by construction, and nothing in a plain evidence check catches it,
because after pruning the frame simply looks smaller.

The gate: every evidence item may be elided, but each obligation it induced must
still be discharged by something present, or be explicitly carried in the ledger as
an outstanding obligation. Elision without a ledger entry is a REJECT, not a
smaller frame. (Compare 1.1.16-style protection, already in the index: that
protects an element from deletion; this one lets the element go and holds onto
its effect.)

GATE 2 — NON-VACUOUS CONTROL (`anitya` discipline, 1.1.35 neighbourhood)
------------------------------------------------------------------------
A check that cannot fail is not evidence. Every control shipped with a claim must
flip its verdict under a declared planted mutation; if it does not, the control is
reported VACUOUS and contributes nothing to admission. This is a rule about the
verifier's own claims, which is where verification systems are weakest.

GATE 3 — PROVENANCE SWEEP (1.1.32 `samjna` neighbourhood)
----------------------------------------------------------
A designation must say who defines it. Each object in a frame declares the
authority that defines it; an object whose defining authority is undeclared, or is
outside the frame's declared authority set, yields INCOMPLETE — not REJECT, since
undeclared provenance is a gap rather than a contradiction.

Interface follows the repository's kernel shape:

    verify_frame(frame) -> ADMIT | REJECT | INCOMPLETE  (+ reasons, + certificate)

Frame schema (all fields optional except `claims`):

    {
      "frame_id": "...",
      "authorities": ["retrieval:corpus-v3", "tool:calculator"],
      "evidence": [
         {"id": "e1", "authority": "retrieval:corpus-v3", "elided": false,
          "induces": ["o1"]},
         {"id": "e2", "authority": "retrieval:corpus-v3", "elided": true,
          "induces": ["o2"]}
      ],
      "obligations": [
         {"id": "o1", "discharged_by": "e1"},
         {"id": "o2", "discharged_by": null, "carried": true}
      ],
      "controls": [
         {"id": "c1", "passes": true, "passes_under_mutation": false}
      ],
      "claims": [{"id": "k1", "requires": ["o1", "o2"]}]
    }
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

ADMIT = "ADMIT"
REJECT = "REJECT"
INCOMPLETE = "INCOMPLETE"

RULE_ELISION_LEDGER = "1.1.62"
RULE_NONVACUOUS = "1.1.35"
RULE_PROVENANCE = "1.1.32"


@dataclass(frozen=True)
class Reason:
    rule_id: str
    code: str
    subject: str
    detail: str


@dataclass
class FrameVerdict:
    frame_id: str
    verdict: str
    reasons: List[Reason] = field(default_factory=list)
    elided_with_ledger: List[str] = field(default_factory=list)
    vacuous_controls: List[str] = field(default_factory=list)
    undeclared_authorities: List[str] = field(default_factory=list)
    certificate_hash: str = ""


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def _index(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(it.get("id")): it for it in items or []}


def check_elision_ledger(frame: Dict[str, Any]) -> Tuple[List[Reason], List[str]]:
    """1.1.62: elision removes the element, never its induced obligation."""
    reasons: List[Reason] = []
    ledgered: List[str] = []
    evidence = _index(frame.get("evidence", []))
    obligations = _index(frame.get("obligations", []))
    for eid, ev in evidence.items():
        induced = [str(o) for o in ev.get("induces", [])]
        if not ev.get("elided"):
            continue
        for oid in induced:
            ob = obligations.get(oid)
            if ob is None:
                reasons.append(Reason(
                    RULE_ELISION_LEDGER, "obligation_lost_with_elision", oid,
                    f"evidence {eid} was elided and the obligation it induced is absent from the ledger"))
                continue
            discharger = ob.get("discharged_by")
            carried = bool(ob.get("carried"))
            if discharger is not None:
                d = evidence.get(str(discharger))
                if d is None or d.get("elided"):
                    reasons.append(Reason(
                        RULE_ELISION_LEDGER, "discharger_elided", oid,
                        f"obligation {oid} is discharged by {discharger}, which is absent or elided"))
                    continue
                ledgered.append(oid)
            elif carried:
                ledgered.append(oid)
            else:
                reasons.append(Reason(
                    RULE_ELISION_LEDGER, "obligation_neither_discharged_nor_carried", oid,
                    f"evidence {eid} was elided; obligation {oid} is neither discharged nor carried"))
    return reasons, sorted(set(ledgered))


def check_controls(frame: Dict[str, Any]) -> Tuple[List[Reason], List[str]]:
    """A control that cannot fail is not evidence."""
    reasons: List[Reason] = []
    vacuous: List[str] = []
    for ctl in frame.get("controls", []) or []:
        cid = str(ctl.get("id"))
        if not ctl.get("passes", False):
            reasons.append(Reason(RULE_NONVACUOUS, "control_failed", cid, "declared control does not pass"))
            continue
        if "passes_under_mutation" not in ctl:
            reasons.append(Reason(RULE_NONVACUOUS, "control_mutation_undeclared", cid,
                                  "control ships no planted mutation, so its discriminating power is unknown"))
            vacuous.append(cid)
        elif ctl.get("passes_under_mutation"):
            reasons.append(Reason(RULE_NONVACUOUS, "control_vacuous", cid,
                                  "control still passes under its own planted mutation: it cannot fail"))
            vacuous.append(cid)
    return reasons, sorted(set(vacuous))


def check_provenance(frame: Dict[str, Any]) -> Tuple[List[Reason], List[str]]:
    """Every defined object must name the authority that defines it."""
    reasons: List[Reason] = []
    undeclared: List[str] = []
    declared = set(frame.get("authorities", []) or [])
    for ev in frame.get("evidence", []) or []:
        eid = str(ev.get("id"))
        auth = ev.get("authority")
        if not auth:
            reasons.append(Reason(RULE_PROVENANCE, "authority_undeclared", eid,
                                  "object does not name the authority that defines it"))
            undeclared.append(eid)
        elif declared and auth not in declared:
            reasons.append(Reason(RULE_PROVENANCE, "authority_outside_frame", eid,
                                  f"authority {auth} is not in the frame's declared authority set"))
            undeclared.append(eid)
    return reasons, sorted(set(undeclared))


def check_claims(frame: Dict[str, Any]) -> List[Reason]:
    reasons: List[Reason] = []
    obligations = _index(frame.get("obligations", []))
    for claim in frame.get("claims", []) or []:
        kid = str(claim.get("id"))
        for oid in [str(o) for o in claim.get("requires", [])]:
            if oid not in obligations:
                reasons.append(Reason(RULE_ELISION_LEDGER, "required_obligation_absent", kid,
                                      f"claim requires obligation {oid}, absent from the ledger"))
    return reasons


def verify_frame(frame: Dict[str, Any]) -> FrameVerdict:
    e_reasons, ledgered = check_elision_ledger(frame)
    c_reasons, vacuous = check_controls(frame)
    p_reasons, undeclared = check_provenance(frame)
    k_reasons = check_claims(frame)

    reasons = e_reasons + c_reasons + p_reasons + k_reasons
    hard = [r for r in reasons if r.code in {
        "obligation_lost_with_elision", "discharger_elided",
        "obligation_neither_discharged_nor_carried", "required_obligation_absent",
        "control_failed", "control_vacuous"}]
    soft = [r for r in reasons if r not in hard]

    if hard:
        verdict = REJECT
    elif soft:
        verdict = INCOMPLETE
    else:
        verdict = ADMIT

    body = {
        "frame_id": frame.get("frame_id", ""),
        "verdict": verdict,
        "reasons": [asdict(r) for r in reasons],
        "elided_with_ledger": ledgered,
        "vacuous_controls": vacuous,
        "undeclared_authorities": undeclared,
    }
    return FrameVerdict(
        frame_id=str(frame.get("frame_id", "")),
        verdict=verdict,
        reasons=reasons,
        elided_with_ledger=ledgered,
        vacuous_controls=vacuous,
        undeclared_authorities=undeclared,
        certificate_hash=sha256_json(body),
    )


def certificate(frame: Dict[str, Any]) -> Dict[str, Any]:
    v = verify_frame(frame)
    return {
        "certificate_type": "PANINIAN_ELISION_LEDGER_V1",
        "frame_id": v.frame_id,
        "verdict": v.verdict,
        "rules_applied": [RULE_ELISION_LEDGER, RULE_NONVACUOUS, RULE_PROVENANCE],
        "reasons": [asdict(r) for r in v.reasons],
        "elided_with_ledger": v.elided_with_ledger,
        "vacuous_controls": v.vacuous_controls,
        "undeclared_authorities": v.undeclared_authorities,
        "certificate_hash": v.certificate_hash,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Paninian elision-ledger frame verifier")
    parser.add_argument("--frame", help="path to a frame JSON file")
    parser.add_argument("--json", action="store_true", help="emit the certificate as JSON")
    args = parser.parse_args()
    if args.frame:
        frame = json.load(open(args.frame))
    else:
        frame = {
            "frame_id": "demo",
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
    cert = certificate(frame)
    if args.json:
        print(canonical_json(cert))
    else:
        print(f"{cert['verdict']}  ({len(cert['reasons'])} reasons)")
        for r in cert["reasons"]:
            print(f"  [{r['rule_id']}] {r['code']}: {r['subject']} — {r['detail']}")


if __name__ == "__main__":
    main()
