# Challenge Engine Connector Contract

Protocol version: `1.0`
Engine version: `1.1.0`

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

## Discover capabilities

```bash
python challenge_engine/challenge.py --capabilities --compact
```

Output is one JSON object containing `engine_version`, `schema_version`, default package (`math`), installed package manifests, terminal result names, accepted break conditions, semantic default, genesis contract, and stdin/stdout support. No network call is made by the engine.

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

If `package` is omitted, `math` is used. If `mode` is omitted, the selected package's default mode is used. If `semantics` is omitted, `payload_only` is used.

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

The canonical hash commits to the contract declaration, while later pass/fail/open statuses are not used to redefine the original rules.

A connector may pin a previously agreed contract:

```json
"genesis": {"expected_hash": "<sha256>"}
```

A mismatch fails `genesis_integrity`.

## Output

```json
{
  "engine_version": "1.1.0",
  "schema_version": "1.0",
  "challenge_id": "external-001",
  "package": "code",
  "mode": "adversarial",
  "result": "ADVERSARIAL_PASS",
  "formal_promotion": false,
  "challenge_genesis": {},
  "checks": [],
  "open_obligations": [],
  "failed_obligations": [],
  "blocked_obligations": [],
  "not_in_scope": [],
  "challenge_definition": "...",
  "claim_boundary": "...",
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
