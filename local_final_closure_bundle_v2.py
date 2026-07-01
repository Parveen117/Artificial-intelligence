from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from ai_trust_enablement.rnke_closure_engine import RNKEClosureEngine, stable_hash
from ai_trust_enablement.service_contract import version_payload


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"missing": True, "path": str(path)}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    root = Path.cwd()
    out_dir = root / "local_full_stack_outputs"
    out_dir.mkdir(exist_ok=True)

    sources = {
        "service_contract": version_payload(),
        "full_stack_summary": read_json(root / "local_full_stack_outputs" / "full_stack_summary.json"),
        "full_stack_ledger": read_json(root / "local_full_stack_outputs" / "full_stack_ledger_summary.json"),
        "contract_check": read_json(root / "local_contract_outputs" / "contract_summary.json"),
        "rnke_closure_validation": read_json(root / "local_closure_outputs" / "closure_validation_summary.json"),
        "smoke": read_json(root / "local_run_outputs" / "local_smoke_summary.json"),
        "benchmark": read_json(root / "local_benchmark_outputs" / "local_smoke_summary.json"),
        "repair": read_json(root / "local_repair_validation_outputs" / "repair_validation_summary.json"),
        "retrieval_resolution": read_json(root / "local_resolution_validation_outputs" / "resolution_validation_summary.json"),
        "release_controller": read_json(root / "local_release_controller_outputs" / "release_controller_validation_summary.json"),
        "release_api": read_json(root / "local_release_api_outputs" / "release_api_validation_summary.json"),
        "resolution_api": read_json(root / "local_resolution_api_outputs" / "resolution_api_validation_summary.json"),
        "adversarial": read_json(root / "local_adversarial_outputs_v1" / "local_smoke_summary.json"),
        "baseline": read_json(root / "local_baseline_outputs" / "baseline_comparison_summary.json"),
        "adversarial_baseline": read_json(root / "local_adversarial_baseline_outputs_v1" / "adversarial_baseline_summary.json"),
    }

    basis = {f"{name}_hash": stable_hash(value) for name, value in sources.items()}
    basis["full_bundle_hash"] = stable_hash(basis)

    summary = sources["full_stack_summary"]
    certificate = asdict(RNKEClosureEngine().check_summary(summary))
    certificate["certificate_version"] = "2.0.0"
    certificate["basis"] = basis
    certificate["source_count"] = len(sources)
    certificate["report_hash"] = stable_hash({key: value for key, value in certificate.items() if key != "report_hash"})
    certificate["ok"] = certificate["status"] == "CLOSED" and certificate["item_count"] == 0

    (out_dir / "final_closure_bundle_v2.json").write_text(json.dumps(certificate, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    print("\nFINAL CLOSURE BUNDLE V2")
    print("=" * 88)
    print(f"status={certificate['status']} item_count={certificate['item_count']} ok={certificate['ok']}")
    print(f"bundle_hash={basis['full_bundle_hash']}")
    print(f"report_hash={certificate['report_hash']}")
    print(f"certificate={out_dir / 'final_closure_bundle_v2.json'}")
    if not certificate["ok"]:
        print(json.dumps(certificate, indent=2, sort_keys=True, ensure_ascii=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
