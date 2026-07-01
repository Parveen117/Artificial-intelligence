#!/usr/bin/env python3
"""Answer Release Controller v1.

A compact deployment wrapper for the AI Trust Enablement stack.
It converts repair and retrieval certificates into one release certificate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from .claim_repair_engine import ClaimRepairEngine
    from .evidence_ledger import EvidenceLedger
    from .retrieval_router import RetrievalRouter
except ImportError:
    from claim_repair_engine import ClaimRepairEngine
    from evidence_ledger import EvidenceLedger
    from retrieval_router import RetrievalRouter


@dataclass(frozen=True)
class ReleaseCertificate:
    version: str
    engine: str
    context_hash: str
    prompt_hash: str
    answer_hash: str
    repair_hash: str
    release_action: str
    user_visible_answer: str
    reason: str
    retrieval_plan: Optional[Dict[str, Any]]
    ledger_write: Optional[Dict[str, Any]]
    repair_certificate: Dict[str, Any]
    release_hash: str


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def sha256_json(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


class ReleaseController:
    def __init__(self, ledger_path: Optional[str | Path] = None) -> None:
        self.repair_engine = ClaimRepairEngine()
        self.router = RetrievalRouter()
        self.ledger_path = Path(ledger_path) if ledger_path else None

    def evaluate(self, context: str, prompt: str, answer: str, model_id: str = "model-under-test") -> ReleaseCertificate:
        repair = asdict(self.repair_engine.repair(context=context, prompt=prompt, answer=answer, model_id=model_id))
        retrieval_plan = None
        if repair.get("retrieval_needed"):
            retrieval_plan = asdict(self.router.plan_from_repair_certificate(repair))
        action, visible, reason = self._release_decision(repair, retrieval_plan)
        ledger_write = None
        if self.ledger_path is not None:
            ledger_write = asdict(EvidenceLedger(self.ledger_path).append_repair_certificate(repair, model_id=model_id))
        payload = {
            "version": "1.0.0",
            "engine": "ReleaseController",
            "context_hash": repair["context_hash"],
            "prompt_hash": repair["prompt_hash"],
            "answer_hash": repair["answer_hash"],
            "repair_hash": repair["repair_hash"],
            "release_action": action,
            "user_visible_answer": visible,
            "reason": reason,
            "retrieval_plan": retrieval_plan,
            "ledger_write": ledger_write,
            "repair_certificate": repair,
        }
        return ReleaseCertificate(release_hash=sha256_json(payload), **payload)

    def _release_decision(self, repair: Dict[str, Any], retrieval_plan: Optional[Dict[str, Any]]) -> tuple[str, str, str]:
        fusion_action = str(repair.get("fusion_decision", {}).get("final_action", "UNKNOWN"))
        repair_action = str(repair.get("final_repair_action", "UNKNOWN"))
        safe_answer = str(repair.get("safe_answer", ""))
        original_answer = str(repair.get("original_answer", ""))
        if retrieval_plan and int(retrieval_plan.get("request_count", 0) or 0) > 0:
            return "HOLD_FOR_RETRIEVAL", safe_answer, "retrieval_required_before_release"
        if fusion_action == "BLOCK_OUTPUT" and safe_answer and safe_answer != original_answer and not safe_answer.startswith("Insufficient"):
            return "RELEASE_REPAIRED", safe_answer, "original_failed_but_repair_is_available"
        if fusion_action == "BLOCK_OUTPUT":
            return "DO_NOT_RELEASE", "The answer cannot be released from the supplied evidence.", "contradiction_without_safe_repair"
        if repair_action in {"REPAIRED_CONTRADICTIONS", "REMOVED_UNSUPPORTED_CLAIMS"}:
            return "RELEASE_REPAIRED", safe_answer, "claim_level_repair_applied"
        if repair_action == "NO_SAFE_ANSWER":
            return "NO_SAFE_ANSWER", safe_answer, "no_safe_answer_from_supplied_evidence"
        return "RELEASE_ORIGINAL", original_answer, "certified_without_repair"


def demo() -> Dict[str, Any]:
    return asdict(ReleaseController("release_controller_demo_ledger.jsonl").evaluate(
        context="The school library opens at 8 AM. Students may borrow two books at a time.",
        prompt="Answer using only the supplied context.",
        answer="The school library opens at 10 AM. Students may borrow two books at a time. The library has a robotics lab.",
        model_id="release-controller-demo",
    ))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the answer release controller")
    parser.add_argument("--context")
    parser.add_argument("--prompt", default="Answer using only the supplied context.")
    parser.add_argument("--answer")
    parser.add_argument("--model-id", default="model-under-test")
    parser.add_argument("--ledger")
    parser.add_argument("--out", default="release_certificate.json")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    if args.demo:
        result = demo()
    else:
        if not args.context or not args.answer:
            parser.error("--context and --answer are required unless --demo is used")
        result = asdict(ReleaseController(args.ledger).evaluate(args.context, args.prompt, args.answer, args.model_id))
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, ensure_ascii=False)
    print(json.dumps({"ok": True, "out": args.out, "release_action": result["release_action"], "release_hash": result["release_hash"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
