#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import hashlib
import json
import math


ENGINE_VERSION = "1.1.0"
SCHEMA_VERSION = "1.0"

TERMINAL_RESULTS = {
    "OBSERVED",
    "ADVERSARIAL_PASS",
    "CERTIFIED",
    "INCOMPLETE",
    "FAILED",
    "INVALID",
    "BLOCKED_SCOPE",
    "SEMANTICS_NOT_IN_SCOPE",
}

BREAK_CONDITIONS = [
    "false_acceptance",
    "blindness_escape",
    "scope_escape",
    "negative_control_escape",
    "invalid_promotion",
    "flow_consistency_escape",
    "ledger_integrity_failure",
]


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
    for key in ("challenge_id", "target"):
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


def _check_threat_model(challenge: dict[str, Any], mode: str) -> Check | None:
    if mode == "exploratory":
        return None
    model = challenge.get("threat_model")
    if not isinstance(model, dict):
        return Check(
            "threat_model",
            "open",
            "adversarial/certified mode requires a declared goal and break_conditions",
        )
    goal = str(model.get("goal", "")).strip()
    conditions = model.get("break_conditions")
    if not goal:
        return Check("threat_model", "open", "threat_model.goal must be declared")
    if not isinstance(conditions, list) or not conditions:
        return Check("threat_model", "open", "threat_model.break_conditions must be a non-empty list")
    bad = [c for c in conditions if c not in BREAK_CONDITIONS]
    if bad:
        return Check("threat_model", "fail", f"unknown break condition(s): {', '.join(map(str, bad))}")
    return Check("threat_model", "pass", f"goal fixed; break_conditions={','.join(conditions)}")


def _check_semantics(challenge: dict[str, Any]) -> Check:
    semantics = challenge.get("semantics")
    if semantics is None:
        semantics = {"mode": "payload_only"}
    if not isinstance(semantics, dict):
        return Check("semantic_scope", "fail", "semantics must be an object")
    mode = semantics.get("mode", "payload_only")
    if mode == "payload_only":
        return Check(
            "semantic_scope",
            "pass",
            "target.statement is treated as declared payload/label; unrestricted natural-language semantics are not inferred",
        )
    if mode != "adapter_declared":
        return Check("semantic_scope", "fail", "semantics.mode must be payload_only or adapter_declared")
    adapter = challenge.get("semantic_adapter")
    if not isinstance(adapter, dict):
        return Check(
            "semantic_scope",
            "not_in_scope",
            "semantic interpretation was requested but no semantic_adapter was declared",
        )
    if not str(adapter.get("id", "")).strip():
        return Check("semantic_scope", "fail", "semantic_adapter.id is required")
    status = adapter.get("status")
    if status == "pass":
        return Check("semantic_scope", "pass", f"semantic adapter closed: {adapter['id']}")
    if status == "fail":
        return Check("semantic_scope", "fail", f"semantic adapter failed: {adapter['id']}")
    return Check(
        "semantic_scope",
        "not_in_scope",
        f"semantic adapter has not closed: {adapter['id']}",
    )


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
        return Check(
            "formal_adapter",
            "open" if adapter.get("status") != "fail" else "fail",
            "formal adapter has not passed",
        )
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
    checks.append(
        Check(
            "flow:recognition_monotonicity",
            "pass" if monotone else "fail",
            "visibility does not revert at higher probe order"
            if monotone
            else "target visibility reverted at a higher probe order",
        )
    )

    visible_orders = [order for order, visible in parsed if visible]
    declared_first = flow.get("first_recognition_order")
    if visible_orders:
        actual_first = min(visible_orders)
        if declared_first is None:
            checks.append(Check("flow:first_recognition_order", "open", f"observed first visible order is {actual_first}"))
        elif declared_first == actual_first:
            checks.append(Check("flow:first_recognition_order", "pass", str(actual_first)))
        else:
            checks.append(
                Check(
                    "flow:first_recognition_order",
                    "fail",
                    f"declared {declared_first}, observed {actual_first}",
                )
            )
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


def _strip_status(item: Any) -> Any:
    if not isinstance(item, dict):
        return item
    keep = {}
    for key in ("id", "type", "formal", "sha256", "hash", "ref", "source"):
        if key in item:
            keep[key] = item[key]
    return keep


