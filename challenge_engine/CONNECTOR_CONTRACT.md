# Challenge Engine Connector Contract

Protocol version: `1.0`

This document defines the stable local process interface intended for connectors, CI systems and other tools.

## Discover capabilities

```bash
python challenge_engine/challenge.py --capabilities --compact
```

Output is one JSON object containing `engine_version`, `schema_version`, `default_package` (`math`), installed package manifests, terminal result names, and stdin/stdout support. No network call is made by the engine.

## Evaluate by file

```bash
python challenge_engine/challenge.py /path/to/challenge.json --compact
```

## Evaluate by stdin

```bash
python challenge_engine/challenge.py - --compact
```

Send exactly one JSON object on stdin. Read exactly one JSON object on stdout.

## Minimum input

```json
{
  "challenge_id": "external-001",
  "target": {"statement": "The declared target to test."}
}
```

If `package` is omitted, `math` is used. If `mode` is omitted, the selected package's default mode is used.

## Recommended input fields

```json
{
  "schema_version": "1.0",
  "challenge_id": "external-001",
  "package": "math",
  "mode": "adversarial",
  "target": {"statement": "..."},
  "scope": {},
  "evidence": [],
  "obligations": [],
  "negative_controls": [],
  "formal_adapter": {},
  "flow": {},
  "burden": {},
  "completion": {}
}
```

Input schema: `schema/challenge.schema.json`.

## Output

```json
{
  "engine_version": "1.0.0",
  "schema_version": "1.0",
  "challenge_id": "external-001",
  "package": "math",
  "mode": "adversarial",
  "result": "ADVERSARIAL_PASS",
  "formal_promotion": false,
  "checks": [],
  "open_obligations": [],
  "failed_obligations": [],
  "blocked_obligations": [],
  "claim_boundary": "..."
}
```

Output schema: `schema/result.schema.json`.

## Exit codes

| Code | Result |
| ---: | --- |
| 0 | `OBSERVED`, `ADVERSARIAL_PASS`, `CERTIFIED` |
| 2 | `INCOMPLETE` |
| 3 | `FAILED` |
| 4 | `INVALID` |
| 5 | `BLOCKED_SCOPE` |

Connectors should use the JSON `result` as the authoritative classification and may also use the process exit code for CI behavior.

## Formal promotion boundary

A connector may submit non-formal evidence in exploratory or adversarial mode. It must not label a result `CERTIFIED` itself. `CERTIFIED` is emitted only by the engine after the selected package's certification contract closes, including a passing formal adapter when required.

## Adapters

An adapter is responsible for converting domain-specific observations into challenge fields. Examples include a proof parser producing formal evidence, a black-box test harness producing non-formal trace evidence, a model evaluator producing probe observations, or a numerical verifier producing `finite_upper`, `completion_error`, and `beta`.

The challenge engine checks the declared contract. It does not silently infer domain semantics that the adapter did not supply.

## Versioning

Breaking protocol changes require a new `schema_version`. Additive fields may be introduced within schema version `1.0` because the schemas permit extension fields.
