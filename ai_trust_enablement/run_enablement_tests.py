#!/usr/bin/env python3
"""
Minimal no-dependency enablement tests.

These are intentionally plain Python assertions so a reviewer can run them with:
    python ai_trust_enablement/run_enablement_tests.py

No pytest, no external packages, no ceremonial dependency bonfire.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict
from pathlib import Path

try:  # package execution
    from .ai_hallucination_recognition_engine import build_signature, demo, entropy_capacity_from_logits, sha256_json
    from .batch_evaluator import evaluate_cases
    from .ecl_commit_adapter import ECLCommitAdapter
    from .future_arrow_operator import FutureArrowConfig, FutureArrowOperator
    from .lambda_laplace_operator import LambdaLaplaceConfig, LambdaLaplaceOperator
    from .monti_operator import MontiOperator, MontiOperatorConfig
except ImportError:  # direct script execution
    from ai_hallucination_recognition_engine import build_signature, demo, entropy_capacity_from_logits, sha256_json
    from batch_evaluator import evaluate_cases
    from ecl_commit_adapter import ECLCommitAdapter
    from future_arrow_operator import FutureArrowConfig, FutureArrowOperator
    from lambda_laplace_operator import LambdaLaplaceConfig, LambdaLaplaceOperator
    from monti_operator import MontiOperator, MontiOperatorConfig


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


def test_ecl_finality_commit_adapter() -> None:
    result = demo()
    certificate = result["hallucinated_certificate"]
    with tempfile.TemporaryDirectory() as tmp:
        ledger_path = Path(tmp) / "ai_ecl_ledger.jsonl"
        adapter = ECLCommitAdapter(ledger_path)
        first = adapter.commit_certificate(certificate, source_type="AI_RECOGNITION_CERTIFICATE").to_dict()
        second = adapter.commit_certificate(result["grounded_certificate"], source_type="AI_RECOGNITION_CERTIFICATE").to_dict()
        status = adapter.status()
        verify = adapter.verify()

    assert len(first["certificate_hash"]) == 64
    assert len(first["proposal_hash"]) == 64
    assert len(first["commit_hash"]) == 64
    assert first["entropy_delta"] > 0
    assert first["prev_state_hash"] == "0" * 64
    assert second["prev_state_hash"] == first["commit_hash"]
    assert status["commit_count"] == 2
    assert status["last_commit_hash"] == second["commit_hash"]
    assert verify["ok"] is True
    assert verify["checked"] == 2


def test_monti_operator_detects_winding_transition() -> None:
    operator = MontiOperator(MontiOperatorConfig(threshold=0.45, alpha=0.25, beta=0.20))
    cert = asdict(operator.evaluate_series(
        lambda_p_series=[0.00, 0.15, 0.32, 0.50, 0.74, 1.02, 1.18],
        skew_intensity_series=[0.0, 0.1, 0.1, 0.2, 0.4, 0.5, 0.5],
        model_id="test-monti",
    ))
    assert cert["certificate_type"] == "AI_TOPOLOGICAL_MEMORY_CERTIFICATE"
    assert cert["engine"] == "MontiOperatorSpectralWinding"
    assert cert["transition"]["classification"] == "TOPOLOGICAL_MEMORY_TRANSITION"
    assert cert["transition"]["transition_detected"] is True
    assert cert["transition"]["primary_trigger"] == "spectral_winding_jump"
    assert cert["transition"]["delta_nu"] >= 1
    assert cert["spectral_state"]["spectral_flow"] == cert["transition"]["delta_nu"]
    assert cert["technical_action"]["action"] == "HOLD_AND_COMMIT_TOPOLOGICAL_JUMP"
    assert len(cert["certificate_hash"]) == 64


def test_monti_operator_curvature_stress_without_sector_jump() -> None:
    operator = MontiOperator(MontiOperatorConfig(threshold=0.01, alpha=0.0, beta=0.0))
    cert = asdict(operator.evaluate_series(
        lambda_p_series=[0.00, 0.03, 0.20, 0.24, 0.26],
        model_id="test-monti-stress",
    ))
    assert cert["transition"]["classification"] == "CURVATURE_STRESS_WITHOUT_SECTOR_JUMP"
    assert cert["transition"]["transition_detected"] is False
    assert cert["transition"]["delta_nu"] == 0
    assert cert["monti_state"]["curvature_stress"] is True
    assert cert["technical_action"]["action"] == "FLAG_CURVATURE_STRESS"


def test_monti_operator_stable_sector() -> None:
    operator = MontiOperator(MontiOperatorConfig(threshold=10.0))
    cert = asdict(operator.evaluate_series(lambda_p_series=[0.00, 0.02, 0.03, 0.04, 0.05], model_id="test-monti-stable"))
    assert cert["transition"]["classification"] == "STABLE_TOPOLOGICAL_SECTOR"
    assert cert["transition"]["transition_detected"] is False
    assert cert["transition"]["delta_nu"] == 0
    assert cert["technical_action"]["action"] == "CONTINUE_MONITORING"


def test_ecl_adapter_reads_monti_transition_classification() -> None:
    operator = MontiOperator(MontiOperatorConfig(threshold=0.45, alpha=0.25, beta=0.20))
    cert = asdict(operator.evaluate_series(
        lambda_p_series=[0.00, 0.15, 0.32, 0.50, 0.74, 1.02, 1.18],
        skew_intensity_series=[0.0, 0.1, 0.1, 0.2, 0.4, 0.5, 0.5],
        model_id="test-monti-ecl",
    ))
    # Simulate a mixed certificate where a recognition-like block exists but the
    # topological transition block should dominate the ECL finality label.
    cert["recognition_state"] = {"classification": "UNKNOWN"}
    with tempfile.TemporaryDirectory() as tmp:
        commit = ECLCommitAdapter(Path(tmp) / "monti_ecl.jsonl").commit_certificate(
            cert,
            source_type="AI_TOPOLOGICAL_MEMORY_CERTIFICATE",
        ).to_dict()

    assert commit["classification"] == "TOPOLOGICAL_MEMORY_TRANSITION"
    assert commit["action"] == "HOLD_AND_COMMIT_TOPOLOGICAL_JUMP"
    assert commit["source_type"] == "AI_TOPOLOGICAL_MEMORY_CERTIFICATE"


def test_future_arrow_projects_probability_cone() -> None:
    monti = asdict(MontiOperator(MontiOperatorConfig(threshold=0.45, alpha=0.25, beta=0.20)).evaluate_series(
        lambda_p_series=[0.00, 0.15, 0.32, 0.50, 0.74, 1.02, 1.18],
        skew_intensity_series=[0.0, 0.1, 0.1, 0.2, 0.4, 0.5, 0.5],
        model_id="test-future-monti",
    ))
    recognition = {
        "recognition_state": {
            "classification": "ACTIONABLE_RESIDUE",
            "open_residue": 0.42,
            "phase_value": 1.18,
            "scale_value": 0.22,
        },
        "seam_memory": {"k": 2},
    }
    future = asdict(FutureArrowOperator(FutureArrowConfig(delta_t=2.0, nsl_strength=0.25)).project(
        recognition_certificate=recognition,
        monti_certificate=monti,
        entropy_potential=0.45,
        statistical_layer=0.60,
        anchor_constraints=["prime_anchor:recognition"],
        model_id="test-future-arrow",
    ))

    assert future["certificate_type"] == "AI_FUTURE_ARROW_CERTIFICATE"
    assert future["engine"] == "FutureArrowOperator"
    assert len(future["certificate_hash"]) == 64
    assert 0.0 <= future["future_cone"]["probability_of_sector_jump"] <= 1.0
    assert abs(sum(future["future_cone"]["distribution"].values()) - 1.0) < 1e-9
    assert future["forecast"]["classification"] in future["future_cone"]["distribution"]


def test_future_arrow_ecl_commit() -> None:
    future = asdict(FutureArrowOperator(FutureArrowConfig(delta_t=1.5, nsl_strength=0.20)).project(
        entropy_potential=0.50,
        statistical_layer=0.55,
        anchor_constraints=["prime_anchor:a", "prime_anchor:b"],
        model_id="test-future-ecl",
    ))
    with tempfile.TemporaryDirectory() as tmp:
        commit = ECLCommitAdapter(Path(tmp) / "future_ecl.jsonl").commit_certificate(
            future,
            source_type="AI_FUTURE_ARROW_CERTIFICATE",
        ).to_dict()

    assert commit["source_type"] == "AI_FUTURE_ARROW_CERTIFICATE"
    assert commit["classification"] == future["forecast"]["classification"]
    assert len(commit["certificate_hash"]) == 64
    assert commit["action"] in {"CONTINUE_MONITORING", "WATCH_CURVATURE_STRESS_CONE", "PREPARE_TO_HOLD_AND_RECHECK_MONTI", "CONTINUE_WITH_ANCHOR_CONSTRAINTS"}
    assert commit["entropy_delta"] > 0


def test_lambda_laplace_detects_seam_signature() -> None:
    cert = asdict(LambdaLaplaceOperator(LambdaLaplaceConfig(seam_threshold=0.10, stress_threshold=0.60)).evaluate_series(
        lambda_p_series=[0.00, 0.10, 0.22, 0.37, 0.54, 0.73, 0.95],
        lambda_v_series=[0.00, 0.05, 0.09, 0.12, 0.18, 0.22, 0.30],
        skew_intensity_series=[0.0, 0.2, 0.2, 0.4, 0.6, 0.8, 0.9],
        entropy_potential_series=[0.01, 0.04, 0.08, 0.13, 0.20, 0.27, 0.35],
        model_id="test-lambda-laplace",
    ))
    assert cert["certificate_type"] == "AI_LAMBDA_LAPLACE_CERTIFICATE"
    assert cert["engine"] == "LambdaLaplaceOperator"
    assert cert["analysis"]["classification"] == "LAMBDA_SEAM_SIGNATURE"
    assert cert["analysis"]["feeds_monti"] is True
    assert cert["technical_action"]["action"] == "FEED_SEAM_SIGNAL_TO_MONTI"
    assert len(cert["certificate_hash"]) == 64


def test_lambda_laplace_ecl_commit() -> None:
    cert = asdict(LambdaLaplaceOperator(LambdaLaplaceConfig(seam_threshold=0.10, stress_threshold=0.60)).evaluate_series(
        lambda_p_series=[0.00, 0.10, 0.22, 0.37, 0.54, 0.73, 0.95],
        lambda_v_series=[0.00, 0.05, 0.09, 0.12, 0.18, 0.22, 0.30],
        skew_intensity_series=[0.0, 0.2, 0.2, 0.4, 0.6, 0.8, 0.9],
        entropy_potential_series=[0.01, 0.04, 0.08, 0.13, 0.20, 0.27, 0.35],
        model_id="test-lambda-laplace-ecl",
    ))
    with tempfile.TemporaryDirectory() as tmp:
        commit = ECLCommitAdapter(Path(tmp) / "lambda_laplace_ecl.jsonl").commit_certificate(
            cert,
            source_type="AI_LAMBDA_LAPLACE_CERTIFICATE",
        ).to_dict()

    assert commit["source_type"] == "AI_LAMBDA_LAPLACE_CERTIFICATE"
    assert commit["classification"] == cert["analysis"]["classification"]
    assert commit["action"] == cert["technical_action"]["action"]
    assert commit["entropy_delta"] > 0


def main() -> None:
    tests = [
        test_signature_has_concrete_fields,
        test_grounded_vs_hallucinated_demo,
        test_entropy_capacity_collapse_path,
        test_batch_cases,
        test_ecl_finality_commit_adapter,
        test_monti_operator_detects_winding_transition,
        test_monti_operator_curvature_stress_without_sector_jump,
        test_monti_operator_stable_sector,
        test_ecl_adapter_reads_monti_transition_classification,
        test_future_arrow_projects_probability_cone,
        test_future_arrow_ecl_commit,
        test_lambda_laplace_detects_seam_signature,
        test_lambda_laplace_ecl_commit,
    ]
    passed = []
    for test in tests:
        test()
        passed.append(test.__name__)
    report = {"passed": passed, "count": len(passed)}
    print(json.dumps({"ok": True, "report": report, "report_hash": sha256_json(report)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
