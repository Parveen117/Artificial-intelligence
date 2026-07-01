#!/usr/bin/env python3
"""
Monti Operator temporal memory diagnostics for AI Trust Enablement.

The layer evaluates a phase trajectory lambda_p(t), estimates winding-number
sector movement, computes a discrete Monti memory signal, and emits a
machine-readable topological memory certificate.

It is intentionally no-dependency and conservative: the module does not assert
that every phase jump is physical truth. It provides a deterministic diagnostic
record that can be reviewed, gated, or sealed through the ECL finality bridge.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

TWO_PI = 2.0 * math.pi


@dataclass(frozen=True)
class MontiOperatorConfig:
    dt: float = 1.0
    alpha: float = 0.10
    beta: float = 0.10
    threshold: float = 0.75
    topology_jump_threshold: int = 1


@dataclass(frozen=True)
class MontiMemoryCertificate:
    version: str
    certificate_type: str
    engine: str
    model_id: str
    event: Dict[str, Any]
    input_state: Dict[str, Any]
    winding_state: Dict[str, Any]
    monti_state: Dict[str, Any]
    transition: Dict[str, Any]
    technical_action: Dict[str, Any]
    certificate_hash: str


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def sha256_json(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


def _as_float_series(values: Sequence[Any], name: str) -> List[float]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ValueError(f"{name}_must_be_number_array")
    out: List[float] = []
    for index, value in enumerate(values):
        if not isinstance(value, (int, float)):
            raise ValueError(f"{name}_{index}_must_be_number")
        out.append(float(value))
    if len(out) < 3:
        raise ValueError(f"{name}_must_have_at_least_3_samples")
    return out


def unwrap_phase(phases: Sequence[float]) -> List[float]:
    """Unwrap angular samples so phase movement is continuous."""
    if not phases:
        return []
    unwrapped = [float(phases[0])]
    offset = 0.0
    previous = float(phases[0])
    for raw in phases[1:]:
        current = float(raw)
        delta = current - previous
        if delta > math.pi:
            offset -= TWO_PI
        elif delta < -math.pi:
            offset += TWO_PI
        unwrapped.append(current + offset)
        previous = current
    return unwrapped


def winding_from_lambda(lambda_p_series: Sequence[float]) -> Dict[str, Any]:
    lambda_values = _as_float_series(lambda_p_series, "lambda_p_series")
    wrapped_phases = [TWO_PI * value for value in lambda_values]
    unwrapped_phases = unwrap_phase(wrapped_phases)
    start = unwrapped_phases[0]
    winding_path = [(phase - start) / TWO_PI for phase in unwrapped_phases]
    winding_raw = winding_path[-1]
    winding_number = int(round(winding_raw))
    sector_series = [int(round(value)) for value in winding_path]
    delta_nu = sector_series[-1] - sector_series[0]
    return {
        "winding_raw": winding_raw,
        "winding_number": winding_number,
        "delta_nu": delta_nu,
        "sector_series": sector_series,
        "winding_path": winding_path,
        "unwrapped_phase_series": unwrapped_phases,
    }


def second_derivative(values: Sequence[float], dt: float) -> List[float]:
    dt2 = max(float(dt), 1e-9) ** 2
    out = [0.0] * len(values)
    for index in range(1, len(values) - 1):
        out[index] = (float(values[index + 1]) - 2.0 * float(values[index]) + float(values[index - 1])) / dt2
    return out


def first_derivative(values: Sequence[float], dt: float) -> List[float]:
    safe_dt = max(float(dt), 1e-9)
    out = [0.0] * len(values)
    for index in range(1, len(values)):
        out[index] = (float(values[index]) - float(values[index - 1])) / safe_dt
    return out


def phase_series_from_certificates(certificates: Sequence[Dict[str, Any]]) -> List[float]:
    """Extract lambda_p samples from AI trust certificates.

    Priority order:
      1. recognition_state.phase_value
      2. recognition_state.open_residue
      3. fusion_decision.open_residue / score-like fallback
    """
    if not isinstance(certificates, Sequence) or isinstance(certificates, (str, bytes)):
        raise ValueError("certificates_must_be_array")
    samples: List[float] = []
    for index, certificate in enumerate(certificates):
        if not isinstance(certificate, dict):
            raise ValueError(f"certificate_{index}_must_be_object")
        recognition = certificate.get("recognition_state", {}) if isinstance(certificate.get("recognition_state", {}), dict) else {}
        fusion = certificate.get("fusion_decision", {}) if isinstance(certificate.get("fusion_decision", {}), dict) else {}
        value = recognition.get("phase_value")
        if not isinstance(value, (int, float)):
            value = recognition.get("open_residue")
        if not isinstance(value, (int, float)):
            value = fusion.get("open_residue") or fusion.get("score")
        if not isinstance(value, (int, float)):
            raise ValueError(f"certificate_{index}_has_no_phase_like_value")
        samples.append(float(value))
    return _as_float_series(samples, "lambda_p_series")


class MontiOperator:
    """Compute winding-sector and Monti memory diagnostics from lambda_p(t)."""

    def __init__(self, config: Optional[MontiOperatorConfig] = None) -> None:
        self.config = config or MontiOperatorConfig()

    def evaluate_series(
        self,
        lambda_p_series: Sequence[Any],
        skew_intensity_series: Optional[Sequence[Any]] = None,
        model_id: str = "monti-operator",
        event_index: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MontiMemoryCertificate:
        cfg = self.config
        lambda_values = _as_float_series(lambda_p_series, "lambda_p_series")
        if skew_intensity_series is None:
            skew_values = [0.0] * len(lambda_values)
        else:
            skew_values = _as_float_series(skew_intensity_series, "skew_intensity_series")
            if len(skew_values) != len(lambda_values):
                raise ValueError("skew_intensity_series_must_match_lambda_p_series_length")

        winding = winding_from_lambda(lambda_values)
        lambda_ddot = second_derivative(lambda_values, cfg.dt)
        nu_dot = first_derivative(winding["winding_path"], cfg.dt)

        monti_values: List[float] = []
        for index, curvature in enumerate(lambda_ddot):
            skew_term = cfg.alpha * (float(skew_values[index]) ** 2)
            memory_term = cfg.beta * abs(float(nu_dot[index]))
            monti_values.append(float(curvature) + skew_term + memory_term)

        max_monti = max(abs(value) for value in monti_values)
        threshold_crossed = max_monti > cfg.threshold
        sector_jump = abs(int(winding["delta_nu"])) >= int(cfg.topology_jump_threshold)
        transition_detected = bool(threshold_crossed or sector_jump)
        action = "HOLD_AND_COMMIT_MEMORY_TRANSITION" if transition_detected else "CONTINUE_MONITORING"
        classification = "TOPOLOGICAL_MEMORY_TRANSITION" if transition_detected else "STABLE_TOPOLOGICAL_SECTOR"

        payload = {
            "version": "1.0.0",
            "certificate_type": "AI_TOPOLOGICAL_MEMORY_CERTIFICATE",
            "engine": "MontiOperator",
            "model_id": model_id,
            "event": {
                "event_index": int(event_index),
                "timestamp_unix": int(time.time()),
                "metadata": metadata or {},
            },
            "input_state": {
                "lambda_p_series": lambda_values,
                "skew_intensity_series": skew_values,
                "sample_count": len(lambda_values),
                "dt": cfg.dt,
                "alpha": cfg.alpha,
                "beta": cfg.beta,
                "threshold": cfg.threshold,
            },
            "winding_state": winding,
            "monti_state": {
                "lambda_ddot_series": lambda_ddot,
                "nu_dot_series": nu_dot,
                "monti_series": monti_values,
                "max_abs_monti": max_monti,
                "threshold_crossed": threshold_crossed,
            },
            "transition": {
                "classification": classification,
                "transition_detected": transition_detected,
                "sector_jump": sector_jump,
                "delta_nu": winding["delta_nu"],
            },
            "technical_action": {
                "action": action,
                "reason": "monti_threshold_or_winding_jump" if transition_detected else "subcritical_stable_sector",
            },
        }
        return MontiMemoryCertificate(certificate_hash=sha256_json(payload), **payload)

    def evaluate_certificates(
        self,
        certificates: Sequence[Dict[str, Any]],
        skew_intensity_series: Optional[Sequence[Any]] = None,
        model_id: str = "monti-operator",
        event_index: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MontiMemoryCertificate:
        return self.evaluate_series(
            lambda_p_series=phase_series_from_certificates(certificates),
            skew_intensity_series=skew_intensity_series,
            model_id=model_id,
            event_index=event_index,
            metadata=metadata,
        )


def demo() -> Dict[str, Any]:
    # This trajectory makes one full turn in lambda-space and includes a small
    # seam acceleration near the sector crossing.
    lambda_p = [0.00, 0.15, 0.32, 0.50, 0.74, 1.02, 1.18]
    skew = [0.0, 0.1, 0.1, 0.2, 0.4, 0.5, 0.5]
    cert = MontiOperator(MontiOperatorConfig(threshold=0.45, alpha=0.25, beta=0.20)).evaluate_series(
        lambda_p,
        skew_intensity_series=skew,
        model_id="monti-demo",
        metadata={"demo": "one winding sector transition"},
    )
    return asdict(cert)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute a Monti topological memory certificate")
    parser.add_argument("--lambda-p", nargs="+", type=float, default=None, help="lambda_p samples")
    parser.add_argument("--skew", nargs="+", type=float, default=None, help="optional skew intensity samples")
    parser.add_argument("--dt", type=float, default=1.0)
    parser.add_argument("--alpha", type=float, default=0.10)
    parser.add_argument("--beta", type=float, default=0.10)
    parser.add_argument("--threshold", type=float, default=0.75)
    parser.add_argument("--model-id", default="monti-cli")
    parser.add_argument("--out", default="monti_memory_certificate.json")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    if args.demo or args.lambda_p is None:
        result = demo()
    else:
        result = asdict(MontiOperator(MontiOperatorConfig(
            dt=args.dt,
            alpha=args.alpha,
            beta=args.beta,
            threshold=args.threshold,
        )).evaluate_series(args.lambda_p, skew_intensity_series=args.skew, model_id=args.model_id))

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
    print(json.dumps({
        "ok": True,
        "out": args.out,
        "classification": result["transition"]["classification"],
        "action": result["technical_action"]["action"],
        "certificate_hash": result["certificate_hash"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
