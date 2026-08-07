# Challenge Engine v1.2.0

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

## Strict connector JSON

Raw connector input uses strict interoperable JSON:

- duplicate object keys are rejected at any nesting level;
- `NaN`, `Infinity`, and `-Infinity` are rejected;
- explicit malformed `package` or `mode` values do not silently fall back to defaults;
- package names are restricted to installed package manifests;
- ordinary finite decimal tokens retain their original JSON spelling for exact declared-value threshold and canonical-contract decisions.

This prevents parser-differential tricks such as supplying two `mode` keys and relying on one parser to keep the first while another keeps the last. For truly arbitrary-precision proof values, use quoted exact decimal/rational strings in `arithmetic_certificate`; do not rely on an ordinary platform float to preserve an unlimited numeric token.

## Challenge Genesis: ledger initiation

Every evaluation emits a `CHALLENGE_GENESIS` object. Genesis means:

> **Freeze the rules of engagement before evaluating the candidate.**

It does not mean “the claim is accepted.” At genesis:

```text
accepted_claims = 0
parent = null
rules_frozen = true
```

The engine hashes the canonical contract with SHA-256. The committed contract includes target, package/mode, scope, threat model, semantic mode, declared obligation/control identifiers, evidence references, adapter identities, every enabled rule selector or threshold that can affect promotion, the installed package-manifest hash, parser/arithmetic contracts, exact connector numeric declarations, and any declared arithmetic or seam-quotient certificate.

A connector can pin the agreed rules:

```json
"genesis": {"expected_hash": "<sha256>"}
```

Changing a committed rule changes the genesis hash. Changing a later test outcome does not redefine the original rules. Numerically equivalent finite-decimal spellings such as `0.1` and `0.10` canonicalize to the same exact declared value rather than creating a fake rule change.

## Challenge Evaluation: outcome commitment

Genesis intentionally freezes rules rather than outcomes. Each run therefore also emits a separate `CHALLENGE_EVALUATION` record containing:

- the Genesis hash;
- a SHA-256 hash of the normalized evaluated input;
- the result and computed checks;
- its own `evaluation_hash`;
- an optional `parent_evaluation_hash`.

A subsequent request may declare:

```json
"evaluation": {"parent_hash": "<sha256>"}
```

This lets a persistent connector/ledger form an outcome chain without confusing changing evidence with changing rules.

The engine itself is stateless. It can verify the shape and carry a parent hash, but it cannot know whether an old valid evaluation is being replayed as a new request. Cross-request replay rejection therefore belongs to the persistent connector or append-only ledger.

## Quick start

Default package is `math`.

```bash
python challenge_engine/challenge.py challenge_engine/examples/math_challenge.json
```

Validated arithmetic example:

```bash
python challenge_engine/challenge.py challenge_engine/examples/arithmetic_ball_challenge.json
```

Exact seam-quotient example:

