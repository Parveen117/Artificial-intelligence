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


HOST = "127.0.0.1"
PORT = 8099
BASE_URL = f"http://{HOST}:{PORT}"
EXPECTED_SERVICE_VERSION = "1.2.0"


CASES: List[Dict[str, Any]] = [
    {
        "case_id": "api_release_grounded_original",
        "context": "The school library opens at 8 AM. Students may borrow two books at a time.",
        "prompt": "Answer using only the supplied context.",
        "answer": "The school library opens at 8 AM. Students may borrow two books at a time.",
        "expected_action": "RELEASE_ORIGINAL",
        "required_visible_substrings": ["opens at 8 AM", "borrow two books"],
        "forbidden_visible_substrings": ["robotics lab"],
    },
    {
        "case_id": "api_release_repaired_wrong_time",
        "context": "The school library opens at 8 AM. Students may borrow two books at a time.",
        "prompt": "Answer using only the supplied context.",
        "answer": "The school library opens at 10 AM. Students may borrow two books at a time.",
        "expected_action": "RELEASE_REPAIRED",
        "required_visible_substrings": ["opens at 8 AM", "borrow two books"],
        "forbidden_visible_substrings": ["10 AM"],
    },
    {
        "case_id": "api_hold_unsupported_extra_claim",
        "context": "The school library opens at 8 AM. Students may borrow two books at a time.",
        "prompt": "Answer using only the supplied context.",
        "answer": "The school library opens at 8 AM. Students may borrow two books at a time. The library has a robotics lab.",
        "expected_action": "HOLD_FOR_RETRIEVAL",
        "required_visible_substrings": ["opens at 8 AM", "borrow two books"],
        "forbidden_visible_substrings": ["robotics lab"],
        "expected_retrieval_requests": 1,
    },
]


def contains_all(text: str, needles: List[str]) -> bool:
    low = text.lower()
    return all(n.lower() in low for n in needles)


def contains_none(text: str, needles: List[str]) -> bool:
    low = text.lower()
    return all(n.lower() not in low for n in needles)


def get_json(path: str) -> Dict[str, Any]:
    with urllib.request.urlopen(BASE_URL + path, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(path: str, payload: Dict[str, Any], expected_status: int = 200) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
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
        "model_id": "release-api-validator",
    }
    cert = post_json("/v1/release", payload)
    visible = cert.get("user_visible_answer", "")
    retrieval_plan = cert.get("retrieval_plan") or {}
    request_count = int(retrieval_plan.get("request_count", 0) or 0)
    checks = {
        "action": cert.get("release_action") == case["expected_action"],
        "visible_required": contains_all(visible, case.get("required_visible_substrings", [])),
        "visible_forbidden": contains_none(visible, case.get("forbidden_visible_substrings", [])),
        "release_hash": isinstance(cert.get("release_hash"), str) and len(cert.get("release_hash", "")) == 64,
        "service_version": cert.get("service_version") == EXPECTED_SERVICE_VERSION,
    }
    if "expected_retrieval_requests" in case:
        checks["retrieval_count"] = request_count == case["expected_retrieval_requests"]
    return {
        "case_id": case["case_id"],
        "ok": all(checks.values()),
        "expected_action": case["expected_action"],
        "actual_action": cert.get("release_action"),
        "reason": cert.get("reason"),
        "retrieval_request_count": request_count,
        "checks": checks,
        "release_hash": cert.get("release_hash"),
    }


def main() -> None:
    out_dir = Path("local_release_api_outputs")
    out_dir.mkdir(exist_ok=True)
    ledger_path = out_dir / "release_api_ledger.jsonl"
    if ledger_path.exists():
        ledger_path.unlink()

    env = os.environ.copy()
    env["AI_TRUST_HOST"] = HOST
    env["AI_TRUST_PORT"] = str(PORT)
    env["AI_TRUST_RELEASE_LEDGER_PATH"] = str(ledger_path)

    process = subprocess.Popen(
        [sys.executable, "-m", "ai_trust_enablement.server"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        health = wait_for_server()
        version = get_json("/version")
        endpoint_ok = "POST /v1/release" in version.get("endpoints", [])
        version_ok = version.get("version") == EXPECTED_SERVICE_VERSION
        results = [validate_case(case) for case in CASES]
        bad_request = post_json("/v1/release", {"context": "x"}, expected_status=400)
        bad_request_ok = bad_request.get("error") == "bad_request"
        summary = {
            "suite": "local_release_api_validator_v1",
            "health_ok": bool(health.get("ok")),
            "endpoint_ok": endpoint_ok,
            "version_ok": version_ok,
            "expected_service_version": EXPECTED_SERVICE_VERSION,
            "actual_service_version": version.get("version"),
            "bad_request_ok": bad_request_ok,
            "case_count": len(results),
            "pass_count": sum(1 for r in results if r["ok"]),
            "fail_count": sum(1 for r in results if not r["ok"]),
            "results": results,
            "ledger_path": str(ledger_path),
        }
        summary["ok"] = summary["health_ok"] and summary["endpoint_ok"] and summary["version_ok"] and summary["bad_request_ok"] and summary["fail_count"] == 0
        (out_dir / "release_api_validation_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        print("\nLOCAL RELEASE API VALIDATION V1")
        print("=" * 88)
        print(f"health_ok={summary['health_ok']} endpoint_ok={summary['endpoint_ok']} version_ok={summary['version_ok']} bad_request_ok={summary['bad_request_ok']}")
        for r in results:
            print(f"{r['case_id'][:36]:36} {str(r['ok']):5} {r['actual_action']}")
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
