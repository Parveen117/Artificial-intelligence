from __future__ import annotations

from typing import Dict, Tuple

SERVICE_NAME = "ai-trust-enable"
SERVICE_VERSION = "1.2.0"
SCHEMA_ID = "AI_RECOGNITION_CERTIFICATE/v1"
ENGINE_NAME = "AIHallucinationRecognitionEngine+ReleaseController+RetrievalResolutionEngine"

HEALTH_ENDPOINT = "GET /healthz"
VERSION_ENDPOINT = "GET /version"
SCHEMA_ENDPOINT = "GET /schema"
EVALUATE_ENDPOINT = "POST /v1/evaluate"
BATCH_ENDPOINT = "POST /v1/batch"
RELEASE_ENDPOINT = "POST /v1/release"
RESOLVE_ENDPOINT = "POST /v1/resolve"

ENDPOINTS: Tuple[str, ...] = (
    HEALTH_ENDPOINT,
    VERSION_ENDPOINT,
    SCHEMA_ENDPOINT,
    EVALUATE_ENDPOINT,
    BATCH_ENDPOINT,
    RELEASE_ENDPOINT,
    RESOLVE_ENDPOINT,
)


def version_payload() -> Dict[str, object]:
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "engine": ENGINE_NAME,
        "schema": SCHEMA_ID,
        "endpoints": list(ENDPOINTS),
    }


def health_payload() -> Dict[str, object]:
    return {"ok": True, "service": SERVICE_NAME, "version": SERVICE_VERSION}
