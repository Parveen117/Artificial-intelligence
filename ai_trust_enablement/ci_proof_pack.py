#!/usr/bin/env python3
"""
CI Proof Pack v3
================

Fresh-clone proof runner for the AI Trust Enablement stack.

v3 adds the release-controller validator to the full-stack proof. The repository
now checks not only detection, repair, retrieval, adversarial cases, baselines,
and ledger continuity, but also whether the final answer-release layer behaves
correctly.
"""

from __future__ import annotations

import argparse
import compileall
import json
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

try:
    from .fusion_certificate_engine import FusionCertificateEngine, sha256_json
    from .local_smoke_suite import ensure_dir, evaluate_case, load_cases, print_table, write_summary
except ImportError:
    from fusion_certificate_engine import FusionCertificateEngine, sha256_json
    from local_smoke_suite import ensure_dir, evaluate_case, load_cases, print_table, write_summary


PROOF_PACK_VERSION = "3.0.0"
DEFAULT_BENCHMARK = Path("ai_trust_enablement") / "benchmark_cases_v1.json"
FULL_STACK_VALIDATOR = Path("local_full_stack_validator.py")
FULL_STACK_OUTPUT_DIR = Path("local_full_stack_outputs")


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


def run_command(name: str, cmd: Sequence[str]) -> Dict[str, Any]:
    result = subprocess.run(list(cmd), text=True, capture_output=True, check=False)
    return {
        "name": name,
        "cmd": list(cmd),
        "returncode": result.returncode,
        "ok": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def read_json_if_present(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": str(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("exists", True)
            data.setdefault("path", str(path))
            return data
    except Exception as exc:
        return {"exists": False, "path": str(path), "error": repr(exc)}
    return {"exists": False, "path": str(path), "error": "JSON root is not an object"}


def copy_full_stack_artifacts(output_dir: Path) -> Dict[str, Any]:
    artifact_dir = output_dir / "full_stack_validator_v3"
    ensure_dir(artifact_dir)
    copied = []
    for extra in [
        "local_full_stack_outputs",
        "local_run_outputs",
        "local_benchmark_outputs",
        "local_repair_validation_outputs",
        "local_resolution_validation_outputs",
        "local_release_controller_outputs",
        "local_adversarial_outputs_v1",
        "local_baseline_outputs",
        "local_adversarial_baseline_outputs_v1",
    ]:
        src = Path(extra)
        if src.exists():
            dst = artifact_dir / src.name
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            copied.append(str(dst))
    return {"artifact_dir": str(artifact_dir), "copied": copied}


def run_full_stack_validator(output_dir: Path) -> Dict[str, Any]:
    if not FULL_STACK_VALIDATOR.exists():
        return {
            "name": "full_stack_validator_v3",
            "ok": False,
            "returncode": 127,
            "stdout": "",
            "stderr": f"Missing {FULL_STACK_VALIDATOR}",
            "summary": {"exists": False},
            "artifacts": {"copied": []},
        }
    command = run_command("full_stack_validator_v3", [sys.executable, str(FULL_STACK_VALIDATOR)])
    summary = read_json_if_present(FULL_STACK_OUTPUT_DIR / "full_stack_summary.json")
    artifacts = copy_full_stack_artifacts(output_dir)
    command["summary"] = summary
    command["artifacts"] = artifacts
    command["ok"] = bool(command["ok"] and summary.get("ok") is True)
    return command


def write_proof_markdown(output_dir: Path, proof: Dict[str, Any]) -> None:
    lines = [
        "# CI Proof Pack v3",
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
        lines.append(f"- {suite['name']}: `{status}` ({suite['pass_count']}/{suite['case_count']} passed)")

    full_stack = proof["full_stack_validator"]
    full_stack_status = "PASS" if full_stack.get("ok") else "FAIL"
    lines.append(f"- full_stack_validator_v3: `{full_stack_status}`")

    fs = full_stack.get("summary", {}) or {}
    if fs.get("exists"):
        lines.extend([
            "",
            "## Full-stack validator v3",
            "",
            f"- Overall OK: `{fs.get('ok')}`",
            f"- Smoke: `{fs.get('smoke_pass')}` pass, `{fs.get('smoke_fail')}` fail",
            f"- Detection benchmark: `{fs.get('benchmark_pass')}` pass, `{fs.get('benchmark_fail')}` fail",
            f"- Repair validation: `{fs.get('repair_pass')}` pass, `{fs.get('repair_fail')}` fail",
            f"- Retrieval resolution: `{fs.get('resolution_pass')}` pass, `{fs.get('resolution_fail')}` fail",
            f"- Release controller: `{fs.get('release_pass')}` pass, `{fs.get('release_fail')}` fail",
            f"- Adversarial benchmark: `{fs.get('adversarial_pass')}` pass, `{fs.get('adversarial_fail')}` fail",
            f"- Baseline comparison: fusion `{fs.get('baseline_fusion_pass')}`, naive `{fs.get('baseline_naive_pass')}`",
            f"- Adversarial baseline: fusion `{fs.get('adversarial_baseline_fusion_pass')}`, naive `{fs.get('adversarial_baseline_naive_pass')}`",
            f"- Evidence ledger: `{fs.get('ledger_entries')}` entries, chain OK `{fs.get('ledger_chain_ok')}`",
        ])

    lines.extend(["", "## Suite details", ""])
    for suite in proof["suites"]:
        lines.extend([
            f"### {suite['name']}",
            "",
            f"Cases: {suite['case_count']}",
            f"Passed: {suite['pass_count']}",
            f"Failed: {suite['fail_count']}",
            f"Summary hash: `{suite['summary_hash']}`",
            "",
            "| Case | OK | Action | Classification | Risk | Confidence | Route agreement | Reasons |",
            "|---|---:|---|---|---:|---:|---:|---|",
        ])
        for result in suite["results"]:
            reasons = ", ".join(result.get("dominant_reasons", []))
            lines.append(
                f"| {result['case_id']} | {str(result['ok'])} | {result['actual_action']} | "
                f"{result['actual_classification']} | {result['final_risk']:.3f} | "
                f"{result['confidence']:.3f} | {result['route_agreement']:.3f} | {reasons} |"
            )
        lines.append("")

    if not full_stack.get("ok"):
        lines.extend([
            "## Full-stack failure output",
            "",
            "### stdout",
            "",
            "```text",
            full_stack.get("stdout", ""),
            "```",
            "",
            "### stderr",
            "",
            "```text",
            full_stack.get("stderr", ""),
            "```",
        ])

    with (output_dir / "CI_PROOF_PACK_REPORT.md").open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def build_proof(output_dir: Path, benchmark_cases: Path) -> Dict[str, Any]:
    ensure_dir(output_dir)
    compile_ok = compileall.compile_dir("ai_trust_enablement", force=True, quiet=1)
    suites = [
        run_case_suite("smoke_default", None, output_dir),
        run_case_suite("benchmark_v1", benchmark_cases, output_dir),
    ]
    full_stack = run_full_stack_validator(output_dir)
    proof_payload = {
        "proof_pack": "ci_proof_pack_v3",
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
        "full_stack_validator": full_stack,
    }
    proof_payload["ok"] = bool(compile_ok) and all(s["fail_count"] == 0 for s in suites) and bool(full_stack.get("ok"))
    proof_payload["proof_hash"] = sha256_json(proof_payload)
    with (output_dir / "ci_proof_pack_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(proof_payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
    write_proof_markdown(output_dir, proof_payload)
    return proof_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CI Proof Pack v3 for the AI trust stack")
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