def _genesis_payload(challenge: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
    mode = challenge.get("mode", package.get("default_mode", "exploratory"))
    semantics = challenge.get("semantics") if isinstance(challenge.get("semantics"), dict) else {"mode": "payload_only"}
    flow = challenge.get("flow") if isinstance(challenge.get("flow"), dict) else {}
    burden = challenge.get("burden") if isinstance(challenge.get("burden"), dict) else {}
    completion = challenge.get("completion") if isinstance(challenge.get("completion"), dict) else {}
    bilateral = flow.get("bilateral") if isinstance(flow.get("bilateral"), dict) else {}
    return {
        "engine_version": ENGINE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "challenge_id": challenge.get("challenge_id"),
        "package": package.get("package"),
        "package_version": package.get("version"),
        "mode": mode,
        "target": challenge.get("target"),
        "scope": challenge.get("scope", {}),
        "threat_model": challenge.get("threat_model", {}),
        "semantics": {"mode": semantics.get("mode", "payload_only")},
        "required_obligations": package.get("required_obligations", {}).get(mode, []),
        "declared_obligation_ids": sorted(
            str(x.get("id")) for x in challenge.get("obligations", []) if isinstance(x, dict) and x.get("id") is not None
        ),
        "negative_control_ids": sorted(
            str(x.get("id")) for x in challenge.get("negative_controls", []) if isinstance(x, dict) and x.get("id") is not None
        ),
        "evidence_refs": [_strip_status(x) for x in challenge.get("evidence", []) if isinstance(x, dict)],
        "formal_adapter_id": challenge.get("formal_adapter", {}).get("id")
        if isinstance(challenge.get("formal_adapter"), dict)
        else None,
        "semantic_adapter_id": challenge.get("semantic_adapter", {}).get("id")
        if isinstance(challenge.get("semantic_adapter"), dict)
        else None,
        "thresholds": {
            "burden": burden.get("threshold"),
            "completion": completion.get("threshold"),
            "bilateral_tolerance": bilateral.get("tolerance"),
        },
    }


def _challenge_genesis(challenge: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
    payload = _genesis_payload(challenge, package)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {
        "kind": "CHALLENGE_GENESIS",
        "hash_algorithm": "sha256",
        "genesis_hash": digest,
        "parent": None,
        "accepted_claims": 0,
        "rules_frozen": True,
        "meaning": "immutable rules of engagement before candidate evaluation; no claim is accepted at genesis",
        "contract": payload,
    }


def _check_genesis_pin(challenge: dict[str, Any], genesis: dict[str, Any]) -> Check | None:
    pin = challenge.get("genesis")
    if not isinstance(pin, dict) or "expected_hash" not in pin:
        return None
    expected = str(pin.get("expected_hash", "")).strip().lower()
    if not expected:
        return Check("genesis_integrity", "fail", "genesis.expected_hash must be non-empty")
    actual = genesis["genesis_hash"]
    if expected == actual:
        return Check("genesis_integrity", "pass", actual)
    return Check("genesis_integrity", "fail", f"expected {expected}, computed {actual}")


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
    if "semantics" not in challenge:
        challenge["semantics"] = {"mode": "payload_only"}

    genesis = _challenge_genesis(challenge, package)

    checks = _check_basic_structure(challenge, package)
    scope_check = _check_scope(challenge, package)
    if scope_check:
        checks.append(scope_check)
    threat_check = _check_threat_model(challenge, mode)
    if threat_check:
        checks.append(threat_check)
    checks.append(_check_semantics(challenge))
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
    genesis_check = _check_genesis_pin(challenge, genesis)
    if genesis_check:
        checks.append(genesis_check)

    statuses = [c.status for c in checks]
    if "blocked" in statuses:
        result = "BLOCKED_SCOPE"
    elif any(c.id.startswith("field:") and c.status == "fail" for c in checks) or any(
        c.id in {"schema_version", "target", "mode", "evidence_shape", "obligations_shape", "semantic_scope"}
        and c.status == "fail"
        for c in checks
    ):
        result = "INVALID"
    elif "not_in_scope" in statuses:
        result = "SEMANTICS_NOT_IN_SCOPE"
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
    not_in_scope_items = [c.id for c in checks if c.status == "not_in_scope"]

    return {
        "engine_version": ENGINE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "challenge_id": challenge.get("challenge_id"),
        "package": package_name,
        "mode": mode,
        "result": result,
        "formal_promotion": formal_promotion,
        "challenge_genesis": genesis,
        "checks": [asdict(c) for c in checks],
        "open_obligations": open_items,
        "failed_obligations": failed_items,
        "blocked_obligations": blocked_items,
        "not_in_scope": not_in_scope_items,
        "challenge_definition": "Break the declared claim-to-evidence closure contract, not the prose used to label the target.",
        "claim_boundary": (
            "The result is relative to this declared challenge contract. target.statement is payload by default; "
            "unrestricted natural-language semantics are not evaluated unless a declared semantic adapter closes. "
            "Non-formal evidence is permitted in exploratory/adversarial modes, but it does not become a formal "
            "certificate without a passing formal adapter."
        ),
        "license_boundary": (
            "The Challenge protocol grants no additional copyright, patent, deployment, benchmarking, or other use rights. "
            "Repository use remains governed by LICENSE and any separate written challenge authorization."
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
        "semantic_default": "payload_only",
        "challenge_definition": "Break the declared claim-to-evidence closure contract, not natural-language prose.",
        "break_conditions": BREAK_CONDITIONS,
        "challenge_genesis": {
            "accepted_claims": 0,
            "parent": None,
            "rules_frozen": True,
            "hash_algorithm": "sha256",
        },
        "license_boundary": (
            "The protocol itself grants no use rights; repository use is governed by LICENSE and any separate written challenge authorization."
        ),
    }
