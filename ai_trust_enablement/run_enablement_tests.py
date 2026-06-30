#!/usr/bin/env python3
"""
Minimal no-dependency enablement tests.

These are intentionally plain Python assertions so a reviewer can run them with:
    python ai_trust_enablement/run_enablement_tests.py

No pytest, no external packages, no ceremonial dependency bonfire.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from ai_hallucination_recognition_engine import (
    AIHallucinationRecognitionEngine,
    build_signature,
    demo,
    entropy_capacity_from_logits,
    sha256_json,
)
from batch_evaluator import evaluate_cases


def test_signature_has_concrete_fields() -> None:
    sig = build_signature("The Eiffel Tower was completed in 1889 in Paris.")
    assert sig.token_count > 0
    assert sig.content_token_count > 0
    assert "1889" in sig.numbers
    assert "Eiffel" in sig.entities
    assert len(sig.signature_hash) == 64
    assert len(sig.phase_hash) == 64


def test_grounded_vs_hallucinated_demo() -> None:
    result = demo()
    grounded = result["grounded_certificate"]
    hallucinated = result["hallucinated_certificate"]
    assert grounded["recognition_state"]["classification"] == "RECOGNITION"
    assert grounded["technical_action"]["action"] == "COMMIT_OUTPUT"
    assert hallucinated["recognition_state"]["classification"] == "ACTIONABLE_RESIDUE"
    assert hallucinated["technical_action"]["action"] == "DEFER_AND_REGENERATE_WITH_RETRIEVAL"
    assert hallucinated["recognition_state"]["open_residue"] > grounded["recognition_state"]["open_residue"]
    assert hallucinated["seam_memory"]["k"] > grounded["seam_memory"]["k"]


def test_entropy_capacity_collapse_path() -> None:
    metrics = entropy_capacity_from_logits([100.0, -100.0, -100.0])
    assert metrics.entropy >= 0.0
    assert isinstance(metrics.confidence_collapse, bool)


def test_batch_cases() -> None:
    root = Path(__file__).resolve().parent
    summary = evaluate_cases(
        input_path=root / "sample_cases.jsonl",
        output_path=root / "_test_batch_certificates.jsonl",
        model_id="test-model",
    )
    assert summary["case_count"] >= 3
    assert summary["checked_count"] >= 3
    # The bounded paraphrase row is allowed to be implementation-sensitive; the
    # hard safety cases must pass.
    hard_cases = {row["case_id"]: row for row in summary["rows"] if row["case_id"] in {"grounded_eiffel", "hallucinated_eiffel", "dosage_error"}}
    assert hard_cases["grounded_eiffel"]["classification"] == "RECOGNITION"
    assert hard_cases["hallucinated_eiffel"]["classification"] == "ACTIONABLE_RESIDUE"
    assert hard_cases["dosage_error"]["classification"] == "ACTIONABLE_RESIDUE"


def main() -> None:
    tests = [
        test_signature_has_concrete_fields,
        test_grounded_vs_hallucinated_demo,
        test_entropy_capacity_collapse_path,
        test_batch_cases,
    ]
    passed = []
    for test in tests:
        test()
        passed.append(test.__name__)
    report = {"passed": passed, "count": len(passed)}
    print(json.dumps({"ok": True, "report": report, "report_hash": sha256_json(report)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
