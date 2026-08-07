#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .engine import ChallengeError, ENGINE_VERSION, capabilities, evaluate_challenge
    from .strict_json import StrictJSONError, loads_strict
except ImportError:
    from engine import ChallengeError, ENGINE_VERSION, capabilities, evaluate_challenge
    from strict_json import StrictJSONError, loads_strict

EXIT = {
    "OBSERVED": 0,
    "ADVERSARIAL_PASS": 0,
    "CERTIFIED": 0,
    "INCOMPLETE": 2,
    "FAILED": 3,
    "INVALID": 4,
    "BLOCKED_SCOPE": 5,
    "SEMANTICS_NOT_IN_SCOPE": 6,
}


def read_input(path: str) -> dict:
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    return loads_strict(text)


def main() -> int:
    p = argparse.ArgumentParser(description="Evaluate a declared challenge contract using the local Challenge Engine.")
    p.add_argument("challenge", nargs="?", help="challenge JSON path, or '-' for stdin")
    p.add_argument("--capabilities", action="store_true", help="print machine-readable capabilities and exit")
    p.add_argument("--compact", action="store_true", help="emit compact JSON")
    args = p.parse_args()
    if args.capabilities:
        print(json.dumps(capabilities(), indent=None if args.compact else 2, sort_keys=True))
        return 0
    if not args.challenge:
        p.error("challenge path or '-' is required unless --capabilities is used")
    try:
        result = evaluate_challenge(read_input(args.challenge))
    except (OSError, json.JSONDecodeError, StrictJSONError, ChallengeError, ValueError) as exc:
        result = {"engine_version": ENGINE_VERSION, "result": "INVALID", "error": str(exc)}
    print(json.dumps(result, indent=None if args.compact else 2, sort_keys=True, allow_nan=False))
    return EXIT.get(result.get("result", "INVALID"), 4)


if __name__ == "__main__":
    raise SystemExit(main())
