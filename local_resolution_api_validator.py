#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

from ai_trust_enablement.service_contract import RESOLVE_ENDPOINT, SERVICE_VERSION


HOST = "127.0.0.1"
PORT = 8100
BASE_URL = f"http://{HOST}:{PORT}"


CASES: List[Dict[str, Any]] = [
    {
        "case_id": "api_resolve_supported_robotics_lab",
        "context": "The school library opens at 8 AM. Students may borrow two books at a time.",
        "prompt": "Answer using only the supplied context.",
        "answer": "The school library opens at 8 AM. Students may borrow two books at a time. The library has a robotics lab.",
        "retrieved_evidence": [
            {"request_id": "R1", "evidence_text": "The school library has a robotics lab.", "source_id": "manual-school-facility-note"}
        ],
        "expected_final_release_action": "RELEASE_REPAIRED",
        "expected_supported": 1,
        "expected_contradicted": 0,
        "expected_unresolved": 0,
        "required_final_safe_substrings": ["robotics lab"]
    },
    {
        "case_id": "api_resolve_refuted_extra_capability",
        "context": "The device should be stored after use.",
        "prompt": "Answer using only the supplied context.",
        "answer": "The device should be stored after use. It also repairs phones automatically.",
        "retrieved_evidence": [
            {"request_id": "R1", "evidence_text": "The device manual does not state that it repairs phones automatically.", "source_id": "manual-device-note"}
        ],
        "expected_final_release_action": "DO_NOT_RELEASE",
        "expected_supported": 0,
        "expected_contradicted": 1,
        "expected_unresolved": 0,
        "required_final_safe_substrings": []
    },
    {
        "case_id": "api_resolve_unrelated_evidence",
        "context": "The school library opens at 8 AM. Students may borrow two books at a time.",
        "prompt": "Answer using only the supplied context.",
        "answer": "The school library opens at 8 AM. Students may borrow two books at a time. The library has a robotics lab.",
        "retrieved_evidence": [
            {"request_id": "R1", "evidence_text": "The school library has a quiet reading corner.", "source_id": "manual-school-facility-note"}
        ],
        "expected_final_release_action": "HOLD_FOR_RETRIEVAL",
        "expected_supported": 0,
        "expected_contradicted": 0,
        "expected_unresolved": 1,
        "required_final_safe_substrings": ["opens at 8 AM"]
    }
]


def contains_all(text: str, needles: List[str]) -> bool:
    low = text.lower()
    return all(n.lower() in low for n in needles)


def get_json(path: str) -> Dict[str, Any]:
    with urllib.request.urlopen(BASE_URL + path, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(path: str, payload: Dict[str, Any], expected_status: int = 200) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(BASE_URL + path, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
            if response.status != expected_status:
                raise AssertionError(f"expected HTTP {expected_status}, got {response.status}: {body}")
            return body
    except urllib.error.HTTPError as exc:
        body = json.loads(exc.read().decode("utf-8"))
        if exc.code != expected_status:
            raise AssertionError(f"expected HTTP {expected_status}, got {exc.code}: {body}")
        return body


def wait_for_server() -> Dict[str, Any]:
    last_error: Exception | None = None
    for _ in range(60):
        try:
            payload = get_json("/healthz")
            if payload.get("ok"):
                return payload
        except Exception as exc:
            last_error = exc
            time.sleep(0.25)
    raise RuntimeError(f"server_not_ready:{last_error!r}")


def validate_case(case: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "context": case["context"],
        "prompt": case["prompt"],
        "answer": case["answer"],
        "retrieved_evidence": case["retrieved_evidence"],
        "model_id": "resolution-api-validator",
    }
    cert = post_json("/v1/resolve", payload)
    final_safe = cert.get("final_safe_answer", "")
    checks = {
        "final_action": cert.get("final_release_action") == case["expected_final_release_action"],
        "supported_count": cert.get("resolved_supported_count") == case["expected_supported"],
        "contradicted_count": cert.get("resolved_contradicted_count") == case["expected_contradicted"],
        "unresolved_count": cert.get("unresolved_count") == case["expected_unresolved"],
        "safe_required": contains_all(final_safe, case.get("required_final_safe_substrings", [])),
        "resolution_hash": isinstance(cert.get("resolution_hash"), str) and len(cert.get("resolution_hash", "")) == 64,
        "certificate_hash": cert.get("resolution_hash") == cert.get("certificate_hash"),
        "service_version": cert.get("service_version") == SERVICE_VERSION,
    }
    return {
        "case_id": case["case_id"],
        "ok": all(checks.values()),
        "expected_final_release_action": case["expected_final_release_action"],
        "actual_final_release_action": cert.get("final_release_action"),
        "supported": cert.get("resolved_supported_count"),
        "contradicted": cert.get("resolved_contradicted_count"),
        "unresolved": cert.get("unresolved_count"),
        "final_safe_answer": final_safe,
        "checks": checks,
        "resolution_hash": cert.get("resolution_hash"),
    }


def main() -> None:
    out_dir = Path("local_resolution_api_outputs")
    out_dir.mkdir(exist_ok=True)
    env = os.environ.copy()
    env["AI_TRUST_HOST"] = HOST
    env["AI_TRUST_PORT"] = str(PORT)
    process = subprocess.Popen([sys.executable, "-m", "ai_trust_enablement.server"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    try:
        health = wait_for_server()
        version = get_json("/version")
        endpoint_ok = RESOLVE_ENDPOINT in version.get("endpoints", [])
        version_ok = version.get("version") == SERVICE_VERSION
        results = [validate_case(case) for case in CASES]
        bad_request = post_json("/v1/resolve", {"context": "x"}, expected_status=400)
        bad_request_ok = bad_request.get("error") == "bad_request"
        summary = {
            "suite": "local_resolution_api_validator_v1",
            "health_ok": bool(health.get("ok")),
            "endpoint_ok": endpoint_ok,
            "version_ok": version_ok,
            "expected_service_version": SERVICE_VERSION,
            "actual_service_version": version.get("version"),
            "bad_request_ok": bad_request_ok,
            "case_count": len(results),
            "pass_count": sum(1 for r in results if r["ok"]),
            "fail_count": sum(1 for r in results if not r["ok"]),
            "results": results,
        }
        summary["ok"] = summary["health_ok"] and summary["endpoint_ok"] and summary["version_ok"] and summary["bad_request_ok"] and summary["fail_count"] == 0
        (out_dir / "resolution_api_validation_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        print("\nLOCAL RESOLUTION API VALIDATION V1")
        print("=" * 88)
        print(f"health_ok={summary['health_ok']} endpoint_ok={summary['endpoint_ok']} version_ok={summary['version_ok']} bad_request_ok={summary['bad_request_ok']}")
        for r in results:
            print(f"{r['case_id'][:36]:36} {str(r['ok']):5} {r['actual_final_release_action']}")
        print("-" * 88)
        print(f"PASS={summary['pass_count']} FAIL={summary['fail_count']} OK={summary['ok']}")
        if not summary["ok"]:
            print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
            sys.exit(1)
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    main()
