#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from ai_trust_enablement.claim_repair_engine import ClaimRepairEngine


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def contains_all(text: str, substrings: List[str]) -> bool:
    low = text.lower()
    return all(s.lower() in low for s in substrings)


def contains_none(text: str, substrings: List[str]) -> bool:
    low = text.lower()
    return all(s.lower() not in low for s in substrings)


def validate_one(case: Dict[str, Any], expectation: Dict[str, Any], engine: ClaimRepairEngine, out_dir: Path) -> Dict[str, Any]:
    cert = asdict(engine.repair(
        context=case["context"],
        prompt=case.get("prompt", "Answer using only the supplied context."),
        answer=case["answer"],
        model_id="repair-validator",
    ))

    out_file = out_dir / f'{case["case_id"]}_repair_certificate.json'
    out_file.write_text(json.dumps(cert, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")

    fusion_action = cert["fusion_decision"]["final_action"]
    repair_action = cert["final_repair_action"]
    safe_answer = cert["safe_answer"]

    corrected = len(cert["corrected_claims"])
    removed = len(cert["removed_claims"])
    retrieval = len(cert["retrieval_needed"])

    checks = {
        "fusion_action_ok": fusion_action in expectation["expected_fusion_actions"],
        "repair_action_ok": repair_action in expectation["expected_repair_actions"],
        "required_safe_ok": contains_all(safe_answer, expectation.get("required_safe_substrings", [])),
        "forbidden_safe_ok": contains_none(safe_answer, expectation.get("forbidden_safe_substrings", [])),
        "corrected_count_ok": expectation["min_corrected"] <= corrected <= expectation["max_corrected"],
        "retrieval_count_ok": expectation["min_retrieval"] <= retrieval <= expectation["max_retrieval"],
    }

    ok = all(checks.values())

    return {
        "case_id": case["case_id"],
        "ok": ok,
        "checks": checks,
        "fusion_action": fusion_action,
        "repair_action": repair_action,
        "safe_answer": safe_answer,
        "corrected": corrected,
        "removed": removed,
        "retrieval": retrieval,
        "certificate_path": str(out_file),
    }


def main() -> None:
    cases_path = Path("local_benchmark_cases.json")
    expectations_path = Path("local_repair_expectations.json")
    out_dir = Path("local_repair_validation_outputs")
    out_dir.mkdir(exist_ok=True)

    cases = load_json(cases_path)
    expectations_raw = load_json(expectations_path)
    expectations = {e["case_id"]: e for e in expectations_raw}

    engine = ClaimRepairEngine()
    results = []

    for case in cases:
        exp = expectations[case["case_id"]]
        results.append(validate_one(case, exp, engine, out_dir))

    summary = {
        "suite": "repair_benchmark_validator",
        "case_count": len(results),
        "pass_count": sum(1 for r in results if r["ok"]),
        "fail_count": sum(1 for r in results if not r["ok"]),
        "results": results,
    }

    (out_dir / "repair_validation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8"
    )

    lines = [
        "# Repair Validation Summary",
        "",
        f"Cases: {summary['case_count']}",
        f"Passed: {summary['pass_count']}",
        f"Failed: {summary['fail_count']}",
        "",
        "| Case | OK | Fusion | Repair | Corrected | Removed | Retrieval | Safe Answer |",
        "|---|---:|---|---|---:|---:|---:|---|",
    ]

    for r in results:
        safe = r["safe_answer"].replace("|", "\\|")
        lines.append(
            f"| {r['case_id']} | {r['ok']} | {r['fusion_action']} | {r['repair_action']} | "
            f"{r['corrected']} | {r['removed']} | {r['retrieval']} | {safe} |"
        )

    (out_dir / "repair_validation_summary.md").write_text("\n".join(lines), encoding="utf-8")

    print("\nREPAIR VALIDATION")
    print("=" * 80)
    for r in results:
        print(f"{r['case_id'][:32]:32} {str(r['ok']):5} {r['fusion_action'][:24]:24} {r['repair_action']}")
    print("-" * 80)
    print(f"PASS={summary['pass_count']} FAIL={summary['fail_count']}")

    if summary["fail_count"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
