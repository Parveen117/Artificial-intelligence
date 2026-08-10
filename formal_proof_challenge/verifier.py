#!/usr/bin/env python3
"""Deterministic finite-calculus verifier for the Formal Proof Gate.

The verifier intentionally accepts only a small typed grammar. Unknown syntax is
rejected as PARSE_NOT_ADMITTED instead of being guessed into a proof.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

VERSION = "1.0.0"
RULE_SET_ID = "formal-proof-gate-finite-calculus-v1"
ALLOWED_RULES = (
    "ASSUMPTION",
    "ARITHMETIC_EVAL",
    "EQ_SYMMETRY",
    "EQ_TRANSITIVITY",
    "AND_INTRO",
    "AND_ELIM_LEFT",
    "AND_ELIM_RIGHT",
    "MODUS_PONENS",
)


class ProofSyntaxError(ValueError):
    """Raised when input lies outside the declared proof grammar."""


@dataclass(frozen=True)
class VerificationError:
    code: str
    message: str
    step_id: Optional[str] = None


@dataclass(frozen=True)
class ProofCertificate:
    version: str
    engine: str
    rule_set_id: str
    rule_set_hash: str
    proof_id: str
    proof_hash: str
    dependency_graph_hash: str
    admitted_syntax: bool
    dependency_graph_acyclic: bool
    all_steps_licensed: bool
    conclusion_step: Optional[str]
    target_match: bool
    status: str
    error_count: int
    errors: Tuple[Dict[str, Any], ...]
    certificate_hash: str


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def normalize_term(value: Any) -> Dict[str, Any]:
    if isinstance(value, bool):
        raise ProofSyntaxError("boolean is not an arithmetic term")
    if isinstance(value, int):
        return {"op": "const", "value": value}
    if isinstance(value, str):
        name = value.strip()
        if not name:
            raise ProofSyntaxError("empty variable name")
        return {"op": "var", "name": name}
    if not isinstance(value, Mapping):
        raise ProofSyntaxError("term must be an integer, variable, or mapping")
    op = str(value.get("op", ""))
    if op == "const":
        raw = value.get("value")
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise ProofSyntaxError("const value must be an integer")
        return {"op": "const", "value": raw}
    if op == "var":
        name = str(value.get("name", "")).strip()
        if not name:
            raise ProofSyntaxError("var name is empty")
        return {"op": "var", "name": name}
    if op == "neg":
        return {"op": "neg", "arg": normalize_term(value.get("arg"))}
    if op in {"add", "sub", "mul"}:
        return {
            "op": op,
            "left": normalize_term(value.get("left")),
            "right": normalize_term(value.get("right")),
        }
    raise ProofSyntaxError(f"unsupported term operator: {op or '<missing>'}")


def normalize_formula(value: Any) -> Dict[str, Any]:
    if isinstance(value, str):
        name = value.strip()
        if not name:
            raise ProofSyntaxError("empty atom name")
        return {"op": "atom", "name": name}
    if not isinstance(value, Mapping):
        raise ProofSyntaxError("formula must be an atom name or mapping")
    op = str(value.get("op", ""))
    if op == "atom":
        name = str(value.get("name", "")).strip()
        if not name:
            raise ProofSyntaxError("atom name is empty")
        return {"op": "atom", "name": name}
    if op in {"eq", "lt", "le"}:
        return {
            "op": op,
            "left": normalize_term(value.get("left")),
            "right": normalize_term(value.get("right")),
        }
    if op == "not":
        return {"op": "not", "arg": normalize_formula(value.get("arg"))}
    if op in {"and", "or", "implies"}:
        return {
            "op": op,
            "left": normalize_formula(value.get("left")),
            "right": normalize_formula(value.get("right")),
        }
    raise ProofSyntaxError(f"unsupported formula operator: {op or '<missing>'}")


def evaluate_closed_term(term: Mapping[str, Any]) -> int:
    op = term["op"]
    if op == "const":
        return int(term["value"])
    if op == "var":
        raise ProofSyntaxError("ARITHMETIC_EVAL requires closed terms without variables")
    if op == "neg":
        return -evaluate_closed_term(term["arg"])
    left = evaluate_closed_term(term["left"])
    right = evaluate_closed_term(term["right"])
    if op == "add":
        return left + right
    if op == "sub":
        return left - right
    if op == "mul":
        return left * right
    raise ProofSyntaxError(f"cannot evaluate term operator {op}")


def normalize_step(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ProofSyntaxError("each step must be a mapping")
    step_id = str(raw.get("id", "")).strip()
    if not step_id:
        raise ProofSyntaxError("step id is empty")
    rule = str(raw.get("rule", "")).strip().upper()
    if rule not in ALLOWED_RULES:
        raise ProofSyntaxError(f"unsupported proof rule: {rule or '<missing>'}")
    premises_raw = raw.get("premises", [])
    if not isinstance(premises_raw, list) or any(not isinstance(x, str) or not x.strip() for x in premises_raw):
        raise ProofSyntaxError(f"step {step_id} premises must be a list of nonempty step ids")
    return {
        "id": step_id,
        "rule": rule,
        "premises": [x.strip() for x in premises_raw],
        "conclusion": normalize_formula(raw.get("conclusion")),
    }


def normalize_proof(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ProofSyntaxError("proof must be a mapping")
    proof_id = str(raw.get("proof_id", "")).strip()
    if not proof_id:
        raise ProofSyntaxError("proof_id is empty")
    version = str(raw.get("version", VERSION)).strip()
    if version != VERSION:
        raise ProofSyntaxError(f"unsupported proof version: {version}")
    assumptions_raw = raw.get("assumptions", [])
    if not isinstance(assumptions_raw, list):
        raise ProofSyntaxError("assumptions must be a list")
    steps_raw = raw.get("steps", [])
    if not isinstance(steps_raw, list) or not steps_raw:
        raise ProofSyntaxError("steps must be a nonempty list")
    conclusion_step = str(raw.get("conclusion_step", "")).strip()
    if not conclusion_step:
        raise ProofSyntaxError("conclusion_step is empty")
    return {
        "version": VERSION,
        "proof_id": proof_id,
        "rule_set": RULE_SET_ID,
        "assumptions": [normalize_formula(x) for x in assumptions_raw],
        "target": normalize_formula(raw.get("target")),
        "steps": [normalize_step(x) for x in steps_raw],
        "conclusion_step": conclusion_step,
    }


def _dependency_graph(steps: Sequence[Mapping[str, Any]]) -> Dict[str, List[str]]:
    return {str(step["id"]): list(step["premises"]) for step in steps}


def _topological_order(graph: Mapping[str, Sequence[str]]) -> Tuple[List[str], bool]:
    visiting: set[str] = set()
    visited: set[str] = set()
    order: List[str] = []
    acyclic = True

    def visit(node: str) -> None:
        nonlocal acyclic
        if node in visited:
            return
        if node in visiting:
            acyclic = False
            return
        visiting.add(node)
        for premise in graph.get(node, ()):
            if premise in graph:
                visit(premise)
        visiting.remove(node)
        visited.add(node)
        order.append(node)

    for node in graph:
        visit(node)
    return order, acyclic


def _eq(left: Any, right: Any) -> bool:
    return canonical_json(left) == canonical_json(right)


def _license_rule(
    step: Mapping[str, Any],
    premise_formulas: Sequence[Mapping[str, Any]],
    assumptions: Sequence[Mapping[str, Any]],
) -> Optional[str]:
    rule = step["rule"]
    conclusion = step["conclusion"]

    if rule == "ASSUMPTION":
        if premise_formulas:
            return "ASSUMPTION accepts no premises"
        if not any(_eq(conclusion, assumption) for assumption in assumptions):
            return "conclusion is not one of the declared assumptions"
        return None

    if rule == "ARITHMETIC_EVAL":
        if premise_formulas:
            return "ARITHMETIC_EVAL accepts no premises"
        if conclusion["op"] not in {"eq", "lt", "le"}:
            return "ARITHMETIC_EVAL conclusion must be eq, lt, or le"
        try:
            left = evaluate_closed_term(conclusion["left"])
            right = evaluate_closed_term(conclusion["right"])
        except ProofSyntaxError as exc:
            return str(exc)
        valid = {"eq": left == right, "lt": left < right, "le": left <= right}[conclusion["op"]]
        return None if valid else f"closed arithmetic statement is false: {left} {conclusion['op']} {right}"

    if rule == "EQ_SYMMETRY":
        if len(premise_formulas) != 1:
            return "EQ_SYMMETRY requires one premise"
        premise = premise_formulas[0]
        expected = {"op": "eq", "left": premise.get("right"), "right": premise.get("left")} if premise.get("op") == "eq" else None
        if expected is None or not _eq(conclusion, expected):
            return "conclusion is not the symmetric equality of the premise"
        return None

    if rule == "EQ_TRANSITIVITY":
        if len(premise_formulas) != 2:
            return "EQ_TRANSITIVITY requires two premises"
        first, second = premise_formulas
        if first.get("op") != "eq" or second.get("op") != "eq":
            return "EQ_TRANSITIVITY premises must be equalities"
        if not _eq(first["right"], second["left"]):
            return "middle equality terms do not match"
        expected = {"op": "eq", "left": first["left"], "right": second["right"]}
        return None if _eq(conclusion, expected) else "conclusion is not the transitive equality"

    if rule == "AND_INTRO":
        if len(premise_formulas) != 2:
            return "AND_INTRO requires two premises"
        expected = {"op": "and", "left": premise_formulas[0], "right": premise_formulas[1]}
        return None if _eq(conclusion, expected) else "conclusion is not the conjunction of the premises"

    if rule in {"AND_ELIM_LEFT", "AND_ELIM_RIGHT"}:
        if len(premise_formulas) != 1:
            return f"{rule} requires one premise"
        premise = premise_formulas[0]
        if premise.get("op") != "and":
            return f"{rule} premise must be a conjunction"
        side = "left" if rule == "AND_ELIM_LEFT" else "right"
        return None if _eq(conclusion, premise[side]) else f"conclusion is not the {side} conjunct"

    if rule == "MODUS_PONENS":
        if len(premise_formulas) != 2:
            return "MODUS_PONENS requires two premises"
        implication = next((p for p in premise_formulas if p.get("op") == "implies"), None)
        if implication is None:
            return "one MODUS_PONENS premise must be an implication"
        antecedent_candidates = [p for p in premise_formulas if p is not implication]
        if len(antecedent_candidates) != 1 or not _eq(antecedent_candidates[0], implication["left"]):
            return "the non-implication premise does not match the implication antecedent"
        return None if _eq(conclusion, implication["right"]) else "conclusion does not match the implication consequent"

    return f"unimplemented rule: {rule}"


def verify_proof(raw: Any) -> ProofCertificate:
    syntax_errors: List[VerificationError] = []
    try:
        proof = normalize_proof(raw)
        admitted_syntax = True
    except (ProofSyntaxError, KeyError, TypeError) as exc:
        proof = None
        admitted_syntax = False
        syntax_errors.append(VerificationError("PARSE_NOT_ADMITTED", str(exc)))

    rule_set_hash = digest({"rule_set_id": RULE_SET_ID, "rules": ALLOWED_RULES, "version": VERSION})
    if proof is None:
        unsigned = {
            "version": VERSION,
            "engine": "FormalProofGate",
            "rule_set_id": RULE_SET_ID,
            "rule_set_hash": rule_set_hash,
            "proof_id": str(raw.get("proof_id", "UNKNOWN")) if isinstance(raw, Mapping) else "UNKNOWN",
            "proof_hash": digest(raw),
            "dependency_graph_hash": digest({}),
            "admitted_syntax": False,
            "dependency_graph_acyclic": False,
            "all_steps_licensed": False,
            "conclusion_step": None,
            "target_match": False,
            "status": "REJECTED",
            "error_count": len(syntax_errors),
            "errors": tuple(asdict(error) for error in syntax_errors),
        }
        return ProofCertificate(certificate_hash=digest(unsigned), **unsigned)

    errors: List[VerificationError] = []
    step_ids = [step["id"] for step in proof["steps"]]
    duplicates = sorted({step_id for step_id in step_ids if step_ids.count(step_id) > 1})
    for step_id in duplicates:
        errors.append(VerificationError("DUPLICATE_STEP_ID", f"duplicate step id: {step_id}", step_id))

    step_map = {step["id"]: step for step in proof["steps"]}
    graph = _dependency_graph(proof["steps"])
    for step in proof["steps"]:
        for premise in step["premises"]:
            if premise not in step_map:
                errors.append(VerificationError("MISSING_PREMISE", f"premise {premise} is not a declared step", step["id"]))
    order, acyclic = _topological_order(graph)
    if not acyclic:
        errors.append(VerificationError("CIRCULAR_DEPENDENCY", "dependency graph contains a directed cycle"))

    licensed: Dict[str, bool] = {}
    formulas: Dict[str, Mapping[str, Any]] = {}
    if acyclic and not duplicates:
        for step_id in order:
            step = step_map[step_id]
            premises_available = all(premise in formulas and licensed.get(premise, False) for premise in step["premises"])
            if not premises_available and step["premises"]:
                errors.append(VerificationError("UNLICENSED_PREMISE", "one or more premises are missing or were not licensed", step_id))
                licensed[step_id] = False
                formulas[step_id] = step["conclusion"]
                continue
            premise_formulas = [formulas[premise] for premise in step["premises"]]
            problem = _license_rule(step, premise_formulas, proof["assumptions"])
            if problem is None:
                licensed[step_id] = True
            else:
                code = {"ASSUMPTION": "UNSUPPORTED_LEMMA", "ARITHMETIC_EVAL": "ARITHMETIC_MISMATCH"}.get(step["rule"], "RULE_APPLICATION_MISMATCH")
                errors.append(VerificationError(code, problem, step_id))
                licensed[step_id] = False
            formulas[step_id] = step["conclusion"]

    conclusion_step = proof["conclusion_step"]
    if conclusion_step not in step_map:
        errors.append(VerificationError("MISSING_CONCLUSION_STEP", f"conclusion_step {conclusion_step} is not a declared step"))
        target_match = False
    else:
        target_match = _eq(step_map[conclusion_step]["conclusion"], proof["target"])
        if not target_match:
            errors.append(VerificationError("TARGET_MISMATCH", "declared conclusion step does not equal the target formula", conclusion_step))
        if not licensed.get(conclusion_step, False):
            errors.append(VerificationError("CONCLUSION_NOT_LICENSED", "declared conclusion step was not licensed", conclusion_step))

    all_steps_licensed = bool(step_map) and all(licensed.get(step_id, False) for step_id in step_map)
    status = "VALID_PROOF" if admitted_syntax and acyclic and all_steps_licensed and target_match and not errors else "REJECTED"
    unsigned = {
        "version": VERSION,
        "engine": "FormalProofGate",
        "rule_set_id": RULE_SET_ID,
        "rule_set_hash": rule_set_hash,
        "proof_id": proof["proof_id"],
        "proof_hash": digest(proof),
        "dependency_graph_hash": digest(graph),
        "admitted_syntax": admitted_syntax,
        "dependency_graph_acyclic": acyclic,
        "all_steps_licensed": all_steps_licensed,
        "conclusion_step": conclusion_step,
        "target_match": target_match,
        "status": status,
        "error_count": len(errors),
        "errors": tuple(asdict(error) for error in errors),
    }
    return ProofCertificate(certificate_hash=digest(unsigned), **unsigned)


def tamper_one_step(raw: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a deterministic one-step tamper fixture without mutating the input."""
    proof = copy.deepcopy(dict(raw))
    steps = proof.get("steps", [])
    for step in steps:
        if str(step.get("rule", "")).upper() == "ARITHMETIC_EVAL":
            conclusion = step.get("conclusion", {})
            if isinstance(conclusion, MutableMapping) and conclusion.get("op") == "eq":
                right = conclusion.get("right")
                if isinstance(right, int):
                    conclusion["right"] = right + 1
                    proof["tamper_note"] = f"incremented right side of {step.get('id')}"
                    return proof
                if isinstance(right, MutableMapping) and right.get("op") == "const" and isinstance(right.get("value"), int):
                    right["value"] += 1
                    proof["tamper_note"] = f"incremented right constant of {step.get('id')}"
                    return proof
    if steps:
        steps[0]["rule"] = "UNDECLARED_RULE"
        proof["tamper_note"] = f"replaced rule of {steps[0].get('id')}"
    return proof


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a finite formal proof and emit a deterministic certificate")
    parser.add_argument("proof", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--tamper", action="store_true", help="tamper one step before verification")
    args = parser.parse_args()
    raw = load_json(args.proof)
    if args.tamper:
        raw = tamper_one_step(raw)
    certificate = asdict(verify_proof(raw))
    rendered = json.dumps(certificate, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if certificate["status"] == "VALID_PROOF" else 2


if __name__ == "__main__":
    raise SystemExit(main())