```bash
python challenge_engine/challenge.py challenge_engine/examples/seam_quotient_challenge.json
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

All adversarial requirements apply, plus at least one formal support item, a passing `formal_adapter`, every package-required obligation closed, and any declared burden/completion/arithmetic/seam-quotient bound closed. A fully closed challenge returns `CERTIFIED`.

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

A package specifies allowed modes, its default mode, mandatory obligations per mode, whether authorization is required, and whether formal certification requires a formal adapter. The canonical package manifest is SHA-256 committed inside Challenge Genesis, so changing package rules without changing the Genesis commitment is detectable.

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

The engine checks that declared target visibility does not revert at a deeper probe order and that the declared first-recognition order matches the supplied probe record. Connector decimal spellings used in numeric flow checks are retained for exact declared-value comparison.

The probe objects are adapter outputs. The engine does not infer a generator or semantic model from arbitrary raw prose/data.

## Burden / reserve

A challenge may declare:

```json
"burden": {"beta": 0.72, "threshold": 1.0}
```

The engine reports the strict reserve `threshold - beta` and fails when the burden exceeds the threshold. Negative, Boolean, NaN, or malformed values are rejected rather than coerced.

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

Declared finite decimal tokens are compared through their exact decimal values. Thus a boundary such as `0.1 + 0.7 = 0.8` remains equality and cannot become a false strict pass merely because a binary float happens to lie just below `0.8`.

A finite value without `completion_error` returns `INCOMPLETE`. Removing or disabling a previously committed completion gate changes the genesis hash.

## Proof-bearing arithmetic enclosures

The generic arithmetic protocol is:

```text
exact-rational-directed-enclosure-v1
```

It does **not** turn every number into a fraction. Exact integers, rationals and finite declared decimals have zero arithmetic radius. Irrational, transcendental, solver-produced or otherwise approximate values can be supplied as directed intervals or validated balls.

Exact rational example:

```json
"arithmetic_certificate": {
  "kind": "exact_rational",
  "numerator": "7",
  "denominator": "10",
  "analytic_tail": "1/100",
  "threshold": "4/5"
}
```

Validated ball example:

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

The certificate separates two different uncertainties:

```text
arithmetic radius   = uncertainty introduced by numerical representation/operations
analytic tail       = uncertainty from finite analytic/refinement depth
```

The scalar promotion rule is strictly outward:

```text
enclosure_upper + analytic_tail < threshold
```

Equality is `INCOMPLETE`, not a strict pass. An outward upper above the threshold is `FAILED`.

Supported certificate kinds are:

```text
exact_rational
exact_decimal
directed_interval
ball
raw_float
```

For arbitrary precision, use quoted exact decimal/rational strings in the certificate fields. A `raw_float` centre without a validated outward `radius` is calibration only and returns `INCOMPLETE`; with a separately validated radius it participates as an enclosure.

**Trust boundary:** the current arithmetic layer checks closure relative to the declared radius/tail but does not itself authenticate an external backend or independently prove a participant-supplied radius/tail. Such provenance remains an external adapter obligation. This is a known pre-release hardening target and must not be confused with Theorem 45 itself.

A challenge may also supply two or more `independent_enclosures`. Their common scalar intersection must be nonempty. Disjoint claimed certified paths fail closed because they cannot all contain the same exact target. Overlap is a necessary consistency check, not proof that the external backends are intrinsically correct.

See [`ARITHMETIC_ENCLOSURE_AUDIT.md`](ARITHMETIC_ENCLOSURE_AUDIT.md).

## First-visible-jet seam quotient

The seam-quotient protocol is:

```text
first-visible-jet-seam-quotient-v1
```

It does **not** redefine field division by zero. Raw algebraic `1/0` and raw algebraic `0/0` remain invalid.

The proof-bearing release model is currently only:

```text
exact_polynomial_jet
```

A declaration such as:

```json
"seam_quotient_certificate": {
  "seam_id": "demo-regular-seam",
  "model": "exact_polynomial_jet",
  "relation": "finite_seam_quotient",
  "numerator_coefficients": [0, 0, "2"],
  "denominator_coefficients": [0, 0, "4"]
}
```

represents two exact vanishing polynomials along one declared seam. The engine finds the first nonzero coefficient order in each series. If the orders agree at `r` and the denominator coefficient is nonzero, the finite seam quotient is the exact ratio `a_r / b_r`. In the example above it is `1/2`.

The classifications are:

```text
numerator order > denominator order    FINITE_QUOTIENT_ZERO
orders equal                            FINITE_SEAM_QUOTIENT
numerator order < denominator order    DIVERGENT_NO_FINITE_QUOTIENT
all declared denominator jets zero     INCOMPLETE_FLAT_OR_UNRESOLVED
```

The all-zero finite-jet case remains incomplete because flat functions can have all endpoint derivatives zero while their punctured ratio still has a finite limit. The engine refuses to invent that missing asymptotic information.

The more general Theorem-46 model with validated analytic remainders is **not yet proof-bearing in the engine**. A certificate using `analytic_with_validated_remainder` returns `INCOMPLETE` until a trusted remainder/denominator-separation validator is wired in. Participant-supplied text such as `claimed_remainder` cannot promote the result by itself.

See [`SEAM_QUOTIENT_AUDIT.md`](SEAM_QUOTIENT_AUDIT.md).

## Security-audit scope

The `security_audit` package requires a machine-bound TOE as well as declared authorization:

```json
{
  "scope": {
    "authorization": "declared",
    "target": "local-demo-service"
  },
  "target": {
    "toe": "local-demo-service",
    "statement": "The declared property to test"
  }
}
```

For authorization-gated packages, `target.toe` must match `scope.target`. This prevents a contract from carrying authorization for one machine-readable target while evaluating another.

This package is intended for authorized defensive testing. Scope is part of the machine-readable challenge contract, not a decorative disclaimer.

## External input trust boundary

The engine evaluates closure over supplied package/connector/adapter outputs. It does not authenticate real-world evidence merely because a participant sends valid JSON. Evidence authenticity, provenance, signatures, sandboxing, remote attestation, or correctness of an external interval/ball backend must be supplied by the relevant connector/package when those properties matter.

This distinction is deliberate: **contract closure is tested here; external-world authenticity is a separate obligation unless explicitly wired in.**

## Licence / participation boundary

The Challenge protocol does not create a new licence. Repository use is governed by the existing [`LICENSE`](../LICENSE), [`PATENT_NOTICE.md`](../PATENT_NOTICE.md), and any separate written challenge authorization supplied by the rights holder.

If a public Challenge is activated, the public invitation should state the exact permission/scope participants are being given. The engine itself does not enlarge those rights.

## Release verification

The foundational theorem/audit layer currently records:

```text
236,456 exact/random/exhaustive adversarial cases
```

The current Challenge Engine workflow records:

```text
112 unit/adversarial tests
```

These counts are reported separately because mathematical adversarial cases and software unit tests are different forms of evidence.

Current audit statuses:

```text
PASS_FINAL_CHALLENGE_SEAL_AUDIT
PASS_EXACT_RATIONAL_ENCLOSURE_AUDIT
PASS_EXACT_FINITE_JET_SEAM_QUOTIENT_AUDIT
```

See [`FINAL_ADVERSARIAL_RELEASE_AUDIT.md`](FINAL_ADVERSARIAL_RELEASE_AUDIT.md), [`FINAL_SEAL_AUDIT.md`](FINAL_SEAL_AUDIT.md), [`ARITHMETIC_ENCLOSURE_AUDIT.md`](ARITHMETIC_ENCLOSURE_AUDIT.md), and [`SEAM_QUOTIENT_AUDIT.md`](SEAM_QUOTIENT_AUDIT.md).

## Tests

```bash
python -m unittest discover -s challenge_engine/tests -v
```

The tests cover the default `math` package, certified math promotion, non-formal adversarial evidence, authorization blocking, formal/non-formal evidence boundary, completion-error gating, burden failure, flow recognition monotonicity, negative controls, semantic scope, challenge-genesis integrity, duplicate-ID attacks, malformed numeric inputs, evidence-status spoofing, rule-removal mutations, strict JSON parser differentials, exact long-decimal threshold boundaries, scoped TOE binding, package-manifest commitment, evaluation-hash chaining, exact rational/decimal certificates, interval/ball outward promotion, raw-float fail-closed behavior, independent-enclosure consistency, exact first-visible-jet seam quotients, order-mismatch divergence, flat-denominator incompleteness, seam Genesis commitment, and approximate-seam fail-closed behavior.

## Connector contract

See [`CONNECTOR_CONTRACT.md`](CONNECTOR_CONTRACT.md) for stable stdin/stdout, genesis, evaluation-chain, arithmetic-certificate, seam-quotient and exit-code behavior.

## Mathematical foundation

The Challenge Engine is the user-facing contract layer. The theorem paper under `foundational_mathematics/invariant_gated_state_transitions/` supplies the public mathematical justification for target blindness, flow/observer refinement, finite-to-infinite completion, finite obstruction certificates, burden reserve, gate closure and persistent records. The generic arithmetic certificate is an outward-enclosure adapter over those declared completion obligations. The exact seam-quotient adapter consumes the separately verified first-visible-jet theorem from the Recognition-Kernel theorem chain while keeping raw division by zero invalid.

The interface deliberately uses ordinary testing/red-team language. The theorem layer remains rigorous underneath it.
