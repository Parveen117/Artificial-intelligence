#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from ai_trust_enablement.evidence_ledger import read_jsonl, verify_chain


def run_cmd(name: str, cmd: List[str]) -> Dict[str, Any]:
    result = subprocess.run(
        cmd,
        text=True,
        capture_output=True
    )

    return {
        "name": name,
        "cmd": cmd,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "ok": result.returncode == 0,
    }


def read_summary(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "exists": False,
            "pass_count": 0,
            "fail_count": 999,
        }

    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "exists": True,
        "pass_count": data.get("pass_count", data.get("passed", 0)),
        "fail_count": data.get("fail_count", data.get("failed", 0)),
        "raw": data,
    }


def main() -> None:
    root = Path.cwd()
    out_dir = root / "local_full_stack_outputs"
    out_dir.mkdir(exist_ok=True)

    runs = []

    # 1. Compile package
    runs.append(run_cmd(
        "compile",
        [sys.executable, "-m", "compileall", "ai_trust_enablement"]
    ))

    # 2. Smoke suite: default 6 cases
    runs.append(run_cmd(
        "smoke_suite",
        [
            sys.executable,
            "-m",
            "ai_trust_enablement.local_smoke_suite",
            "--out-dir",
            "local_run_outputs"
        ]
    ))

    # 3. Detection benchmark: 10 cases
    runs.append(run_cmd(
        "detection_benchmark",
        [
            sys.executable,
            "-m",
            "ai_trust_enablement.local_smoke_suite",
            "--cases",
            "local_benchmark_cases.json",
            "--out-dir",
            "local_benchmark_outputs"
        ]
    ))

    # 4. Repair validator
    runs.append(run_cmd(
        "repair_validator",
        [sys.executable, "local_repair_validator.py"]
    ))

    # 5. Retrieval resolution validator
    runs.append(run_cmd(
        "retrieval_resolution_validator",
        [sys.executable, "local_resolution_validator.py"]
    ))

    # 6. Evidence ledger verification
    ledger_path = root / "local_evidence_ledger.jsonl"
    ledger_entries = read_jsonl(ledger_path) if ledger_path.exists() else []
    ledger_ok = verify_chain(ledger_entries) if ledger_entries else False

    smoke_summary = read_summary(root / "local_run_outputs" / "local_smoke_summary.json")
    benchmark_summary = read_summary(root / "local_benchmark_outputs" / "local_smoke_summary.json")
    repair_summary = read_summary(root / "local_repair_validation_outputs" / "repair_validation_summary.json")
    resolution_summary = read_summary(root / "local_resolution_validation_outputs" / "resolution_validation_summary.json")

    final = {
        "suite": "local_full_stack_validator",
        "compile_ok": runs[0]["ok"],
        "smoke_pass": smoke_summary["pass_count"],
        "smoke_fail": smoke_summary["fail_count"],
        "benchmark_pass": benchmark_summary["pass_count"],
        "benchmark_fail": benchmark_summary["fail_count"],
        "repair_pass": repair_summary["pass_count"],
        "repair_fail": repair_summary["fail_count"],
        "resolution_pass": resolution_summary["pass_count"],
        "resolution_fail": resolution_summary["fail_count"],
        "ledger_entries": len(ledger_entries),
        "ledger_chain_ok": ledger_ok,
        "command_results": runs,
    }

    final["ok"] = (
        final["compile_ok"]
        and final["smoke_fail"] == 0
        and final["benchmark_fail"] == 0
        and final["repair_fail"] == 0
        and final["resolution_fail"] == 0
        and final["ledger_chain_ok"]
    )

    summary_json = out_dir / "full_stack_summary.json"
    summary_json.write_text(
        json.dumps(final, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8"
    )

    lines = [
        "# Local Full Stack Validation Report",
        "",
        f"Overall OK: `{final['ok']}`",
        "",
        "| Layer | Pass | Fail / Status |",
        "|---|---:|---|",
        f"| Compile | {1 if final['compile_ok'] else 0} | {'OK' if final['compile_ok'] else 'FAIL'} |",
        f"| Smoke suite | {final['smoke_pass']} | {final['smoke_fail']} fail |",
        f"| Detection benchmark | {final['benchmark_pass']} | {final['benchmark_fail']} fail |",
        f"| Repair validation | {final['repair_pass']} | {final['repair_fail']} fail |",
        f"| Retrieval resolution | {final['resolution_pass']} | {final['resolution_fail']} fail |",
        f"| Evidence ledger | {final['ledger_entries']} entries | Chain OK: `{final['ledger_chain_ok']}` |",
        "",
        "## Command Status",
        "",
        "| Command | OK | Return Code |",
        "|---|---:|---:|",
    ]

    for r in runs:
        lines.append(f"| {r['name']} | {r['ok']} | {r['returncode']} |")

    report_md = out_dir / "full_stack_report.md"
    report_md.write_text("\n".join(lines), encoding="utf-8")

    print("\nLOCAL FULL STACK VALIDATION")
    print("=" * 90)
    print(f"Compile OK: {final['compile_ok']}")
    print(f"Smoke: {final['smoke_pass']} pass, {final['smoke_fail']} fail")
    print(f"Detection benchmark: {final['benchmark_pass']} pass, {final['benchmark_fail']} fail")
    print(f"Repair validation: {final['repair_pass']} pass, {final['repair_fail']} fail")
    print(f"Retrieval resolution: {final['resolution_pass']} pass, {final['resolution_fail']} fail")
    print(f"Ledger: {final['ledger_entries']} entries, chain OK = {final['ledger_chain_ok']}")
    print("-" * 90)
    print(f"OVERALL OK = {final['ok']}")
    print(f"Report: {report_md}")

    if not final["ok"]:
        print("\nFAILED COMMAND OUTPUTS")
        print("=" * 90)
        for r in runs:
            if not r["ok"]:
                print(f"\n--- {r['name']} ---")
                print(r["stdout"])
                print(r["stderr"])
        sys.exit(1)


if __name__ == "__main__":
    main()
