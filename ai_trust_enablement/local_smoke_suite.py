#!/usr/bin/env python3
"""
Local Smoke Suite
=================

Runs the complete AI trust pipeline locally and writes deterministic artifacts.

Purpose:
    - compile/runtime sanity check
    - run grounded, paraphrase, unsupported, contradiction, and no-evidence cases
    - save fusion certificates for inspection
    - produce a compact summary JSON and Markdown report

No external dependencies. No network. No external knowledge base.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from .fusion_certificate_engine import FusionCertificateEngine, sha256_json
except ImportError:
    from fusion_certificate_engine import FusionCertificateEngine, sha256_json


@dataclass(frozen=True)
class SmokeCase:
    case_id: str
    description: str
    context: str
    prompt: str
    answer: str
    expected_action_family: Tuple[str, ...]


@dataclass(frozen=True)
class SmokeCaseResult:
    case_id: str
    description: str
    ok: bool
    expected_action_family: Tuple[str, ...]
    actual_action: str
    actual_classification: str
    final_risk: float
    confidence: float
    route_agreement: float
    dominant_reasons: Tuple[str, ...]
    certificate_path: str
    error: Optional[str]


DEFAULT_CASES: Tuple[SmokeCase, ...] = (
    SmokeCase(
        case_id="grounded_exact",
        description="Exact answer supported by supplied context.",
        context="The Eiffel Tower is located in Paris. It was completed in 1889. The tower is made of iron.",
        prompt="Answer using only the supplied context.",
        answer="The Eiffel Tower is located in Paris. It was completed in 1889. The tower is made of iron.",
        expected_action_family=("COMMIT", "REVIEW"),
    ),
    SmokeCase(
        case_id="grounded_paraphrase",
        description="Paraphrase answer that should remain bounded if fields close.",
        context="A solar panel converts sunlight into electrical energy. A battery stores electrical energy for later use.",
        prompt="Answer using only the supplied context.",
        answer="A solar panel changes sunlight into electrical energy, and a battery stores that energy for later.",
        expected_action_family=("COMMIT", "REVIEW"),
    ),
    SmokeCase(
        case_id="entity_contradiction",
        description="Entity contradiction under the same relation.",
        context="The Eiffel Tower is located in Paris. It was completed in 1889. The tower is made of iron.",
        prompt="Answer using only the supplied context.",
        answer="The Eiffel Tower is located in Berlin. It was completed in 1889. The tower is made of iron.",
        expected_action_family=("BLOCK_OUTPUT", "REGENERATE_WITH_EVIDENCE", "RETRIEVE_MORE_EVIDENCE"),
    ),
    SmokeCase(
        case_id="number_contradiction",
        description="Numeric contradiction against the supplied context.",
        context="The device records 24 samples per hour. The safe limit is 48 samples per day.",
        prompt="Answer using only the supplied context.",
        answer="The device records 42 samples per hour. The safe limit is 48 samples per day.",
        expected_action_family=("BLOCK_OUTPUT", "REGENERATE_WITH_EVIDENCE", "RETRIEVE_MORE_EVIDENCE"),
    ),
    SmokeCase(
        case_id="unsupported_claim",
        description="Unsupported extra claim not present in the evidence.",
        context="The school library opens at 8 AM. Students may borrow two books at a time.",
        prompt="Answer using only the supplied context.",
        answer="The school library opens at 8 AM. Students may borrow two books at a time. The library also has a robotics lab.",
        expected_action_family=("REVIEW", "RETRIEVE_MORE_EVIDENCE", "REGENERATE_WITH_EVIDENCE", "BLOCK_OUTPUT"),
    ),
    SmokeCase(
        case_id="no_evidence",
        description="Empty context should not certify an answer as grounded.",
        context="",
        prompt="Answer using only the supplied context.",
        answer="The tower is located in Paris.",
        expected_action_family=("RETRIEVE_MORE_EVIDENCE", "REGENERATE_WITH_EVIDENCE", "BLOCK_OUTPUT", "REVIEW"),
    ),
)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def safe_filename(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in name)


def load_cases(path: Optional[Path]) -> Tuple[SmokeCase, ...]:
    if not path:
        return DEFAULT_CASES
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    cases: List[SmokeCase] = []
    for item in raw:
        cases.append(
            SmokeCase(
                case_id=str(item["case_id"]),
                description=str(item.get("description", "")),
                context=str(item.get("context", "")),
                prompt=str(item.get("prompt", "Answer using only the supplied context.")),
                answer=str(item.get("answer", "")),
                expected_action_family=tuple(item.get("expected_action_family", [])) or ("COMMIT", "REVIEW", "RETRIEVE_MORE_EVIDENCE", "REGENERATE_WITH_EVIDENCE", "BLOCK_OUTPUT"),
            )
        )
    return tuple(cases)


def evaluate_case(engine: FusionCertificateEngine, case: SmokeCase, output_dir: Path) -> SmokeCaseResult:
    cert_path = output_dir / f"{safe_filename(case.case_id)}_fusion_certificate.json"
    try:
        certificate = asdict(engine.evaluate(case.context, case.prompt, case.answer, model_id="local-smoke-suite"))
        decision = certificate.get("fusion_decision", {})
        actual_action = str(decision.get("final_action", "UNKNOWN"))
        ok = actual_action in case.expected_action_family
        with cert_path.open("w", encoding="utf-8") as handle:
            json.dump(certificate, handle, indent=2, sort_keys=True, ensure_ascii=False)
        return SmokeCaseResult(
            case_id=case.case_id,
            description=case.description,
            ok=ok,
            expected_action_family=case.expected_action_family,
            actual_action=actual_action,
            actual_classification=str(decision.get("final_classification", "UNKNOWN")),
            final_risk=float(decision.get("final_risk", 0.0) or 0.0),
            confidence=float(decision.get("confidence", 0.0) or 0.0),
            route_agreement=float(decision.get("route_agreement", 0.0) or 0.0),
            dominant_reasons=tuple(decision.get("dominant_reasons", ()) or ()),
            certificate_path=str(cert_path),
            error=None,
        )
    except Exception:
        error_text = traceback.format_exc()
        return SmokeCaseResult(
            case_id=case.case_id,
            description=case.description,
            ok=False,
            expected_action_family=case.expected_action_family,
            actual_action="ERROR",
            actual_classification="ERROR",
            final_risk=1.0,
            confidence=0.0,
            route_agreement=0.0,
            dominant_reasons=("runtime_error",),
            certificate_path=str(cert_path),
            error=error_text,
        )


def write_summary(output_dir: Path, results: Sequence[SmokeCaseResult]) -> Dict[str, Any]:
    summary = {
        "suite": "local_smoke_suite",
        "version": "1.0.0",
        "timestamp_unix": int(time.time()),
        "case_count": len(results),
        "pass_count": sum(1 for r in results if r.ok),
        "fail_count": sum(1 for r in results if not r.ok),
        "results": [asdict(r) for r in results],
    }
    summary["summary_hash"] = sha256_json(summary)
    with (output_dir / "local_smoke_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True, ensure_ascii=False)
    with (output_dir / "local_smoke_summary.jsonl").open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(asdict(result), sort_keys=True, ensure_ascii=False) + "\n")
    write_markdown_report(output_dir, summary)
    return summary


def write_markdown_report(output_dir: Path, summary: Dict[str, Any]) -> None:
    lines = [
        "# Local AI Trust Smoke Suite",
        "",
        f"Cases: {summary['case_count']}",
        f"Passed: {summary['pass_count']}",
        f"Failed: {summary['fail_count']}",
        f"Summary hash: `{summary['summary_hash']}`",
        "",
        "| Case | OK | Action | Classification | Risk | Confidence | Route agreement | Reasons |",
        "|---|---:|---|---|---:|---:|---:|---|",
    ]
    for result in summary["results"]:
        reasons = ", ".join(result.get("dominant_reasons", []))
        lines.append(
            f"| {result['case_id']} | {str(result['ok'])} | {result['actual_action']} | "
            f"{result['actual_classification']} | {result['final_risk']:.3f} | "
            f"{result['confidence']:.3f} | {result['route_agreement']:.3f} | {reasons} |"
        )
    lines.append("")
    with (output_dir / "local_smoke_summary.md").open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def print_table(results: Sequence[SmokeCaseResult]) -> None:
    print("\nLOCAL AI TRUST SMOKE SUITE")
    print("=" * 78)
    print(f"{'CASE':24} {'OK':4} {'ACTION':28} {'RISK':>7} {'CONF':>7}")
    print("-" * 78)
    for r in results:
        print(f"{r.case_id[:24]:24} {str(r.ok):4} {r.actual_action[:28]:28} {r.final_risk:7.3f} {r.confidence:7.3f}")
    print("-" * 78)
    print(f"PASS={sum(1 for r in results if r.ok)} FAIL={sum(1 for r in results if not r.ok)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local smoke tests for the AI trust fusion pipeline")
    parser.add_argument("--cases", help="optional JSON file containing custom cases")
    parser.add_argument("--out-dir", default="local_run_outputs")
    parser.add_argument("--strict", action="store_true", help="exit with code 1 if any smoke case fails")
    args = parser.parse_args()

    output_dir = Path(args.out_dir)
    ensure_dir(output_dir)
    cases = load_cases(Path(args.cases) if args.cases else None)
    engine = FusionCertificateEngine()
    results = [evaluate_case(engine, case, output_dir) for case in cases]
    summary = write_summary(output_dir, results)
    print_table(results)
    print(json.dumps({"ok": summary["fail_count"] == 0, "out_dir": str(output_dir), "summary_hash": summary["summary_hash"]}, indent=2, sort_keys=True))
    if args.strict and summary["fail_count"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
