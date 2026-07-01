#!/usr/bin/env python3
"""
CI Proof Pack v1
================

Fresh-clone proof runner for the AI Trust Enablement stack.

The proof pack is intentionally boring: compile the package, run the default smoke
suite, run the benchmark suite, write artifacts, and fail the process if a gate fails.
Boring is good here. Boring is what reviewers can reproduce.
"""

from __future__ import annotations

import argparse
import compileall
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

try:
    from .fusion_certificate_engine import sha256_json
    from .local_smoke_suite import SmokeCaseResult, ensure_dir, evaluate_case, load_cases, print_table, write_summary
    from .fusion_certificate_engine import FusionCertificateEngine
except ImportError:
    from fusion_certificate_engine import sha256_json
    from local_smoke_suite import SmokeCaseResult, ensure_dir, evaluate_case, load_cases, print_table, write_summary
    from fusion_certificate_engine import FusionCertificateEngine


PROOF_PACK_VERSION = "1.0.0"
DEFAULT_BENCHMARK = Path("ai_trust_enablement") / "benchmark_cases_v1.json"


def git_value(args: Sequence[str]) -> str:
    try:
        result = subprocess.run(["git", *args], text=True, capture_output=True, check=False)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def run_case_suite(name: str, cases_path: Optional[Path], output_root: Path) -> Dict[str, Any]:
    suite_dir = output_root / name
    ensure_dir(suite_dir)
    cases = load_cases(cases_path)
    engine = FusionCertificateEngine()
    results = [evaluate_case(engine, case, suite_dir) for case in cases]
    summary = write_summary(suite_dir, results)
    print_table(results)
    return {
        "name": name,
        "cases_path": str(cases_path) if cases_path else "default",
        "output_dir": str(suite_dir),
        "case_count": summary["case_count"],
        "pass_count": summary["pass_count"],
        "fail_count": summary["fail_count"],
        "summary_hash": summary["summary_hash"],
        "summary_json": str(suite_dir / "local_smoke_summary.json"),
        "summary_markdown": str(suite_dir / "local_smoke_summary.md"),
        "results": [asdict(r) for r in results],
    }


def write_proof_markdown(output_dir: Path, proof: Dict[str, Any]) -> None:
    lines = [
        "# CI Proof Pack v1",
        "",
        f"Status: **{'PASS' if proof['ok'] else 'FAIL'}**",
        f"Proof hash: `{proof['proof_hash']}`",
        "",
        "## Environment",
        "",
        f"- Python: `{proof['environment']['python']}`",
        f"- Platform: `{proof['environment']['platform']}`",
        f"- Commit: `{proof['git']['commit']}`",
        f"- Branch: `{proof['git']['branch']}`",
        "",
        "## Gates",
        "",
        f"- Compile package: `{'PASS' if proof['compile_ok'] else 'FAIL'}`",
    ]
    for suite in proof["suites"]:
        status = "PASS" if suite["fail_count"] == 0 else "FAIL"
        lines.extend(
            [
                f"- {suite['name']}: `{status}` ({suite['pass_count']}/{suite['case_count']} passed)",
            ]
        )
    lines.extend(["", "## Suite details", ""])
    for suite in proof["suites"]:
        lines.extend(
            [
                f"### {suite['name']}",
                "",
                f"Cases: {suite['case_count']}",
                f"Passed: {suite['pass_count']}",
                f"Failed: {suite['fail_count']}",
                f"Summary hash: `{suite['summary_hash']}`",
                "",
                "| Case | OK | Action | Classification | Risk | Confidence | Route agreement | Reasons |",
                "|---|---:|---|---|---:|---:|---:|---|",
            ]
        )
        for result in suite["results"]:
            reasons = ", ".join(result.get("dominant_reasons", []))
            lines.append(
                f"| {result['case_id']} | {str(result['ok'])} | {result['actual_action']} | "
                f"{result['actual_classification']} | {result['final_risk']:.3f} | "
                f"{result['confidence']:.3f} | {result['route_agreement']:.3f} | {reasons} |"
            )
        lines.append("")
    with (output_dir / "CI_PROOF_PACK_REPORT.md").open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def build_proof(output_dir: Path, benchmark_cases: Path) -> Dict[str, Any]:
    ensure_dir(output_dir)
    compile_ok = compileall.compile_dir("ai_trust_enablement", force=True, quiet=1)
    suites = [
        run_case_suite("smoke_default", None, output_dir),
        run_case_suite("benchmark_v1", benchmark_cases, output_dir),
    ]
    proof_payload = {
        "proof_pack": "ci_proof_pack_v1",
        "version": PROOF_PACK_VERSION,
        "timestamp_unix": int(time.time()),
        "environment": {
            "python": sys.version.replace("\n", " "),
            "platform": platform.platform(),
            "executable": sys.executable,
        },
        "git": {
            "commit": git_value(["rev-parse", "HEAD"]),
            "branch": git_value(["rev-parse", "--abbrev-ref", "HEAD"]),
            "status_porcelain": git_value(["status", "--porcelain"]),
        },
        "compile_ok": bool(compile_ok),
        "suites": suites,
    }
    proof_payload["ok"] = bool(compile_ok) and all(s["fail_count"] == 0 for s in suites)
    proof_payload["proof_hash"] = sha256_json(proof_payload)
    with (output_dir / "ci_proof_pack_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(proof_payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
    write_proof_markdown(output_dir, proof_payload)
    return proof_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CI Proof Pack v1 for the AI trust stack")
    parser.add_argument("--out-dir", default="ci_proof_outputs")
    parser.add_argument("--benchmark-cases", default=str(DEFAULT_BENCHMARK))
    parser.add_argument("--strict", action="store_true", help="exit with code 1 if any gate fails")
    args = parser.parse_args()

    output_dir = Path(args.out_dir)
    benchmark_cases = Path(args.benchmark_cases)
    proof = build_proof(output_dir, benchmark_cases)
    print(json.dumps({"ok": proof["ok"], "out_dir": str(output_dir), "proof_hash": proof["proof_hash"]}, indent=2, sort_keys=True))
    if args.strict and not proof["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
