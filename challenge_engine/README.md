# Challenge Engine

A fail-closed front door for theorem-backed testing.

## Read this first: what are you supposed to break?

The Challenge is **not** “make the English sentence confusing.”

The Challenge is:

> **Break the declared claim-to-evidence closure contract.**

A meaningful challenge fixes, before evaluation, the target of evaluation (TOE), claim, scope, threat model, evidence channels, obligations, negative controls, adapters and thresholds. A successful break demonstrates that an invalid/unsupported case can still escape those declared controls.

The accepted break classes are machine-readable:

- `false_acceptance`
- `blindness_escape`
- `scope_escape`
- `negative_control_escape`
- `invalid_promotion`
- `flow_consistency_escape`
- `ledger_integrity_failure`

See [`RED_TEAM_RULES.md`](RED_TEAM_RULES.md) for the rules of engagement.

## Natural-language boundary

`target.statement` is **payload by default**, not an invitation to test unrestricted English semantics.

Default:

```json
"semantics": {"mode": "payload_only"}
```

In this mode the statement names/describes the target, while the package, adapters, evidence and obligations determine what is actually testable.

If a package explicitly wants natural-language semantics to participate, it must provide a declared semantic adapter:

```json
{
  "semantics": {"mode": "adapter_declared"},
  "semantic_adapter": {"id": "my-semantic-adapter", "status": "pass"}
}
```

Requesting semantic interpretation without a closed adapter returns `SEMANTICS_NOT_IN_SCOPE`.

Non-formal testing is still allowed. Black-box traces, fuzz summaries, measurements, logs, model outputs and similar evidence may be used in exploratory/adversarial modes. They do not silently become formal proof.

## Challenge Genesis: ledger initiation

Every evaluation emits a `CHALLENGE_GENESIS` object. Genesis means:

> **Freeze the rules of engagement before evaluating the candidate.**

It does not mean “the claim is accepted.” At genesis:

```text
accepted_claims = 0
parent = null
rules_frozen = true
```

The engine hashes the canonical contract with SHA-256. The committed contract includes target, package/mode, scope, threat model, semantic mode, declared obligation/control identifiers, evidence references, adapter identities and thresholds.

A connector can pin the agreed rules:

```json
"genesis": {"expected_hash": "<sha256>"}
```

Changing a committed rule changes the genesis hash. Changing a later test outcome does not redefine the original rules.

## Quick start

Default package is `math`.

```bash
python challenge_engine/challenge.py challenge_engine/examples/math_challenge.json
```

Black-box / non-formal adversarial example:

```bash
python challenge_engine/challenge.py challenge_engine/examples/nonformal_behavioral_challenge.json
```

Authorized security-audit example:

```bash
python challenge_engine/challenge.py challenge_engine/examples/security_audit_challenge.json
```

Machine-readable capabilities:

```bash
python challenge_engine/challenge.py --capabilities
```

Connector / stdin mode:

```bash
cat challenge.json | python challenge_engine/challenge.py - --compact
```

The process writes one JSON result to stdout. It does not require network access.

## Modes

### `exploratory`

Ordinary empirical or black-box evidence is allowed. A fully closed exploratory challenge returns `OBSERVED`. This is evidence, not a formal proof.

### `adversarial`

The threat-model goal, accepted break conditions, target, evidence and mandatory obligations are declared before evaluation. Negative controls are required. A fully closed challenge returns `ADVERSARIAL_PASS`. This means the declared adversarial contract passed. It is still not automatically a mathematical certificate.

### `certified`

All adversarial requirements apply, plus at least one formal support item, a passing `formal_adapter`, every package-required obligation closed, and any declared burden/completion bound closed. A fully closed challenge returns `CERTIFIED`.

Certification is always relative to the declared challenge contract. It is not a universal truth oracle.

## Result states

