#!/usr/bin/env python3
"""
Retrieval Router
================

Generates evidence retrieval requests for unsupported or uncertain AI claims.

This is not a web search tool. It creates structured retrieval tasks:
    - what claim needs evidence
    - what query should be searched
    - why retrieval is needed
    - what risk level applies
    - what evidence would resolve the claim

This prepares the pipeline:
    Detect -> Repair -> Ledger -> Retrieval -> Re-check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from .claim_repair_engine import ClaimRepairEngine
except ImportError:
    from claim_repair_engine import ClaimRepairEngine


TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)?")
ENTITY_RE = re.compile(r"\b[A-Z][A-Za-z0-9_-]{2,}\b")
NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "in", "into", "is", "it", "its", "of", "on", "or", "that", "the",
    "this", "to", "was", "were", "with", "which", "who", "will", "can", "may",
    "must", "should", "using", "only", "supplied", "context", "answer", "also",
}

HIGH_STAKES_TERMS = {
    "medicine", "medical", "dose", "dosage", "cure", "cures", "fever", "doctor",
    "legal", "law", "court", "financial", "investment", "bank", "tax",
}


@dataclass(frozen=True)
class RetrievalRequest:
    request_id: str
    claim_frame_id: str
    claim_text: str
    classification: str
    reason: str
    risk_level: str
    query: str
    required_evidence_type: str
    expected_resolution: str
    source_policy: str
    request_hash: str


@dataclass(frozen=True)
class RetrievalPlan:
    version: str
    engine: str
    context_hash: str
    prompt_hash: str
    answer_hash: str
    repair_hash: str
    request_count: int
    requests: Tuple[Dict[str, Any], ...]
    plan_hash: str


def sha256_text(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


def tokenize(text: str) -> List[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text)]


def content_tokens(text: str) -> List[str]:
    return [t for t in tokenize(text) if t not in STOPWORDS]


def extract_entities(text: str) -> Tuple[str, ...]:
    return tuple(dict.fromkeys(ENTITY_RE.findall(text)))


def extract_numbers(text: str) -> Tuple[str, ...]:
    return tuple(dict.fromkeys(NUMBER_RE.findall(text)))


def risk_level_for_claim(claim_text: str, classification: str) -> str:
    tokens = set(content_tokens(claim_text))
    if tokens & HIGH_STAKES_TERMS:
        return "HIGH"
    if str(classification).startswith("UNSUPPORTED_NO_EVIDENCE"):
        return "HIGH"
    if str(classification).startswith("UNCERTAIN"):
        return "MEDIUM"
    return "LOW"


def source_policy_for_risk(risk_level: str) -> str:
    if risk_level == "HIGH":
        return "authoritative_sources_required"
    if risk_level == "MEDIUM":
        return "independent_evidence_preferred"
    return "context_or_retrieval_ok"


def required_evidence_type(claim_text: str, classification: str) -> str:
    lower = claim_text.lower()
    if any(w in lower for w in ["cure", "dose", "medicine", "fever"]):
        return "medical_or_label_evidence"
    if any(w in lower for w in ["located", "in"]):
        return "entity_location_evidence"
    if any(w in lower for w in ["opens", "am", "pm", "time"]):
        return "schedule_or_policy_evidence"
    if any(w in lower for w in ["converts", "energy", "made", "material"]):
        return "scientific_fact_evidence"
    return "direct_textual_evidence"


def build_query(claim_text: str) -> str:
    entities = list(extract_entities(claim_text))
    numbers = list(extract_numbers(claim_text))
    tokens = content_tokens(claim_text)

    priority = []
    priority.extend(entities)
    priority.extend(numbers)

    for t in tokens:
        if t not in {x.lower() for x in priority} and len(t) > 2:
            priority.append(t)

    compact = priority[:10]
    if not compact:
        compact = tokens[:8]

    return " ".join(compact)


class RetrievalRouter:
    def __init__(self) -> None:
        pass

    def plan_from_repair_certificate(self, repair_certificate: Dict[str, Any]) -> RetrievalPlan:
        requests: List[RetrievalRequest] = []

        retrieval_items = list(repair_certificate.get("retrieval_needed", []))

        for i, item in enumerate(retrieval_items, start=1):
            claim_text = item.get("claim_text", "")
            classification = item.get("classification", "UNKNOWN")
            risk = risk_level_for_claim(claim_text, classification)

            payload = {
                "request_id": f"R{i}",
                "claim_frame_id": item.get("claim_frame_id", f"C{i}"),
                "claim_text": claim_text,
                "classification": classification,
                "reason": item.get("reason", "retrieval_needed"),
                "risk_level": risk,
                "query": build_query(claim_text),
                "required_evidence_type": required_evidence_type(claim_text, classification),
                "expected_resolution": "support_or_refute_claim_with_new_evidence",
                "source_policy": source_policy_for_risk(risk),
            }

            requests.append(RetrievalRequest(request_hash=sha256_json(payload), **payload))

        payload = {
            "version": "1.0.0",
            "engine": "RetrievalRouter",
            "context_hash": repair_certificate["context_hash"],
            "prompt_hash": repair_certificate["prompt_hash"],
            "answer_hash": repair_certificate["answer_hash"],
            "repair_hash": repair_certificate["repair_hash"],
            "request_count": len(requests),
            "requests": tuple(asdict(r) for r in requests),
        }

        return RetrievalPlan(plan_hash=sha256_json(payload), **payload)

    def plan(self, context: str, prompt: str, answer: str, model_id: str = "model-under-test") -> RetrievalPlan:
        repair_certificate = asdict(
            ClaimRepairEngine().repair(
                context=context,
                prompt=prompt,
                answer=answer,
                model_id=model_id,
            )
        )
        return self.plan_from_repair_certificate(repair_certificate)


def demo() -> Dict[str, Any]:
    context = "The medicine should be taken after meals."
    prompt = "Answer using only the supplied context."
    answer = "The medicine should be taken after meals. It also cures fever within one hour."
    return asdict(RetrievalRouter().plan(context, prompt, answer, model_id="retrieval-demo"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate retrieval requests for unsupported AI claims")
    parser.add_argument("--context")
    parser.add_argument("--prompt", default="Answer using only the supplied context.")
    parser.add_argument("--answer")
    parser.add_argument("--out", default="retrieval_plan.json")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    if args.demo:
        result = demo()
    else:
        if not args.context or not args.answer:
            parser.error("--context and --answer are required unless --demo is used")
        result = asdict(RetrievalRouter().plan(args.context, args.prompt, args.answer))

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, ensure_ascii=False)

    print(json.dumps({
        "ok": True,
        "out": args.out,
        "request_count": result["request_count"],
        "plan_hash": result["plan_hash"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
