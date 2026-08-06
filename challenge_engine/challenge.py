#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .engine import ChallengeError, capabilities, evaluate_challenge
except ImportError:
    from engine import ChallengeError, capabilities, evaluate_challenge

EXIT = {"OBSERVED":0,"ADVERSARIAL_PASS":0,"CERTIFIED":0,"INCOMPLETE":2,"FAILED":3,"INVALID":4,"BLOCKED_SCOPE":5}

def read_input(path: str) -> dict:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))

def main() -> int:
    p = argparse.ArgumentParser(description="Evaluate a declared challenge contract using the local challenge engine.")
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
    except (OSError, json.JSONDecodeError, ChallengeError, ValueError) as exc:
        result = {"engine_version":"1.0.0","result":"INVALID","error":str(exc)}
    print(json.dumps(result, indent=None if args.compact else 2, sort_keys=True))
    return EXIT.get(result.get("result","INVALID"),4)

if __name__ == "__main__":
    raise SystemExit(main())
