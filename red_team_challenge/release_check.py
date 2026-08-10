#!/usr/bin/env python3
"""Fail-closed release audit for the RNKE public red-team launch package."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from challenge_engine.engine import evaluate_challenge
from challenge_engine.strict_json import StrictJSONError, loads_strict

MANIFEST = ROOT / "red_team_challenge" / "CHALLENGE_MANIFEST.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ReleaseError(ValueError):
    pass


def load(path: Path) -> Any:
    try:
        return loads_strict(path.read_text(encoding="utf-8"))
    except (OSError, StrictJSONError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"cannot load {path}: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReleaseError(message)


def repo_file(value: Any, field: str) -> Path:
    require(isinstance(value, str) and value and "\\" not in value, f"{field} must be a repository-relative POSIX path")
    path = (ROOT / value).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ReleaseError(f"{field} escapes repository root") from exc
    require(path.is_file(), f"missing required file: {value}")
    return path


def git_blob_sha1(path: Path) -> str:
    completed = subprocess.run(
        ["git", "hash-object", str(path)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    require(completed.returncode == 0, f"git hash-object failed for {path}: {completed.stderr.strip()}")
    digest = completed.stdout.strip()
    require(HEX40.fullmatch(digest) is not None, f"invalid git blob digest for {path}")
    return digest


def main() -> int:
    try:
        manifest = load(MANIFEST)
        require(isinstance(manifest, dict), "challenge manifest must be an object")
        require(manifest.get("schema_version") == "1.0", "unsupported challenge manifest schema")
        require(manifest.get("challenge_id") == "rnke-proof-before-action-red-team-v1", "unexpected challenge id")
        require(manifest.get("protocol") == "proof-before-action-v1", "unexpected Proof-Before-Action protocol")
        require(HEX40.fullmatch(str(manifest.get("engine_subject_commit", ""))) is not None, "invalid engine subject commit")
        require(manifest.get("no_bounty_promised") is True, "v1 must not imply an undeclared bounty")

        for required in [
            "red_team_challenge/README.md",
            "red_team_challenge/CHALLENGE_AUTHORIZATION.md",
            "red_team_challenge/SUBMISSION_SPEC.md",
            "red_team_challenge/submission.schema.json",
            "red_team_challenge/verify_submission.py",
        ]:
            repo_file(required, "required_launch_file")

        for relative, expected in manifest.get("critical_git_blob_sha1", {}).items():
            require(isinstance(expected, str) and HEX40.fullmatch(expected) is not None,
                    f"invalid manifest blob pin for {relative}")
            observed = git_blob_sha1(repo_file(relative, "critical_git_blob_sha1"))
            require(observed == expected, f"critical engine blob drift: {relative}: {observed} != {expected}")

        fixture = repo_file(manifest.get("baseline_fixture"), "baseline_fixture")
        challenge = load(fixture)
        result = evaluate_challenge(challenge)
        require(isinstance(result, dict), "Challenge Engine returned a non-object baseline result")
        expected = manifest.get("baseline_expected", {})
        require(result.get("result") == expected.get("result"), "baseline result class drift")
        require(result.get("action_decision") == expected.get("action_decision"), "baseline action decision drift")
        require(result.get("action_executable") is expected.get("action_executable"), "baseline executable flag drift")
        genesis = result.get("challenge_genesis", {}).get("genesis_hash")
        require(isinstance(genesis, str) and HEX64.fullmatch(genesis) is not None, "baseline Genesis is not a SHA-256 digest")

        release_status = manifest.get("release_status")
        pin = manifest.get("pinned_genesis_sha256")
        require(release_status in {"release_candidate", "ready_for_public_release"}, "invalid release status")
        if release_status == "ready_for_public_release":
            require(isinstance(pin, str) and HEX64.fullmatch(pin) is not None, "release has no valid Genesis pin")
            require(pin == genesis, "published Genesis pin does not match the baseline")
        else:
            require(pin == "PENDING_CI_PIN" or (isinstance(pin, str) and HEX64.fullmatch(pin) is not None),
                    "release-candidate Genesis pin is malformed")
            if pin != "PENDING_CI_PIN":
                require(pin == genesis, "candidate Genesis pin does not match the baseline")

        evidence = manifest.get("published_internal_evidence", {})
        require(evidence.get("directed_core_cases") == 15, "directed-case evidence drift")
        require(evidence.get("deterministic_hostile_mutations") == 20000, "mutation-count evidence drift")
        require(evidence.get("unauthorized_admit") == 0, "internal evidence must not claim an unauthorized ADMIT")

        output = {
            "result": "RNKE_RED_TEAM_RELEASE_CHECK_PASS",
            "release_status": release_status,
            "challenge_id": manifest["challenge_id"],
            "engine_subject_commit": manifest["engine_subject_commit"],
            "baseline_result": result.get("result"),
            "baseline_action_decision": result.get("action_decision"),
            "baseline_action_executable": result.get("action_executable"),
            "baseline_genesis_sha256": genesis,
            "manifest_genesis_pin": pin,
            "genesis_pin_required_before_public_release": pin == "PENDING_CI_PIN",
            "critical_blob_count": len(manifest.get("critical_git_blob_sha1", {})),
        }
        print(json.dumps(output, sort_keys=True))
        print(f"RNKE_RED_TEAM_BASELINE_GENESIS={genesis}")
        return 0
    except ReleaseError as exc:
        print(json.dumps({"result": "RNKE_RED_TEAM_RELEASE_CHECK_FAIL", "error": str(exc)}, sort_keys=True))
        return 1
    except Exception as exc:
        print(json.dumps({"result": "RNKE_RED_TEAM_RELEASE_CHECK_ERROR", "error": f"{type(exc).__name__}: {exc}"}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
