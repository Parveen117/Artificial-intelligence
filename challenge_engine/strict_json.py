#!/usr/bin/env python3
"""Strict JSON parsing for Challenge Engine connector inputs.

The connector rejects duplicate keys and non-standard NaN/Infinity tokens. For
ordinary finite JSON decimals it also preserves the original numeric token on a
float-compatible wrapper. Legacy engine code can therefore keep treating the
value as a float, while exact threshold and canonical-contract logic can recover
the declared decimal before binary rounding.

Truly arbitrary-precision proof values should use the string-valued arithmetic
certificate fields rather than relying on a platform float carrier.
"""
from __future__ import annotations

import json
import math
from typing import Any


class StrictJSONError(ValueError):
    pass


class ExactJSONFloat(float):
    """Float-compatible connector number retaining its exact JSON lexeme."""

    def __new__(cls, token: str):
        value = float.__new__(cls, token)
        if not math.isfinite(value):
            raise StrictJSONError(
                "finite JSON number exceeds the legacy float-compatible connector range; "
                "use a quoted exact value in arithmetic_certificate"
            )
        value.json_lexeme = token
        return value


def exact_json_lexeme(value: Any) -> str | None:
    token = getattr(value, "json_lexeme", None)
    return token if isinstance(token, str) else None


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
        parse_float=ExactJSONFloat,
        parse_constant=_reject_constant,
    )


def load_strict(fp) -> Any:
    return loads_strict(fp.read())
