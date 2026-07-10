#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Set

from ai_trust_enablement.fusion_certificate_engine import FusionCertificateEngine


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "in", "into", "is", "it", "its", "of", "on", "or", "that", "the",
    "this", "to", "was", "were", "with", "which", "who", "will", "can", "may",
    "must", "should", "using", "only", "supplied", "context", "answer", "also",
}


def tokens(text: str) -> Set[str]:
    out = set()
    for raw in str(text or "").lower().replace(".", " ").replace(",", " ").split():
        tok = "".join(ch for ch in raw if ch.isalnum() or ch in {"_", "-"})
        if tok and tok not in STOPWORDS:
            out.add(tok)
    return out


def jaccard(a: str, b: str) -> float:
    ta = tokens(a)
    tb = tokens(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def naive_similarity_action(context: str, answer: str) -> Dict[str, Any]:
    score = jaccard(context, answer)
    if not context.strip():
        action = "REGENERATE_WITH_EVIDENCE"
    elif score >= 0.45:
        action = "COMMIT"
    elif score >= 0.25:
        action = "REVIEW"
    else:
        action = "RETRIEVE_MORE_EVIDENCE"
    return {
        "baseline": "naive_token_jaccard",
        "score": score,
        "action": action,
    }


def is_safe_action_for_case(action: str, expected_family: List[str]) -> bool:
    return action in expected_family


def main() -> None:
    cases = json.loads(Path("local_benchmark_cases.json").read_text(encoding="utf-8"))
    engine = FusionCertificateEngine()

    rows = []

    for case in cases:
        expected = case["expected_action_family"]
        naive = naive_similarity_action(case["context"], case["answer"])
        fusion = asdict(
            engine.evaluate(
                context=case["context"],
                prompt=case.get("prompt", "Answer using only the supplied context."),
                answer=case["answer"],
                model_id="baseline-comparison",
            )
        )
        fusion_action = fusion["fusion_decision"]["final_action"]

        rows.append({
            "case_id": case["case_id"],
            "expected_family": expected,
            "naive_action": naive["action"],
            "naive_score": naive["score"],
            "naive_ok": is_safe_action_for_case(naive["action"], expected),
            "fusion_action": fusion_action,
            "fusion_risk": fusion["fusion_decision"]["final_risk"],
            "fusion_ok": is_safe_action_for_case(fusion_action, expected),
        })

    naive_pass = sum(1 for r in rows if r["naive_ok"])
    fusion_pass = sum(1 for r in rows if r["fusion_ok"])

    summary = {
        "suite": "baseline_comparison_v1",
        "case_count": len(rows),
        "naive_pass": naive_pass,
        "naive_fail": len(rows) - naive_pass,
        "fusion_pass": fusion_pass,
        "fusion_fail": len(rows) - fusion_pass,
        "rows": rows,
    }

    out_dir = Path("local_baseline_outputs")
    out_dir.mkdir(exist_ok=True)

    (out_dir / "baseline_comparison_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "# Baseline Comparison v1",
        "",
        f"Cases: {len(rows)}",
        f"Naive token baseline: {naive_pass}/{len(rows)}",
        f"Fusion engine: {fusion_pass}/{len(rows)}",
        "",
        "| Case | Naive Action | Naive OK | Naive Score | Fusion Action | Fusion OK | Fusion Risk |",
        "|---|---|---:|---:|---|---:|---:|",
    ]

    for r in rows:
        lines.append(
            f"| {r['case_id']} | {r['naive_action']} | {r['naive_ok']} | "
            f"{r['naive_score']:.3f} | {r['fusion_action']} | {r['fusion_ok']} | {r['fusion_risk']:.3f} |"
        )

    (out_dir / "baseline_comparison_report.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print("\nBASELINE COMPARISON V1")
    print("=" * 88)
    print(f"Naive token baseline: {naive_pass}/{len(rows)}")
    print(f"Fusion engine:        {fusion_pass}/{len(rows)}")
    print("-" * 88)
    for r in rows:
        marker = "GAIN" if (not r["naive_ok"] and r["fusion_ok"]) else ""
        print(
            f"{r['case_id'][:32]:32} "
            f"naive={r['naive_action'][:22]:22} ok={str(r['naive_ok']):5} "
            f"fusion={r['fusion_action'][:22]:22} ok={str(r['fusion_ok']):5} {marker}"
        )


if __name__ == "__main__":
    main()
