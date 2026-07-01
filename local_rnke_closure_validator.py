from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from ai_trust_enablement.rnke_closure_engine import RNKEClosureEngine
from ai_trust_enablement.service_contract import ENDPOINTS, SERVICE_NAME, SERVICE_VERSION, version_payload


CASES: List[Dict[str, Any]] = [
    {
        "case_id": "closed_service_contract",
        "health": {"ok": True, "service": SERVICE_NAME, "version": SERVICE_VERSION},
        "version_doc": version_payload(),
        "expected_status": "CLOSED",
        "expected_item_count": 0,
    },
    {
        "case_id": "version_mismatch_residue",
        "health": {"ok": True, "service": SERVICE_NAME, "version": "0.0.0"},
        "version_doc": {**version_payload(), "version": "0.0.0"},
        "expected_status": "SEAM_RESIDUE",
        "expected_kinds": ["SERVICE_VERSION_MISMATCH", "VERSION_PAYLOAD_MISMATCH"],
    },
    {
        "case_id": "endpoint_missing_residue",
        "health": {"ok": True, "service": SERVICE_NAME, "version": SERVICE_VERSION},
        "version_doc": {**version_payload(), "endpoints": [x for x in ENDPOINTS if x != "POST /v1/resolve"]},
        "expected_status": "SEAM_RESIDUE",
        "expected_kinds": ["VERSION_PAYLOAD_MISMATCH", "ENDPOINT_MISSING"],
    },
    {
        "case_id": "summary_open_residue",
        "summary": {"ok": False, "contract_fail": 1, "release_api_fail": 0, "resolution_api_fail": 0, "ledger_chain_ok": True},
        "expected_status": "SEAM_RESIDUE",
        "expected_kinds": ["SUMMARY_NOT_OK", "LAYER_FAIL_COUNT"],
    },
]


def has_kinds(report: Dict[str, Any], kinds: List[str]) -> bool:
    observed = {item.get("kind") for item in report.get("items", [])}
    return all(kind in observed for kind in kinds)


def validate_case(engine: RNKEClosureEngine, case: Dict[str, Any], out_dir: Path) -> Dict[str, Any]:
    if "summary" in case:
        report = asdict(engine.check_summary(case["summary"]))
    else:
        report = asdict(engine.check_service(case["health"], case["version_doc"]))
    (out_dir / f"{case['case_id']}_closure_report.json").write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    checks = {
        "status": report.get("status") == case["expected_status"],
        "hash": isinstance(report.get("report_hash"), str) and len(report.get("report_hash", "")) == 64,
    }
    if "expected_item_count" in case:
        checks["item_count"] = report.get("item_count") == case["expected_item_count"]
    if "expected_kinds" in case:
        checks["kinds"] = has_kinds(report, case["expected_kinds"])
    return {
        "case_id": case["case_id"],
        "ok": all(checks.values()),
        "status": report.get("status"),
        "item_count": report.get("item_count"),
        "checks": checks,
        "report_hash": report.get("report_hash"),
    }


def main() -> None:
    out_dir = Path("local_closure_outputs")
    out_dir.mkdir(exist_ok=True)
    engine = RNKEClosureEngine()
    results = [validate_case(engine, case, out_dir) for case in CASES]
    summary = {
        "suite": "local_rnke_closure_validator_v1",
        "case_count": len(results),
        "pass_count": sum(1 for r in results if r["ok"]),
        "fail_count": sum(1 for r in results if not r["ok"]),
        "results": results,
    }
    summary["ok"] = summary["fail_count"] == 0
    (out_dir / "closure_validation_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    print("\nLOCAL RNKE CLOSURE VALIDATION V1")
    print("=" * 88)
    for r in results:
        print(f"{r['case_id'][:36]:36} {str(r['ok']):5} {r['status']} items={r['item_count']}")
    print("-" * 88)
    print(f"PASS={summary['pass_count']} FAIL={summary['fail_count']} OK={summary['ok']}")
    if not summary["ok"]:
        print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
