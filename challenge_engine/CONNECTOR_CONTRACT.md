# Challenge Engine Connector Contract

Protocol version: `1.0`
Engine version: `1.2.0`
Arithmetic protocol: `exact-rational-directed-enclosure-v1`

This document defines the stable local process interface intended for connectors, CI systems and other tools.

## What the connector is connecting to

The engine evaluates a **declared claim-to-evidence closure contract**.

It does not treat `target.statement` as unrestricted natural-language semantics. By default the statement is a payload/label identifying the target. A connector that wants language semantics evaluated must declare a semantic adapter.

A red-team connector should therefore think in these terms:

```text
TOE + claim + scope + threat model + evidence + adapters + obligations + success criterion
```

not:

```text
arbitrary English prompt -> universal truth verdict
```

## Strict JSON and numeric boundary

Connector input is strict interoperable JSON. Before challenge evaluation the process rejects:

- duplicate object keys at any nesting level;
- `NaN`, `Infinity`, and `-Infinity` tokens;
- malformed explicit package/mode selections instead of silently replacing them with defaults.

Ordinary finite decimal JSON tokens retain their original numeric lexeme so exact declared-value threshold and canonical-contract decisions do not depend on a later binary floating representation. Numerically equivalent finite-decimal spellings canonicalize to the same exact rational value for Genesis.

For genuinely arbitrary-precision proof values, use quoted exact decimal/rational strings inside `arithmetic_certificate`. A connector should not expect an ordinary platform float to preserve an unlimited decimal token merely because JSON looked very serious about it.

## Discover capabilities

```bash
python challenge_engine/challenge.py --capabilities --compact
```

Output is one JSON object containing `engine_version`, `schema_version`, default package (`math`), installed package manifests and their SHA-256 commitments, terminal result names, accepted break conditions, semantic default, Genesis contract information, parser/evaluation capabilities, arithmetic protocol, and stdin/stdout support. No network call is made by the engine.

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

If `package` is **omitted**, `math` is used. If `mode` is **omitted**, the selected package's default mode is used. If `semantics` is omitted, `payload_only` is used. Explicit blank, null, Boolean, unknown or otherwise malformed package/mode values are not omissions and fail closed as `INVALID`.

For adversarial/certified operation, declare a threat model. Without one the result remains `INCOMPLETE`.

## Recommended adversarial input

