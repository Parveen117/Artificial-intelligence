#!/usr/bin/env python3
"""AI Native Coherence v2
======================

Root--Template--Phase coherence checker seed for AI outputs.

Concept:
- Root = core claim/invariant that must survive.
- Template = reasoning path or task schema.
- Phase = context/style/noise modulation.
- Seam ledger = lawful memory of unresolved residue.

This toy compares native_on vs native_off over synthetic claims.
No external dependencies.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class Config:
    samples: int = 512
    dim: int = 16
    template_noise: float = 0.14
    context_phase_noise: float = 0.20
    compensator: float = 0.35
    ledger: float = 0.65
    seed: int = 117
    out_dir: str = "ai_native_coherence_v2_pack"


def sha256_json(obj: Dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def bits(rng: random.Random, n: int) -> List[int]:
    return [rng.randrange(2) for _ in range(n)]


def agreement(a: List[int], b: List[int]) -> float:
    return sum(1 for x, y in zip(a, b) if x == y) / len(a)


def apply_template(root: List[int], template: List[int]) -> List[int]:
    return [r ^ t for r, t in zip(root, template)]


def mutate(rng: random.Random, xs: List[int], rate: float) -> List[int]:
    return [x ^ (1 if rng.random() < rate else 0) for x in xs]


def run_condition(cfg: Config, native_on: bool) -> Dict:
    rng = random.Random(cfg.seed)
    rows = []
    k_memory = 0.0

    for sample_id in range(1, cfg.samples + 1):
        root_claim = bits(rng, cfg.dim)
        reasoning_template = [1 if rng.random() < 0.25 else 0 for _ in range(cfg.dim)]
        lawful_answer = apply_template(root_claim, reasoning_template)

        template_drifted = mutate(rng, lawful_answer, cfg.template_noise)
        output = mutate(rng, template_drifted, cfg.context_phase_noise)

        raw_total = 0.0
        comp_total = 0.0
        ledger_total = 0.0
        open_total = 0.0
        repaired = []

        for lawful, observed in zip(lawful_answer, output):
            raw = observed - lawful
            raw_total += abs(raw)
            if native_on:
                comp = cfg.compensator * raw
                rest = raw - comp
                ledg = cfg.ledger * rest
                open_part = rest - ledg
                k_memory += ledg
                final = observed if abs(open_part) > 0.5 else lawful
            else:
                comp = 0.0
                ledg = 0.0
                open_part = raw
                final = observed
            comp_total += abs(comp)
            ledger_total += abs(ledg)
            open_total += abs(open_part)
            repaired.append(final)

        root_preservation = agreement(repaired, lawful_answer)
        hallucination_gap = 1.0 - root_preservation
        g_ugd = open_total / raw_total if raw_total else 0.0
        coherent = int(root_preservation >= 0.95 and g_ugd <= 0.25)

        rows.append({
            "sample_id": sample_id,
            "root_preservation": root_preservation,
            "hallucination_gap": hallucination_gap,
            "G_UGD_native": g_ugd,
            "raw_residue": raw_total,
            "seam_compensated": comp_total,
            "ledgered_memory": ledger_total,
            "open_residue": open_total,
            "k_memory": k_memory,
            "coherent": coherent,
        })

    keys = [k for k in rows[0] if k != "sample_id"]
    avg = {k: sum(row[k] for row in rows) / len(rows) for k in keys}
    return {"averages": avg, "rows": rows}


def write_csv(path: Path, condition: str, rows: List[Dict], cert: str) -> None:
    fields = ["condition", "certificate_hash"] + list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({"condition": condition, "certificate_hash": cert, **row})


def main() -> None:
    p = argparse.ArgumentParser(description="AI native coherence v2")
    p.add_argument("--samples", type=int, default=512)
    p.add_argument("--dim", type=int, default=16)
    p.add_argument("--template-noise", type=float, default=0.14)
    p.add_argument("--context-phase-noise", type=float, default=0.20)
    p.add_argument("--compensator", type=float, default=0.35)
    p.add_argument("--ledger", type=float, default=0.65)
    p.add_argument("--seed", type=int, default=117)
    p.add_argument("--out-dir", default="ai_native_coherence_v2_pack")
    cfg = Config(**vars(p.parse_args()))

    on = run_condition(cfg, True)
    off = run_condition(cfg, False)
    comparison = {
        "delta_root_preservation": on["averages"]["root_preservation"] - off["averages"]["root_preservation"],
        "delta_hallucination_gap": on["averages"]["hallucination_gap"] - off["averages"]["hallucination_gap"],
        "delta_G_UGD_native": on["averages"]["G_UGD_native"] - off["averages"]["G_UGD_native"],
        "delta_coherent_rate": on["averages"]["coherent"] - off["averages"]["coherent"],
        "native_ai_advantage": bool(
            on["averages"]["root_preservation"] > off["averages"]["root_preservation"]
            and on["averages"]["G_UGD_native"] < off["averages"]["G_UGD_native"]
        ),
    }
    report = {
        "marker": "AI-Native-Coherence-v2",
        "grammar": "Root claim -> Template reasoning -> Context phase -> Seam ledger closure",
        "config": asdict(cfg),
        "native_on": on,
        "native_off": off,
        "comparison": comparison,
    }
    report["certificate_hash"] = sha256_json(report)

    out = Path(cfg.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    write_csv(out / "native_on_rows.csv", "native_on", on["rows"], report["certificate_hash"])
    write_csv(out / "native_off_rows.csv", "native_off", off["rows"], report["certificate_hash"])
    (out / "SUMMARY.md").write_text(
        "# AI Native Coherence v2\n\n"
        f"Certificate hash: `{report['certificate_hash']}`\n\n"
        f"```json\n{json.dumps(comparison, indent=2)}\n```\n",
        encoding="utf-8",
    )
    print(json.dumps({"certificate_hash": report["certificate_hash"], "comparison": comparison}, indent=2))
    print("output_dir:", out)


if __name__ == "__main__":
    main()
