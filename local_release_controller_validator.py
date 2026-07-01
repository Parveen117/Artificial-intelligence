#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from ai_trust_enablement.evidence_ledger import read_jsonl, verify_chain
from ai_trust_enablement.release_controller import ReleaseController


CASES: List[Dict[str, Any]] = [
    {
        "case_id": "release_grounded_original",
        "context": "The school library opens at 8 AM. Students may borrow two books at a time.",
        "prompt": "Answer using only the supplied context.",
        "answer": "The school library opens at 8 AM. Students may borrow two books at a time.",
        "expected_action": "RELEASE_ORIGINAL",
        "required_visible_substrings": ["opens at 8 AM", "borrow two books"],
        "forbidden_visible_substrings": ["robotics lab"],
        "expected_retrieval_requests": 0
    },
    {
        "case_id": "release_repaired_wrong_time",
        "context": "The school library opens at 8 AM. Students may borrow two books at a time.",
        "prompt": "Answer using only the supplied context.",
        "answer": "The school library opens at 10 AM. Students may borrow two books at a time.",
        "expected_action": "RELEASE_REPAIRED",
        "required_visible_substrings": ["opens at 8 AM", "borrow two books"],
        "forbidden_visible_substrings": ["10 AM"],
        "expected_retrieval_requests": 0
    },
    {
        "case_id": "hold_unsupported_extra_claim",
        "context": "The school library opens at 8 AM. Students may borrow two books at a time.",
        "prompt": "Answer using only the supplied context.",
        "answer": "The school library opens at 8 AM. Students may borrow two books at a time. The library has a robotics lab.",
        "expected_action": "HOLD_FOR_RETRIEVAL",
        "required_visible_substrings": ["opens at 8 AM", "borrow two books"],
        "forbidden_visible_substrings": ["robotics lab"],
        "expected_retrieval_requests": 1
    },
    {
        "case_id": "hold_empty_context",
        "context": "",
        "prompt": "Answer using only the supplied context.",
        "answer": "The Red Fort is located in Delhi.",
        "expected_action": "HOLD_FOR_RETRIEVAL",
        "required_visible_substrings": ["Insufficient supplied evidence"],
        "forbidden_visible_substrings": [],
        "expected_retrieval_requests": 1
    },
    {
        "case_id": "release_repaired_wrong_conversion",
        "context": "A solar panel converts sunlight into electrical energy.",
        "prompt": "Answer using only the supplied context.",
        "answer": "A solar panel converts sunlight into sound energy.",
        "expected_action": "RELEASE_REPAIRED",
        "required_visible_substrings": ["electrical energy"],
        "forbidden_visible_substrings": ["sound energy"],
        "expected_retrieval_requests": 0
    }
]


def contains_all(text: str, needles: List[str]) -> bool:
    lower = text.lower()
    return all(n.lower() in lower for n in needles)


def contains_none(text: str, needles: List[str]) -> bool:
    lower = text.lower()
    return all(n.lower() not in lower for n in needles)


def validate_case(case: Dict[str, Any], out_dir: Path) -> Dict[str, Any]:
    ledger_path = out_dir / f"{case['case_id']}_ledger.jsonl"
    if ledger_path.exists():
        ledger_path.unlink()
    cert = asdict(ReleaseController(ledger_path).evaluate(
        context=case["context"],
        prompt=case.get("prompt", "Answer using only the supplied context."),
        answer=case["answer"],
        model_id="release-controller-validator"
    ))
    cert_path = out_dir / f"{case['case_id']}_release_certificate.json"
    cert_path.write_text(json.dumps(cert, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    retrieval_plan = cert.get("retrieval_plan") or {}
    requests = retrieval_plan.get("requests", []) or []
    visible = cert.get("user_visible_answer", "")
    entries = read_jsonl(ledger_path)
    checks = {
        "action": cert.get("release_action") == case["expected_action"],
        "visible_required": contains_all(visible, case.get("required_visible_substrings", [])),
        "visible_forbidden": contains_none(visible, case.get("forbidden_visible_substrings", [])),
        "retrieval_count": len(requests) == case.get("expected_retrieval_requests", 0),
        "ledger_chain": verify_chain(entries)
    }
    ok = all(checks.values())
    return {
        "case_id": case["case_id"],
        "ok": ok,
        "expected_action": case["expected_action"],
        "actual_action": cert.get("release_action"),
        "reason": cert.get("reason"),
        "visible_answer": visible,
        "retrieval_request_count": len(requests),
        "ledger_entries": len(entries),
        "ledger_chain_ok": checks["ledger_chain"],
        "checks": checks,
        "certificate_path": str(cert_path),
        "release_hash": cert.get("release_hash")
    }


def main() -> None:
    out_dir = Path("local_release_controller_outputs")
    out_dir.mkdir(exist_ok=True)
    results = [validate_case(case, out_dir) for case in CASES]
    summary = {
        "suite": "local_release_controller_validator_v1",
        "case_count": len(results),
        "pass_count": sum(1 for r in results if r["ok"]),
        "fail_count": sum(1 for r in results if not r["ok"]),
        "results": results
    }
    (out_dir / "release_controller_validation_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    print("\nLOCAL RELEASE CONTROLLER VALIDATION V1")
    print("=" * 88)
    for r in results:
        print(f"{r['case_id'][:36]:36} {str(r['ok']):5} {r['actual_action']}")
    print("-" * 88)
    print(f"PASS={summary['pass_count']} FAIL={summary['fail_count']}")
    if summary["fail_count"]:
        print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
