#!/usr/bin/env python3
"""Reproduce and structurally validate an RNKE red-team submission.

This verifier can establish that a submitted candidate deterministically produces
an executable ADMIT under the pinned Challenge Genesis. It cannot decide the
normative question of whether the frozen authority contract actually authorizes
the candidate; that remains an independent adjudication obligation.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from challenge_engine.engine import evaluate_challenge
from challenge_engine.strict_json import StrictJSONError, loads_strict

MANIFEST_PATH = ROOT / "red_team_challenge" / "CHALLENGE_MANIFEST.json"
SAFETY_TEXT = (
    "I used only the authorized local synthetic challenge scope and included "
    "no secrets, personal data, or real-world side effects."
)
CORE_BREAK_CLASSES = {
    "unauthorized_admit",
    "replay_escape",
    "delegation_escape",
    "genesis_integrity_escape",
    "negative_control_escape",
    "parser_or_canonicalization_escape",
}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SUBMISSION_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")


class SubmissionError(ValueError):
    pass


def load_json(path: Path) -> Any:
    try:
        return loads_strict(path.read_text(encoding="utf-8"))
    except (OSError, StrictJSONError, json.JSONDecodeError) as exc:
        raise SubmissionError(f"cannot load strict JSON {path}: {exc}") from exc


def canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise SubmissionError(f"value is not canonical JSON: {exc}") from exc


def repo_path(value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise SubmissionError(f"{field} must be a non-empty repository-relative POSIX path")
    candidate = (ROOT / value).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise SubmissionError(f"{field} escapes the repository root") from exc
    if not candidate.is_file():
        raise SubmissionError(f"{field} does not identify a file: {value}")
    return candidate


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SubmissionError(message)


def validate_shape(data: Any) -> dict[str, Any]:
    require(isinstance(data, dict), "submission must be a JSON object")
    required = {
        "schema_version",
        "submission_id",
        "participant",
        "engine_subject_commit",
        "challenge_file",
        "observed_output_file",
        "pinned_genesis_sha256",
        "claimed_break_class",
        "authorization_argument",
        "reproduction_command",
        "environment",
        "safety_acknowledgement",
    }
    allowed = required | {"evidence", "notes"}
    require(required <= data.keys(), f"missing required fields: {sorted(required - data.keys())}")
    require(set(data) <= allowed, f"unknown fields: {sorted(set(data) - allowed)}")
    require(data["schema_version"] == "1.0", "schema_version must be 1.0")
    require(isinstance(data["submission_id"], str) and SUBMISSION_ID.fullmatch(data["submission_id"]) is not None,
            "submission_id must match ^[a-z0-9][a-z0-9._-]{2,63}$")

    participant = data["participant"]
    require(isinstance(participant, dict), "participant must be an object")
    require(set(participant) <= {"handle", "contact", "credit_name"}, "participant contains unknown fields")
    require(isinstance(participant.get("handle"), str) and 2 <= len(participant["handle"]) <= 80,
            "participant.handle must contain 2..80 characters")

    require(isinstance(data["engine_subject_commit"], str) and HEX40.fullmatch(data["engine_subject_commit"]) is not None,
            "engine_subject_commit must be a lowercase 40-hex commit")
    require(isinstance(data["pinned_genesis_sha256"], str) and HEX64.fullmatch(data["pinned_genesis_sha256"]) is not None,
            "pinned_genesis_sha256 must be a lowercase 64-hex digest")
    require(data["claimed_break_class"] in CORE_BREAK_CLASSES, "claimed_break_class is not a published v1 class")
    require(isinstance(data["authorization_argument"], str) and 50 <= len(data["authorization_argument"]) <= 12000,
            "authorization_argument must contain 50..12000 characters")
    require(isinstance(data["reproduction_command"], str) and 10 <= len(data["reproduction_command"]) <= 2000,
            "reproduction_command must contain 10..2000 characters")

    environment = data["environment"]
    require(isinstance(environment, dict), "environment must be an object")
    require(set(environment) <= {"python", "os", "architecture", "container"}, "environment contains unknown fields")
    require(isinstance(environment.get("python"), str) and len(environment["python"]) >= 3,
            "environment.python is required")
    require(isinstance(environment.get("os"), str) and len(environment["os"]) >= 2,
            "environment.os is required")
    require(data["safety_acknowledgement"] == SAFETY_TEXT, "safety acknowledgement does not match the authorized scope")

    evidence = data.get("evidence", [])
    require(isinstance(evidence, list) and len(evidence) <= 50, "evidence must be an array with at most 50 items")
    for index, item in enumerate(evidence):
        require(isinstance(item, dict) and set(item) == {"kind", "value"},
                f"evidence[{index}] must contain exactly kind and value")
        require(isinstance(item["kind"], str) and item["kind"], f"evidence[{index}].kind is required")
        require(isinstance(item["value"], str) and item["value"], f"evidence[{index}].value is required")
    return data


def baseline_result(manifest: dict[str, Any]) -> dict[str, Any]:
    fixture = repo_path(manifest.get("baseline_fixture"), "manifest.baseline_fixture")
    challenge = load_json(fixture)
    result = evaluate_challenge(challenge)
    require(isinstance(result, dict), "Challenge Engine returned a non-object baseline result")
    return result


def self_test() -> int:
    manifest = load_json(MANIFEST_PATH)
    require(isinstance(manifest, dict), "challenge manifest must be an object")
    result = baseline_result(manifest)
    expected = manifest.get("baseline_expected", {})
    require(result.get("result") == expected.get("result"), "baseline result class drift")
    require(result.get("action_decision") == expected.get("action_decision"), "baseline action decision drift")
    require(result.get("action_executable") is expected.get("action_executable"), "baseline executable flag drift")
    genesis = result.get("challenge_genesis", {}).get("genesis_hash")
    require(isinstance(genesis, str) and HEX64.fullmatch(genesis) is not None, "baseline Genesis is not a SHA-256 digest")
    pin = manifest.get("pinned_genesis_sha256")
    if pin != "PENDING_CI_PIN":
        require(genesis == pin, "baseline Genesis does not match the launch pin")
    print(json.dumps({
        "result": "SELF_TEST_PASS",
        "baseline_result": result.get("result"),
        "action_decision": result.get("action_decision"),
        "action_executable": result.get("action_executable"),
        "baseline_genesis_sha256": genesis,
        "manifest_pin": pin,
    }, sort_keys=True))
    return 0


def verify(submission_path: Path, require_break_candidate: bool) -> int:
    manifest = load_json(MANIFEST_PATH)
    require(isinstance(manifest, dict), "challenge manifest must be an object")
    pin = manifest.get("pinned_genesis_sha256")
    require(isinstance(pin, str) and HEX64.fullmatch(pin) is not None,
            "public launch Genesis is not pinned; submissions are not yet open")

    submission = validate_shape(load_json(submission_path))
    require(submission["engine_subject_commit"] == manifest.get("engine_subject_commit"),
            "submission targets a different engine subject commit")
    require(submission["pinned_genesis_sha256"] == pin,
            "submission does not target the published Challenge Genesis")

    challenge_path = repo_path(submission["challenge_file"], "challenge_file")
    observed_path = repo_path(submission["observed_output_file"], "observed_output_file")
    challenge = load_json(challenge_path)
    observed = load_json(observed_path)
    fresh = evaluate_challenge(challenge)
    require(isinstance(fresh, dict), "Challenge Engine returned a non-object result")
    require(canonical(fresh) == canonical(observed), "observed output does not reproduce exactly")

    fresh_genesis = fresh.get("challenge_genesis", {}).get("genesis_hash")
    require(fresh_genesis == pin, "candidate evaluates under a different Challenge Genesis")
    is_admit = fresh.get("action_decision") == "ADMIT" and fresh.get("action_executable") is True
    if require_break_candidate:
        require(is_admit, "candidate does not reproduce executable ADMIT")

    classification = "REPRODUCIBLE_ADMIT_CANDIDATE" if is_admit else "REPRODUCIBLE_NON_ADMIT"
    output = {
        "result": classification,
        "submission_id": submission["submission_id"],
        "claimed_break_class": submission["claimed_break_class"],
        "challenge_genesis_sha256": fresh_genesis,
        "action_decision": fresh.get("action_decision"),
        "action_executable": fresh.get("action_executable"),
        "challenge_result": fresh.get("result"),
        "manual_authorization_adjudication_required": True,
        "meaning": (
            "The candidate output reproduced under the pinned Genesis. A maintainer must still prove that the frozen authority contract does not authorize it."
        ),
    }
    print(json.dumps(output, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and reproduce an RNKE red-team submission")
    parser.add_argument("submission", nargs="?", help="path to submission.json")
    parser.add_argument("--require-break-candidate", action="store_true", help="fail unless the candidate reproduces executable ADMIT")
    parser.add_argument("--self-test", action="store_true", help="evaluate the official baseline and challenge manifest")
    args = parser.parse_args()
    try:
        if args.self_test:
            return self_test()
        if not args.submission:
            parser.error("submission path is required unless --self-test is used")
        path = Path(args.submission)
        if not path.is_absolute():
            path = (ROOT / path).resolve()
        return verify(path, args.require_break_candidate)
    except SubmissionError as exc:
        print(json.dumps({"result": "INVALID_SUBMISSION", "error": str(exc)}, sort_keys=True))
        return 4
    except Exception as exc:  # fail closed without hiding unexpected validator defects
        print(json.dumps({"result": "VALIDATOR_ERROR", "error": f"{type(exc).__name__}: {exc}"}, sort_keys=True))
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
