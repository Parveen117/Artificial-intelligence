#!/usr/bin/env python3
"""Tiny client for the AI Trust Enablement HTTP service."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict


def post_json(url: str, payload: Dict[str, Any], token: str = "") -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:  # noqa: S310 - caller supplied URL for local/internal API
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Client for AI Trust Enablement service")
    parser.add_argument("--url", default="http://127.0.0.1:8080/v1/evaluate")
    parser.add_argument("--token", default=os.getenv("AI_TRUST_API_TOKEN", ""))
    parser.add_argument("--context", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--answer", required=True)
    parser.add_argument("--model-id", default="client-model")
    parser.add_argument("--out", default="client_certificate.json")
    args = parser.parse_args()

    payload = {
        "context": args.context,
        "prompt": args.prompt,
        "answer": args.answer,
        "model_id": args.model_id,
    }
    result = post_json(args.url, payload, token=args.token)
    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"ok": True, "out": args.out, "classification": result.get("recognition_state", {}).get("classification")}, indent=2))


if __name__ == "__main__":
    main()
