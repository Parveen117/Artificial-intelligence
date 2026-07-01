from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List

from .service_contract import ENDPOINTS, SERVICE_NAME, SERVICE_VERSION, version_payload


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass
class ClosureItem:
    kind: str
    path: str
    expected: Any
    observed: Any
    level: str


@dataclass
class ClosureReport:
    engine: str
    version: str
    status: str
    item_count: int
    items: List[Dict[str, Any]]
    basis: Dict[str, str]
    report_hash: str


class RNKEClosureEngine:
    version = "1.1.0"
    name = "RNKEClosureEngine"

    FAIL_KEYS = (
        "contract_fail",
        "closure_fail",
        "smoke_fail",
        "benchmark_fail",
        "repair_fail",
        "resolution_fail",
        "release_fail",
        "release_api_fail",
        "resolution_api_fail",
        "adversarial_fail",
    )

    def check_service(self, health: Dict[str, Any], version_doc: Dict[str, Any]) -> ClosureReport:
        items: List[ClosureItem] = []
        self._cmp(items, "health.service", SERVICE_NAME, health.get("service"), "SERVICE_NAME_MISMATCH")
        self._cmp(items, "health.version", SERVICE_VERSION, health.get("version"), "SERVICE_VERSION_MISMATCH")
        self._cmp(items, "version", version_payload(), version_doc, "VERSION_PAYLOAD_MISMATCH")
        observed_eps = list(version_doc.get("endpoints", []))
        expected_eps = list(ENDPOINTS)
        missing = [x for x in expected_eps if x not in observed_eps]
        extra = [x for x in observed_eps if x not in expected_eps]
        if missing:
            items.append(ClosureItem("ENDPOINT_MISSING", "version.endpoints", missing, [], "HIGH"))
        if extra:
            items.append(ClosureItem("ENDPOINT_EXTRA", "version.endpoints", [], extra, "MEDIUM"))
        return self._report(items, {"health": stable_hash(health), "version_doc": stable_hash(version_doc), "contract": stable_hash(version_payload())})

    def check_summary(self, summary: Dict[str, Any]) -> ClosureReport:
        items: List[ClosureItem] = []
        if summary.get("ok") is not True:
            items.append(ClosureItem("SUMMARY_NOT_OK", "ok", True, summary.get("ok"), "HIGH"))
        for key in self.FAIL_KEYS:
            if key in summary and int(summary.get(key, 0) or 0) != 0:
                items.append(ClosureItem("LAYER_FAIL_COUNT", key, 0, summary.get(key), "HIGH"))
        if summary.get("compile_ok") is False:
            items.append(ClosureItem("COMPILE_OPEN", "compile_ok", True, False, "HIGH"))
        if summary.get("contract_ok") is False:
            items.append(ClosureItem("CONTRACT_OPEN", "contract_ok", True, False, "HIGH"))
        if summary.get("closure_ok") is False:
            items.append(ClosureItem("CLOSURE_OPEN", "closure_ok", True, False, "HIGH"))
        if summary.get("ledger_chain_ok") is False:
            items.append(ClosureItem("LEDGER_CHAIN", "ledger_chain_ok", True, False, "HIGH"))
        return self._report(items, {"summary": stable_hash(summary)})

    def _cmp(self, items: List[ClosureItem], path: str, expected: Any, observed: Any, kind: str) -> None:
        if expected != observed:
            items.append(ClosureItem(kind, path, expected, observed, "HIGH"))

    def _report(self, items: List[ClosureItem], basis: Dict[str, str]) -> ClosureReport:
        rows = [asdict(item) for item in items]
        status = "CLOSED" if not rows else "SEAM_RESIDUE"
        payload = {"engine": self.name, "version": self.version, "status": status, "items": rows, "basis": basis}
        return ClosureReport(self.name, self.version, status, len(rows), rows, basis, stable_hash(payload))
