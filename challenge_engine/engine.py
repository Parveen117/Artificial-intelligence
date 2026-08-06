#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json
import math


ENGINE_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"

TERMINAL_RESULTS = {
    "OBSERVED",
    "ADVERSARIAL_PASS",
    "CERTIFIED",
    "INCOMPLETE",
    "FAILED",
    "INVALID",
    "BLOCKED_SCOPE",
}


@dataclass
class Check:
    id: str
    status: str
    detail: str


class ChallengeError(Exception):
    pass


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


def _package_dir() -> Path:
    return Path(__file__).resolve().parent / "packages"


def available_packages() -> list[str]:
    return sorted(p.stem for p in _package_dir().glob("*.json"))


def load_package(name: str) -> dict[str, Any]:
    path = _package_dir() / f"{name}.json"
    if not path.exists():
        raise ChallengeError(f"unknown package: {name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("package") != name:
        raise ChallengeError(f"package manifest mismatch: {name}")
    return data


def _obligation_map(challenge: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in challenge.get("obligations", []):
        if not isinstance(item, dict):
            continue
        oid = item.get("id")
        status = item.get("status")
        if isinstance(oid, str) and status in {"pass", "fail", "open"}:
            out[oid] = status
    return out


def _check_basic_structure(challenge: dict[str, Any], package: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    required = ["challenge_id", "target"]
    for key in required:
        if key not in challenge:
            checks.append(Check(f"field:{key}", "fail", f"missing required field '{key}'"))
        else:
            checks.append(Check(f"field:{key}", "pass", "present"))

    if challenge.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
        checks.append(Check("schema_version", "fail", f"expected {SCHEMA_VERSION}"))
    else:
        checks.append(Check("schema_version", "pass", SCHEMA_VERSION))

    target = challenge.get("target")
    if not isinstance(target, dict) or not str(target.get("statement", "")).strip():
        checks.append(Check("target", "fail", "target.statement must be a non-empty string"))
    else:
        checks.append(Check("target", "pass", "declared before evaluation"))

    mode = challenge.get("mode", package.get("default_mode", "exploratory"))
    if mode not in package.get("allowed_modes", []):
        checks.append(Check("mode", "fail", f"mode '{mode}' is not allowed by package"))
    else:
        checks.append(Check("mode", "pass", mode))

    evidence = challenge.get("evidence", [])
    if evidence is not None and not isinstance(evidence, list):
        checks.append(Check("evidence_shape", "fail", "evidence must be a list"))
    else:
        checks.append(Check("evidence_shape", "pass", f"{len(evidence or [])} entries"))

    obligations = challenge.get("obligations", [])
    if obligations is not None and not isinstance(obligations, list):
        checks.append(Check("obligations_shape", "fail", "obligations must be a list"))
    else:
        checks.append(Check("obligations_shape", "pass", f"{len(obligations or [])} entries"))
    return checks


def _check_scope(challenge: dict[str, Any], package: dict[str, Any]) -> Check | None:
    if not package.get("requires_authorization", False):
        return None
    scope = challenge.get("scope")
    if not isinstance(scope, dict):
        return Check("scope_authorization", "blocked", "authorized scope is required by this package")
    if scope.get("authorization") != "declared":
        return Check("scope_authorization", "blocked", "scope.authorization must equal 'declared'")
    target = str(scope.get("target", "")).strip()
    if not target:
        return Check("scope_authorization", "blocked", "scope.target must be declared")
    return Check("scope_authorization", "pass", f"declared for {target}")


def _required_obligations(challenge: dict[str, Any], package: dict[str, Any]) -> list[Check]:
    mode = challenge.get("mode", package.get("default_mode", "exploratory"))
    required = package.get("required_obligations", {}).get(mode, [])
    omap = _obligation_map(challenge)
    checks: list[Check] = []
    for oid in required:
        status = omap.get(oid)
        if status is None:
            checks.append(Check(f"obligation:{oid}", "open", "required obligation missing"))
        elif status == "pass":
            checks.append(Check(f"obligation:{oid}", "pass", "closed"))
        elif status == "fail":
            checks.append(Check(f"obligation:{oid}", "fail", "declared failure"))
        else:
            checks.append(Check(f"obligation:{oid}", "open", "not yet closed"))
    return checks


def _check_negative_controls(challenge: dict[str, Any], mode: str) -> list[Check]:
    if mode not in {"adversarial", "certified"}:
        return []
    controls = challenge.get("negative_controls", [])
    if not isinstance(controls, list) or not controls:
        return [Check("negative_controls", "open", "at least one negative control is required")]
    checks: list[Check] = []
    for i, item in enumerate(controls):
        if not isinstance(item, dict):
            checks.append(Check(f"negative_control:{i}", "fail", "control must be an object"))
            continue
        cid = str(item.get("id", i))
        status = item.get("status")
        if status == "pass":
            checks.append(Check(f"negative_control:{cid}", "pass", "invalid/mutated case was detected"))
        elif status == "fail":
            checks.append(Check(f"negative_control:{cid}", "fail", "negative control escaped detection"))
        else:
            checks.append(Check(f"negative_control:{cid}", "open", "negative control has not closed"))
    return checks


def _check_formal_promotion(challenge: dict[str, Any], package: dict[str, Any], mode: str) -> Check | None:
    if mode != "certified":
        return None
    if not package.get("certification_requires_formal_adapter", True):
        return Check("formal_adapter", "pass", "package permits certification without a formal adapter")
    adapter = challenge.get("formal_adapter")
    if not isinstance(adapter, dict):
        return Check("formal_adapter", "open", "certified mode requires a declared formal_adapter")
    if adapter.get("status") != "pass":
        return Check("formal_adapter", "open" if adapter.get("status") != "fail" else "fail",
                     "formal adapter has not passed")
    if not str(adapter.get("id", "")).strip():
        return Check("formal_adapter", "fail", "formal_adapter.id is required")
    return Check("formal_adapter", "pass", str(adapter.get("id")))


def _check_evidence_boundary(challenge: dict[str, Any], mode: str) -> Check:
    evidence = challenge.get("evidence", [])
    formal_support = 0
    nonformal_support = 0
    for item in evidence if isinstance(evidence, list) else []:
        if not isinstance(item, dict) or item.get("status", "pass") != "pass":
            continue
        if item.get("formal") is True:
            formal_support += 1
        else:
            nonformal_support += 1
    if mode == "certified" and formal_support == 0:
        return Check(
            "evidence_boundary",
            "open",
            "non-formal evidence may be retained, but certified mode needs at least one formal support item",
        )
    return Check(
        "evidence_boundary",
        "pass",
        f"formal_support={formal_support}, nonformal_support={nonformal_support}",
    )


def _check_flow(challenge: dict[str, Any]) -> list[Check]:
    flow = challenge.get("flow")
    if not isinstance(flow, dict) or not flow.get("enabled", False):
        return []
    checks: list[Check] = []
    probes = flow.get("probes", [])
    if not isinstance(probes, list) or not probes:
        return [Check("flow:probes", "open", "flow enabled but no probes were supplied")]

    parsed: list[tuple[int, bool]] = []
    for item in probes:
        if not isinstance(item, dict) or not isinstance(item.get("order"), int):
            checks.append(Check("flow:probe_shape", "fail", "every probe needs integer order"))
            continue
        if "target_visible" in item and not isinstance(item["target_visible"], bool):
            checks.append(Check(f"flow:probe:{item['order']}", "fail", "target_visible must be Boolean"))
            continue
        parsed.append((item["order"], bool(item.get("target_visible", False))))
    parsed.sort()

    seen_visible = False
    monotone = True
    for _, visible in parsed:
        if seen_visible and not visible:
            monotone = False
        seen_visible = seen_visible or visible
    if monotone:
        checks.append(Check("flow:recognition_monotonicity", "pass", "visibility does not revert at higher probe order"))
    else:
        checks.append(Check("flow:recognition_monotonicity", "fail", "target visibility reverted at a higher probe order"))

    visible_orders = [order for order, visible in parsed if visible]
    declared_first = flow.get("first_recognition_order")
    if visible_orders:
        actual_first = min(visible_orders)
        if declared_first is None:
            checks.append(Check("flow:first_recognition_order", "open", f"observed first visible order is {actual_first}"))
        elif declared_first == actual_first:
            checks.append(Check("flow:first_recognition_order", "pass", str(actual_first)))
        else:
            checks.append(Check("flow:first_recognition_order", "fail",
                                f"declared {declared_first}, observed {actual_first}"))
    elif declared_first is not None:
        checks.append(Check("flow:first_recognition_order", "fail", "declared recognition without a visible probe"))

    bilateral = flow.get("bilateral")
    if isinstance(bilateral, dict):
        defect = bilateral.get("defect")
        tolerance = bilateral.get("tolerance")
        if _is_number(defect) and _is_number(tolerance) and float(tolerance) >= 0:
            if abs(float(defect)) <= float(tolerance):
                checks.append(Check("flow:bilateral_defect", "pass", f"|defect| <= {tolerance}"))
            else:
                checks.append(Check("flow:bilateral_defect", "fail", f"|defect|={abs(float(defect))} > {tolerance}"))
        else:
            checks.append(Check("flow:bilateral_defect", "open", "defect and nonnegative tolerance are required"))

    if "remainder_bound" in flow:
        rb = flow.get("remainder_bound")
        if _is_number(rb) and float(rb) >= 0:
            checks.append(Check("flow:remainder_bound", "pass", str(rb)))
        else:
            checks.append(Check("flow:remainder_bound", "fail", "remainder_bound must be a nonnegative finite number"))
    return checks


def _check_burden(challenge: dict[str, Any]) -> Check | None:
    burden = challenge.get("burden")
    if not isinstance(burden, dict):
        return None
    beta = burden.get("beta")
    threshold = burden.get("threshold", 1.0)
    if not _is_number(beta) or not _is_number(threshold):
        return Check("burden", "fail", "beta and threshold must be finite numbers")
    reserve = float(threshold) - float(beta)
    if reserve > 0:
        return Check("burden", "pass", f"beta={beta}; strict reserve={reserve}")
    if reserve == 0:
        return Check("burden", "open", f"beta={beta}; boundary saturation")
    return Check("burden", "fail", f"beta={beta} exceeds threshold={threshold}")


def _check_completion(challenge: dict[str, Any]) -> Check | None:
    completion = challenge.get("completion")
    if not isinstance(completion, dict) or not completion.get("enabled", False):
        return None
    u = completion.get("finite_upper")
    e = completion.get("completion_error")
    threshold = completion.get("threshold", 1.0)
    if not _is_number(u):
        return Check("completion", "open", "finite_upper is required")
    if not _is_number(e):
        return Check("completion", "open", "completion_error is required; a finite result alone cannot promote")
    if not _is_number(threshold):
        return Check("completion", "fail", "threshold must be finite")
    if float(e) < 0:
        return Check("completion", "fail", "completion_error must be nonnegative")
    worst = float(u) + float(e)
    margin = float(threshold) - worst
    if margin > 0:
        return Check("completion", "pass", f"finite_upper + error = {worst}; reserve={margin}")
    if margin == 0:
        return Check("completion", "open", f"worst-case bound reaches threshold {threshold}")
    return Check("completion", "fail", f"worst-case bound {worst} exceeds threshold {threshold}")


def evaluate_challenge(challenge: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(challenge, dict):
        raise ChallengeError("challenge input must be a JSON object")

    package_name = challenge.get("package") or "math"
    package = load_package(package_name)
    mode = challenge.get("mode") or package.get("default_mode", "exploratory")
    challenge = dict(challenge)
    challenge["package"] = package_name
    challenge["mode"] = mode
    challenge.setdefault("schema_version", SCHEMA_VERSION)

    checks = _check_basic_structure(challenge, package)
    scope_check = _check_scope(challenge, package)
    if scope_check:
        checks.append(scope_check)
    checks.extend(_required_obligations(challenge, package))
    checks.extend(_check_negative_controls(challenge, mode))
    formal_check = _check_formal_promotion(challenge, package, mode)
    if formal_check:
        checks.append(formal_check)
    checks.append(_check_evidence_boundary(challenge, mode))
    checks.extend(_check_flow(challenge))
    burden_check = _check_burden(challenge)
    if burden_check:
        checks.append(burden_check)
    completion_check = _check_completion(challenge)
    if completion_check:
        checks.append(completion_check)

    statuses = [c.status for c in checks]
    if "blocked" in statuses:
        result = "BLOCKED_SCOPE"
    elif any(c.id.startswith("field:") and c.status == "fail" for c in checks) or any(
        c.id in {"schema_version", "target", "mode", "evidence_shape", "obligations_shape"} and c.status == "fail"
        for c in checks
    ):
        result = "INVALID"
    elif "fail" in statuses:
        result = "FAILED"
    elif "open" in statuses:
        result = "INCOMPLETE"
    elif mode == "exploratory":
        result = "OBSERVED"
    elif mode == "adversarial":
        result = "ADVERSARIAL_PASS"
    elif mode == "certified":
        result = "CERTIFIED"
    else:
        result = "INVALID"

    formal_promotion = result == "CERTIFIED"
    open_items = [c.id for c in checks if c.status == "open"]
    failed_items = [c.id for c in checks if c.status == "fail"]
    blocked_items = [c.id for c in checks if c.status == "blocked"]

    return {
        "engine_version": ENGINE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "challenge_id": challenge.get("challenge_id"),
        "package": package_name,
        "mode": mode,
        "result": result,
        "formal_promotion": formal_promotion,
        "checks": [asdict(c) for c in checks],
        "open_obligations": open_items,
        "failed_obligations": failed_items,
        "blocked_obligations": blocked_items,
        "claim_boundary": (
            "The result is relative to this declared challenge contract. "
            "Non-formal evidence is permitted in exploratory/adversarial modes, "
            "but it does not become a formal certificate without a passing formal adapter."
        ),
    }


def capabilities() -> dict[str, Any]:
    manifests = [load_package(name) for name in available_packages()]
    return {
        "engine_version": ENGINE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "default_package": "math",
        "results": sorted(TERMINAL_RESULTS),
        "packages": manifests,
        "stdin_stdout_json": True,
        "network_required": False,
    }
