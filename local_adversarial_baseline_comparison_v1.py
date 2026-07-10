#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from ai_trust_enablement.fusion_certificate_engine import FusionCertificateEngine
from local_baseline_comparison import naive_similarity_action


def main() -> None:
    cases = json.loads(Path("local_adversarial_cases_v1.json").read_text(encoding="utf-8"))
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
                model_id="adversarial-baseline-comparison-v1",
            )
        )

        fusion_action = fusion["fusion_decision"]["final_action"]

        rows.append({
            "case_id": case["case_id"],
            "expected_family": expected,
            "naive_action": naive["action"],
            "naive_score": naive["score"],
            "naive_ok": naive["action"] in expected,
            "fusion_action": fusion_action,
            "fusion_risk": fusion["fusion_decision"]["final_risk"],
            "fusion_ok": fusion_action in expected,
        })

    naive_pass = sum(1 for r in rows if r["naive_ok"])
    fusion_pass = sum(1 for r in rows if r["fusion_ok"])

    summary = {
        "suite": "adversarial_baseline_comparison_v1",
        "case_count": len(rows),
        "naive_pass": naive_pass,
        "naive_fail": len(rows) - naive_pass,
        "fusion_pass": fusion_pass,
        "fusion_fail": len(rows) - fusion_pass,
        "rows": rows,
    }

    out_dir = Path("local_adversarial_baseline_outputs_v1")
    out_dir.mkdir(exist_ok=True)

    summary_path = out_dir / "adversarial_baseline_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8"
    )

    lines = [
        "# Adversarial Baseline Comparison v1",
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

    report_path = out_dir / "adversarial_baseline_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print()
    print("ADVERSARIAL BASELINE COMPARISON V1")
    print("=" * 96)
    print(f"Naive token baseline: {naive_pass}/{len(rows)}")
    print(f"Fusion engine:        {fusion_pass}/{len(rows)}")
    print("-" * 96)

    for r in rows:
        marker = "GAIN" if (not r["naive_ok"] and r["fusion_ok"]) else ""
        miss = "FUSION_FAIL" if not r["fusion_ok"] else ""

        print(
            f"{r['case_id'][:36]:36} "
            f"naive={r['naive_action'][:22]:22} ok={str(r['naive_ok']):5} "
            f"fusion={r['fusion_action'][:22]:22} ok={str(r['fusion_ok']):5} "
            f"{marker} {miss}"
        )

    print()
    print("Summary:", summary_path)
    print("Report:", report_path)


if __name__ == "__main__":
    main()
