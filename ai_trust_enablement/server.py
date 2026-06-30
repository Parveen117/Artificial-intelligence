#!/usr/bin/env python3
"""
AI Trust Enablement HTTP service.

A no-dependency deployment server for the AIHallucinationRecognitionEngine.
It exposes:
    GET  /healthz
    GET  /version
    GET  /schema
    POST /v1/evaluate
    POST /v1/batch

Security controls included without external packages:
    - optional bearer token auth via AI_TRUST_API_TOKEN
    - request body size limit via AI_TRUST_MAX_BODY_BYTES
    - simple per-client rate limit via AI_TRUST_RATE_LIMIT_PER_MIN

For real production exposure, put this behind TLS and a hardened reverse proxy.
Civilization has learned this the hard way, usually after someone exposed port 80
with the confidence of a toddler holding scissors.
"""

from __future__ import annotations

import json
import os
import time
import traceback
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List

try:  # package execution
    from .ai_hallucination_recognition_engine import AIHallucinationRecognitionEngine, sha256_json
except ImportError:  # direct script execution
    from ai_hallucination_recognition_engine import AIHallucinationRecognitionEngine, sha256_json

SERVICE_VERSION = "1.0.1"
BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "certificate_schema_v1.json"


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: Dict[str, Any]) -> None:
    data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


