#!/usr/bin/env python3
"""
Fusion Certificate Engine
=========================

Combines the four verification layers into one deployable certificate:
    1. answer-level residue engine
    2. claim-level Panini-Nyaya verifier
    3. Paninian rule-trace enrichment
    4. semantic claim-frame closure kernel

The fusion layer does not replace the component engines. It acts as an evidence
court: compare the independent routes, detect route disagreement, compute a final
risk score, and issue a deterministic technical action.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from .ai_hallucination_recognition_engine import AIHallucinationRecognitionEngine
    from .claim_frame_kernel import ClaimFrameKernel
    from .panini_nyaya_claim_verifier import PaniniNyayaClaimVerifier
    from .paninian_certificate_adapter import enrich_report
except ImportError:
    from ai_hallucination_recognition_engine import AIHallucinationRecognitionEngine
    from claim_frame_kernel import ClaimFrameKernel
    from panini_nyaya_claim_verifier import PaniniNyayaClaimVerifier
    from paninian_certificate_adapter import enrich_report


FINAL_COMMIT = "COMMIT"
FINAL_REVIEW = "REVIEW"
FINAL_RETRIEVE = "RETRIEVE_MORE_EVIDENCE"
FINAL_REGENERATE = "REGENERATE_WITH_EVIDENCE"
FINAL_BLOCK = "BLOCK_OUTPUT"


@dataclass(frozen=True)
class FusionDecision:
    final_action: str
    final_classification: str
    final_risk: float
    confidence: float
    route_agreement: float
    dominant_reasons: Tuple[str, ...]


@dataclass(frozen=True)
class FusionCertificate:
    version: str
    engine: str
    context_hash: str
    prompt_hash: str
    answer_hash: str
    answer_level: Dict[str, Any]
    claim_level: Dict[str, Any]
    paninian_enriched: Dict[str, Any]
    frame_level: Dict[str, Any]
    fusion_decision: Dict[str, Any]
    certificate_hash: str


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


class FusionCertificateEngine:
    def __init__(self) -> None:
        self.answer_engine = AIHallucinationRecognitionEngine()
        self.claim_engine = PaniniNyayaClaimVerifier()
        self.frame_engine = ClaimFrameKernel()

    def evaluate(
        self,
        context: str,
        prompt: str,
        answer: str,
        model_id: str = "model-under-test",
        logits: Optional[Sequence[float]] = None,
        event_index: int = 1,
    ) -> FusionCertificate:
        answer_cert = asdict(
            self.answer_engine.evaluate(
                reference_text=context,
                prompt_text=prompt,
                answer_text=answer,
                model_id=model_id,
                logits=logits,
                event_index=event_index,
            )
        )
        claim_report = asdict(self.claim_engine.verify(context, prompt, answer))
        paninian_report = enrich_report(context, prompt, answer)
        frame_report = asdict(self.frame_engine.verify(context, prompt, answer))
        decision = self._decide(answer_cert, claim_report, paninian_report, frame_report)
        payload = {
            "version": "1.0.2",
            "engine": "FusionCertificateEngine",
            "context_hash": sha256_text(context),
            "prompt_hash": sha256_text(prompt),
            "answer_hash": sha256_text(answer),
            "answer_level": answer_cert,
            "claim_level": claim_report,
            "paninian_enriched": paninian_report,
            "frame_level": frame_report,
            "fusion_decision": asdict(decision),
        }
        return FusionCertificate(certificate_hash=sha256_json(payload), **payload)

    def _decide(
        self,
        answer_cert: Dict[str, Any],
        claim_report: Dict[str, Any],
        paninian_report: Dict[str, Any],
        frame_report: Dict[str, Any],
    ) -> FusionDecision:
        reasons: List[str] = []

        answer_state = answer_cert.get("recognition_state", {})
        answer_cls = str(answer_state.get("classification", "UNKNOWN"))
        answer_residue = float(answer_state.get("open_residue", 0.0) or 0.0)
        answer_risk = self._risk_from_answer_class(answer_cls, answer_residue)
        if answer_cls == "ACTIONABLE_RESIDUE":
            reasons.append("answer_level_actionable_residue")
        elif answer_cls == "BOUNDED_RESIDUE":
            reasons.append("answer_level_bounded_residue")

        claim_counts = claim_report.get("classification_counts", {}) or {}
        claim_count = max(1, int(claim_report.get("claim_count", 0) or 0))
        contradicted = int(claim_counts.get("CONTRADICTED", 0) or 0)
        unsupported = int(claim_counts.get("UNSUPPORTED", 0) or 0)
        uncertain = int(claim_counts.get("UNCERTAIN", 0) or 0)
        claim_risk = min(1.0, (1.0 * contradicted + 0.75 * unsupported + 0.45 * uncertain) / claim_count)
        if contradicted:
            reasons.append("claim_level_contradiction")
        if unsupported:
            reasons.append("claim_level_unsupported")
        if uncertain:
            reasons.append("claim_level_uncertain")

        trace_count = int(paninian_report.get("paninian_trace_count", 0) or 0)
        enriched_claims = paninian_report.get("claim_results", []) or []
        route_conflicts = sum(1 for c in enriched_claims if c.get("route_conflict"))
        trace_risk = min(1.0, 0.08 * trace_count + 0.20 * route_conflicts)
        if route_conflicts:
            reasons.append("paninian_route_conflict")

        frame_counts = frame_report.get("closure_counts", {}) or {}
        frame_claim_count = max(1, int(frame_report.get("claim_frame_count", 0) or 0))
        frame_bad = sum(
            int(v or 0)
            for k, v in frame_counts.items()
            if str(k).startswith("CONTRADICTED") or str(k).startswith("UNSUPPORTED") or str(k).startswith("UNCERTAIN")
        )
        frame_open_residue = float(frame_report.get("open_residue", 0.0) or 0.0)
        frame_risk = min(1.0, 0.70 * (frame_bad / frame_claim_count) + 0.30 * frame_open_residue)
        for k, v in frame_counts.items():
            if int(v or 0) and (str(k).startswith("CONTRADICTED") or str(k).startswith("UNSUPPORTED") or str(k).startswith("UNCERTAIN")):
                reasons.append(f"frame_{str(k).lower()}")

        risk_values = [answer_risk, claim_risk, trace_risk, frame_risk]
        final_risk = min(1.0, 0.20 * answer_risk + 0.30 * claim_risk + 0.15 * trace_risk + 0.35 * frame_risk)
        route_agreement = self._route_agreement(risk_values)
        confidence = max(0.0, min(1.0, 1.0 - abs(final_risk - 0.5) * 0.25 - (1.0 - route_agreement) * 0.35))
        action, classification = self._action_from_risk(final_risk, reasons, route_agreement)
        compact_reasons = tuple(dict.fromkeys(reasons))[:12]
        return FusionDecision(
            final_action=action,
            final_classification=classification,
            final_risk=final_risk,
            confidence=confidence,
            route_agreement=route_agreement,
            dominant_reasons=compact_reasons,
        )

    def _risk_from_answer_class(self, answer_cls: str, residue: float) -> float:
        if answer_cls == "RECOGNITION":
            return min(0.25, residue)
        if answer_cls == "BOUNDED_RESIDUE":
            return max(0.30, min(0.60, residue + 0.20))
        if answer_cls == "ACTIONABLE_RESIDUE":
            return max(0.70, min(1.0, residue + 0.35))
        return 0.50

    def _route_agreement(self, risks: Sequence[float]) -> float:
        if not risks:
            return 1.0
        mean = sum(risks) / len(risks)
        variance = sum((r - mean) ** 2 for r in risks) / len(risks)
        return max(0.0, min(1.0, 1.0 - (variance ** 0.5)))

    def _action_from_risk(self, risk: float, reasons: Sequence[str], route_agreement: float) -> Tuple[str, str]:
        joined = "|".join(reasons)
        contradiction_present = "contradiction" in joined or "contradicted" in joined
        if contradiction_present and risk >= 0.38:
            return FINAL_BLOCK, "CONTRADICTION_BLOCK"
        if contradiction_present:
            return FINAL_RETRIEVE, "CONTRADICTION_REQUIRES_EVIDENCE_RECHECK"
        if not reasons and risk < 0.18:
            return FINAL_COMMIT, "CERTIFIED_GROUNDED"
        if risk >= 0.72:
            return FINAL_REGENERATE, "HIGH_HALLUCINATION_RISK"
        if risk >= 0.50:
            return FINAL_RETRIEVE, "EVIDENCE_INSUFFICIENT"
        if risk >= 0.28 or route_agreement < 0.55:
            return FINAL_REVIEW, "BOUNDED_REVIEW"
        return FINAL_COMMIT, "CERTIFIED_GROUNDED"


def demo() -> Dict[str, Any]:
    context = "The Eiffel Tower is located in Paris. It was completed in 1889. The tower is made of iron."
    prompt = "Answer using only the supplied context."
    answer = "The Eiffel Tower is located in Berlin. It was completed in 1789. The tower is made of wood."
    return asdict(FusionCertificateEngine().evaluate(context, prompt, answer, model_id="demo-llm"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified fusion certificate engine for AI trust evaluation")
    parser.add_argument("--context")
    parser.add_argument("--prompt", default="Answer using only the supplied context.")
    parser.add_argument("--answer")
    parser.add_argument("--model-id", default="model-under-test")
    parser.add_argument("--event-index", type=int, default=1)
    parser.add_argument("--out", default="fusion_certificate.json")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    if args.demo:
        result = demo()
    else:
        if not args.context or not args.answer:
            parser.error("--context and --answer are required unless --demo is used")
        result = asdict(FusionCertificateEngine().evaluate(args.context, args.prompt, args.answer, model_id=args.model_id, event_index=args.event_index))
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
    print(json.dumps({"ok": True, "out": args.out, "hash": sha256_json(result)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
