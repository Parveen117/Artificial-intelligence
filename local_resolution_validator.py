#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from ai_trust_enablement.retrieval_resolution_engine import RetrievalResolutionEngine


CASES = [
    {
        "case_id": "retrieval_supports_robotics_lab",
        "context": "The school library opens at 8 AM. Students may borrow two books at a time.",
        "prompt": "Answer using only the supplied context.",
        "answer": "The school library opens at 8 AM. Students may borrow two books at a time. The library has a robotics lab.",
        "retrieved_evidence": [
            {
                "request_id": "R1",
                "evidence_text": "The school library has a robotics lab.",
                "source_id": "manual-school-facility-note"
            }
        ],
        "expected_supported": 1,
        "expected_contradicted": 0,
        "expected_unresolved": 0,
        "required_final_safe_substrings": ["robotics lab"],
        "forbidden_final_safe_substrings": []
    },
    {
        "case_id": "retrieval_refutes_fever_cure",
        "context": "The medicine should be taken after meals.",
        "prompt": "Answer using only the supplied context.",
        "answer": "The medicine should be taken after meals. It also cures fever within one hour.",
        "retrieved_evidence": [
            {
                "request_id": "R1",
                "evidence_text": "The supplied medicine label does not state that it cures fever within one hour.",
                "source_id": "manual-medicine-label",
                "source_policy": "authoritative_sources_required"
            }
        ],
        "expected_supported": 0,
        "expected_contradicted": 1,
        "expected_unresolved": 0,
        "required_final_safe_substrings": ["does not state"],
        "forbidden_final_safe_substrings": ["It also cures fever within one hour."]
    },
    {
        "case_id": "retrieval_still_unresolved",
        "context": "The school library opens at 8 AM.",
        "prompt": "Answer using only the supplied context.",
        "answer": "The school library opens at 8 AM. The library has a robotics lab.",
        "retrieved_evidence": [
            {
                "request_id": "R1",
                "evidence_text": "The school library has many books and reading tables.",
                "source_id": "manual-school-general-note"
            }
        ],
        "expected_supported": 0,
        "expected_contradicted": 0,
        "expected_unresolved": 1,
        "required_final_safe_substrings": ["opens at 8 AM"],
        "forbidden_final_safe_substrings": ["robotics lab"]
    }
]


def contains_all(text: str, substrings: List[str]) -> bool:
    low = text.lower()
    return all(s.lower() in low for s in substrings)


def contains_none(text: str, substrings: List[str]) -> bool:
    low = text.lower()
    return all(s.lower() not in low for s in substrings)


def validate_case(case: Dict[str, Any], engine: RetrievalResolutionEngine, out_dir: Path) -> Dict[str, Any]:
    cert = asdict(
        engine.resolve(
            context=case["context"],
            prompt=case["prompt"],
            answer=case["answer"],
            retrieved_evidence=case["retrieved_evidence"],
            model_id="resolution-validator",
        )
    )

    out_file = out_dir / f"{case['case_id']}_resolution_certificate.json"
    out_file.write_text(json.dumps(cert, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")

    checks = {
        "supported_count_ok": cert["resolved_supported_count"] == case["expected_supported"],
        "contradicted_count_ok": cert["resolved_contradicted_count"] == case["expected_contradicted"],
        "unresolved_count_ok": cert["unresolved_count"] == case["expected_unresolved"],
        "required_safe_ok": contains_all(cert["final_safe_answer"], case["required_final_safe_substrings"]),
        "forbidden_safe_ok": contains_none(cert["final_safe_answer"], case["forbidden_final_safe_substrings"]),
    }

    return {
        "case_id": case["case_id"],
        "ok": all(checks.values()),
        "checks": checks,
        "supported": cert["resolved_supported_count"],
        "contradicted": cert["resolved_contradicted_count"],
        "unresolved": cert["unresolved_count"],
        "final_safe_answer": cert["final_safe_answer"],
        "certificate_hash": cert["certificate_hash"],
        "certificate_path": str(out_file),
    }


def main() -> None:
    out_dir = Path("local_resolution_validation_outputs")
    out_dir.mkdir(exist_ok=True)

    engine = RetrievalResolutionEngine()
    results = [validate_case(case, engine, out_dir) for case in CASES]

    summary = {
        "suite": "retrieval_resolution_validator",
        "case_count": len(results),
        "pass_count": sum(1 for r in results if r["ok"]),
        "fail_count": sum(1 for r in results if not r["ok"]),
        "results": results,
    }

    (out_dir / "resolution_validation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8"
    )

    lines = [
        "# Retrieval Resolution Validation Summary",
        "",
        f"Cases: {summary['case_count']}",
        f"Passed: {summary['pass_count']}",
        f"Failed: {summary['fail_count']}",
        "",
        "| Case | OK | Supported | Contradicted | Unresolved | Final Safe Answer |",
        "|---|---:|---:|---:|---:|---|",
    ]

    for r in results:
        safe = r["final_safe_answer"].replace("|", "\\|")
        lines.append(
            f"| {r['case_id']} | {r['ok']} | {r['supported']} | {r['contradicted']} | {r['unresolved']} | {safe} |"
        )

    (out_dir / "resolution_validation_summary.md").write_text("\n".join(lines), encoding="utf-8")

    print("\nRETRIEVAL RESOLUTION VALIDATION")
    print("=" * 88)
    for r in results:
        print(
            f"{r['case_id'][:36]:36} "
            f"{str(r['ok']):5} "
            f"S={r['supported']} C={r['contradicted']} U={r['unresolved']}"
        )
    print("-" * 88)
    print(f"PASS={summary['pass_count']} FAIL={summary['fail_count']}")

    if summary["fail_count"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