| Result | Meaning |
| --- | --- |
| `OBSERVED` | exploratory contract closed |
| `ADVERSARIAL_PASS` | adversarial contract and negative controls closed |
| `CERTIFIED` | formal promotion requirements closed |
| `INCOMPLETE` | no contradiction, but one or more mandatory obligations are still open |
| `FAILED` | a declared test, bound, negative control, genesis pin or obligation failed |
| `INVALID` | malformed challenge contract |
| `BLOCKED_SCOPE` | a package requiring declared authorization was invoked without it |
| `SEMANTICS_NOT_IN_SCOPE` | semantic interpretation was requested without a closed semantic adapter |

Exit code is `0` only for `OBSERVED`, `ADVERSARIAL_PASS`, and `CERTIFIED`.

## Package model

Package manifests live under `challenge_engine/packages/`.

Included packages:

- `math` — default package; certified by default.
- `logic` — logical derivation testing.
- `code` — program/specification and behavioral testing.
- `security_audit` — authorized defensive testing; declared scope is mandatory.

A package specifies allowed modes, its default mode, mandatory obligations per mode, whether authorization is required, and whether formal certification requires a formal adapter.

Adding another domain does not require changing the mathematical core. Add a package manifest and, when needed, an adapter that produces the declared evidence/obligation fields.

## Flow probes

An adapter may expose a transformation/observer-flow sequence:

```json
"flow": {
  "enabled": true,
  "probes": [
    {"order": 0, "target_visible": false},
    {"order": 1, "target_visible": false},
    {"order": 2, "target_visible": true}
  ],
  "first_recognition_order": 2,
  "bilateral": {"defect": 0.002, "tolerance": 0.01},
  "remainder_bound": 0.05
}
```

The engine checks that declared target visibility does not revert at a deeper probe order and that the declared first-recognition order matches the supplied probe record.

The probe objects are adapter outputs. The engine does not infer a generator or semantic model from arbitrary raw prose/data.

## Burden / reserve

A challenge may declare:

```json
"burden": {"beta": 0.72, "threshold": 1.0}
```

The engine reports the strict reserve `threshold - beta` and fails when the burden exceeds the threshold.

## Finite-to-limit promotion

For a finite approximation to support a limiting claim:

```json
"completion": {
  "enabled": true,
  "finite_upper": 0.83,
  "completion_error": 0.06,
  "threshold": 1.0
}
```

The promotion check is fail-closed:

```text
finite_upper + completion_error < threshold
```

A finite value without `completion_error` returns `INCOMPLETE`.

## Security-audit scope

The `security_audit` package will not evaluate without:

```json
"scope": {
  "authorization": "declared",
  "target": "local-demo-service"
}
```

This package is intended for authorized defensive testing. Scope is part of the machine-readable challenge contract, not a decorative disclaimer.

## Licence / participation boundary

The Challenge protocol does not create a new licence. Repository use is governed by the existing [`LICENSE`](../LICENSE), [`PATENT_NOTICE.md`](../PATENT_NOTICE.md), and any separate written challenge authorization supplied by the rights holder.

If a public Challenge is activated, the public invitation should state the exact permission/scope participants are being given. The engine itself does not enlarge those rights.

## Tests

```bash
python -m unittest discover -s challenge_engine/tests -v
```

The tests cover the default `math` package, certified math promotion, non-formal adversarial evidence, authorization blocking, formal/non-formal evidence boundary, completion-error gating, burden failure, flow recognition monotonicity, negative controls, semantic scope and challenge-genesis integrity.

## Connector contract

See [`CONNECTOR_CONTRACT.md`](CONNECTOR_CONTRACT.md) for stable stdin/stdout, genesis and exit-code behavior.

## Mathematical foundation

The Challenge Engine is the user-facing contract layer. The theorem paper under `foundational_mathematics/invariant_gated_state_transitions/` supplies the mathematical justification for target blindness, flow/observer refinement, finite-to-infinite completion, finite obstruction certificates, burden reserve, gate closure and persistent records.

The interface deliberately uses ordinary testing/red-team language. The theorem layer remains rigorous underneath it.
