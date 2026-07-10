#!/usr/bin/env python3
"""
Demo: evaluate an AI answer and seal the resulting recognition certificate into
the local ECL-style finality ledger.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

try:
    from .ai_hallucination_recognition_engine import AIHallucinationRecognitionEngine
    from .ecl_commit_adapter import ECLCommitAdapter
except ImportError:
    from ai_hallucination_recognition_engine import AIHallucinationRecognitionEngine
    from ecl_commit_adapter import ECLCommitAdapter


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate an answer and commit its certificate to the ECL-style finality ledger")
    parser.add_argument("--context", default="The Eiffel Tower is located in Paris. It was completed in 1889. The tower is made of iron.")
    parser.add_argument("--prompt", default="Answer using only the supplied context.")
    parser.add_argument("--answer", default="The Eiffel Tower is located in Berlin. It was completed in 1789 and is made of wood.")
    parser.add_argument("--model-id", default="ecl-finality-demo")
    parser.add_argument("--ledger", default="ai_trust_ecl_finality_demo_ledger.jsonl")
    parser.add_argument("--out", default="ai_trust_ecl_finality_demo_result.json")
    args = parser.parse_args()

    certificate = asdict(AIHallucinationRecognitionEngine().evaluate(
        reference_text=args.context,
        prompt_text=args.prompt,
        answer_text=args.answer,
        model_id=args.model_id,
    ))
    adapter = ECLCommitAdapter(args.ledger)
    commit = adapter.commit_certificate(certificate, source_type="AI_RECOGNITION_CERTIFICATE").to_dict()
    result = {
        "recognition_certificate": certificate,
        "ecl_finality_commit": commit,
        "ecl_finality_verify": adapter.verify(),
    }

    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "out": args.out,
        "classification": certificate["recognition_state"]["classification"],
        "action": certificate["technical_action"]["action"],
        "commit_hash": commit["commit_hash"],
        "ledger": commit["ledger_path"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
