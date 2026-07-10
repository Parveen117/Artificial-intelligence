#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from ai_trust_enablement.claim_repair_engine import ClaimRepairEngine
from ai_trust_enablement.evidence_ledger import EvidenceLedger, read_jsonl, verify_chain
from ai_trust_enablement.rnke_closure_engine import RNKEClosureEngine


def run_cmd(name: str, cmd: List[str]) -> Dict[str, Any]:
    result = subprocess.run(cmd, text=True, capture_output=True)
    return {"name": name, "cmd": cmd, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "ok": result.returncode == 0}


def read_summary(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"exists": False, "pass_count": 0, "fail_count": 999, "ok": False}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "exists": True,
        "pass_count": data.get("pass_count", data.get("passed", 1 if data.get("ok") else 0)),
        "fail_count": data.get("fail_count", data.get("failed", 0 if data.get("ok") else 1)),
        "ok": bool(data.get("ok", data.get("fail_count", 1) == 0)),
        "raw": data,
    }


def first_present(data: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return default


def regenerate_ledger(root: Path, out_dir: Path) -> Dict[str, Any]:
    cases_path = root / "local_benchmark_cases.json"
    ledger_path = out_dir / "full_stack_evidence_ledger.jsonl"
    if ledger_path.exists():
        ledger_path.unlink()
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    repair_engine = ClaimRepairEngine()
    ledger = EvidenceLedger(ledger_path)
    rows = []
    for case in cases:
        cert = asdict(repair_engine.repair(
            context=case["context"],
            prompt=case.get("prompt", "Answer using only the supplied context."),
            answer=case["answer"],
            model_id="full-stack-validator-v8",
        ))
        raw_entry = ledger.append_repair_certificate(cert, model_id="full-stack-validator-v8")
        entry = asdict(raw_entry) if hasattr(raw_entry, "__dataclass_fields__") else dict(raw_entry)
        rows.append({
            "case_id": case["case_id"],
            "entry_hash": first_present(entry, ["entry_hash", "record_hash", "chain_hash", "ledger_hash", "hash", "entry_sha256"]),
            "previous_entry_hash": first_present(entry, ["previous_entry_hash", "previous_hash", "prev_entry_hash", "prev_hash"]),
            "final_repair_action": first_present(entry, ["final_repair_action", "repair_action"], cert.get("final_repair_action")),
            "fusion_action": first_present(entry, ["fusion_action", "final_action"], cert.get("fusion_action")),
            "entry_keys": sorted(entry.keys()),
        })
    entries = read_jsonl(ledger_path)
    ledger_summary = {"ledger_path": str(ledger_path), "entry_count": len(entries), "chain_ok": verify_chain(entries), "rows": rows}
    (out_dir / "full_stack_ledger_summary.json").write_text(json.dumps(ledger_summary, indent=2, sort_keys=True), encoding="utf-8")
    return ledger_summary


def main() -> None:
    root = Path.cwd()
    out_dir = root / "local_full_stack_outputs"
    out_dir.mkdir(exist_ok=True)

    runs = []
    runs.append(run_cmd("compile", [sys.executable, "-m", "compileall", "ai_trust_enablement"]))
    runs.append(run_cmd("contract_check", [sys.executable, "local_contract_check.py"]))
    runs.append(run_cmd("closure_validator", [sys.executable, "local_rnke_closure_validator.py"]))
    runs.append(run_cmd("smoke_suite", [sys.executable, "-m", "ai_trust_enablement.local_smoke_suite", "--out-dir", "local_run_outputs"]))
    runs.append(run_cmd("detection_benchmark", [sys.executable, "-m", "ai_trust_enablement.local_smoke_suite", "--cases", "local_benchmark_cases.json", "--out-dir", "local_benchmark_outputs"]))
    runs.append(run_cmd("repair_validator", [sys.executable, "local_repair_validator.py"]))
    runs.append(run_cmd("retrieval_resolution_validator", [sys.executable, "local_resolution_validator.py"]))
    runs.append(run_cmd("release_controller_validator", [sys.executable, "local_release_controller_validator.py"]))
    runs.append(run_cmd("release_api_validator", [sys.executable, "local_release_api_validator.py"]))
    runs.append(run_cmd("resolution_api_validator", [sys.executable, "local_resolution_api_validator.py"]))
    runs.append(run_cmd("adversarial_benchmark", [sys.executable, "-m", "ai_trust_enablement.local_smoke_suite", "--cases", "local_adversarial_cases_v1.json", "--out-dir", "local_adversarial_outputs_v1"]))
    runs.append(run_cmd("baseline_comparison", [sys.executable, "local_baseline_comparison.py"]))
    runs.append(run_cmd("adversarial_baseline_comparison", [sys.executable, "local_adversarial_baseline_comparison_v1.py"]))

    ledger_summary = regenerate_ledger(root, out_dir)

    contract_summary = read_summary(root / "local_contract_outputs" / "contract_summary.json")
    closure_summary = read_summary(root / "local_closure_outputs" / "closure_validation_summary.json")
    smoke_summary = read_summary(root / "local_run_outputs" / "local_smoke_summary.json")
    benchmark_summary = read_summary(root / "local_benchmark_outputs" / "local_smoke_summary.json")
    repair_summary = read_summary(root / "local_repair_validation_outputs" / "repair_validation_summary.json")
    resolution_summary = read_summary(root / "local_resolution_validation_outputs" / "resolution_validation_summary.json")
    release_summary = read_summary(root / "local_release_controller_outputs" / "release_controller_validation_summary.json")
    release_api_summary = read_summary(root / "local_release_api_outputs" / "release_api_validation_summary.json")
    resolution_api_summary = read_summary(root / "local_resolution_api_outputs" / "resolution_api_validation_summary.json")
    adversarial_summary = read_summary(root / "local_adversarial_outputs_v1" / "local_smoke_summary.json")

    baseline_path = root / "local_baseline_outputs" / "baseline_comparison_summary.json"
    adversarial_baseline_path = root / "local_adversarial_baseline_outputs_v1" / "adversarial_baseline_summary.json"
    baseline_summary = json.loads(baseline_path.read_text(encoding="utf-8")) if baseline_path.exists() else {}
    adversarial_baseline_summary = json.loads(adversarial_baseline_path.read_text(encoding="utf-8")) if adversarial_baseline_path.exists() else {}

    final = {
        "suite": "local_full_stack_validator_v8",
        "compile_ok": runs[0]["ok"],
        "contract_ok": contract_summary["ok"],
        "contract_pass": contract_summary["pass_count"], "contract_fail": contract_summary["fail_count"],
        "closure_ok": closure_summary["ok"],
        "closure_pass": closure_summary["pass_count"], "closure_fail": closure_summary["fail_count"],
        "smoke_pass": smoke_summary["pass_count"], "smoke_fail": smoke_summary["fail_count"],
        "benchmark_pass": benchmark_summary["pass_count"], "benchmark_fail": benchmark_summary["fail_count"],
        "repair_pass": repair_summary["pass_count"], "repair_fail": repair_summary["fail_count"],
        "resolution_pass": resolution_summary["pass_count"], "resolution_fail": resolution_summary["fail_count"],
        "release_pass": release_summary["pass_count"], "release_fail": release_summary["fail_count"],
        "release_api_pass": release_api_summary["pass_count"], "release_api_fail": release_api_summary["fail_count"],
        "resolution_api_pass": resolution_api_summary["pass_count"], "resolution_api_fail": resolution_api_summary["fail_count"],
        "adversarial_pass": adversarial_summary["pass_count"], "adversarial_fail": adversarial_summary["fail_count"],
        "baseline_naive_pass": baseline_summary.get("naive_pass"), "baseline_fusion_pass": baseline_summary.get("fusion_pass"),
        "adversarial_baseline_naive_pass": adversarial_baseline_summary.get("naive_pass"),
        "adversarial_baseline_fusion_pass": adversarial_baseline_summary.get("fusion_pass"),
        "ledger_entries": ledger_summary["entry_count"], "ledger_chain_ok": ledger_summary["chain_ok"],
        "command_results": runs,
    }
    final["ok"] = (
        final["compile_ok"] and final["contract_ok"] and final["closure_ok"]
        and final["smoke_fail"] == 0 and final["benchmark_fail"] == 0
        and final["repair_fail"] == 0 and final["resolution_fail"] == 0
        and final["release_fail"] == 0 and final["release_api_fail"] == 0
        and final["resolution_api_fail"] == 0 and final["adversarial_fail"] == 0
        and final["ledger_chain_ok"]
        and baseline_summary.get("fusion_pass") == 10
        and adversarial_baseline_summary.get("fusion_pass") == 15
    )

    pre_closure_summary = dict(final)
    final_closure = asdict(RNKEClosureEngine().check_summary(pre_closure_summary))
    final["final_closure_status"] = final_closure["status"]
    final["final_closure_item_count"] = final_closure["item_count"]
    final["final_closure_hash"] = final_closure["report_hash"]
    final["final_closure_ok"] = final_closure["status"] == "CLOSED" and final_closure["item_count"] == 0
    final["ok"] = bool(final["ok"] and final["final_closure_ok"])
    (out_dir / "final_closure_certificate.json").write_text(json.dumps(final_closure, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    (out_dir / "full_stack_summary.json").write_text(json.dumps(final, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Local Full Stack Validation Report v8", "", f"Overall OK: `{final['ok']}`", "",
        "| Layer | Pass | Fail / Status |", "|---|---:|---|",
        f"| Compile | {1 if final['compile_ok'] else 0} | {'OK' if final['compile_ok'] else 'FAIL'} |",
        f"| Service contract | {final['contract_pass']} | {final['contract_fail']} fail |",
        f"| RNKE closure | {final['closure_pass']} | {final['closure_fail']} fail |",
        f"| Final proof closure | {1 if final['final_closure_ok'] else 0} | {final['final_closure_status']} items={final['final_closure_item_count']} |",
        f"| Smoke suite | {final['smoke_pass']} | {final['smoke_fail']} fail |",
        f"| Detection benchmark | {final['benchmark_pass']} | {final['benchmark_fail']} fail |",
        f"| Repair validation | {final['repair_pass']} | {final['repair_fail']} fail |",
        f"| Retrieval resolution | {final['resolution_pass']} | {final['resolution_fail']} fail |",
        f"| Release controller | {final['release_pass']} | {final['release_fail']} fail |",
        f"| Release API | {final['release_api_pass']} | {final['release_api_fail']} fail |",
        f"| Resolution API | {final['resolution_api_pass']} | {final['resolution_api_fail']} fail |",
        f"| Adversarial benchmark | {final['adversarial_pass']} | {final['adversarial_fail']} fail |",
        f"| Baseline comparison | Fusion {final['baseline_fusion_pass']} | Naive {final['baseline_naive_pass']} |",
        f"| Adversarial baseline | Fusion {final['adversarial_baseline_fusion_pass']} | Naive {final['adversarial_baseline_naive_pass']} |",
        f"| Evidence ledger | {final['ledger_entries']} entries | Chain OK: `{final['ledger_chain_ok']}` |",
        "", "## Final Closure", "",
        f"- Status: `{final['final_closure_status']}`",
        f"- Item count: `{final['final_closure_item_count']}`",
        f"- Closure hash: `{final['final_closure_hash']}`",
        f"- Certificate: `local_full_stack_outputs/final_closure_certificate.json`",
        "", "## Command Status", "", "| Command | OK | Return Code |", "|---|---:|---:|",
    ]
    for r in runs:
        lines.append(f"| {r['name']} | {r['ok']} | {r['returncode']} |")
    report_md = out_dir / "full_stack_report.md"
    report_md.write_text("\n".join(lines), encoding="utf-8")

    print()
    print("LOCAL FULL STACK VALIDATION V8")
    print("=" * 94)
    print(f"Compile OK: {final['compile_ok']}")
    print(f"Service contract: {final['contract_pass']} pass, {final['contract_fail']} fail")
    print(f"RNKE closure: {final['closure_pass']} pass, {final['closure_fail']} fail")
    print(f"Final proof closure: {final['final_closure_status']} items={final['final_closure_item_count']}")
    print(f"Smoke: {final['smoke_pass']} pass, {final['smoke_fail']} fail")
    print(f"Detection benchmark: {final['benchmark_pass']} pass, {final['benchmark_fail']} fail")
    print(f"Repair validation: {final['repair_pass']} pass, {final['repair_fail']} fail")
    print(f"Retrieval resolution: {final['resolution_pass']} pass, {final['resolution_fail']} fail")
    print(f"Release controller: {final['release_pass']} pass, {final['release_fail']} fail")
    print(f"Release API: {final['release_api_pass']} pass, {final['release_api_fail']} fail")
    print(f"Resolution API: {final['resolution_api_pass']} pass, {final['resolution_api_fail']} fail")
    print(f"Adversarial benchmark: {final['adversarial_pass']} pass, {final['adversarial_fail']} fail")
    print(f"Baseline comparison: fusion {final['baseline_fusion_pass']}, naive {final['baseline_naive_pass']}")
    print(f"Adversarial baseline: fusion {final['adversarial_baseline_fusion_pass']}, naive {final['adversarial_baseline_naive_pass']}")
    print(f"Ledger: {final['ledger_entries']} entries, chain OK = {final['ledger_chain_ok']}")
    print("-" * 94)
    print(f"OVERALL OK = {final['ok']}")
    print(f"Final closure certificate: {out_dir / 'final_closure_certificate.json'}")
    print(f"Report: {report_md}")

    if not final["ok"]:
        print()
        print("FAILED COMMAND OUTPUTS")
        print("=" * 94)
        for r in runs:
            if not r["ok"]:
                print(f"\n--- {r['name']} ---")
                print(r["stdout"])
                print(r["stderr"])
        sys.exit(1)


if __name__ == "__main__":
    main()
