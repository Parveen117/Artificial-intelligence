#!/usr/bin/env python3
"""
AI Trust Enablement HTTP service.

A no-dependency deployment server for the AI trust stack. Endpoint names and
service version are imported from service_contract.py so API tests and server
behavior stay closed under one shared contract. A rare outbreak of paperwork
behaving itself.
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
    from .ecl_commit_adapter import ECLCommitAdapter
    from .future_arrow_operator import FutureArrowConfig, FutureArrowOperator
    from .lambda_laplace_operator import LambdaLaplaceConfig, LambdaLaplaceOperator
    from .monti_operator import MontiOperator, MontiOperatorConfig
    from .release_controller import ReleaseController
    from .retrieval_resolution_engine import RetrievalResolutionEngine
    from .service_contract import SERVICE_NAME, SERVICE_VERSION, health_payload, version_payload
except ImportError:  # direct script execution
    from ai_hallucination_recognition_engine import AIHallucinationRecognitionEngine, sha256_json
    from ecl_commit_adapter import ECLCommitAdapter
    from future_arrow_operator import FutureArrowConfig, FutureArrowOperator
    from lambda_laplace_operator import LambdaLaplaceConfig, LambdaLaplaceOperator
    from monti_operator import MontiOperator, MontiOperatorConfig
    from release_controller import ReleaseController
    from retrieval_resolution_engine import RetrievalResolutionEngine
    from service_contract import SERVICE_NAME, SERVICE_VERSION, health_payload, version_payload

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
    server_version = "AITrustEnablementHTTP/1.5"
    engine = AIHallucinationRecognitionEngine()
    rate_limiter = RateLimiter(env_int("AI_TRUST_RATE_LIMIT_PER_MIN", 120))

    def log_message(self, fmt: str, *args: Any) -> None:
        client = self.client_address[0] if self.client_address else "unknown"
        print(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {client} {fmt % args}")

    def do_GET(self) -> None:  # noqa: N802
        if not self._rate_limit_ok():
            return
        if self.path == "/healthz":
            json_response(self, HTTPStatus.OK, health_payload())
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
            if self.path == "/v1/release":
                result = self._handle_release(payload)
                json_response(self, HTTPStatus.OK, result)
                return
            if self.path == "/v1/resolve":
                result = self._handle_resolve(payload)
                json_response(self, HTTPStatus.OK, result)
                return
            if self.path == "/v1/lambda-laplace":
                result = self._handle_lambda_laplace(payload)
                json_response(self, HTTPStatus.OK, result)
                return
            if self.path == "/v1/monti":
                result = self._handle_monti(payload)
                json_response(self, HTTPStatus.OK, result)
                return
            if self.path == "/v1/future-arrow":
                result = self._handle_future_arrow(payload)
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
        return version_payload()

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

    def _required_text_fields(self, payload: Dict[str, Any]) -> None:
        for field in ["context", "prompt", "answer"]:
            if field not in payload or not isinstance(payload[field], str):
                raise ValueError(f"missing_or_invalid_{field}")

    def _handle_evaluate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._required_text_fields(payload)
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

    def _handle_release(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._required_text_fields(payload)
        ledger_path = os.getenv("AI_TRUST_RELEASE_LEDGER_PATH", "") or None
        cert = ReleaseController(ledger_path).evaluate(
            context=payload["context"],
            prompt=payload["prompt"],
            answer=payload["answer"],
            model_id=str(payload.get("model_id") or os.getenv("AI_TRUST_MODEL_ID", "release-model")),
        )
        result = asdict(cert)
        result["service_version"] = SERVICE_VERSION
        return result

    def _handle_resolve(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._required_text_fields(payload)
        retrieved = payload.get("retrieved_evidence")
        if not isinstance(retrieved, list) or not all(isinstance(item, dict) for item in retrieved):
            raise ValueError("retrieved_evidence_must_be_array_of_objects")
        cert = RetrievalResolutionEngine().resolve(
            context=payload["context"],
            prompt=payload["prompt"],
            answer=payload["answer"],
            retrieved_evidence=retrieved,
            model_id=str(payload.get("model_id") or os.getenv("AI_TRUST_MODEL_ID", "resolve-model")),
        )
        result = asdict(cert)
        result["resolution_hash"] = result["certificate_hash"]
        result["final_release_action"] = self._release_action_from_resolution(result)
        result["service_version"] = SERVICE_VERSION
        return result

    def _handle_lambda_laplace(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        config = LambdaLaplaceConfig(
            dt=float(payload.get("dt", 1.0)),
            alpha=float(payload.get("alpha", 0.15)),
            beta=float(payload.get("beta", 0.10)),
            seam_threshold=float(payload.get("seam_threshold", 0.18)),
            stress_threshold=float(payload.get("stress_threshold", 0.45)),
            gap_threshold=float(payload.get("gap_threshold", 0.08)),
            heat_time=float(payload.get("heat_time", 1.0)),
        )
        operator = LambdaLaplaceOperator(config)
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        if "lambda_p_series" in payload:
            cert = operator.evaluate_series(
                lambda_p_series=payload["lambda_p_series"],
                lambda_v_series=payload.get("lambda_v_series"),
                skew_intensity_series=payload.get("skew_intensity_series"),
                entropy_potential_series=payload.get("entropy_potential_series"),
                model_id=str(payload.get("model_id") or os.getenv("AI_TRUST_MODEL_ID", "lambda-laplace-model")),
                event_index=int(payload.get("event_index", 1)),
                metadata=metadata,
            )
        elif "certificates" in payload:
            certificates = payload.get("certificates")
            if not isinstance(certificates, list) or not all(isinstance(item, dict) for item in certificates):
                raise ValueError("certificates_must_be_array_of_objects")
            cert = operator.evaluate_certificates(
                certificates=certificates,
                model_id=str(payload.get("model_id") or os.getenv("AI_TRUST_MODEL_ID", "lambda-laplace-model")),
                event_index=int(payload.get("event_index", 1)),
                metadata=metadata,
            )
        else:
            raise ValueError("missing_lambda_p_series_or_certificates")
        result = asdict(cert)
        result["service_version"] = SERVICE_VERSION
        if bool(payload.get("commit_to_ecl", False)):
            ecl_commit = ECLCommitAdapter(payload.get("ledger_path") or None).commit_certificate(
                result,
                source_type="AI_LAMBDA_LAPLACE_CERTIFICATE",
            )
            result["ecl_finality_commit"] = ecl_commit.to_dict()
        return result

    def _handle_monti(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        config = MontiOperatorConfig(
            dt=float(payload.get("dt", 1.0)),
            alpha=float(payload.get("alpha", 0.10)),
            beta=float(payload.get("beta", 0.10)),
            threshold=float(payload.get("threshold", 0.75)),
            topology_jump_threshold=int(payload.get("topology_jump_threshold", 1)),
        )
        operator = MontiOperator(config)
        skew = payload.get("skew_intensity_series")
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        if "lambda_p_series" in payload:
            cert = operator.evaluate_series(
                lambda_p_series=payload["lambda_p_series"],
                lambda_v_series=payload.get("lambda_v_series"),
                skew_intensity_series=skew,
                model_id=str(payload.get("model_id") or os.getenv("AI_TRUST_MODEL_ID", "monti-model")),
                event_index=int(payload.get("event_index", 1)),
                metadata=metadata,
            )
        elif "certificates" in payload:
            certificates = payload.get("certificates")
            if not isinstance(certificates, list) or not all(isinstance(item, dict) for item in certificates):
                raise ValueError("certificates_must_be_array_of_objects")
            cert = operator.evaluate_certificates(
                certificates=certificates,
                skew_intensity_series=skew,
                model_id=str(payload.get("model_id") or os.getenv("AI_TRUST_MODEL_ID", "monti-model")),
                event_index=int(payload.get("event_index", 1)),
                metadata=metadata,
            )
        else:
            raise ValueError("missing_lambda_p_series_or_certificates")

        result = asdict(cert)
        result["service_version"] = SERVICE_VERSION
        if bool(payload.get("commit_to_ecl", False)):
            ecl_commit = ECLCommitAdapter(payload.get("ledger_path") or None).commit_certificate(
                result,
                source_type="AI_TOPOLOGICAL_MEMORY_CERTIFICATE",
            )
            result["ecl_finality_commit"] = ecl_commit.to_dict()
        return result

    def _handle_future_arrow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        config = FutureArrowConfig(
            delta_t=float(payload.get("delta_t", 1.0)),
            entropy_weight=float(payload.get("entropy_weight", 0.45)),
            layer_weight=float(payload.get("layer_weight", 0.25)),
            anchor_weight=float(payload.get("anchor_weight", 0.20)),
            monti_weight=float(payload.get("monti_weight", 0.55)),
            nsl_strength=float(payload.get("nsl_strength", payload.get("nsl", 0.0))),
            jump_threshold=float(payload.get("jump_threshold", 0.62)),
            stress_threshold=float(payload.get("stress_threshold", 0.38)),
        )
        operator = FutureArrowOperator(config)
        state = payload.get("state") if isinstance(payload.get("state"), dict) else {}
        recognition_certificate = payload.get("recognition_certificate") if isinstance(payload.get("recognition_certificate"), dict) else None
        monti_certificate = payload.get("monti_certificate") if isinstance(payload.get("monti_certificate"), dict) else None
        anchor_constraints = payload.get("anchor_constraints")
        if anchor_constraints is not None and not isinstance(anchor_constraints, list):
            raise ValueError("anchor_constraints_must_be_array")
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        cert = operator.project(
            state=state,
            recognition_certificate=recognition_certificate,
            monti_certificate=monti_certificate,
            entropy_potential=payload.get("entropy_potential"),
            statistical_layer=payload.get("statistical_layer"),
            anchor_constraints=anchor_constraints,
            model_id=str(payload.get("model_id") or os.getenv("AI_TRUST_MODEL_ID", "future-arrow-model")),
            event_index=int(payload.get("event_index", 1)),
            metadata=metadata,
        )
        result = asdict(cert)
        result["service_version"] = SERVICE_VERSION
        if bool(payload.get("commit_to_ecl", False)):
            ecl_commit = ECLCommitAdapter(payload.get("ledger_path") or None).commit_certificate(
                result,
                source_type="AI_FUTURE_ARROW_CERTIFICATE",
            )
            result["ecl_finality_commit"] = ecl_commit.to_dict()
        return result

    def _release_action_from_resolution(self, resolution: Dict[str, Any]) -> str:
        if int(resolution.get("unresolved_count", 0) or 0) > 0:
            return "HOLD_FOR_RETRIEVAL"
        if int(resolution.get("resolved_contradicted_count", 0) or 0) > 0:
            return "DO_NOT_RELEASE"
        if int(resolution.get("resolved_supported_count", 0) or 0) > 0:
            return "RELEASE_REPAIRED"
        return "NO_RETRIEVAL_NEEDED"

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
    print(json.dumps({"service": SERVICE_NAME, "version": SERVICE_VERSION, "host": host, "port": port}, sort_keys=True))
    server.serve_forever()


if __name__ == "__main__":
    run()
