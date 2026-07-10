from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from ai_trust_enablement.rnke_closure_engine import RNKEClosureEngine, stable_hash
from ai_trust_enablement.service_contract import version_payload


ROOT = Path.cwd()
OUT_DIR = ROOT / "local_full_stack_outputs"
CERT_PATH = OUT_DIR / "final_closure_bundle_v2.json"
VERIFY_PATH = OUT_DIR / "final_closure_bundle_v2_verification.json"


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"missing": True, "path": str(path)}
    return json.loads(path.read_text(encoding="utf-8"))


def build_sources() -> Dict[str, Any]:
    return {
        "service_contract": version_payload(),
        "full_stack_summary": read_json(ROOT / "local_full_stack_outputs" / "full_stack_summary.json"),
        "full_stack_ledger": read_json(ROOT / "local_full_stack_outputs" / "full_stack_ledger_summary.json"),
        "contract_check": read_json(ROOT / "local_contract_outputs" / "contract_summary.json"),
        "rnke_closure_validation": read_json(ROOT / "local_closure_outputs" / "closure_validation_summary.json"),
        "smoke": read_json(ROOT / "local_run_outputs" / "local_smoke_summary.json"),
        "benchmark": read_json(ROOT / "local_benchmark_outputs" / "local_smoke_summary.json"),
        "repair": read_json(ROOT / "local_repair_validation_outputs" / "repair_validation_summary.json"),
        "retrieval_resolution": read_json(ROOT / "local_resolution_validation_outputs" / "resolution_validation_summary.json"),
        "release_controller": read_json(ROOT / "local_release_controller_outputs" / "release_controller_validation_summary.json"),
        "release_api": read_json(ROOT / "local_release_api_outputs" / "release_api_validation_summary.json"),
        "resolution_api": read_json(ROOT / "local_resolution_api_outputs" / "resolution_api_validation_summary.json"),
        "adversarial": read_json(ROOT / "local_adversarial_outputs_v1" / "local_smoke_summary.json"),
        "baseline": read_json(ROOT / "local_baseline_outputs" / "baseline_comparison_summary.json"),
        "adversarial_baseline": read_json(ROOT / "local_adversarial_baseline_outputs_v1" / "adversarial_baseline_summary.json"),
    }


def build_basis(sources: Dict[str, Any]) -> Dict[str, str]:
    basis = {f"{name}_hash": stable_hash(value) for name, value in sources.items()}
    basis["full_bundle_hash"] = stable_hash(basis)
    return basis


def generate_certificate() -> Dict[str, Any]:
    sources = build_sources()
    basis = build_basis(sources)
    summary = sources["full_stack_summary"]
    certificate = asdict(RNKEClosureEngine().check_summary(summary))
    certificate["certificate_version"] = "2.1.0"
    certificate["basis"] = basis
    certificate["source_count"] = len(sources)
    certificate["ok"] = certificate["status"] == "CLOSED" and certificate["item_count"] == 0
    certificate["report_hash"] = stable_hash({key: value for key, value in certificate.items() if key != "report_hash"})
    CERT_PATH.write_text(json.dumps(certificate, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    return certificate


def verify_certificate(certificate: Dict[str, Any]) -> Dict[str, Any]:
    sources = build_sources()
    basis = build_basis(sources)
    summary = sources["full_stack_summary"]
    closure = RNKEClosureEngine().check_summary(summary)
    strict_payload = {key: value for key, value in certificate.items() if key != "report_hash"}
    legacy_payload = {key: value for key, value in certificate.items() if key not in {"report_hash", "ok"}}
    report_hashes = {
        "strict_report_hash": stable_hash(strict_payload),
        "legacy_v2_report_hash": stable_hash(legacy_payload),
    }
    checks = {
        "basis_matches_sources": certificate.get("basis") == basis,
        "full_bundle_hash_matches": certificate.get("basis", {}).get("full_bundle_hash") == basis.get("full_bundle_hash"),
        "status_closed": certificate.get("status") == "CLOSED",
        "item_count_zero": certificate.get("item_count") == 0,
        "items_empty": certificate.get("items") == [],
        "source_count_matches": certificate.get("source_count") == len(sources),
        "engine_recheck_matches": certificate.get("status") == closure.status and certificate.get("item_count") == closure.item_count,
        "report_hash_matches": certificate.get("report_hash") in set(report_hashes.values()),
    }
    verification = {
        "suite": "final_closure_bundle_v2_verifier",
        "ok": all(checks.values()),
        "checks": checks,
        "stored_full_bundle_hash": certificate.get("basis", {}).get("full_bundle_hash"),
        "recomputed_full_bundle_hash": basis.get("full_bundle_hash"),
        "stored_report_hash": certificate.get("report_hash"),
        "recomputed_report_hashes": report_hashes,
        "certificate_path": str(CERT_PATH),
    }
    VERIFY_PATH.write_text(json.dumps(verification, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    return verification


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate or verify the final closure bundle certificate.")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    OUT_DIR.mkdir(exist_ok=True)
    cert = read_json(CERT_PATH) if args.verify_only else generate_certificate()
    verification = verify_certificate(cert)

    print("\nFINAL CLOSURE BUNDLE V2")
    print("=" * 88)
    print(f"status={cert.get('status')} item_count={cert.get('item_count')} ok={cert.get('ok')}")
    print(f"bundle_hash={cert.get('basis', {}).get('full_bundle_hash')}")
    print(f"report_hash={cert.get('report_hash')}")
    print(f"verification_ok={verification['ok']}")
    print(f"certificate={CERT_PATH}")
    print(f"verification={VERIFY_PATH}")
    if not verification["ok"]:
        print(json.dumps(verification, indent=2, sort_keys=True, ensure_ascii=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
