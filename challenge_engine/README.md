# Challenge Engine

A small, fail-closed front door for the repository's theorem-backed testing model.

The engine accepts a **Challenge Package** rather than assuming every input is already a formal proof. Non-formal evidence is allowed in exploratory and adversarial testing. Promotion to `CERTIFIED` requires a declared formal adapter and formal support.

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

The target, evidence and mandatory obligations are declared before evaluation. Negative controls are required. A fully closed challenge returns `ADVERSARIAL_PASS`. This means the declared adversarial contract passed. It is still not automatically a mathematical certificate.

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
| `FAILED` | a declared test, bound, negative control or obligation failed |
| `INVALID` | malformed challenge contract |
| `BLOCKED_SCOPE` | a package requiring declared authorization was invoked without it |

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

## Non-formal evidence boundary

Evidence entries can set:

```json
{
  "id": "black-box-traces",
  "type": "trace",
  "status": "pass",
  "formal": false
}
```

This is accepted in `exploratory` and `adversarial` mode. It cannot by itself promote a `certified` challenge. A certified challenge requires formal support plus a passing formal adapter.

```text
non-formal observation -> evidence

evidence + declared adapter + closed obligations -> possible formal promotion
```

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

The probe objects are adapter outputs. The engine does not pretend to infer a generator from arbitrary raw data.

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

## Tests

```bash
python -m unittest discover -s challenge_engine/tests -v
```

The tests cover the default `math` package, certified math promotion, non-formal adversarial evidence, authorization blocking, the formal/non-formal evidence boundary, completion-error gating, burden failure, flow recognition monotonicity, negative controls, and open obligations.

## Connector contract

See `CONNECTOR_CONTRACT.md` for stable stdin/stdout and exit-code behavior.

## Mathematical foundation

The challenge engine is the user-facing contract layer. The theorem paper under `foundational_mathematics/invariant_gated_state_transitions/` supplies the mathematical justification for target blindness, flow/observer refinement, finite-to-infinite completion, finite obstruction certificates, burden reserve, gate closure and persistent records.

The interface deliberately uses ordinary testing language. The theorem layer remains rigorous underneath it.