class RateLimiter:
    def __init__(self, limit_per_minute: int) -> None:
        self.limit = max(1, int(limit_per_minute))
        self.window_seconds = 60.0
        self._hits: Dict[str, List[float]] = {}

    def allow(self, client_key: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        hits = [t for t in self._hits.get(client_key, []) if t >= cutoff]
        if len(hits) >= self.limit:
            self._hits[client_key] = hits
            return False
        hits.append(now)
        self._hits[client_key] = hits
        return True


class AITrustHandler(BaseHTTPRequestHandler):
    server_version = "AITrustEnablementHTTP/1.0"
    engine = AIHallucinationRecognitionEngine()
    rate_limiter = RateLimiter(env_int("AI_TRUST_RATE_LIMIT_PER_MIN", 120))

    def log_message(self, fmt: str, *args: Any) -> None:
        # Avoid logging prompts/answers. Only standard request metadata is logged.
        client = self.client_address[0] if self.client_address else "unknown"
        print(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {client} {fmt % args}")

    def do_GET(self) -> None:  # noqa: N802
        if not self._rate_limit_ok():
            return
        if self.path == "/healthz":
            json_response(self, HTTPStatus.OK, {"ok": True, "service": "ai-trust-enable", "version": SERVICE_VERSION})
            return
        if self.path == "/version":
            json_response(self, HTTPStatus.OK, self._version_payload())
            return
        if self.path == "/schema":
            if SCHEMA_PATH.exists():
                payload = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
            else:
                payload = {"error": "schema_not_found"}
            json_response(self, HTTPStatus.OK, payload)
            return
        json_response(self, HTTPStatus.NOT_FOUND, {"error": "not_found", "path": self.path})

    def do_POST(self) -> None:  # noqa: N802
        if not self._rate_limit_ok():
            return
        if not self._auth_ok():
            return
        try:
            payload = self._read_json_body()
            if self.path == "/v1/evaluate":
                result = self._handle_evaluate(payload)
                json_response(self, HTTPStatus.OK, result)
                return
            if self.path == "/v1/batch":
                result = self._handle_batch(payload)
                json_response(self, HTTPStatus.OK, result)
                return
            json_response(self, HTTPStatus.NOT_FOUND, {"error": "not_found", "path": self.path})
        except ValueError as exc:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": "bad_request", "message": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive service boundary
            if os.getenv("AI_TRUST_DEBUG") == "1":
                detail = traceback.format_exc()
            else:
                detail = str(exc)
            json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "internal_error", "message": detail})

    def _version_payload(self) -> Dict[str, Any]:
        return {
            "service": "ai-trust-enable",
            "version": SERVICE_VERSION,
            "engine": "AIHallucinationRecognitionEngine",
            "schema": "AI_RECOGNITION_CERTIFICATE/v1",
            "endpoints": ["GET /healthz", "GET /version", "GET /schema", "POST /v1/evaluate", "POST /v1/batch"],
        }

    def _rate_limit_ok(self) -> bool:
        client = self.client_address[0] if self.client_address else "unknown"
        if not self.rate_limiter.allow(client):
            json_response(self, HTTPStatus.TOO_MANY_REQUESTS, {"error": "rate_limit_exceeded"})
            return False
        return True

    def _auth_ok(self) -> bool:
        expected = os.getenv("AI_TRUST_API_TOKEN", "")
        if not expected:
            return True
        observed = self.headers.get("Authorization", "")
        if observed != f"Bearer {expected}":
            json_response(self, HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return False
        return True

    def _read_json_body(self) -> Dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        max_body = env_int("AI_TRUST_MAX_BODY_BYTES", 1_000_000)
        if content_length <= 0:
            raise ValueError("empty_request_body")
        if content_length > max_body:
            raise ValueError(f"request_body_too_large:max={max_body}")
        raw = self.rfile.read(content_length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid_json:{exc.msg}") from exc
        if not isinstance(payload, dict):
            raise ValueError("json_body_must_be_object")
        return payload

    def _handle_evaluate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        for field in ["context", "prompt", "answer"]:
            if field not in payload or not isinstance(payload[field], str):
                raise ValueError(f"missing_or_invalid_{field}")
        logits = payload.get("logits")
        if logits is not None:
            if not isinstance(logits, list) or not all(isinstance(x, (int, float)) for x in logits):
                raise ValueError("logits_must_be_number_array")
        cert = self.engine.evaluate(
            reference_text=payload["context"],
            prompt_text=payload["prompt"],
            answer_text=payload["answer"],
            model_id=str(payload.get("model_id") or os.getenv("AI_TRUST_MODEL_ID", "model-under-test")),
            logits=logits,
            event_index=int(payload.get("event_index", 1)),
        )
        result = asdict(cert)
        result["service_version"] = SERVICE_VERSION
        return result

    def _handle_batch(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        cases = payload.get("cases")
        if not isinstance(cases, list):
            raise ValueError("cases_must_be_array")
        max_cases = env_int("AI_TRUST_MAX_BATCH_CASES", 50)
        if len(cases) > max_cases:
            raise ValueError(f"too_many_cases:max={max_cases}")
        results: List[Dict[str, Any]] = []
        for index, case in enumerate(cases, start=1):
            if not isinstance(case, dict):
                raise ValueError(f"case_{index}_must_be_object")
            cert = self.engine.evaluate(
                reference_text=str(case.get("context", "")),
                prompt_text=str(case.get("prompt", "")),
                answer_text=str(case.get("answer", "")),
                model_id=str(case.get("model_id") or payload.get("model_id") or os.getenv("AI_TRUST_MODEL_ID", "batch-model")),
                logits=case.get("logits"),
                event_index=int(case.get("event_index", index)),
            )
            item = asdict(cert)
            item["case_id"] = case.get("case_id", f"case_{index}")
            results.append(item)
        summary = {
            "case_count": len(results),
            "classification_counts": self._classification_counts(results),
            "batch_hash": sha256_json(results),
        }
        return {"summary": summary, "results": results, "service_version": SERVICE_VERSION}

    def _classification_counts(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for item in results:
            cls = item.get("recognition_state", {}).get("classification", "UNKNOWN")
            counts[cls] = counts.get(cls, 0) + 1
        return counts


def run() -> None:
    host = os.getenv("AI_TRUST_HOST", "0.0.0.0")
    port = env_int("AI_TRUST_PORT", 8080)
    server = ThreadingHTTPServer((host, port), AITrustHandler)
    print(json.dumps({"service": "ai-trust-enable", "version": SERVICE_VERSION, "host": host, "port": port}, sort_keys=True))
    server.serve_forever()


if __name__ == "__main__":
    run()
