#!/usr/bin/env python3
"""
Claim Repair Engine
===================

Converts AI trust certificates into repair actions.

This is the next layer after detection:
    - keep supported claims
    - replace contradicted claims with best evidence
    - remove unsupported claims
    - request retrieval for uncertain/no-evidence claims
    - emit deterministic repair certificate
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from .fusion_certificate_engine import FusionCertificateEngine
except ImportError:
    from fusion_certificate_engine import FusionCertificateEngine


KEEP = "KEEP"
REPLACE_WITH_EVIDENCE = "REPLACE_WITH_EVIDENCE"
REMOVE_UNSUPPORTED = "REMOVE_UNSUPPORTED"
RETRIEVE_MORE_EVIDENCE = "RETRIEVE_MORE_EVIDENCE"
NO_SAFE_ANSWER = "NO_SAFE_ANSWER"

SUPPORTED_PREFIX = "SUPPORTED"
CONTRADICTED_PREFIX = "CONTRADICTED"
UNSUPPORTED_PREFIX = "UNSUPPORTED"
UNCERTAIN_PREFIX = "UNCERTAIN"


@dataclass(frozen=True)
class ClaimRepairAction:
    claim_frame_id: str
    original_claim: str
    classification: str
    action: str
    evidence_frame_id: Optional[str]
    evidence_text: Optional[str]
    repaired_text: Optional[str]
    reason_tags: Tuple[str, ...]


@dataclass(frozen=True)
class RepairCertificate:
    version: str
    engine: str
    context_hash: str
    prompt_hash: str
    answer_hash: str
    original_answer: str
    safe_answer: str
    final_repair_action: str
    fusion_decision: Dict[str, Any]
    kept_claims: Tuple[Dict[str, Any], ...]
    corrected_claims: Tuple[Dict[str, Any], ...]
    removed_claims: Tuple[Dict[str, Any], ...]
    retrieval_needed: Tuple[Dict[str, Any], ...]
    repair_actions: Tuple[Dict[str, Any], ...]
    repair_hash: str


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


def clean_sentence(text: str) -> str:
    text = " ".join(str(text or "").strip().split())
    if not text:
        return ""
    if text[-1] not in ".!?":
        text += "."
    return text


def unique_preserve_order(items: Sequence[str]) -> Tuple[str, ...]:
    seen = set()
    out: List[str] = []
    for item in items:
        cleaned = clean_sentence(item)
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            out.append(cleaned)
    return tuple(out)


class ClaimRepairEngine:
    def __init__(self) -> None:
        self.fusion_engine = FusionCertificateEngine()

    def repair(
        self,
        context: str,
        prompt: str,
        answer: str,
        model_id: str = "model-under-test",
    ) -> RepairCertificate:
        fusion_certificate = asdict(
            self.fusion_engine.evaluate(
                context=context,
                prompt=prompt,
                answer=answer,
                model_id=model_id,
            )
        )

        frame_level = fusion_certificate.get("frame_level", {})
        claim_frames = {
            frame["frame_id"]: frame
            for frame in frame_level.get("claim_frames", [])
        }
        evidence_frames = {
            frame["frame_id"]: frame
            for frame in frame_level.get("evidence_frames", [])
        }

        kept: List[Dict[str, Any]] = []
        corrected: List[Dict[str, Any]] = []
        removed: List[Dict[str, Any]] = []
        retrieval: List[Dict[str, Any]] = []
        actions: List[ClaimRepairAction] = []
        safe_parts: List[str] = []

        for match in frame_level.get("matches", []):
            claim_id = match.get("claim_frame_id")
            evidence_id = match.get("evidence_frame_id")
            classification = str(match.get("classification", "UNKNOWN"))
            claim = claim_frames.get(claim_id, {})
            evidence = evidence_frames.get(evidence_id, {}) if evidence_id else {}

            claim_text = clean_sentence(claim.get("text", ""))
            evidence_text = clean_sentence(evidence.get("text", "")) if evidence else None
            reason_tags = tuple(match.get("reason_tags", ()) or ())

            if classification.startswith(SUPPORTED_PREFIX):
                repaired_text = claim_text
                safe_parts.append(repaired_text)
                kept.append({
                    "claim_frame_id": claim_id,
                    "claim_text": claim_text,
                    "classification": classification,
                })
                action = KEEP

            elif classification.startswith(CONTRADICTED_PREFIX):
                if evidence_text:
                    repaired_text = evidence_text
                    safe_parts.append(repaired_text)
                    corrected.append({
                        "claim_frame_id": claim_id,
                        "original_claim": claim_text,
                        "replacement": evidence_text,
                        "classification": classification,
                    })
                    action = REPLACE_WITH_EVIDENCE
                else:
                    repaired_text = None
                    removed.append({
                        "claim_frame_id": claim_id,
                        "claim_text": claim_text,
                        "classification": classification,
                    })
                    action = REMOVE_UNSUPPORTED

            elif classification.startswith(UNSUPPORTED_PREFIX):
                repaired_text = None
                if classification == "UNSUPPORTED_NO_EVIDENCE":
                    retrieval.append({
                        "claim_frame_id": claim_id,
                        "claim_text": claim_text,
                        "classification": classification,
                    })
                    action = RETRIEVE_MORE_EVIDENCE
                else:
                    removed.append({
                        "claim_frame_id": claim_id,
                        "claim_text": claim_text,
                        "classification": classification,
                    })
                    action = REMOVE_UNSUPPORTED

            elif classification.startswith(UNCERTAIN_PREFIX):
                repaired_text = None
                retrieval.append({
                    "claim_frame_id": claim_id,
                    "claim_text": claim_text,
                    "classification": classification,
                    "reason": "uncertain_route_closure",
                })
                action = RETRIEVE_MORE_EVIDENCE

            else:
                repaired_text = None
                retrieval.append({
                    "claim_frame_id": claim_id,
                    "claim_text": claim_text,
                    "classification": classification,
                    "reason": "unknown_classification",
                })
                action = RETRIEVE_MORE_EVIDENCE

            actions.append(
                ClaimRepairAction(
                    claim_frame_id=str(claim_id),
                    original_claim=claim_text,
                    classification=classification,
                    action=action,
                    evidence_frame_id=evidence_id,
                    evidence_text=evidence_text,
                    repaired_text=repaired_text,
                    reason_tags=reason_tags,
                )
            )

        safe_sentences = unique_preserve_order(safe_parts)

        if safe_sentences:
            safe_answer = " ".join(safe_sentences)
        elif retrieval:
            safe_answer = "Insufficient supplied evidence to answer safely."
        else:
            safe_answer = "No safe answer could be produced from the supplied evidence."

        final_repair_action = self._final_repair_action(actions, safe_answer)

        payload = {
            "version": "1.0.0",
            "engine": "ClaimRepairEngine",
            "context_hash": sha256_text(context),
            "prompt_hash": sha256_text(prompt),
            "answer_hash": sha256_text(answer),
            "original_answer": answer,
            "safe_answer": safe_answer,
            "final_repair_action": final_repair_action,
            "fusion_decision": fusion_certificate.get("fusion_decision", {}),
            "kept_claims": tuple(kept),
            "corrected_claims": tuple(corrected),
            "removed_claims": tuple(removed),
            "retrieval_needed": tuple(retrieval),
            "repair_actions": tuple(asdict(a) for a in actions),
        }

        return RepairCertificate(repair_hash=sha256_json(payload), **payload)

    def _final_repair_action(self, actions: Sequence[ClaimRepairAction], safe_answer: str) -> str:
        action_set = {a.action for a in actions}
        if not safe_answer or safe_answer.startswith("Insufficient"):
            return NO_SAFE_ANSWER
        if REPLACE_WITH_EVIDENCE in action_set:
            return "REPAIRED_CONTRADICTIONS"
        if REMOVE_UNSUPPORTED in action_set and RETRIEVE_MORE_EVIDENCE in action_set:
            return "PARTIAL_REPAIR_RETRIEVAL_NEEDED"
        if REMOVE_UNSUPPORTED in action_set:
            return "REMOVED_UNSUPPORTED_CLAIMS"
        if RETRIEVE_MORE_EVIDENCE in action_set:
            return "RETRIEVAL_NEEDED"
        return "UNCHANGED_SAFE"


def demo() -> Dict[str, Any]:
    context = "The school library opens at 8 AM. Students may borrow two books at a time."
    prompt = "Answer using only the supplied context."
    answer = "The school library opens at 10 AM. Students may borrow two books at a time. The library has a robotics lab."
    return asdict(ClaimRepairEngine().repair(context, prompt, answer, model_id="repair-demo"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair AI answers using claim-frame certificates")
    parser.add_argument("--context")
    parser.add_argument("--prompt", default="Answer using only the supplied context.")
    parser.add_argument("--answer")
    parser.add_argument("--out", default="claim_repair_certificate.json")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    if args.demo:
        result = demo()
    else:
        if not args.context or not args.answer:
            parser.error("--context and --answer are required unless --demo is used")
        result = asdict(ClaimRepairEngine().repair(args.context, args.prompt, args.answer))

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, ensure_ascii=False)

    print(json.dumps({
        "ok": True,
        "out": args.out,
        "final_repair_action": result["final_repair_action"],
        "repair_hash": result["repair_hash"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
