#!/usr/bin/env python3
"""
Paninian Certificate Adapter
============================

Adds on-demand Paninian rule traces to claim-level verification reports.

This file intentionally sits beside the existing verifier rather than rewriting it.
It can be used by tests, CLIs, or the HTTP service to produce a richer certificate:
    claim result + derivation state + rule trace + support-vector hash
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import Any, Dict, List

try:
    from .panini_nyaya_claim_verifier import PaniniNyayaClaimVerifier, build_derivation_state, sha256_json
    from .paninian_meta_engine import compact_trace
except ImportError:
    from panini_nyaya_claim_verifier import PaniniNyayaClaimVerifier, build_derivation_state, sha256_json
    from paninian_meta_engine import compact_trace


def enrich_report(context: str, prompt: str, answer: str) -> Dict[str, Any]:
    verifier = PaniniNyayaClaimVerifier()
    report = asdict(verifier.verify(context, prompt, answer))
    enriched_claims: List[Dict[str, Any]] = []
    for claim in report["claim_results"]:
        state = build_derivation_state(claim["claim_text"])
        trace = compact_trace(state.marker_set, state.effect_tags, bool(claim.get("route_conflict")))
        enriched = dict(claim)
        enriched["derivation_state"] = asdict(state)
        enriched["paninian_rule_trace"] = trace
        enriched["trace_hash"] = sha256_json(trace)
        enriched_claims.append(enriched)
    report["claim_results"] = enriched_claims
    report["paninian_trace_count"] = sum(len(c["paninian_rule_trace"]) for c in enriched_claims)
    report["enriched_report_hash"] = sha256_json(report)
    return report


def demo() -> Dict[str, Any]:
    context = "The Eiffel Tower is located in Paris. It was completed in 1889. The tower is made of iron."
    prompt = "Answer using only the supplied context."
    answer = "The Eiffel Tower is located in Berlin. It was completed in 1789. The tower is made of wood."
    return enrich_report(context, prompt, answer)


def main() -> None:
    parser = argparse.ArgumentParser(description="Add Paninian rule traces to AI claim certificates")
    parser.add_argument("--context")
    parser.add_argument("--prompt", default="Answer using only the supplied context.")
    parser.add_argument("--answer")
    parser.add_argument("--out", default="paninian_enriched_certificate.json")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    if args.demo:
        result = demo()
    else:
        if not args.context or not args.answer:
            parser.error("--context and --answer are required unless --demo is used")
        result = enrich_report(args.context, args.prompt, args.answer)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
    print(json.dumps({"ok": True, "out": args.out, "hash": sha256_json(result)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
