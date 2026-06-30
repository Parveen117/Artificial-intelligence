#!/usr/bin/env python3
"""
Batch evaluator for the AI Hallucination Recognition Engine.

Input: JSONL records with fields:
    case_id, context, prompt, answer, expected_classification(optional)

Output: JSONL certificates and a compact summary JSON.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List

from ai_hallucination_recognition_engine import AIHallucinationRecognitionEngine, canonical_json, sha256_json


def read_jsonl(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            for field in ["case_id", "context", "prompt", "answer"]:
                if field not in row:
                    raise ValueError(f"missing_{field}_at_line_{line_number}")
            rows.append(row)
    return rows


def evaluate_cases(input_path: Path, output_path: Path, model_id: str) -> Dict:
    engine = AIHallucinationRecognitionEngine()
    cases = read_jsonl(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    with output_path.open("w", encoding="utf-8") as handle:
        for index, case in enumerate(cases, start=1):
            cert = engine.evaluate(
                reference_text=case["context"],
                prompt_text=case["prompt"],
                answer_text=case["answer"],
                model_id=model_id,
                event_index=index,
            )
            cert_dict = asdict(cert)
            cert_dict["case_id"] = case["case_id"]
            cert_dict["expected_classification"] = case.get("expected_classification")
            handle.write(canonical_json(cert_dict) + "\n")
            got = cert.recognition_state["classification"]
            expected = case.get("expected_classification")
            summary_rows.append({
                "case_id": case["case_id"],
                "classification": got,
                "expected_classification": expected,
                "matches_expected": None if expected is None else got == expected,
                "open_residue": cert.recognition_state["open_residue"],
                "seam_memory_value": cert.recognition_state["seam_memory_value"],
                "action": cert.technical_action["action"],
                "certificate_hash": cert.certificate_hash,
            })

    checked = [row for row in summary_rows if row["matches_expected"] is not None]
    passed = sum(1 for row in checked if row["matches_expected"])
    summary = {
        "input": str(input_path),
        "output": str(output_path),
        "case_count": len(summary_rows),
        "checked_count": len(checked),
        "passed_count": passed,
        "all_checked_passed": passed == len(checked),
        "rows": summary_rows,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch evaluate AI hallucination recognition cases")
    parser.add_argument("--input", default="ai_trust_enablement/sample_cases.jsonl")
    parser.add_argument("--output", default="ai_trust_enablement/batch_certificates.jsonl")
    parser.add_argument("--summary", default="ai_trust_enablement/batch_summary.json")
    parser.add_argument("--model-id", default="batch-demo-model")
    args = parser.parse_args()

    summary = evaluate_cases(Path(args.input), Path(args.output), args.model_id)
    Path(args.summary).write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "summary": args.summary,
        "output": args.output,
        "case_count": summary["case_count"],
        "all_checked_passed": summary["all_checked_passed"],
        "summary_hash": sha256_json(summary),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
