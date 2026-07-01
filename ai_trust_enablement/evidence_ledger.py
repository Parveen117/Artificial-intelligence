#!/usr/bin/env python3
"""
Evidence Ledger
===============

Append-only audit ledger for AI trust and repair certificates.

The ledger records:
    - original answer hash
    - safe answer hash
    - context/prompt hashes
    - claim repair actions
    - evidence sentence hashes
    - fusion and repair decisions
    - hash-chain continuity

This converts claim repair into replayable audit infrastructure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from .claim_repair_engine import ClaimRepairEngine
except ImportError:
    from claim_repair_engine import ClaimRepairEngine


GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class EvidenceLedgerEntry:
    version: str
    engine: str
    timestamp_utc: str
    event_index: int
    model_id: str
    context_hash: str
    prompt_hash: str
    answer_hash: str
    safe_answer_hash: str
    repair_hash: str
    fusion_action: str
    fusion_classification: str
    final_repair_action: str
    claim_frame_id: str
    original_claim: str
    original_claim_hash: str
    claim_classification: str
    claim_repair_action: str
    evidence_frame_id: Optional[str]
    evidence_text: Optional[str]
    evidence_role: Optional[str]
    evidence_text_hash: Optional[str]
    repaired_text: Optional[str]
    repaired_text_hash: Optional[str]
    reason_tags: Tuple[str, ...]
    previous_entry_hash: str
    entry_hash: str


@dataclass(frozen=True)
class LedgerWriteResult:
    ledger_path: str
    entries_written: int
    first_entry_hash: Optional[str]
    last_entry_hash: Optional[str]
    chain_ok: bool


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def sha256_json(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()



def evidence_role_for_action(claim_repair_action: str, claim_classification: str, evidence_text: Optional[str]) -> str:
    """Label whether the attached evidence text is supporting evidence or only a retrieval candidate."""
    if not evidence_text:
        return "NO_EVIDENCE"
    if claim_repair_action in {"KEEP", "REPLACE_WITH_EVIDENCE"}:
        return "SUPPORTING_EVIDENCE"
    if claim_repair_action == "RETRIEVE_MORE_EVIDENCE":
        return "CANDIDATE_NEAREST_CONTEXT"
    if claim_repair_action == "REMOVE_UNSUPPORTED":
        return "NON_SUPPORTING_CONTEXT"
    if str(claim_classification).startswith("UNCERTAIN"):
        return "CANDIDATE_NEAREST_CONTEXT"
    if str(claim_classification).startswith("UNSUPPORTED"):
        return "CANDIDATE_NEAREST_CONTEXT"
    return "UNCLASSIFIED_CONTEXT"


def hash_optional_text(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    return sha256_text(text)


def entry_payload_without_hash(entry: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(entry)
    payload.pop("entry_hash", None)
    return payload


def compute_entry_hash(entry: Dict[str, Any]) -> str:
    return sha256_json(entry_payload_without_hash(entry))


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def verify_chain(entries: Iterable[Dict[str, Any]]) -> bool:
    previous = GENESIS_HASH
    for entry in entries:
        if entry.get("previous_entry_hash") != previous:
            return False
        expected = compute_entry_hash(entry)
        if entry.get("entry_hash") != expected:
            return False
        previous = entry["entry_hash"]
    return True


class EvidenceLedger:
    def __init__(self, ledger_path: str | Path = "ai_trust_evidence_ledger.jsonl") -> None:
        self.ledger_path = Path(ledger_path)

    def append_repair_certificate(
        self,
        repair_certificate: Dict[str, Any],
        model_id: str = "model-under-test",
        timestamp_utc: Optional[str] = None,
    ) -> LedgerWriteResult:
        existing = read_jsonl(self.ledger_path)
        previous_hash = existing[-1]["entry_hash"] if existing else GENESIS_HASH
        timestamp = timestamp_utc or now_utc()

        fusion_decision = repair_certificate.get("fusion_decision", {})
        repair_actions = repair_certificate.get("repair_actions", [])

        new_entries: List[Dict[str, Any]] = []

        for i, action in enumerate(repair_actions, start=1):
            payload = {
                "version": "1.0.0",
                "engine": "EvidenceLedger",
                "timestamp_utc": timestamp,
                "event_index": len(existing) + len(new_entries) + 1,
                "model_id": model_id,
                "context_hash": repair_certificate["context_hash"],
                "prompt_hash": repair_certificate["prompt_hash"],
                "answer_hash": repair_certificate["answer_hash"],
                "safe_answer_hash": sha256_text(repair_certificate["safe_answer"]),
                "repair_hash": repair_certificate["repair_hash"],
                "fusion_action": fusion_decision.get("final_action", "UNKNOWN"),
                "fusion_classification": fusion_decision.get("final_classification", "UNKNOWN"),
                "final_repair_action": repair_certificate["final_repair_action"],
                "claim_frame_id": action.get("claim_frame_id", f"C{i}"),
                "original_claim": action.get("original_claim", ""),
                "original_claim_hash": sha256_text(action.get("original_claim", "")),
                "claim_classification": action.get("classification", "UNKNOWN"),
                "claim_repair_action": action.get("action", "UNKNOWN"),
                "evidence_frame_id": action.get("evidence_frame_id"),
                "evidence_text": action.get("evidence_text"),
                "evidence_role": evidence_role_for_action(
                    action.get("action", "UNKNOWN"),
                    action.get("classification", "UNKNOWN"),
                    action.get("evidence_text"),
                ),
                "evidence_text_hash": hash_optional_text(action.get("evidence_text")),
                "repaired_text": action.get("repaired_text"),
                "repaired_text_hash": hash_optional_text(action.get("repaired_text")),
                "reason_tags": tuple(action.get("reason_tags", ()) or ()),
                "previous_entry_hash": previous_hash,
            }

            payload["entry_hash"] = compute_entry_hash(payload)
            previous_hash = payload["entry_hash"]
            new_entries.append(payload)

        with self.ledger_path.open("a", encoding="utf-8") as handle:
            for entry in new_entries:
                handle.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")

        all_entries = existing + new_entries

        return LedgerWriteResult(
            ledger_path=str(self.ledger_path),
            entries_written=len(new_entries),
            first_entry_hash=new_entries[0]["entry_hash"] if new_entries else None,
            last_entry_hash=new_entries[-1]["entry_hash"] if new_entries else (existing[-1]["entry_hash"] if existing else None),
            chain_ok=verify_chain(all_entries),
        )

    def verify(self) -> bool:
        return verify_chain(read_jsonl(self.ledger_path))


def demo() -> Dict[str, Any]:
    context = "The school library opens at 8 AM. Students may borrow two books at a time."
    prompt = "Answer using only the supplied context."
    answer = "The school library opens at 10 AM. Students may borrow two books at a time. The library has a robotics lab."

    repair_certificate = asdict(
        ClaimRepairEngine().repair(
            context=context,
            prompt=prompt,
            answer=answer,
            model_id="ledger-demo",
        )
    )

    ledger = EvidenceLedger("ai_trust_evidence_ledger_demo.jsonl")
    result = asdict(
        ledger.append_repair_certificate(
            repair_certificate,
            model_id="ledger-demo",
        )
    )

    return {
        "repair_certificate": repair_certificate,
        "ledger_result": result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Append and verify AI trust evidence ledger entries")
    parser.add_argument("--context")
    parser.add_argument("--prompt", default="Answer using only the supplied context.")
    parser.add_argument("--answer")
    parser.add_argument("--model-id", default="model-under-test")
    parser.add_argument("--ledger", default="ai_trust_evidence_ledger.jsonl")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    ledger = EvidenceLedger(args.ledger)

    if args.verify_only:
        print(json.dumps({
            "ledger": args.ledger,
            "chain_ok": ledger.verify(),
        }, indent=2, sort_keys=True))
        return

    if args.demo:
        result = demo()
    else:
        if not args.context or not args.answer:
            parser.error("--context and --answer are required unless --demo or --verify-only is used")
        repair_certificate = asdict(
            ClaimRepairEngine().repair(
                context=args.context,
                prompt=args.prompt,
                answer=args.answer,
                model_id=args.model_id,
            )
        )
        result = {
            "repair_certificate": repair_certificate,
            "ledger_result": asdict(
                ledger.append_repair_certificate(
                    repair_certificate,
                    model_id=args.model_id,
                )
            ),
        }

    print(json.dumps(result["ledger_result"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
