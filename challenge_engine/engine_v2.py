#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import hashlib
import json
import math

ENGINE_VERSION = "1.2.0"
SCHEMA_VERSION = "1.0"

TERMINAL_RESULTS = {
    "OBSERVED", "ADVERSARIAL_PASS", "CERTIFIED", "INCOMPLETE", "FAILED",
    "INVALID", "BLOCKED_SCOPE", "SEMANTICS_NOT_IN_SCOPE",
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

OUTCOME_KEYS = {"status", "result", "outcome", "observed", "observed_value", "value", "metrics", "details"}


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
    if not isinstance(name, str) or not name.strip():
        raise ChallengeError("package must be a non-empty string")
    path = _package_dir() / f"{name}.json"
    if not path.exists():
        raise ChallengeError(f"unknown package: {name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("package") != name:
        raise ChallengeError(f"package manifest mismatch: {name}")
    return data


def _declaration_view(item: Any) -> Any:
    if isinstance(item, list):
        return [_declaration_view(x) for x in item]
    if not isinstance(item, dict):
        return item
    return {k: _declaration_view(v) for k, v in sorted(item.items()) if k not in OUTCOME_KEYS}


def _check_basic_structure(challenge: dict[str, Any], package: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    cid = challenge.get("challenge_id")
    if not isinstance(cid, str) or not cid.strip():
        checks.append(Check("challenge_id", "invalid", "challenge_id must be a non-empty string"))
    else:
        checks.append(Check("challenge_id", "pass", cid))

    if challenge.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
        checks.append(Check("schema_version", "invalid", f"expected {SCHEMA_VERSION}"))
    else:
        checks.append(Check("schema_version", "pass", SCHEMA_VERSION))

    target = challenge.get("target")
    if not isinstance(target, dict):
        checks.append(Check("target", "invalid", "target must be an object"))
    elif not isinstance(target.get("statement"), str) or not target.get("statement", "").strip():
        checks.append(Check("target", "invalid", "target.statement must be a non-empty string"))
    else:
        checks.append(Check("target", "pass", "declared before evaluation"))

    mode = challenge.get("mode", package.get("default_mode", "exploratory"))
    if not isinstance(mode, str) or mode not in package.get("allowed_modes", []):
        checks.append(Check("mode", "invalid", f"mode '{mode}' is not allowed by package"))
    else:
        checks.append(Check("mode", "pass", mode))

    for key in ("evidence", "obligations", "negative_controls"):
        value = challenge.get(key, [])
        if value is not None and not isinstance(value, list):
            checks.append(Check(f"{key}_shape", "invalid", f"{key} must be a list"))
        else:
            checks.append(Check(f"{key}_shape", "pass", f"{len(value or [])} entries"))

    for key in ("flow", "burden", "completion", "semantics", "threat_model", "scope", "formal_adapter", "semantic_adapter", "genesis"):
        if key in challenge and challenge[key] is not None and not isinstance(challenge[key], dict):
            checks.append(Check(f"{key}_shape", "invalid", f"{key} must be an object"))
    return checks


def _validate_obligations(challenge: dict[str, Any], package: dict[str, Any], mode: str) -> list[Check]:
    items = challenge.get("obligations", [])
    if not isinstance(items, list):
        return []
    checks: list[Check] = []
    seen: set[str] = set()
    status_map: dict[str, str] = {}
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            checks.append(Check(f"obligation_entry:{i}", "invalid", "obligation must be an object"))
            continue
        oid = item.get("id")
        status = item.get("status")
        if not isinstance(oid, str) or not oid.strip():
            checks.append(Check(f"obligation_entry:{i}", "invalid", "obligation.id must be a non-empty string"))
            continue
        if oid in seen:
            checks.append(Check(f"obligation_duplicate:{oid}", "invalid", "duplicate obligation id"))
            continue
        seen.add(oid)
        if status not in {"pass", "fail", "open"}:
            checks.append(Check(f"obligation:{oid}", "invalid", "status must be pass, fail, or open"))
            continue
        status_map[oid] = status

    for oid in package.get("required_obligations", {}).get(mode, []):
        status = status_map.get(oid)
        if status is None:
            checks.append(Check(f"obligation:{oid}", "open", "required obligation missing"))
        elif status == "pass":
            checks.append(Check(f"obligation:{oid}", "pass", "closed"))
        elif status == "fail":
            checks.append(Check(f"obligation:{oid}", "fail", "declared failure"))
        else:
            checks.append(Check(f"obligation:{oid}", "open", "not yet closed"))
    return checks


def _check_evidence(challenge: dict[str, Any], package: dict[str, Any], mode: str) -> list[Check]:
    items = challenge.get("evidence", [])
    if not isinstance(items, list):
        return []
    checks: list[Check] = []
    seen: set[str] = set()
    pass_count = 0
    formal_pass = 0
    nonformal_pass = 0
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            checks.append(Check(f"evidence_entry:{i}", "invalid", "evidence must be an object"))
            continue
        eid = item.get("id")
        status = item.get("status")
        if not isinstance(eid, str) or not eid.strip():
            checks.append(Check(f"evidence_entry:{i}", "invalid", "evidence.id must be a non-empty string"))
            continue
        if eid in seen:
            checks.append(Check(f"evidence_duplicate:{eid}", "invalid", "duplicate evidence id"))
            continue
        seen.add(eid)
        if status not in {"pass", "fail", "open"}:
            checks.append(Check(f"evidence:{eid}", "invalid", "evidence.status must be pass, fail, or open"))
            continue
        if "formal" in item and not isinstance(item.get("formal"), bool):
            checks.append(Check(f"evidence:{eid}", "invalid", "evidence.formal must be Boolean"))
            continue
        if status == "fail":
            checks.append(Check(f"evidence:{eid}", "fail", "evidence failed"))
        elif status == "open":
            checks.append(Check(f"evidence:{eid}", "open", "evidence unresolved"))
        else:
            checks.append(Check(f"evidence:{eid}", "pass", "evidence accepted by declared adapter/evaluator"))
            pass_count += 1
            if item.get("formal") is True:
                formal_pass += 1
            else:
                nonformal_pass += 1

    requires_evidence = "evidence" in package.get("required_obligations", {}).get(mode, [])
    if requires_evidence and pass_count == 0:
        checks.append(Check("evidence_presence", "open", "at least one passing evidence item is required"))
    else:
        checks.append(Check("evidence_presence", "pass", f"passing_evidence={pass_count}"))

    if mode == "certified" and formal_pass == 0:
        checks.append(Check("evidence_boundary", "open", "certified mode needs at least one passing formal support item"))
    else:
        checks.append(Check("evidence_boundary", "pass", f"formal_support={formal_pass}, nonformal_support={nonformal_pass}"))
    return checks


def _check_negative_controls(challenge: dict[str, Any], mode: str) -> list[Check]:
    if mode not in {"adversarial", "certified"}:
        return []
    items = challenge.get("negative_controls", [])
    if not isinstance(items, list) or not items:
        return [Check("negative_controls", "open", "at least one negative control is required")]
    checks: list[Check] = []
    seen: set[str] = set()
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            checks.append(Check(f"negative_control:{i}", "invalid", "negative control must be an object"))
            continue
        cid = item.get("id")
        status = item.get("status")
        if not isinstance(cid, str) or not cid.strip():
            checks.append(Check(f"negative_control:{i}", "invalid", "negative-control id must be non-empty"))
            continue
        if cid in seen:
            checks.append(Check(f"negative_control_duplicate:{cid}", "invalid", "duplicate negative-control id"))
            continue
        seen.add(cid)
        if status == "pass":
            checks.append(Check(f"negative_control:{cid}", "pass", "invalid/mutated case was detected"))
        elif status == "fail":
            checks.append(Check(f"negative_control:{cid}", "fail", "negative control escaped detection"))
        elif status == "open":
            checks.append(Check(f"negative_control:{cid}", "open", "negative control unresolved"))
        else:
            checks.append(Check(f"negative_control:{cid}", "invalid", "status must be pass, fail, or open"))
    return checks


def _check_scope(challenge: dict[str, Any], package: dict[str, Any]) -> Check | None:
    if not package.get("requires_authorization", False):
        return None
    scope = challenge.get("scope")
    if not isinstance(scope, dict):
        return Check("scope_authorization", "blocked", "authorized scope is required by this package")
    if scope.get("authorization") != "declared":
        return Check("scope_authorization", "blocked", "scope.authorization must equal 'declared'")
    target = scope.get("target")
    if not isinstance(target, str) or not target.strip():
        return Check("scope_authorization", "blocked", "scope.target must be a non-empty string")
    return Check("scope_authorization", "pass", f"declared for {target}")


def _check_threat_model(challenge: dict[str, Any], mode: str) -> Check | None:
    if mode == "exploratory":
        return None
    model = challenge.get("threat_model")
    if not isinstance(model, dict):
        return Check("threat_model", "open", "adversarial/certified mode requires a declared threat model")
    goal = model.get("goal")
    conditions = model.get("break_conditions")
    if not isinstance(goal, str) or not goal.strip():
        return Check("threat_model", "open", "threat_model.goal must be a non-empty string")
    if not isinstance(conditions, list) or not conditions:
        return Check("threat_model", "open", "threat_model.break_conditions must be a non-empty list")
    if len({json.dumps(x, sort_keys=True) for x in conditions}) != len(conditions):
        return Check("threat_model", "invalid", "duplicate break condition")
    bad = [c for c in conditions if not isinstance(c, str) or c not in BREAK_CONDITIONS]
    if bad:
        return Check("threat_model", "invalid", f"unknown break condition(s): {bad}")
    return Check("threat_model", "pass", f"goal fixed; break_conditions={','.join(conditions)}")


def _check_semantics(challenge: dict[str, Any]) -> Check:
    semantics = challenge.get("semantics", {"mode": "payload_only"})
    if not isinstance(semantics, dict):
        return Check("semantic_scope", "invalid", "semantics must be an object")
    mode = semantics.get("mode", "payload_only")
    if mode == "payload_only":
        return Check("semantic_scope", "pass", "target.statement is payload/label; unrestricted natural-language semantics are not inferred")
    if mode != "adapter_declared":
        return Check("semantic_scope", "invalid", "semantics.mode must be payload_only or adapter_declared")
    adapter = challenge.get("semantic_adapter")
    if not isinstance(adapter, dict):
        return Check("semantic_scope", "not_in_scope", "semantic interpretation requested without semantic_adapter")
    aid = adapter.get("id")
    if not isinstance(aid, str) or not aid.strip():
        return Check("semantic_scope", "invalid", "semantic_adapter.id is required")
    status = adapter.get("status")
    if status == "pass":
        return Check("semantic_scope", "pass", f"semantic adapter closed: {aid}")
    if status == "fail":
        return Check("semantic_scope", "fail", f"semantic adapter failed: {aid}")
    return Check("semantic_scope", "not_in_scope", f"semantic adapter has not closed: {aid}")


def _check_formal_promotion(challenge: dict[str, Any], package: dict[str, Any], mode: str) -> Check | None:
    if mode != "certified":
        return None
    if not package.get("certification_requires_formal_adapter", True):
        return Check("formal_adapter", "pass", "package does not require a formal adapter")
    adapter = challenge.get("formal_adapter")
    if not isinstance(adapter, dict):
        return Check("formal_adapter", "open", "certified mode requires formal_adapter")
    aid = adapter.get("id")
    if not isinstance(aid, str) or not aid.strip():
        return Check("formal_adapter", "invalid", "formal_adapter.id must be non-empty")
    status = adapter.get("status")
    if status == "pass":
        return Check("formal_adapter", "pass", aid)
    if status == "fail":
        return Check("formal_adapter", "fail", "formal adapter failed")
    if status == "open" or status is None:
        return Check("formal_adapter", "open", "formal adapter has not closed")
    return Check("formal_adapter", "invalid", "formal_adapter.status must be pass, fail, or open")


def _check_flow(challenge: dict[str, Any]) -> list[Check]:
    if "flow" not in challenge:
        return []
    flow = challenge.get("flow")
    if not isinstance(flow, dict):
        return []
    enabled = flow.get("enabled", False)
    if not isinstance(enabled, bool):
        return [Check("flow:enabled", "invalid", "flow.enabled must be Boolean")]
    if not enabled:
        return []
    probes = flow.get("probes")
    if not isinstance(probes, list) or not probes:
        return [Check("flow:probes", "open", "flow enabled but no probes supplied")]
    checks: list[Check] = []
    parsed: list[tuple[int, bool]] = []
    seen_orders: set[int] = set()
    for i, item in enumerate(probes):
        if not isinstance(item, dict):
            checks.append(Check(f"flow:probe:{i}", "invalid", "probe must be an object"))
            continue
        order = item.get("order")
        visible = item.get("target_visible")
        if not isinstance(order, int) or isinstance(order, bool) or order < 0:
            checks.append(Check(f"flow:probe:{i}", "invalid", "probe.order must be a nonnegative integer"))
            continue
        if order in seen_orders:
            checks.append(Check(f"flow:probe:{order}", "invalid", "duplicate probe order"))
            continue
        seen_orders.add(order)
        if not isinstance(visible, bool):
            checks.append(Check(f"flow:probe:{order}", "invalid", "target_visible must be explicitly Boolean"))
            continue
        parsed.append((order, visible))
    parsed.sort()
    if parsed:
        seen_visible = False
        monotone = True
        for _, visible in parsed:
            if seen_visible and not visible:
                monotone = False
            seen_visible = seen_visible or visible
        checks.append(Check("flow:recognition_monotonicity", "pass" if monotone else "fail", "visibility is monotone" if monotone else "target visibility reverted at higher order"))
        visible_orders = [o for o, v in parsed if v]
        declared_first = flow.get("first_recognition_order")
        if declared_first is not None and (not isinstance(declared_first, int) or isinstance(declared_first, bool) or declared_first < 0):
            checks.append(Check("flow:first_recognition_order", "invalid", "first_recognition_order must be a nonnegative integer"))
        elif visible_orders:
            actual = min(visible_orders)
            if declared_first is None:
                checks.append(Check("flow:first_recognition_order", "open", f"observed first visible order is {actual}"))
            elif declared_first == actual:
                checks.append(Check("flow:first_recognition_order", "pass", str(actual)))
            else:
                checks.append(Check("flow:first_recognition_order", "fail", f"declared {declared_first}, observed {actual}"))
        elif declared_first is not None:
            checks.append(Check("flow:first_recognition_order", "fail", "declared recognition without a visible probe"))
    bilateral = flow.get("bilateral")
    if bilateral is not None:
        if not isinstance(bilateral, dict):
            checks.append(Check("flow:bilateral", "invalid", "bilateral must be an object"))
        else:
            defect, tol = bilateral.get("defect"), bilateral.get("tolerance")
            if not _is_number(defect) or not _is_number(tol) or float(tol) < 0:
                checks.append(Check("flow:bilateral_defect", "invalid", "finite defect and nonnegative tolerance are required"))
            elif abs(float(defect)) <= float(tol):
                checks.append(Check("flow:bilateral_defect", "pass", f"|defect| <= {tol}"))
            else:
                checks.append(Check("flow:bilateral_defect", "fail", f"|defect|={abs(float(defect))} > {tol}"))
    if "remainder_bound" in flow:
        rb = flow.get("remainder_bound")
        if not _is_number(rb) or float(rb) < 0:
            checks.append(Check("flow:remainder_bound", "invalid", "remainder_bound must be a nonnegative finite number"))
        else:
            checks.append(Check("flow:remainder_bound", "pass", str(rb)))
    return checks


def _check_burden(challenge: dict[str, Any]) -> Check | None:
    if "burden" not in challenge:
        return None
    burden = challenge.get("burden")
    if not isinstance(burden, dict):
        return None
    beta = burden.get("beta")
    threshold = burden.get("threshold", 1.0)
    if not _is_number(beta) or float(beta) < 0:
        return Check("burden", "invalid", "beta must be a nonnegative finite number")
    if not _is_number(threshold) or float(threshold) <= 0:
        return Check("burden", "invalid", "threshold must be a positive finite number")
    reserve = float(threshold) - float(beta)
    if reserve > 0:
        return Check("burden", "pass", f"beta={beta}; strict reserve={reserve}")
    if reserve == 0:
        return Check("burden", "open", f"beta={beta}; boundary saturation")
    return Check("burden", "fail", f"beta={beta} exceeds threshold={threshold}")


def _check_completion(challenge: dict[str, Any]) -> Check | None:
    if "completion" not in challenge:
        return None
    completion = challenge.get("completion")
    if not isinstance(completion, dict):
        return None
    enabled = completion.get("enabled", False)
    if not isinstance(enabled, bool):
        return Check("completion", "invalid", "completion.enabled must be Boolean")
    if not enabled:
        return None
    u, e = completion.get("finite_upper"), completion.get("completion_error")
    threshold = completion.get("threshold", 1.0)
    if not _is_number(u):
        return Check("completion", "open", "finite_upper is required")
    if float(u) < 0:
        return Check("completion", "invalid", "finite_upper must be nonnegative")
    if not _is_number(e):
        return Check("completion", "open", "completion_error is required; finite result alone cannot promote")
    if float(e) < 0:
        return Check("completion", "invalid", "completion_error must be nonnegative")
    if not _is_number(threshold) or float(threshold) <= 0:
        return Check("completion", "invalid", "threshold must be a positive finite number")
    worst = float(u) + float(e)
    margin = float(threshold) - worst
    if margin > 0:
        return Check("completion", "pass", f"finite_upper + error = {worst}; reserve={margin}")
    if margin == 0:
        return Check("completion", "open", f"worst-case bound reaches threshold {threshold}")
    return Check("completion", "fail", f"worst-case bound {worst} exceeds threshold {threshold}")


def _genesis_payload(challenge: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
    mode = challenge.get("mode", package.get("default_mode", "exploratory"))
    semantics = challenge.get("semantics") if isinstance(challenge.get("semantics"), dict) else {"mode": "payload_only"}
    flow = challenge.get("flow") if isinstance(challenge.get("flow"), dict) else {}
    burden = challenge.get("burden") if isinstance(challenge.get("burden"), dict) else None
    completion = challenge.get("completion") if isinstance(challenge.get("completion"), dict) else {}
    bilateral = flow.get("bilateral") if isinstance(flow.get("bilateral"), dict) else None
    evidence_refs = []
    for x in challenge.get("evidence", []) if isinstance(challenge.get("evidence", []), list) else []:
        if isinstance(x, dict):
            ref = {k: x[k] for k in ("id", "type", "formal", "sha256", "hash", "ref", "source") if k in x}
            evidence_refs.append(ref)
    evidence_refs.sort(key=lambda x: json.dumps(x, sort_keys=True, default=str))
    obligations = [_declaration_view(x) for x in challenge.get("obligations", []) if isinstance(x, dict)] if isinstance(challenge.get("obligations", []), list) else []
    controls = [_declaration_view(x) for x in challenge.get("negative_controls", []) if isinstance(x, dict)] if isinstance(challenge.get("negative_controls", []), list) else []
    obligations.sort(key=lambda x: json.dumps(x, sort_keys=True, default=str))
    controls.sort(key=lambda x: json.dumps(x, sort_keys=True, default=str))
    formal_adapter = _declaration_view(challenge.get("formal_adapter")) if isinstance(challenge.get("formal_adapter"), dict) else None
    semantic_adapter = _declaration_view(challenge.get("semantic_adapter")) if isinstance(challenge.get("semantic_adapter"), dict) else None
    flow_enabled = flow.get("enabled", False) if isinstance(flow.get("enabled", False), bool) else flow.get("enabled")
    completion_enabled = completion.get("enabled", False) if isinstance(completion.get("enabled", False), bool) else completion.get("enabled")
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
        "declared_obligations": obligations,
        "negative_controls": controls,
        "evidence_refs": evidence_refs,
        "formal_adapter": formal_adapter,
        "semantic_adapter": semantic_adapter,
        "gates": {
            "flow_enabled": flow_enabled,
            "first_recognition_order": flow.get("first_recognition_order") if flow_enabled is True else None,
            "bilateral_declared": bilateral is not None,
            "bilateral_tolerance": bilateral.get("tolerance") if bilateral else None,
            "burden_required": burden is not None,
            "burden_threshold": burden.get("threshold", 1.0) if burden is not None else None,
            "completion_enabled": completion_enabled,
            "completion_threshold": completion.get("threshold", 1.0) if completion_enabled is True else None,
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
    expected = pin.get("expected_hash")
    if not isinstance(expected, str) or not expected.strip():
        return Check("genesis_integrity", "invalid", "genesis.expected_hash must be non-empty")
    actual = genesis["genesis_hash"]
    if expected.strip().lower() == actual:
        return Check("genesis_integrity", "pass", actual)
    return Check("genesis_integrity", "fail", f"expected {expected.strip().lower()}, computed {actual}")


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
    challenge.setdefault("semantics", {"mode": "payload_only"})
    genesis = _challenge_genesis(challenge, package)

    checks = _check_basic_structure(challenge, package)
    scope = _check_scope(challenge, package)
    if scope: checks.append(scope)
    threat = _check_threat_model(challenge, mode)
    if threat: checks.append(threat)
    checks.append(_check_semantics(challenge))
    checks.extend(_validate_obligations(challenge, package, mode))
    checks.extend(_check_evidence(challenge, package, mode))
    checks.extend(_check_negative_controls(challenge, mode))
    formal = _check_formal_promotion(challenge, package, mode)
    if formal: checks.append(formal)
    checks.extend(_check_flow(challenge))
    burden = _check_burden(challenge)
    if burden: checks.append(burden)
    completion = _check_completion(challenge)
    if completion: checks.append(completion)
    genesis_check = _check_genesis_pin(challenge, genesis)
    if genesis_check: checks.append(genesis_check)

    statuses = [c.status for c in checks]
    if "invalid" in statuses:
        result = "INVALID"
    elif "blocked" in statuses:
        result = "BLOCKED_SCOPE"
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

    return {
        "engine_version": ENGINE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "challenge_id": challenge.get("challenge_id"),
        "package": package_name,
        "mode": mode,
        "result": result,
        "formal_promotion": result == "CERTIFIED",
        "challenge_genesis": genesis,
        "checks": [asdict(c) for c in checks],
        "open_obligations": [c.id for c in checks if c.status == "open"],
        "failed_obligations": [c.id for c in checks if c.status == "fail"],
        "blocked_obligations": [c.id for c in checks if c.status == "blocked"],
        "invalid_contract_fields": [c.id for c in checks if c.status == "invalid"],
        "not_in_scope": [c.id for c in checks if c.status == "not_in_scope"],
        "challenge_definition": "Break the declared claim-to-evidence closure contract, not the prose used to label the target.",
        "claim_boundary": "The result is relative to the declared challenge contract. target.statement is payload by default; unrestricted natural-language semantics are not evaluated unless a declared semantic adapter closes. Non-formal evidence may support exploratory/adversarial evaluation but cannot by itself produce CERTIFIED.",
        "input_trust_boundary": "The engine checks closure over supplied evaluator/adapter outputs. Authenticity of external evidence and adapter outputs is the package/connector responsibility unless separately authenticated; a participant's self-asserted status is not real-world proof.",
        "license_boundary": "The Challenge protocol grants no additional copyright, patent, deployment, benchmarking, or other use rights. Repository use remains governed by LICENSE and any separate written challenge authorization.",
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
        "challenge_genesis": {"accepted_claims": 0, "parent": None, "rules_frozen": True, "hash_algorithm": "sha256"},
        "input_trust_boundary": "Closure is evaluated over supplied evaluator/adapter outputs; external authenticity is a package/connector responsibility unless separately authenticated.",
        "license_boundary": "The protocol itself grants no use rights; repository use is governed by LICENSE and any separate written challenge authorization.",
    }
