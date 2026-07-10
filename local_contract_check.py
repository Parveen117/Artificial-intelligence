from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict

from ai_trust_enablement.service_contract import ENDPOINTS, SERVICE_NAME, SERVICE_VERSION, version_payload

HOST = "127.0.0.1"
PORT = 8101
BASE_URL = f"http://{HOST}:{PORT}"


def get_json(path: str) -> Dict[str, Any]:
    with urllib.request.urlopen(BASE_URL + path, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_server() -> Dict[str, Any]:
    for _ in range(60):
        try:
            payload = get_json("/healthz")
            if payload.get("ok"):
                return payload
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("server_not_ready")


def main() -> None:
    out_dir = Path("local_contract_outputs")
    out_dir.mkdir(exist_ok=True)
    env = os.environ.copy()
    env["AI_TRUST_HOST"] = HOST
    env["AI_TRUST_PORT"] = str(PORT)
    process = subprocess.Popen([sys.executable, "-m", "ai_trust_enablement.server"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    try:
        health = wait_for_server()
        version = get_json("/version")
        checks = {
            "health_service": health.get("service") == SERVICE_NAME,
            "health_version": health.get("version") == SERVICE_VERSION,
            "version_payload": version == version_payload(),
            "endpoints": list(version.get("endpoints", [])) == list(ENDPOINTS),
        }
        summary = {"suite": "local_contract_check_v1", "ok": all(checks.values()), "checks": checks, "health": health, "version": version}
        (out_dir / "contract_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        print("\nLOCAL CONTRACT CHECK V1")
        print("=" * 88)
        for key, ok in checks.items():
            print(f"{key:20} {ok}")
        print("-" * 88)
        print(f"OK={summary['ok']}")
        if not summary["ok"]:
            print(json.dumps(summary, indent=2, sort_keys=True))
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
