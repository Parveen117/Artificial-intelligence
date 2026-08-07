#!/usr/bin/env python3
"""Strict JSON parsing for Challenge Engine connector inputs.

Python's standard json decoder accepts duplicate object keys by keeping the
last value and also accepts NaN/Infinity tokens. Both behaviours can produce
parser differentials across connectors. Challenge inputs use the interoperable
JSON subset instead: unique object keys and finite standard JSON numbers.
"""
from __future__ import annotations

import json
from typing import Any


class StrictJSONError(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise StrictJSONError(f"duplicate JSON object key: {key}")
        out[key] = value
    return out


def _reject_constant(token: str) -> None:
    raise StrictJSONError(f"non-standard JSON numeric token is not allowed: {token}")


def loads_strict(text: str) -> Any:
    return json.loads(
        text,
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )


def load_strict(fp) -> Any:
    return loads_strict(fp.read())