```json
{
  "schema_version": "1.0",
  "challenge_id": "external-001",
  "package": "code",
  "mode": "adversarial",
  "target": {"statement": "The declared behavior survives the supplied probes."},
  "semantics": {"mode": "payload_only"},
  "scope": {},
  "threat_model": {
    "goal": "Find an unsupported case that escapes the declared controls.",
    "break_conditions": [
      "false_acceptance",
      "blindness_escape",
      "negative_control_escape"
    ]
  },
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

For authorization-gated packages such as `security_audit`, bind the target of evaluation explicitly:

```json
{
  "scope": {
    "authorization": "declared",
    "target": "local-demo-service"
  },
  "target": {
    "toe": "local-demo-service",
    "statement": "The declared security property"
  }
}
```

`target.toe` must match `scope.target`.

## Natural-language semantics

Default:

```json
"semantics": {"mode": "payload_only"}
```

In this mode an ambiguous, adversarial or witty English sentence does not redefine the theorem-backed challenge. The engine evaluates only the declared adapters/evidence/obligations.

To request semantic interpretation:

```json
{
  "semantics": {"mode": "adapter_declared"},
  "semantic_adapter": {"id": "semantic-adapter-v1", "status": "pass"}
}
```

If semantic interpretation is requested without a closed adapter, the terminal result is `SEMANTICS_NOT_IN_SCOPE`.

## Break conditions

The protocol recognizes these red-team break classes:

```text
false_acceptance
blindness_escape
scope_escape
negative_control_escape
invalid_promotion
flow_consistency_escape
ledger_integrity_failure
```

A package-specific challenge may choose the subset relevant to its target. These values define what success for the challenger means before evaluation begins.

## Challenge Genesis / ledger initiation

Every result contains:

```json
"challenge_genesis": {
  "kind": "CHALLENGE_GENESIS",
  "hash_algorithm": "sha256",
  "genesis_hash": "...",
  "parent": null,
  "accepted_claims": 0,
  "rules_frozen": true,
  "contract": {}
}
```

Genesis means the **rules of engagement are committed before candidate evaluation**. It is not a positive verdict on the target.

The canonical hash commits to the contract declaration, the SHA-256 of the selected package manifest, parser/arithmetic contracts, exact connector numeric declarations, and any declared arithmetic certificate. Later pass/fail/open outcome statuses are intentionally not used to redefine the original rules.

A connector may pin a previously agreed contract:

```json
"genesis": {"expected_hash": "<64-hex-sha256>"}
```

A mismatch fails `genesis_integrity`. Malformed pins are `INVALID`.

## Challenge Evaluation / outcome record

Because Genesis freezes rules rather than outcomes, every result also contains a separate hash-bound evaluation object:

```json
"challenge_evaluation": {
  "kind": "CHALLENGE_EVALUATION",
  "hash_algorithm": "sha256",
  "genesis_hash": "...",
  "input_sha256": "...",
  "parent_evaluation_hash": null,
  "result": "ADVERSARIAL_PASS",
  "formal_promotion": false,
  "checks": [],
  "evaluation_hash": "..."
}
```

The same Genesis can therefore support different evidence outcomes while each evaluated input/result remains independently committed.

A subsequent request may carry a parent:

```json
"evaluation": {"parent_hash": "<64-hex-sha256>"}
```

The engine validates the parent hash format and carries it into the new evaluation record. The engine is intentionally stateless and cannot itself prove that the declared parent exists or that an old valid evaluation has not been replayed. Existence, uniqueness, ordering and replay rejection are persistent connector/ledger obligations.

## Exact threshold boundary

Burden, flow numeric checks and finite-to-limit threshold decisions use the exact declared decimal lexeme when the request came through the strict connector parser. This prevents binary floating-point from turning a mathematical equality into a false strict pass. For example:

```text
0.1 + 0.7 = 0.8
```

remains a boundary and cannot satisfy a strict `< 0.8` promotion because of binary rounding.

## Proof-bearing arithmetic certificate

The arithmetic certificate is optional and is intended when numerical uncertainty itself is part of the challenge contract.

Supported `kind` values:

```text
exact_rational
exact_decimal
directed_interval
ball
raw_float
```

The currently certified scalar relation is:

```text
upper_below_threshold
```

### Exact rational

```json
"arithmetic_certificate": {
  "kind": "exact_rational",
  "numerator": "7",
  "denominator": "10",
  "analytic_tail": "1/100",
  "threshold": "4/5"
}
```

The arithmetic radius is zero.

### Exact decimal / arbitrary precision

```json
"arithmetic_certificate": {
  "kind": "exact_decimal",
  "value": "0.123456789012345678901234567890123456789",
  "analytic_tail": "0",
  "threshold": "0.123456789012345678901234567890123456790"
}
```

String values are recommended when precision must exceed the ordinary connector float-compatible range.

### Directed interval

```json
"arithmetic_certificate": {
  "kind": "directed_interval",
  "lower": "0.92",
  "upper": "0.94",
  "analytic_tail": "0.04",
  "threshold": "1"
}
```

### Validated ball

```json
"arithmetic_certificate": {
  "kind": "ball",
  "backend": "validated-backend-v1",
  "center": "0.93",
  "radius": "0.01",
  "analytic_tail": "0.04",
  "threshold": "1"
}
```

The engine treats arithmetic uncertainty and analytic/truncation uncertainty as separate channels. For `upper_below_threshold`, promotion requires:

```text
enclosure_upper + analytic_tail < threshold
```

Equality returns `INCOMPLETE`; an outward upper above the threshold returns `FAILED`.

### Raw floating point

```json
"arithmetic_certificate": {
  "kind": "raw_float",
  "center": "0.93",
  "analytic_tail": "0.04",
  "threshold": "1"
}
```

Without a validated outward `radius`, this remains `INCOMPLETE`. If a separate validated error analysis supplies a radius, the value participates as the corresponding enclosure. The engine does not infer a rounding radius from the number of digits printed.

### Independent enclosure paths

A certificate may also carry:

```json
"independent_enclosures": [
  {"id": "path-a", "lower": "0.92", "upper": "0.94"},
  {"id": "path-b", "center": "0.935", "radius": "0.01"}
]
```

The common scalar intersection must be nonempty. Disjoint claimed certified paths fail `arithmetic_path_overlap`. This is a necessary consistency condition; it does not authenticate the external backends themselves.

## Output

When arithmetic evidence is present, the ordinary result object additionally contains:

```json
{
  "arithmetic_protocol": "exact-rational-directed-enclosure-v1",
  "arithmetic_summary": {
    "kind": "ball",
    "proof_bearing": true,
    "enclosure_lower": "23/25",
    "enclosure_upper": "47/50",
    "arithmetic_radius": "1/100",
    "analytic_tail": "1/25",
    "outward_upper": "49/50",
    "threshold": "1",
    "reserve": "1/50"
  }
}
```

The core result envelope remains:

```json
{
  "engine_version": "1.2.0",
  "schema_version": "1.0",
  "challenge_id": "external-001",
  "package": "code",
  "mode": "adversarial",
  "result": "ADVERSARIAL_PASS",
  "formal_promotion": false,
  "challenge_genesis": {},
  "challenge_evaluation": {},
  "checks": [],
  "open_obligations": [],
  "failed_obligations": [],
  "blocked_obligations": [],
  "invalid_contract_fields": [],
  "not_in_scope": [],
  "challenge_definition": "...",
  "claim_boundary": "...",
  "input_trust_boundary": "...",
  "parser_boundary": "...",
  "replay_boundary": "...",
  "license_boundary": "..."
}
```

## Terminal results and exit codes

```text
OBSERVED                0
ADVERSARIAL_PASS        0
CERTIFIED               0
INCOMPLETE              2
FAILED                  3
INVALID                 4
BLOCKED_SCOPE           5
SEMANTICS_NOT_IN_SCOPE  6
```

## Permission boundary

The connector protocol grants no additional permission to use, deploy, benchmark, modify, copy, commercialize or otherwise exploit repository materials. The repository `LICENSE`, `PATENT_NOTICE.md`, and any separate written challenge authorization govern permitted use.

A public Challenge invitation should therefore state the exact authorization/scope offered to participants. Machine-readable `security_audit` scope does not itself create legal authorization.
