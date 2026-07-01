#!/usr/bin/env python3
"""
Future Arrow Operator for AI Trust Enablement.

The Future Arrow layer projects the current recognition / Monti state forward
into a probability-coated cone of likely future recognition sectors.

It does not replace Monti. Monti asks whether a topological sector jump has
occurred. Future Arrow asks what future sector-risk distribution follows from
current entropy, statistical layering, anchors, and time shift.

Design priority:
  1. use Monti state when available as the topological context,
  2. build a forward probability cone over stable / stress / jump / post-jump,
  3. tighten the cone when NSL symmetry and anchor constraints are supplied,
  4. emit a deterministic forecast certificate that can be ECL-sealed if needed.
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
class FutureArrowConfig:
    delta_t: float = 1.0
    entropy_weight: float = 0.45
    layer_weight: float = 0.25
    anchor_weight: float = 0.20
    monti_weight: float = 0.55
    nsl_strength: float = 0.0
    jump_threshold: float = 0.62
    stress_threshold: float = 0.38


@dataclass(frozen=True)
class FutureArrowCertificate:
    version: str
    certificate_type: str
    engine: str
    model_id: str
    event: Dict[str, Any]
    input_state: Dict[str, Any]
    probability_coating: Dict[str, Any]
    future_cone: Dict[str, Any]
    nsl_state: Dict[str, Any]
    forecast: Dict[str, Any]
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


def normalize(weights: Dict[str, float]) -> Dict[str, float]:
    clean = {key: max(0.0, float(value)) for key, value in weights.items()}
    total = sum(clean.values())
    if total <= 0.0:
        n = max(1, len(clean))
        return {key: 1.0 / n for key in clean}
    return {key: value / total for key, value in clean.items()}


def _number(value: Any, default: float = 0.0) -> float:
    return float(value) if isinstance(value, (int, float)) else float(default)


def _extract_monti_features(monti_certificate: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(monti_certificate, dict):
        return {
            "available": False,
            "classification": "UNKNOWN",
            "delta_nu": 0,
            "spectral_flow": 0,
            "curvature_stress": False,
            "max_abs_monti": 0.0,
            "transition_detected": False,
        }
    transition = monti_certificate.get("transition", {}) if isinstance(monti_certificate.get("transition", {}), dict) else {}
    spectral = monti_certificate.get("spectral_state", {}) if isinstance(monti_certificate.get("spectral_state", {}), dict) else {}
    monti_state = monti_certificate.get("monti_state", {}) if isinstance(monti_certificate.get("monti_state", {}), dict) else {}
    return {
        "available": True,
        "classification": str(transition.get("classification", "UNKNOWN")),
        "delta_nu": int(_number(transition.get("delta_nu", spectral.get("spectral_flow", 0)), 0)),
        "spectral_flow": int(_number(spectral.get("spectral_flow", transition.get("delta_nu", 0)), 0)),
        "curvature_stress": bool(transition.get("curvature_stress", monti_state.get("curvature_stress", False))),
        "max_abs_monti": _number(monti_state.get("max_abs_monti"), 0.0),
        "transition_detected": bool(transition.get("transition_detected", False)),
    }


def _extract_recognition_features(recognition_certificate: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(recognition_certificate, dict):
        return {
            "available": False,
            "classification": "UNKNOWN",
            "open_residue": 0.0,
            "phase_value": 0.0,
            "scale_value": 0.0,
            "seam_k": 0.0,
        }
    recognition = recognition_certificate.get("recognition_state", {}) if isinstance(recognition_certificate.get("recognition_state", {}), dict) else {}
    seam = recognition_certificate.get("seam_memory", {}) if isinstance(recognition_certificate.get("seam_memory", {}), dict) else {}
    return {
        "available": True,
        "classification": str(recognition.get("classification", "UNKNOWN")),
        "open_residue": _number(recognition.get("open_residue"), 0.0),
        "phase_value": _number(recognition.get("phase_value"), 0.0),
        "scale_value": _number(recognition.get("scale_value"), 0.0),
        "seam_k": _number(seam.get("k"), 0.0),
    }


def _anchor_strength(anchor_constraints: Optional[Sequence[Any]]) -> float:
    if not anchor_constraints:
        return 0.0
    valid = 0
    for item in anchor_constraints:
        if isinstance(item, (str, int, float)):
            valid += 1
        elif isinstance(item, dict) and item:
            valid += 1
    return clamp(valid / 8.0)


class FutureArrowOperator:
    """Project an AI recognition/Monti state into a future probability cone."""

    def __init__(self, config: Optional[FutureArrowConfig] = None) -> None:
        self.config = config or FutureArrowConfig()

    def project(
        self,
        state: Optional[Dict[str, Any]] = None,
        recognition_certificate: Optional[Dict[str, Any]] = None,
        monti_certificate: Optional[Dict[str, Any]] = None,
        entropy_potential: Optional[float] = None,
        statistical_layer: Optional[float] = None,
        anchor_constraints: Optional[Sequence[Any]] = None,
        model_id: str = "future-arrow",
        event_index: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FutureArrowCertificate:
        cfg = self.config
        state = state if isinstance(state, dict) else {}
        recognition = _extract_recognition_features(recognition_certificate)
        monti = _extract_monti_features(monti_certificate)

        entropy = clamp(_number(entropy_potential, state.get("entropy_potential", recognition["open_residue"])))
        layer = clamp(_number(statistical_layer, state.get("statistical_layer", 1.0 - recognition["scale_value"])))
        anchor = _anchor_strength(anchor_constraints)
        delta_t_factor = 1.0 - math.exp(-max(0.0, float(cfg.delta_t)))

        monti_jump_signal = 1.0 if abs(int(monti["delta_nu"])) > 0 else 0.0
        monti_stress_signal = clamp(monti["max_abs_monti"] / (1.0 + monti["max_abs_monti"]))
        if bool(monti["curvature_stress"]):
            monti_stress_signal = max(monti_stress_signal, 0.62)
        residue_signal = clamp(recognition["open_residue"])
        seam_signal = clamp(recognition["seam_k"] / (1.0 + recognition["seam_k"]))

        raw_jump_risk = clamp(
            cfg.monti_weight * monti_jump_signal
            + 0.35 * cfg.monti_weight * monti_stress_signal
            + cfg.entropy_weight * entropy * delta_t_factor
            + 0.25 * residue_signal
            + 0.15 * seam_signal
            - cfg.anchor_weight * anchor
        )
        raw_stress_risk = clamp(
            0.45 * monti_stress_signal
            + cfg.entropy_weight * entropy
            + cfg.layer_weight * layer
            + 0.20 * residue_signal
            - 0.15 * anchor
        )
        post_jump_branching = clamp(0.55 * monti_jump_signal + 0.25 * entropy + 0.20 * layer - 0.10 * anchor)

        nsl_strength = clamp(cfg.nsl_strength)
        nsl_tightening = 1.0 / (1.0 + nsl_strength + anchor)
        jump_risk = clamp(raw_jump_risk * nsl_tightening)
        stress_risk = clamp(raw_stress_risk * (0.75 + 0.25 * nsl_tightening))
        stable_score = clamp(1.0 - max(jump_risk, stress_risk) + 0.25 * anchor)

        distribution = normalize({
            "STABLE_FORWARD_CONE": stable_score,
            "CURVATURE_STRESS_LIKELY": stress_risk,
            "SECTOR_JUMP_RISK": jump_risk,
            "POST_JUMP_BRANCHING": post_jump_branching,
            "ANCHOR_CONSTRAINED_FUTURE": anchor,
        })
        dominant = max(distribution, key=distribution.get)
        expected_delta_nu = int(monti["delta_nu"]) + (1 if distribution["SECTOR_JUMP_RISK"] >= cfg.jump_threshold else 0)

        if distribution["SECTOR_JUMP_RISK"] >= cfg.jump_threshold:
            action = "PREPARE_TO_HOLD_AND_RECHECK_MONTI"
            reason = "future_sector_jump_risk_high"
        elif distribution["CURVATURE_STRESS_LIKELY"] >= cfg.stress_threshold:
            action = "WATCH_CURVATURE_STRESS_CONE"
            reason = "future_curvature_stress_likely"
        elif distribution["ANCHOR_CONSTRAINED_FUTURE"] >= 0.40:
            action = "CONTINUE_WITH_ANCHOR_CONSTRAINTS"
            reason = "anchors_tighten_future_cone"
        else:
            action = "CONTINUE_MONITORING"
            reason = "stable_forward_cone"

        payload = {
            "version": "1.0.0",
            "certificate_type": "AI_FUTURE_ARROW_CERTIFICATE",
            "engine": "FutureArrowOperator",
            "model_id": model_id,
            "event": {
                "event_index": int(event_index),
                "timestamp_unix": int(time.time()),
                "metadata": metadata or {},
            },
            "input_state": {
                "state": state,
                "recognition_features": recognition,
                "monti_features": monti,
                "entropy_potential": entropy,
                "statistical_layer": layer,
                "anchor_strength": anchor,
                "anchor_constraints": list(anchor_constraints or []),
                "delta_t": cfg.delta_t,
            },
            "probability_coating": {
                "formula": "P(x,t+Delta t)=f(H,L,E,Delta t) with anchor and NSL tightening",
                "entropy_component": entropy,
                "statistical_layer_component": layer,
                "monti_jump_component": monti_jump_signal,
                "monti_stress_component": monti_stress_signal,
                "anchor_component": anchor,
                "delta_t_factor": delta_t_factor,
            },
            "future_cone": {
                "distribution": distribution,
                "dominant_future": dominant,
                "probability_of_sector_jump": distribution["SECTOR_JUMP_RISK"],
                "probability_of_curvature_stress": distribution["CURVATURE_STRESS_LIKELY"],
                "expected_delta_nu": expected_delta_nu,
            },
            "nsl_state": {
                "nsl_strength": nsl_strength,
                "tightening_factor": nsl_tightening,
                "applied": bool(nsl_strength > 0.0 or anchor > 0.0),
            },
            "forecast": {
                "classification": dominant,
                "delta_t": cfg.delta_t,
                "cone_width": clamp(entropy * delta_t_factor * (1.0 - 0.5 * anchor)),
                "forecast_hash_input": sha256_json({"distribution": distribution, "expected_delta_nu": expected_delta_nu}),
            },
            "technical_action": {
                "action": action,
                "reason": reason,
            },
        }
        return FutureArrowCertificate(certificate_hash=sha256_json(payload), **payload)


def demo() -> Dict[str, Any]:
    monti = {
        "transition": {
            "classification": "TOPOLOGICAL_MEMORY_TRANSITION",
            "delta_nu": 1,
            "curvature_stress": False,
            "transition_detected": True,
        },
        "spectral_state": {"spectral_flow": 1},
        "monti_state": {"max_abs_monti": 0.52, "curvature_stress": False},
    }
    recognition = {
        "recognition_state": {
            "classification": "ACTIONABLE_RESIDUE",
            "open_residue": 0.42,
            "phase_value": 1.18,
            "scale_value": 0.22,
        },
        "seam_memory": {"k": 2},
    }
    cert = FutureArrowOperator(FutureArrowConfig(delta_t=2.0, nsl_strength=0.30)).project(
        recognition_certificate=recognition,
        monti_certificate=monti,
        entropy_potential=0.45,
        statistical_layer=0.60,
        anchor_constraints=["prime_anchor:recognition", "north_axis:low_entropy_gradient"],
        model_id="future-arrow-demo",
        metadata={"demo": "post-Monti future cone"},
    )
    return asdict(cert)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute a Future Arrow probability-cone certificate")
    parser.add_argument("--delta-t", type=float, default=1.0)
    parser.add_argument("--entropy", type=float, default=0.45)
    parser.add_argument("--layer", type=float, default=0.50)
    parser.add_argument("--nsl", type=float, default=0.0)
    parser.add_argument("--model-id", default="future-arrow-cli")
    parser.add_argument("--out", default="future_arrow_certificate.json")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    if args.demo:
        result = demo()
    else:
        result = asdict(FutureArrowOperator(FutureArrowConfig(delta_t=args.delta_t, nsl_strength=args.nsl)).project(
            entropy_potential=args.entropy,
            statistical_layer=args.layer,
            model_id=args.model_id,
        ))

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
    print(json.dumps({
        "ok": True,
        "out": args.out,
        "classification": result["forecast"]["classification"],
        "action": result["technical_action"]["action"],
        "probability_of_sector_jump": result["future_cone"]["probability_of_sector_jump"],
        "certificate_hash": result["certificate_hash"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
