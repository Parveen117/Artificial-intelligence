#!/usr/bin/env python3
"""
ECL finality bridge for AI Trust Enablement.

This module turns AI recognition, repair, release, or retrieval-resolution
certificates into append-only finality commits.

It intentionally avoids importing the separate ECL repository at runtime. The
record shape mirrors the ECL/IEL idea: an external certificate becomes a state
transition with a proposal hash, commit hash, previous commit pointer, and
strictly positive entropy delta. That gives the AI service a deployable
integration path even when the ECL repo is not installed beside it.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

ZERO_HASH = "0" * 64
BRIDGE_VERSION = "AI-ECL-FINALITY-BRIDGE/v1"


@dataclass(frozen=True)
class ECLFinalityCommit:
    version: str
    bridge: str
    source_type: str
    source_engine: str
    certificate_hash: str
    payload_hash: str
    classification: str
    action: str
    prev_state_hash: str
    proposed_state_hash: str
    proposal_hash: str
    effect_units: int
    entropy_delta: int
    commit_hash: str
    ledger_path: str
    timestamp_unix: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def sha256_json(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


def is_hex64(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def entropy_delta_from_hash(hex_hash: str, tail_hex_digits: int = 6) -> int:
    """ECL/IEL-style positive entropy delta from a certificate hash."""
    if not is_hex64(hex_hash):
        raise ValueError("certificate hash must be a 64-character SHA-256 hex string")
    tail = int(hex_hash[-tail_hex_digits:], 16)
    return 1 + int(math.isqrt(abs(tail)))


def _atomic_append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = canonical_json(record) + "\n"
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


class ECLCommitAdapter:
    """Append-only finality adapter for AI Trust certificates."""

    def __init__(self, ledger_path: Optional[str | os.PathLike[str]] = None) -> None:
        selected = ledger_path or os.getenv("AI_TRUST_ECL_LEDGER_PATH", "ai_trust_ecl_finality_ledger.jsonl")
        self.ledger_path = Path(selected)

    def last_commit_hash(self) -> str:
        records = list(_iter_jsonl(self.ledger_path))
        if not records:
            return ZERO_HASH
        return str(records[-1]["commit"]["commit_hash"])

    def commit_certificate(
        self,
        certificate: Dict[str, Any],
        source_type: str = "AI_TRUST_CERTIFICATE",
        source_engine: Optional[str] = None,
    ) -> ECLFinalityCommit:
        if not isinstance(certificate, dict):
            raise ValueError("certificate must be a dictionary")

        payload_hash = sha256_json(certificate)
        certificate_hash = self._extract_certificate_hash(certificate, payload_hash)
        source_engine = source_engine or str(certificate.get("engine") or certificate.get("device", {}).get("engine") or "unknown-engine")
        classification = self._extract_classification(certificate)
        action = self._extract_action(certificate)

        prev_state_hash = self.last_commit_hash()
        proposed_state_hash = sha256_json({
            "bridge": BRIDGE_VERSION,
            "certificate_hash": certificate_hash,
            "payload_hash": payload_hash,
            "classification": classification,
            "action": action,
            "source_engine": source_engine,
        })
        effect_units = int(certificate_hash[-6:], 16)
        entropy_delta = entropy_delta_from_hash(certificate_hash)

        proposal = {
            "version": BRIDGE_VERSION,
            "source_type": source_type,
            "source_engine": source_engine,
            "prev_state_hash": prev_state_hash,
            "proposed_state_hash": proposed_state_hash,
            "effect_units": effect_units,
            "certificate_hash": certificate_hash,
            "payload_hash": payload_hash,
            "classification": classification,
            "action": action,
        }
        proposal_hash = sha256_json(proposal)
        timestamp_unix = int(time.time())
        commit_material = {
            "version": BRIDGE_VERSION,
            "prev_state_hash": prev_state_hash,
            "proposal_hash": proposal_hash,
            "proposed_state_hash": proposed_state_hash,
            "certificate_hash": certificate_hash,
            "entropy_delta": entropy_delta,
            "timestamp_unix": timestamp_unix,
        }
        commit_hash = sha256_json(commit_material)

        commit = ECLFinalityCommit(
            version="1.0.0",
            bridge=BRIDGE_VERSION,
            source_type=source_type,
            source_engine=source_engine,
            certificate_hash=certificate_hash,
            payload_hash=payload_hash,
            classification=classification,
            action=action,
            prev_state_hash=prev_state_hash,
            proposed_state_hash=proposed_state_hash,
            proposal_hash=proposal_hash,
            effect_units=effect_units,
            entropy_delta=entropy_delta,
            commit_hash=commit_hash,
            ledger_path=str(self.ledger_path),
            timestamp_unix=timestamp_unix,
        )

        _atomic_append_jsonl(self.ledger_path, {
            "proposal": proposal,
            "commit": commit.to_dict(),
        })
        return commit

    def status(self) -> Dict[str, Any]:
        records = list(_iter_jsonl(self.ledger_path))
        return {
            "bridge": BRIDGE_VERSION,
            "ledger_path": str(self.ledger_path),
            "commit_count": len(records),
            "last_commit_hash": records[-1]["commit"]["commit_hash"] if records else ZERO_HASH,
        }

    def verify(self) -> Dict[str, Any]:
        errors = []
        prev = ZERO_HASH
        records = list(_iter_jsonl(self.ledger_path))
        for index, record in enumerate(records, start=1):
            try:
                proposal = record["proposal"]
                commit = record["commit"]
                if commit["prev_state_hash"] != prev:
                    errors.append(f"entry {index}: prev_state_hash mismatch")
                expected_proposal_hash = sha256_json(proposal)
                if expected_proposal_hash != commit["proposal_hash"]:
                    errors.append(f"entry {index}: proposal_hash mismatch")
                expected_commit_hash = sha256_json({
                    "version": BRIDGE_VERSION,
                    "prev_state_hash": commit["prev_state_hash"],
                    "proposal_hash": commit["proposal_hash"],
                    "proposed_state_hash": commit["proposed_state_hash"],
                    "certificate_hash": commit["certificate_hash"],
                    "entropy_delta": commit["entropy_delta"],
                    "timestamp_unix": commit["timestamp_unix"],
                })
                if expected_commit_hash != commit["commit_hash"]:
                    errors.append(f"entry {index}: commit_hash mismatch")
                if int(commit["entropy_delta"]) <= 0:
                    errors.append(f"entry {index}: entropy_delta must be positive")
                prev = commit["commit_hash"]
            except Exception as exc:  # defensive verification boundary
                errors.append(f"entry {index}: malformed record: {exc}")
        return {
            "ok": not errors,
            "checked": len(records),
            "errors": errors,
            "last_commit_hash": prev if records else ZERO_HASH,
            "ledger_path": str(self.ledger_path),
        }

    @staticmethod
    def _extract_certificate_hash(certificate: Dict[str, Any], fallback: str) -> str:
        for key in ("certificate_hash", "release_hash", "repair_hash", "resolution_hash", "batch_hash"):
            value = certificate.get(key)
            if is_hex64(value):
                return str(value)
        return fallback

    @staticmethod
    def _extract_classification(certificate: Dict[str, Any]) -> str:
        if "recognition_state" in certificate:
            return str(certificate.get("recognition_state", {}).get("classification", "UNKNOWN"))
        if "release_action" in certificate:
            return str(certificate.get("release_action"))
        if "final_release_action" in certificate:
            return str(certificate.get("final_release_action"))
        if "fusion_decision" in certificate:
            return str(certificate.get("fusion_decision", {}).get("final_action", "UNKNOWN"))
        return "UNKNOWN"

    @staticmethod
    def _extract_action(certificate: Dict[str, Any]) -> str:
        if "technical_action" in certificate:
            return str(certificate.get("technical_action", {}).get("action", "UNKNOWN"))
        if "release_action" in certificate:
            return str(certificate.get("release_action"))
        if "final_release_action" in certificate:
            return str(certificate.get("final_release_action"))
        if "final_repair_action" in certificate:
            return str(certificate.get("final_repair_action"))
        return "UNKNOWN"


def commit_certificate_to_ecl(
    certificate: Dict[str, Any],
    source_type: str = "AI_TRUST_CERTIFICATE",
    ledger_path: Optional[str | os.PathLike[str]] = None,
) -> Dict[str, Any]:
    """Convenience function used by CLI, HTTP service, and tests."""
    return ECLCommitAdapter(ledger_path).commit_certificate(certificate, source_type=source_type).to_dict()
