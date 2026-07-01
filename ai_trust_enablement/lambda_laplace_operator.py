#!/usr/bin/env python3
"""
Lambda-Laplace analytic operator for AI Trust Enablement.

This layer is the analytic hinge before Monti: it studies lambda trajectories as
entropy-weighted diffusion with skew / nonreciprocal perturbation and entropic
drift. It does not declare a topological jump. That remains Monti's job.

Operational role:
  raw lambda trajectory
    -> Lambda-Laplace diffusion / seam diagnostics
    -> cleaner spectral-seam signal
    -> Monti winding-sector detection
    -> Future Arrow forecasting
    -> optional ECL finality
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence


@dataclass(frozen=True)
class LambdaLaplaceConfig:
    dt: float = 1.0
    alpha: float = 0.15
    beta: float = 0.10
    seam_threshold: float = 0.18
    stress_threshold: float = 0.45
    gap_threshold: float = 0.08
    heat_time: float = 1.0


@dataclass(frozen=True)
class LambdaLaplaceCertificate:
    version: str
    certificate_type: str
    engine: str
    model_id: str
    event: Dict[str, Any]
    input_state: Dict[str, Any]
    lambda_geometry: Dict[str, Any]
    operator_state: Dict[str, Any]
    spectral_state: Dict[str, Any]
    heat_state: Dict[str, Any]
    graph_state: Dict[str, Any]
    analysis: Dict[str, Any]
    technical_action: Dict[str, Any]
    certificate_hash: str


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def sha256_json(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


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


def first_derivative(values: Sequence[float], dt: float) -> List[float]:
    safe_dt = max(float(dt), 1e-9)
    out = [0.0] * len(values)
    for index in range(1, len(values)):
        out[index] = (float(values[index]) - float(values[index - 1])) / safe_dt
    return out


def second_derivative(values: Sequence[float], dt: float) -> List[float]:
    dt2 = max(float(dt), 1e-9) ** 2
    out = [0.0] * len(values)
    for index in range(1, len(values) - 1):
        out[index] = (float(values[index + 1]) - 2.0 * float(values[index]) + float(values[index - 1])) / dt2
    return out


def mean_abs(values: Sequence[float]) -> float:
    return sum(abs(float(value)) for value in values) / max(1, len(values))


def max_abs(values: Sequence[float]) -> float:
    return max(abs(float(value)) for value in values) if values else 0.0


def variance(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)


def heat_trace_proxy(eigenvalues: Sequence[float], heat_time: float) -> float:
    t = max(float(heat_time), 1e-9)
    return sum(math.exp(-t * abs(float(value))) for value in eigenvalues)


def lambda_series_from_certificates(certificates: Sequence[Dict[str, Any]]) -> Dict[str, List[float]]:
    if not isinstance(certificates, Sequence) or isinstance(certificates, (str, bytes)):
        raise ValueError("certificates_must_be_array")
    lambda_p: List[float] = []
    lambda_v: List[float] = []
    skew: List[float] = []
    entropy: List[float] = []
    for index, certificate in enumerate(certificates):
        if not isinstance(certificate, dict):
            raise ValueError(f"certificate_{index}_must_be_object")
        recognition = certificate.get("recognition_state", {}) if isinstance(certificate.get("recognition_state", {}), dict) else {}
        seam = certificate.get("seam_memory", {}) if isinstance(certificate.get("seam_memory", {}), dict) else {}
        phase = recognition.get("phase_value")
        if not isinstance(phase, (int, float)):
            phase = recognition.get("open_residue")
        if not isinstance(phase, (int, float)):
            raise ValueError(f"certificate_{index}_has_no_phase_like_value")
        scale = recognition.get("scale_value") if isinstance(recognition.get("scale_value"), (int, float)) else recognition.get("open_residue", 0.0)
        lambda_p.append(float(phase))
        lambda_v.append(float(scale))
        skew.append(float(seam.get("k", 0.0)) if isinstance(seam.get("k", 0.0), (int, float)) else 0.0)
        entropy.append(float(recognition.get("open_residue", phase)) if isinstance(recognition.get("open_residue", phase), (int, float)) else float(phase))
    return {
        "lambda_p_series": _as_float_series(lambda_p, "lambda_p_series"),
        "lambda_v_series": _as_float_series(lambda_v, "lambda_v_series"),
        "skew_intensity_series": _as_float_series(skew, "skew_intensity_series"),
        "entropy_potential_series": _as_float_series(entropy, "entropy_potential_series"),
    }


class LambdaLaplaceOperator:
    """Compute lambda diffusion, seam, heat-trace, and spectral-gap diagnostics."""

    def __init__(self, config: Optional[LambdaLaplaceConfig] = None) -> None:
        self.config = config or LambdaLaplaceConfig()

    def evaluate_series(
        self,
        lambda_p_series: Sequence[Any],
        lambda_v_series: Optional[Sequence[Any]] = None,
        skew_intensity_series: Optional[Sequence[Any]] = None,
        entropy_potential_series: Optional[Sequence[Any]] = None,
        model_id: str = "lambda-laplace",
        event_index: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LambdaLaplaceCertificate:
        cfg = self.config
        lambda_p = _as_float_series(lambda_p_series, "lambda_p_series")
        n = len(lambda_p)
        if lambda_v_series is None:
            lambda_v = [0.0] * n
        else:
            lambda_v = _as_float_series(lambda_v_series, "lambda_v_series")
            if len(lambda_v) != n:
                raise ValueError("lambda_v_series_must_match_lambda_p_series_length")
        if skew_intensity_series is None:
            skew = [0.0] * n
        else:
            skew = _as_float_series(skew_intensity_series, "skew_intensity_series")
            if len(skew) != n:
                raise ValueError("skew_intensity_series_must_match_lambda_p_series_length")
        if entropy_potential_series is None:
            entropy = [abs(p - v) for p, v in zip(lambda_p, lambda_v)]
        else:
            entropy = _as_float_series(entropy_potential_series, "entropy_potential_series")
            if len(entropy) != n:
                raise ValueError("entropy_potential_series_must_match_lambda_p_series_length")

        grad_lambda = first_derivative(lambda_p, cfg.dt)
        laplace_core = second_derivative(lambda_p, cfg.dt)
        entropy_grad = first_derivative(entropy, cfg.dt)
        branch_gap_series = [abs(p - v) for p, v in zip(lambda_p, lambda_v)]
        skew_drift = [cfg.alpha * float(skew[index]) * float(grad_lambda[index]) for index in range(n)]
        entropic_drift = [cfg.beta * float(entropy_grad[index]) * float(grad_lambda[index]) for index in range(n)]
        lambda_laplace_series = [laplace_core[index] + skew_drift[index] + entropic_drift[index] for index in range(n)]

        seam_score = clamp(mean_abs(branch_gap_series) + 0.25 * mean_abs(skew) + 0.10 * max_abs(entropy_grad))
        diffusion_stress = clamp(max_abs(lambda_laplace_series) / (1.0 + max_abs(lambda_laplace_series)))
        spectral_gap_proxy = clamp(1.0 / (1.0 + variance(lambda_laplace_series) + mean_abs(branch_gap_series)))
        half_integer_distance = clamp(abs(round(2.0 * seam_score) / 2.0 - seam_score) * 2.0)
        # Strong only when there is actual seam content and it sits near a half-integer heat-trace band.
        half_integer_trace_strength = clamp(seam_score * (1.0 - half_integer_distance))
        eigen_proxy = [abs(value) + branch_gap_series[index] + 0.05 * abs(skew[index]) for index, value in enumerate(lambda_laplace_series)]
        heat_trace = heat_trace_proxy(eigen_proxy, cfg.heat_time)
        normalized_heat_trace = heat_trace / max(1, n)
        graph_cycle_entropy = clamp(mean_abs(skew) / (1.0 + mean_abs(skew)) + 0.25 * mean_abs(branch_gap_series))

        seam_detected = bool(seam_score >= cfg.seam_threshold or half_integer_trace_strength >= 0.18)
        stress_detected = bool(diffusion_stress >= cfg.stress_threshold)
        gap_weak = bool(spectral_gap_proxy <= cfg.gap_threshold)

        if seam_detected:
            classification = "LAMBDA_SEAM_SIGNATURE"
            action = "FEED_SEAM_SIGNAL_TO_MONTI"
            reason = "lambda_heat_trace_or_branch_gap_seam_signature"
        elif stress_detected:
            classification = "LAMBDA_DIFFUSION_STRESS"
            action = "SMOOTH_AND_RECHECK_LAMBDA_TRAJECTORY"
            reason = "lambda_laplace_diffusion_stress"
        elif gap_weak:
            classification = "LAMBDA_SPECTRAL_GAP_WEAK"
            action = "INCREASE_OBSERVATION_WINDOW"
            reason = "weak_lambda_spectral_gap_proxy"
        else:
            classification = "LAMBDA_SMOOTH_STABLE"
            action = "PASS_TO_MONTI_AS_STABLE_INPUT"
            reason = "stable_lambda_diffusion"

        payload = {
            "version": "1.0.0",
            "certificate_type": "AI_LAMBDA_LAPLACE_CERTIFICATE",
            "engine": "LambdaLaplaceOperator",
            "model_id": model_id,
            "event": {
                "event_index": int(event_index),
                "timestamp_unix": int(time.time()),
                "metadata": metadata or {},
            },
            "input_state": {
                "lambda_p_series": lambda_p,
                "lambda_v_series": lambda_v,
                "skew_intensity_series": skew,
                "entropy_potential_series": entropy,
                "sample_count": n,
                "dt": cfg.dt,
                "alpha": cfg.alpha,
                "beta": cfg.beta,
                "heat_time": cfg.heat_time,
            },
            "lambda_geometry": {
                "interpretation": "elliptic diffusion plus lambda-skew plus entropic drift",
                "branch_gap_series": branch_gap_series,
                "mean_branch_gap": mean_abs(branch_gap_series),
                "seam_score": seam_score,
                "half_integer_trace_strength": half_integer_trace_strength,
            },
            "operator_state": {
                "gradient_series": grad_lambda,
                "laplace_core_series": laplace_core,
                "skew_drift_series": skew_drift,
                "entropic_drift_series": entropic_drift,
                "lambda_laplace_series": lambda_laplace_series,
                "max_abs_lambda_laplace": max_abs(lambda_laplace_series),
                "diffusion_stress": diffusion_stress,
            },
            "spectral_state": {
                "eigen_proxy_series": eigen_proxy,
                "spectral_gap_proxy": spectral_gap_proxy,
                "gap_weak": gap_weak,
            },
            "heat_state": {
                "heat_trace_proxy": heat_trace,
                "normalized_heat_trace": normalized_heat_trace,
                "heat_time": cfg.heat_time,
                "half_integer_signature": half_integer_trace_strength,
            },
            "graph_state": {
                "cycle_entropy_proxy": graph_cycle_entropy,
                "directed_skew_present": bool(mean_abs(skew) > 0.0),
            },
            "analysis": {
                "classification": classification,
                "seam_detected": seam_detected,
                "stress_detected": stress_detected,
                "gap_weak": gap_weak,
                "feeds_monti": True,
            },
            "technical_action": {
                "action": action,
                "reason": reason,
            },
        }
        return LambdaLaplaceCertificate(certificate_hash=sha256_json(payload), **payload)

    def evaluate_certificates(
        self,
        certificates: Sequence[Dict[str, Any]],
        model_id: str = "lambda-laplace",
        event_index: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LambdaLaplaceCertificate:
        series = lambda_series_from_certificates(certificates)
        return self.evaluate_series(
            lambda_p_series=series["lambda_p_series"],
            lambda_v_series=series["lambda_v_series"],
            skew_intensity_series=series["skew_intensity_series"],
            entropy_potential_series=series["entropy_potential_series"],
            model_id=model_id,
            event_index=event_index,
            metadata={**(metadata or {}), "source": "recognition_certificate_series"},
        )


def demo() -> Dict[str, Any]:
    cert = LambdaLaplaceOperator(LambdaLaplaceConfig(seam_threshold=0.10, stress_threshold=0.60)).evaluate_series(
        lambda_p_series=[0.00, 0.10, 0.22, 0.37, 0.54, 0.73, 0.95],
        lambda_v_series=[0.00, 0.05, 0.09, 0.12, 0.18, 0.22, 0.30],
        skew_intensity_series=[0.0, 0.2, 0.2, 0.4, 0.6, 0.8, 0.9],
        entropy_potential_series=[0.01, 0.04, 0.08, 0.13, 0.20, 0.27, 0.35],
        model_id="lambda-laplace-demo",
        metadata={"demo": "lambda seam signature before Monti"},
    )
    return asdict(cert)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute a Lambda-Laplace analytic certificate")
    parser.add_argument("--lambda-p", nargs="+", type=float, default=None, help="lambda_p samples")
    parser.add_argument("--lambda-v", nargs="+", type=float, default=None, help="optional lambda_v samples")
    parser.add_argument("--skew", nargs="+", type=float, default=None, help="optional skew intensity samples")
    parser.add_argument("--entropy", nargs="+", type=float, default=None, help="optional entropy potential samples")
    parser.add_argument("--dt", type=float, default=1.0)
    parser.add_argument("--alpha", type=float, default=0.15)
    parser.add_argument("--beta", type=float, default=0.10)
    parser.add_argument("--seam-threshold", type=float, default=0.18)
    parser.add_argument("--stress-threshold", type=float, default=0.45)
    parser.add_argument("--gap-threshold", type=float, default=0.08)
    parser.add_argument("--heat-time", type=float, default=1.0)
    parser.add_argument("--model-id", default="lambda-laplace-cli")
    parser.add_argument("--out", default="lambda_laplace_certificate.json")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    if args.demo or args.lambda_p is None:
        result = demo()
    else:
        operator = LambdaLaplaceOperator(LambdaLaplaceConfig(
            dt=args.dt,
            alpha=args.alpha,
            beta=args.beta,
            seam_threshold=args.seam_threshold,
            stress_threshold=args.stress_threshold,
            gap_threshold=args.gap_threshold,
            heat_time=args.heat_time,
        ))
        result = asdict(operator.evaluate_series(
            lambda_p_series=args.lambda_p,
            lambda_v_series=args.lambda_v,
            skew_intensity_series=args.skew,
            entropy_potential_series=args.entropy,
            model_id=args.model_id,
        ))

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
    print(json.dumps({
        "ok": True,
        "out": args.out,
        "classification": result["analysis"]["classification"],
        "action": result["technical_action"]["action"],
        "seam_score": result["lambda_geometry"]["seam_score"],
        "spectral_gap_proxy": result["spectral_state"]["spectral_gap_proxy"],
        "certificate_hash": result["certificate_hash"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
