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
from challenge_engine.action_gate import ACTION_CANONICALIZATION
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
        require(
            manifest.get("self_red_team_audit") == "red_team_challenge/SELF_RED_TEAM_AUDIT.md",
            "public release must bind the pre-public self-red-team audit",
        )
        require(
            manifest.get("action_canonicalization") == ACTION_CANONICALIZATION,
            "manifest action canonicalization does not match the executable validator",
        )

        for required in [
            "red_team_challenge/README.md",
            "red_team_challenge/CHALLENGE_AUTHORIZATION.md",
            "red_team_challenge/SUBMISSION_SPEC.md",
            "red_team_challenge/submission.schema.json",
            "red_team_challenge/verify_submission.py",
            "red_team_challenge/SELF_RED_TEAM_AUDIT.md",
            "challenge_engine/tests/test_proof_before_action_self_red_team.py",
            "challenge_engine/tests/test_proof_before_action_external_red_team.py",
        ]:
            repo_file(required, "required_launch_file")

        critical = manifest.get("critical_git_blob_sha1")
        require(isinstance(critical, dict) and len(critical) >= 6, "critical engine blob pins are incomplete")
        for relative, expected in critical.items():
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

        authority = challenge.get("action_authorization", {}) if isinstance(challenge, dict) else {}
        state = authority.get("committed_state", {}) if isinstance(authority, dict) else {}
        require(isinstance(state, dict) and bool(state.get("used_request_nonces")),
                "public replay_escape track is inert: baseline used-nonce set is empty")
        require(authority.get("confirmation_required") is True,
                "public confirmation track is inert: confirmation_required is not true")
        require(isinstance(authority.get("approval"), dict),
                "public confirmation track is inert: baseline approval is missing")

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
        require(isinstance(evidence, dict), "published_internal_evidence must be an object")
        require(evidence.get("directed_core_cases") == 15, "directed-case evidence drift")
        require(evidence.get("deterministic_hostile_mutations") == 20000, "mutation-count evidence drift")
        require(evidence.get("mutation_classes") == 20, "mutation-class evidence drift")
        require(evidence.get("full_regression_tests") == 159, "pre-external regression count drift")
        require(evidence.get("self_red_team_test_methods") == 14, "self-red-team method count drift")
        require(evidence.get("external_red_team_test_methods") == 8, "external red-team method count drift")
        require(evidence.get("combined_regression_tests") == 167, "combined regression count drift")
        require(evidence.get("external_pre_repair_failures") == 8,
                "external pre-repair failure count must remain disclosed")
        require(evidence.get("external_post_repair_failures") == 0,
                "external post-repair failures must be zero for release")
        require(evidence.get("deterministic_decimal_alias_probes") == 1500, "decimal-alias campaign count drift")
        require(evidence.get("pre_fix_unauthorized_admit_reproductions") == 3,
                "pre-fix unauthorized-ADMIT reproduction count must remain disclosed")
        require(evidence.get("pre_fix_numeric_alias_root_causes") == 2,
                "pre-fix numeric-alias root-cause count drift")
        require(evidence.get("pre_fix_genesis_boundary_defects") == 1,
                "pre-fix Genesis-boundary defect count drift")
        require(evidence.get("unauthorized_admit") == 0,
                "post-repair evidence must not contain an unauthorized ADMIT")

        output = {
            "result": "RNKE_RED_TEAM_RELEASE_CHECK_PASS",
            "release_status": release_status,
            "challenge_id": manifest["challenge_id"],
            "engine_subject_commit": manifest["engine_subject_commit"],
            "action_canonicalization": ACTION_CANONICALIZATION,
            "baseline_result": result.get("result"),
            "baseline_action_decision": result.get("action_decision"),
            "baseline_action_executable": result.get("action_executable"),
            "baseline_genesis_sha256": genesis,
            "manifest_genesis_pin": pin,
            "genesis_pin_required_before_public_release": pin == "PENDING_CI_PIN",
            "critical_blob_count": len(critical),
            "combined_regression_tests": evidence["combined_regression_tests"],
            "external_red_team_tests": evidence["external_red_team_test_methods"],
            "decimal_alias_probes": evidence["deterministic_decimal_alias_probes"],
            "pre_fix_unauthorized_admit_reproductions": evidence["pre_fix_unauthorized_admit_reproductions"],
            "post_fix_unauthorized_admit": evidence["unauthorized_admit"],
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
