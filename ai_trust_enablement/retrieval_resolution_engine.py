#!/usr/bin/env python3
"""
Retrieval Resolution Engine
===========================

Closes the loop after retrieval.

Pipeline:
    original context + answer
    -> repair certificate
    -> retrieval plan
    -> retrieved evidence
    -> expanded context
    -> re-check
    -> resolution certificate

This turns retrieval requests into final supported / contradicted / unresolved decisions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from .claim_repair_engine import ClaimRepairEngine
    from .retrieval_router import RetrievalRouter
except ImportError:
    from claim_repair_engine import ClaimRepairEngine
    from retrieval_router import RetrievalRouter


SUPPORTED = "RESOLVED_SUPPORTED"
CONTRADICTED = "RESOLVED_CONTRADICTED"
UNRESOLVED = "RESOLVED_UNCERTAIN"
NO_RETRIEVAL_NEEDED = "NO_RETRIEVAL_NEEDED"


@dataclass(frozen=True)
class RetrievedEvidence:
    request_id: str
    claim_frame_id: str
    evidence_text: str
    source_id: str
    source_policy: str
    source_hash: str


@dataclass(frozen=True)
class ClaimResolution:
    request_id: str
    claim_frame_id: str
    claim_text: str
    retrieval_query: str
    retrieved_evidence_text: str
    source_id: str
    source_hash: str
    resolution: str
    final_fusion_action: str
    final_repair_action: str
    final_safe_answer: str
    resolution_hash: str


@dataclass(frozen=True)
class RetrievalResolutionCertificate:
    version: str
    engine: str
    original_context_hash: str
    original_answer_hash: str
    retrieval_plan_hash: str
    request_count: int
    resolved_supported_count: int
    resolved_contradicted_count: int
    unresolved_count: int
    expanded_context_hash: str
    final_safe_answer: str
    claim_resolutions: Tuple[Dict[str, Any], ...]
    certificate_hash: str


def sha256_text(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


def normalize_text(text: str) -> str:
    text = " ".join(str(text or "").strip().split())
    if text and text[-1] not in ".!?":
        text += "."
    return text


def build_expanded_context(original_context: str, evidence_items: Sequence[RetrievedEvidence]) -> str:
    parts = []
    if original_context.strip():
        parts.append(original_context.strip())
    for item in evidence_items:
        evidence = normalize_text(item.evidence_text)
        if evidence:
            parts.append(evidence)
    return "\n".join(parts)



NEGATION_CUES = {
    "not", "no", "never", "none", "without", "does not", "do not", "did not",
    "cannot", "can't", "doesn't", "didn't", "not state", "does not state",
    "not mention", "does not mention"
}

RESOLUTION_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "in", "into", "is", "it", "its", "of", "on", "or", "that", "the",
    "this", "to", "was", "were", "with", "which", "who", "will", "can", "may",
    "must", "should", "also"
}


def resolution_tokens(text: str) -> set[str]:
    raw = []
    for part in str(text or "").lower().replace(".", " ").replace(",", " ").split():
        token = "".join(ch for ch in part if ch.isalnum() or ch in {"_", "-"})
        if token and token not in RESOLUTION_STOPWORDS:
            raw.append(token)
    return set(raw)


def has_negation_cue(text: str) -> bool:
    low = str(text or "").lower()
    return any(cue in low for cue in NEGATION_CUES)


def evidence_supports_claim(claim_text: str, evidence_text: str, safe_answer: str = "") -> bool:
    """Return True when retrieved evidence materially supports the unresolved claim."""
    claim_tokens = resolution_tokens(claim_text)
    evidence_tokens = resolution_tokens(evidence_text)
    safe_tokens = resolution_tokens(safe_answer)

    if not claim_tokens or not evidence_tokens:
        return False

    # If the evidence is explicitly negative, do not treat high overlap as support.
    if has_negation_cue(evidence_text):
        return False

    overlap = len(claim_tokens & evidence_tokens) / max(1, len(claim_tokens))

    # Direct support: most meaningful claim tokens appear in retrieved evidence.
    if overlap >= 0.70:
        return True

    # Repair support: safe answer was rewritten to the retrieved evidence and preserves core claim tokens.
    if safe_tokens and len(claim_tokens & safe_tokens) / max(1, len(claim_tokens)) >= 0.70:
        return True

    return False


def evidence_refutes_claim(evidence_text: str) -> bool:
    """Return True for retrieved evidence that explicitly denies or fails to state the claim."""
    return has_negation_cue(evidence_text)


class RetrievalResolutionEngine:
    def __init__(self) -> None:
        self.repair_engine = ClaimRepairEngine()
        self.router = RetrievalRouter()

    def resolve(
        self,
        context: str,
        prompt: str,
        answer: str,
        retrieved_evidence: Sequence[Dict[str, Any]],
        model_id: str = "retrieval-resolution",
    ) -> RetrievalResolutionCertificate:
        original_repair = asdict(
            self.repair_engine.repair(
                context=context,
                prompt=prompt,
                answer=answer,
                model_id=model_id,
            )
        )
        retrieval_plan = asdict(self.router.plan_from_repair_certificate(original_repair))
        requests = {r["request_id"]: r for r in retrieval_plan.get("requests", [])}

        evidence_items: List[RetrievedEvidence] = []
        for raw in retrieved_evidence:
            request_id = raw["request_id"]
            request = requests.get(request_id, {})
            evidence_text = normalize_text(raw.get("evidence_text", ""))
            source_id = raw.get("source_id", "local_or_manual_source")
            source_policy = raw.get("source_policy", request.get("source_policy", "unspecified"))

            payload = {
                "request_id": request_id,
                "claim_frame_id": raw.get("claim_frame_id", request.get("claim_frame_id", "")),
                "evidence_text": evidence_text,
                "source_id": source_id,
                "source_policy": source_policy,
            }

            evidence_items.append(
                RetrievedEvidence(
                    source_hash=sha256_json(payload),
                    **payload,
                )
            )

        expanded_context = build_expanded_context(context, evidence_items)

        claim_resolutions: List[ClaimResolution] = []
        safe_answers: List[str] = []

        for item in evidence_items:
            request = requests.get(item.request_id, {})
            claim_text = normalize_text(request.get("claim_text", ""))

            recheck_answer = claim_text
            recheck_cert = asdict(
                self.repair_engine.repair(
                    context=expanded_context,
                    prompt=prompt,
                    answer=recheck_answer,
                    model_id=model_id + "-recheck",
                )
            )

            final_action = recheck_cert["fusion_decision"]["final_action"]
            final_repair = recheck_cert["final_repair_action"]
            final_safe = recheck_cert["safe_answer"]

            resolution = self._resolution_from_recheck(
                final_action,
                final_repair,
                final_safe,
                claim_text,
                item.evidence_text,
            )

            if final_safe and not final_safe.startswith("Insufficient"):
                safe_answers.append(final_safe)

            payload = {
                "request_id": item.request_id,
                "claim_frame_id": item.claim_frame_id,
                "claim_text": claim_text,
                "retrieval_query": request.get("query", ""),
                "retrieved_evidence_text": item.evidence_text,
                "source_id": item.source_id,
                "source_hash": item.source_hash,
                "resolution": resolution,
                "final_fusion_action": final_action,
                "final_repair_action": final_repair,
                "final_safe_answer": final_safe,
            }

            claim_resolutions.append(
                ClaimResolution(
                    resolution_hash=sha256_json(payload),
                    **payload,
                )
            )

        if not retrieval_plan.get("requests"):
            final_safe_answer = original_repair["safe_answer"]
        elif safe_answers:
            final_safe_answer = " ".join(dict.fromkeys(safe_answers))
        else:
            final_safe_answer = original_repair["safe_answer"]

        counts = {
            SUPPORTED: sum(1 for r in claim_resolutions if r.resolution == SUPPORTED),
            CONTRADICTED: sum(1 for r in claim_resolutions if r.resolution == CONTRADICTED),
            UNRESOLVED: sum(1 for r in claim_resolutions if r.resolution == UNRESOLVED),
        }

        payload = {
            "version": "1.0.0",
            "engine": "RetrievalResolutionEngine",
            "original_context_hash": sha256_text(context),
            "original_answer_hash": sha256_text(answer),
            "retrieval_plan_hash": retrieval_plan["plan_hash"],
            "request_count": retrieval_plan["request_count"],
            "resolved_supported_count": counts[SUPPORTED],
            "resolved_contradicted_count": counts[CONTRADICTED],
            "unresolved_count": counts[UNRESOLVED],
            "expanded_context_hash": sha256_text(expanded_context),
            "final_safe_answer": final_safe_answer,
            "claim_resolutions": tuple(asdict(r) for r in claim_resolutions),
        }

        return RetrievalResolutionCertificate(
            certificate_hash=sha256_json(payload),
            **payload,
        )

    def _resolution_from_recheck(
        self,
        fusion_action: str,
        repair_action: str,
        safe_answer: str,
        claim_text: str,
        retrieved_evidence_text: str,
    ) -> str:
        # Retrieval resolution must be stricter than ordinary repair.
        # A claim is supported only when the newly retrieved evidence materially supports it.
        # A safe answer that merely removes the claim is not proof of the claim.
        if evidence_supports_claim(claim_text, retrieved_evidence_text, safe_answer):
            return SUPPORTED

        if evidence_refutes_claim(retrieved_evidence_text):
            return CONTRADICTED

        # If the recheck still blocks after retrieval, treat that as contradiction only
        # when the retrieved evidence is explicitly negative. Otherwise, it remains unresolved.
        if fusion_action == "BLOCK_OUTPUT" and evidence_refutes_claim(retrieved_evidence_text):
            return CONTRADICTED

        return UNRESOLVED


def demo_supported() -> Dict[str, Any]:
    context = "The school library opens at 8 AM. Students may borrow two books at a time."
    prompt = "Answer using only the supplied context."
    answer = "The school library opens at 8 AM. Students may borrow two books at a time. The library has a robotics lab."

    retrieved = [
        {
            "request_id": "R1",
            "evidence_text": "The school library has a robotics lab.",
            "source_id": "manual-school-facility-note",
        }
    ]

    return asdict(RetrievalResolutionEngine().resolve(context, prompt, answer, retrieved, model_id="resolution-demo-supported"))


def demo_contradicted() -> Dict[str, Any]:
    context = "The medicine should be taken after meals."
    prompt = "Answer using only the supplied context."
    answer = "The medicine should be taken after meals. It also cures fever within one hour."

    retrieved = [
        {
            "request_id": "R1",
            "evidence_text": "The supplied medicine label does not state that it cures fever within one hour.",
            "source_id": "manual-medicine-label",
            "source_policy": "authoritative_sources_required",
        }
    ]

    return asdict(RetrievalResolutionEngine().resolve(context, prompt, answer, retrieved, model_id="resolution-demo-contradicted"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve retrieval requests using newly supplied evidence")
    parser.add_argument("--context")
    parser.add_argument("--prompt", default="Answer using only the supplied context.")
    parser.add_argument("--answer")
    parser.add_argument("--retrieved-json", help="Path to JSON list of retrieved evidence items")
    parser.add_argument("--out", default="retrieval_resolution_certificate.json")
    parser.add_argument("--demo-supported", action="store_true")
    parser.add_argument("--demo-contradicted", action="store_true")
    args = parser.parse_args()

    if args.demo_supported:
        result = demo_supported()
    elif args.demo_contradicted:
        result = demo_contradicted()
    else:
        if not args.context or not args.answer or not args.retrieved_json:
            parser.error("--context, --answer, and --retrieved-json are required unless demo mode is used")
        retrieved = json.loads(Path(args.retrieved_json).read_text(encoding="utf-8"))
        result = asdict(
            RetrievalResolutionEngine().resolve(
                context=args.context,
                prompt=args.prompt,
                answer=args.answer,
                retrieved_evidence=retrieved,
            )
        )

    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({
        "ok": True,
        "out": args.out,
        "request_count": result["request_count"],
        "supported": result["resolved_supported_count"],
        "contradicted": result["resolved_contradicted_count"],
        "unresolved": result["unresolved_count"],
        "certificate_hash": result["certificate_hash"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
