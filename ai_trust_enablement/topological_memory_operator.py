#!/usr/bin/env python3
"""
Topological Memory Operator topological-memory diagnostics for AI Trust Enablement.

The layer evaluates a lambda_p(t) phase trajectory, estimates winding-number
sector movement, computes discrete curvature stress, and emits a
machine-readable topological memory certificate.

Conceptual priority:
  1. winding / spectral-flow sector change: Delta nu != 0
  2. curvature stress: M > M* without sector jump
  3. stable sector: no integer jump and subcritical curvature

This follows the spectral-winding interpretation: the topological event is the
integer sector jump / spectral-flow crossing. The curvature-curvature signal value is
supporting evidence and a pre-transition stress signal, not the whole theorem
wearing a fake moustache.
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
class TopologicalMemoryConfig:
    dt: float = 1.0
    alpha: float = 0.10
    beta: float = 0.10
    threshold: float = 0.75
    topology_jump_threshold: int = 1
    reference_angle: float = 0.0


@dataclass(frozen=True)
class TopologicalMemoryCertificate:
    version: str
    certificate_type: str
    engine: str
    model_id: str
    event: Dict[str, Any]
    thermo_seed: Dict[str, Any]
    input_state: Dict[str, Any]
    winding_state: Dict[str, Any]
    spectral_state: Dict[str, Any]
    topological_state: Dict[str, Any]
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


def unit_complex(angle: float) -> Dict[str, float]:
    """JSON-friendly representation of exp(i angle)."""
    return {"real": math.cos(angle), "imag": math.sin(angle)}


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
    holonomy_phase = unwrapped_phases[-1] - unwrapped_phases[0]
    return {
        "winding_raw": winding_raw,
        "winding_number": winding_number,
        "delta_nu": delta_nu,
        "sector_series": sector_series,
        "winding_path": winding_path,
        "unwrapped_phase_series": unwrapped_phases,
        "holonomy_phase": holonomy_phase,
        "holonomy_turns": holonomy_phase / TWO_PI,
        "loop_transport_start": unit_complex(unwrapped_phases[0]),
        "loop_transport_end": unit_complex(unwrapped_phases[-1]),
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


def _number_or_none(value: Any) -> Optional[float]:
    return float(value) if isinstance(value, (int, float)) else None


def thermo_seed_from_certificate(certificate: Dict[str, Any], index: int = 0) -> Dict[str, Any]:
    """Map an AI certificate into the thermodynamic lambda-seed vocabulary.

    This is an engineering interface, not a claim that a model answer literally
    has heat capacity. It preserves the structural role from the thermo seed:
    lambda_p as phase branch, lambda_v as scale branch, and seam/skew memory as
    the branch-defect / nonreciprocal stress channel.
    """
    if not isinstance(certificate, dict):
        raise ValueError(f"certificate_{index}_must_be_object")
    recognition = certificate.get("recognition_state", {}) if isinstance(certificate.get("recognition_state", {}), dict) else {}
    seam = certificate.get("seam_memory", {}) if isinstance(certificate.get("seam_memory", {}), dict) else {}
    fusion = certificate.get("fusion_decision", {}) if isinstance(certificate.get("fusion_decision", {}), dict) else {}

    lambda_p = _number_or_none(recognition.get("phase_value"))
    if lambda_p is None:
        lambda_p = _number_or_none(recognition.get("open_residue"))
    if lambda_p is None:
        lambda_p = _number_or_none(fusion.get("open_residue")) or _number_or_none(fusion.get("score"))
    if lambda_p is None:
        raise ValueError(f"certificate_{index}_has_no_phase_like_value")

    lambda_v = _number_or_none(recognition.get("scale_value"))
    if lambda_v is None:
        lambda_v = _number_or_none(recognition.get("open_residue"))

    skew = _number_or_none(seam.get("k"))
    if skew is None:
        unsupported_entities = seam.get("unsupported_entities")
        unsupported_numbers = seam.get("unsupported_numbers")
        entity_count = len(unsupported_entities) if isinstance(unsupported_entities, list) else 0
        number_count = len(unsupported_numbers) if isinstance(unsupported_numbers, list) else 0
        skew = float(entity_count + number_count)

    return {
        "lambda_p": float(lambda_p),
        "lambda_v": float(lambda_v) if lambda_v is not None else None,
        "skew_intensity": float(skew),
        "source": "AI_CERTIFICATE_THERMO_SEED",
    }


def phase_series_from_certificates(certificates: Sequence[Dict[str, Any]]) -> List[float]:
    return [seed["lambda_p"] for seed in thermo_seed_series_from_certificates(certificates)]


def thermo_seed_series_from_certificates(certificates: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(certificates, Sequence) or isinstance(certificates, (str, bytes)):
        raise ValueError("certificates_must_be_array")
    if len(certificates) < 3:
        raise ValueError("certificates_must_have_at_least_3_samples")
    return [thermo_seed_from_certificate(certificate, index) for index, certificate in enumerate(certificates)]


def classify_topological_state(delta_nu: int, max_curvature_signal: float, threshold: float, topology_jump_threshold: int) -> Tuple[str, str, bool, bool, bool]:
    sector_jump = abs(int(delta_nu)) >= int(topology_jump_threshold)
    threshold_crossed = abs(float(max_curvature_signal)) > float(threshold)
    curvature_stress = bool(threshold_crossed and not sector_jump)
    if sector_jump:
        return (
            "TOPOLOGICAL_MEMORY_TRANSITION",
            "HOLD_AND_COMMIT_TOPOLOGICAL_JUMP",
            True,
            threshold_crossed,
            curvature_stress,
        )
    if threshold_crossed:
        return (
            "CURVATURE_STRESS_WITHOUT_SECTOR_JUMP",
            "FLAG_CURVATURE_STRESS",
            False,
            threshold_crossed,
            curvature_stress,
        )
    return (
        "STABLE_TOPOLOGICAL_SECTOR",
        "CONTINUE_MONITORING",
        False,
        threshold_crossed,
        False,
    )


class TopologicalMemoryOperator:
    """Compute spectral/winding-sector and Topological Memory curvature diagnostics."""

    def __init__(self, config: Optional[TopologicalMemoryConfig] = None) -> None:
        self.config = config or TopologicalMemoryConfig()

    def evaluate_series(
        self,
        lambda_p_series: Sequence[Any],
        skew_intensity_series: Optional[Sequence[Any]] = None,
        lambda_v_series: Optional[Sequence[Any]] = None,
        model_id: str = "topological-memory-operator",
        event_index: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TopologicalMemoryCertificate:
        cfg = self.config
        lambda_values = _as_float_series(lambda_p_series, "lambda_p_series")
        if skew_intensity_series is None:
            skew_values = [0.0] * len(lambda_values)
        else:
            skew_values = _as_float_series(skew_intensity_series, "skew_intensity_series")
            if len(skew_values) != len(lambda_values):
                raise ValueError("skew_intensity_series_must_match_lambda_p_series_length")
        if lambda_v_series is None:
            lambda_v_values: List[Optional[float]] = [None] * len(lambda_values)
        else:
            lambda_v_raw = _as_float_series(lambda_v_series, "lambda_v_series")
            if len(lambda_v_raw) != len(lambda_values):
                raise ValueError("lambda_v_series_must_match_lambda_p_series_length")
            lambda_v_values = [float(value) for value in lambda_v_raw]

        winding = winding_from_lambda(lambda_values)
        lambda_ddot = second_derivative(lambda_values, cfg.dt)
        nu_dot = first_derivative(winding["winding_path"], cfg.dt)

        curvature_signal_values: List[float] = []
        for index, curvature in enumerate(lambda_ddot):
            skew_term = cfg.alpha * (float(skew_values[index]) ** 2)
            memory_term = cfg.beta * abs(float(nu_dot[index]))
            curvature_signal_values.append(float(curvature) + skew_term + memory_term)

        max_curvature_signal = max(abs(value) for value in curvature_signal_values)
        classification, action, transition_detected, threshold_crossed, curvature_stress = classify_topological_state(
            delta_nu=int(winding["delta_nu"]),
            max_curvature_signal=max_curvature_signal,
            threshold=cfg.threshold,
            topology_jump_threshold=cfg.topology_jump_threshold,
        )
        sector_jump = bool(transition_detected)
        spectral_flow = int(winding["delta_nu"])
        spectral_crossing = bool(spectral_flow != 0)

        payload = {
            "version": "2.0.0",
            "certificate_type": "AI_TOPOLOGICAL_MEMORY_CERTIFICATE",
            "engine": "TopologicalMemoryOperatorSpectralWinding",
            "model_id": model_id,
            "event": {
                "event_index": int(event_index),
                "timestamp_unix": int(time.time()),
                "metadata": metadata or {},
            },
            "thermo_seed": {
                "interpretation": "lambda_p is the phase branch; lambda_v is the scale/volume branch when available; skew_intensity is branch-defect or nonreciprocal seam stress.",
                "lambda_p_source": "lambda_p_series",
                "lambda_v_source": "lambda_v_series" if lambda_v_series is not None else "not_supplied",
                "skew_source": "skew_intensity_series" if skew_intensity_series is not None else "zero_baseline",
            },
            "input_state": {
                "lambda_p_series": lambda_values,
                "lambda_v_series": lambda_v_values,
                "skew_intensity_series": skew_values,
                "sample_count": len(lambda_values),
                "dt": cfg.dt,
                "alpha": cfg.alpha,
                "beta": cfg.beta,
                "threshold": cfg.threshold,
                "topology_jump_threshold": cfg.topology_jump_threshold,
                "reference_angle": cfg.reference_angle,
            },
            "winding_state": winding,
            "spectral_state": {
                "spectral_flow": spectral_flow,
                "reference_angle": cfg.reference_angle,
                "spectral_crossing": spectral_crossing,
                "sector_jump_primary": sector_jump,
                "theorem_interface": "spectral_flow_equals_delta_nu",
            },
            "topological_state": {
                "lambda_ddot_series": lambda_ddot,
                "nu_dot_series": nu_dot,
                "curvature_signal_series": curvature_signal_values,
                "max_abs_curvature_signal": max_curvature_signal,
                "threshold_crossed": threshold_crossed,
                "curvature_stress": curvature_stress,
            },
            "transition": {
                "classification": classification,
                "transition_detected": transition_detected,
                "sector_jump": sector_jump,
                "curvature_stress": curvature_stress,
                "delta_nu": winding["delta_nu"],
                "primary_trigger": "spectral_winding_jump" if sector_jump else ("curvature_stress" if curvature_stress else "none"),
            },
            "technical_action": {
                "action": action,
                "reason": "integer_winding_jump" if sector_jump else ("subcritical_topology_curvature_stress" if curvature_stress else "stable_sector_subcritical_curvature"),
            },
        }
        return TopologicalMemoryCertificate(certificate_hash=sha256_json(payload), **payload)

    def evaluate_certificates(
        self,
        certificates: Sequence[Dict[str, Any]],
        skew_intensity_series: Optional[Sequence[Any]] = None,
        model_id: str = "topological-memory-operator",
        event_index: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TopologicalMemoryCertificate:
        seeds = thermo_seed_series_from_certificates(certificates)
        lambda_p = [seed["lambda_p"] for seed in seeds]
        lambda_v = [seed["lambda_v"] for seed in seeds]
        inferred_skew = [seed["skew_intensity"] for seed in seeds]
        return self.evaluate_series(
            lambda_p_series=lambda_p,
            lambda_v_series=lambda_v if all(value is not None for value in lambda_v) else None,
            skew_intensity_series=skew_intensity_series if skew_intensity_series is not None else inferred_skew,
            model_id=model_id,
            event_index=event_index,
            metadata={**(metadata or {}), "thermo_seed_series": seeds},
        )


def demo() -> Dict[str, Any]:
    # This trajectory makes one full turn in lambda-space. Delta nu = 1 is the
    # primary topological event; curvature terms only support the diagnosis.
    lambda_p = [0.00, 0.15, 0.32, 0.50, 0.74, 1.02, 1.18]
    skew = [0.0, 0.1, 0.1, 0.2, 0.4, 0.5, 0.5]
    cert = TopologicalMemoryOperator(TopologicalMemoryConfig(threshold=0.45, alpha=0.25, beta=0.20)).evaluate_series(
        lambda_p,
        skew_intensity_series=skew,
        model_id="topological_memory-demo",
        metadata={"demo": "one winding sector transition"},
    )
    return asdict(cert)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute a Topological Memory topological memory certificate")
    parser.add_argument("--lambda-p", nargs="+", type=float, default=None, help="lambda_p samples")
    parser.add_argument("--lambda-v", nargs="+", type=float, default=None, help="optional lambda_v samples")
    parser.add_argument("--skew", nargs="+", type=float, default=None, help="optional skew intensity samples")
    parser.add_argument("--dt", type=float, default=1.0)
    parser.add_argument("--alpha", type=float, default=0.10)
    parser.add_argument("--beta", type=float, default=0.10)
    parser.add_argument("--threshold", type=float, default=0.75)
    parser.add_argument("--topology-jump-threshold", type=int, default=1)
    parser.add_argument("--model-id", default="topological_memory-cli")
    parser.add_argument("--out", default="topological_memory_memory_certificate.json")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    if args.demo or args.lambda_p is None:
        result = demo()
    else:
        result = asdict(TopologicalMemoryOperator(TopologicalMemoryConfig(
            dt=args.dt,
            alpha=args.alpha,
            beta=args.beta,
            threshold=args.threshold,
            topology_jump_threshold=args.topology_jump_threshold,
        )).evaluate_series(args.lambda_p, lambda_v_series=args.lambda_v, skew_intensity_series=args.skew, model_id=args.model_id))

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
    print(json.dumps({
        "ok": True,
        "out": args.out,
        "classification": result["transition"]["classification"],
        "action": result["technical_action"]["action"],
        "delta_nu": result["transition"]["delta_nu"],
        "spectral_flow": result["spectral_state"]["spectral_flow"],
        "certificate_hash": result["certificate_hash"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
