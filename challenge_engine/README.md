# Challenge Engine v1.2.0 Release Candidate

A fail-closed front door for theorem-backed challenge testing.

## What the Challenge is

The Challenge is:

> **Break the declared claim-to-evidence closure contract.**

A meaningful challenge fixes the target of evaluation, claim, scope, threat model, evidence channels, obligations, negative controls, adapters and thresholds before evaluation. The engine then decides whether those declared obligations close.

It is not a universal natural-language truth oracle. `target.statement` is payload by default. Unrestricted semantic interpretation enters only through an explicitly declared semantic adapter.

Machine-readable break classes are:

```text
false_acceptance
blindness_escape
scope_escape
negative_control_escape
invalid_promotion
flow_consistency_escape
ledger_integrity_failure
```

See `RED_TEAM_RULES.md` and `PUBLIC_CHALLENGE_SCOPE.md`.

## Quick start

```bash
python challenge_engine/challenge.py challenge_engine/examples/math_challenge.json
python challenge_engine/challenge.py challenge_engine/examples/source_bound_numerics_challenge.json
python challenge_engine/challenge.py challenge_engine/examples/seam_quotient_challenge.json
python challenge_engine/challenge.py --capabilities --compact
```

Connector/stdin mode:

```bash
cat challenge.json | python challenge_engine/challenge.py - --compact
```

The engine requires no network access.

## Result states

| Result | Meaning |
| --- | --- |
| `OBSERVED` | exploratory contract closed |
| `ADVERSARIAL_PASS` | declared adversarial contract and negative controls closed |
| `CERTIFIED` | formal promotion requirements closed |
| `INCOMPLETE` | no contradiction, but a mandatory obligation remains open |
| `FAILED` | a declared check or target relation failed |
| `INVALID` | malformed contract |
| `BLOCKED_SCOPE` | required authorization/scope not closed |
| `SEMANTICS_NOT_IN_SCOPE` | semantic interpretation requested without a closed semantic adapter |

Exit code is `0` only for `OBSERVED`, `ADVERSARIAL_PASS`, and `CERTIFIED`.

## Modes and packages

Modes:

```text
exploratory
adversarial
certified
```

Included packages:

```text
math
logic
code
security_audit
```

The `security_audit` package is authorization-gated and requires `target.toe == scope.target`.

## Strict JSON and exact decimals

Raw connector JSON rejects:

- duplicate keys at any nesting level;
- `NaN`, `Infinity`, and `-Infinity`;
- malformed explicit package/mode values.

Finite JSON decimals preserve their original numeric lexeme for exact declared-value decisions. Thus a mathematical boundary such as

```text
0.1 + 0.7 = 0.8
```

cannot become a false strict pass because of binary floating-point representation.

For arbitrary-precision proof values, use quoted exact decimal/rational strings in the numerical certificates.

## Challenge Genesis and Evaluation

Every valid evaluation emits a `CHALLENGE_GENESIS` record with:

```text
accepted_claims = 0
parent = null
rules_frozen = true
```

Genesis freezes the rules before evaluation. It does not accept the claim.

The final T47 release candidate also commits:

```text
implementation_manifest_sha256
```

into every Genesis. The manifest fingerprints the parser/current numerical engine layers, the primary Challenge schema, and installed package manifests. This means a changed interpreter no longer masquerades as the same frozen rules.

A connector can pin Genesis:

```json
"genesis": {"expected_hash": "<64-hex-sha256>"}
```

Each run also emits a hash-bound `CHALLENGE_EVALUATION` containing the Genesis hash, input hash, checks, result and optional parent Evaluation hash.

The engine is stateless. Parent existence, event uniqueness and replay rejection require persistent connector/ledger memory.

## Legacy arithmetic protocol

The earlier arithmetic carrier remains:

```text
exact-rational-directed-enclosure-v1
```

It parses:

```text
exact_rational
exact_decimal
directed_interval
ball
raw_float
```

T47 tightens what may formally promote.

Without source-bound proof, intrinsically proof-bearing legacy cases are now only:

```text
exact_rational + analytic_tail = 0
exact_decimal  + analytic_tail = 0
```

The following are held at `INCOMPLETE` when they would otherwise promote from participant assertions alone:

```text
directed_interval
ball
raw_float with supplied radius
exact value with nonzero supplied analytic_tail
```

Independent enclosure overlap remains a consistency check. Disjoint paths can fail; overlapping paths do not authenticate the external backends.

The historical `arithmetic_ball_challenge.json` is now intentionally an `INCOMPLETE` trust-boundary example rather than a proof-bearing release example.

## Theorem 47: source-bound proof-carrying numerics

The proof-bearing numerical protocol is:

```text
source-bound-proof-carrying-numerics-v1
```

Recognition-Kernel source theorem:

```text
Theorem 47: Source-Bound Proof-Carrying Numerical Validation
RKF main e0e0d051fecf9d7a87fe6386864c7153dd614324
```

The central law is:

> **A bound does not validate itself.**

### Current source model

```text
exact_expression_v1
```

The trace is a finite topologically ordered exact-rational interval DAG. Current protocol limit:

```text
256 nodes
```

Admitted operations:

```text
add
sub
mul
neg
div
```

Every exact source leaf carries a declared exact value and an interval containing that value. For every operation node, the engine recomputes the canonical interval from already-verified dependencies.

A participant may widen an interval. A participant may **not** narrow the interval below the verifier-computed enclosure.

Example:

```json
"source_bound_numerics": {
  "protocol": "source-bound-proof-carrying-numerics-v1",
  "source_model": "exact_expression_v1",
  "nodes": [
    {
      "id": "a",
      "kind": "exact_contract",
      "value": "1/3",
      "interval": {"lower": "1/3", "upper": "1/3"}
    },
    {
      "id": "b",
      "kind": "exact_contract",
      "value": "1/6",
      "interval": {"lower": "1/6", "upper": "1/6"}
    },
    {
      "id": "root",
      "kind": "op",
      "op": "add",
      "deps": ["a", "b"],
      "interval": {"lower": "49/100", "upper": "51/100"}
    }
  ],
  "root": "root",
  "tail": {"rule": "zero"},
  "threshold": "4/5"
}
```

The exact canonical root is `1/2`; `[49/100,51/100]` is a lawful wider enclosure with derived radius `1/100`.

### Division domain

Interval division is admitted only when the denominator interval excludes zero:

```text
0 in denominator enclosure -> no certified division step
```

This is ordinary interval-domain safety. It does not redefine algebraic division by zero.

### Tail rules

Current proof-bearing tail rules:

```text
zero
geometric_tail
```

For a geometric tail, both the first omitted magnitude and ratio upper bound must reference verified DAG nodes. If the verified ratio satisfies `0 <= q < 1`, the engine computes:

```text
tau = first_omitted_upper / (1 - ratio_upper)
```

The participant does not supply the final tail scalar.

The RKF theorem packet separately proves a rational exponential upper rule and a Theorem-43 jet-tail formula. Those specialized tail rules are intentionally not exposed as proof-bearing engine rules until their norm/source hypotheses have an admitted package-specific validator.

### Strict threshold logic

After the root enclosure and absolute tail are combined into `[L,U]`:

```text
U < threshold                  PASS
L >= threshold                 FAIL
L = U = threshold              FAIL for a strict < claim
L < threshold <= U             INCOMPLETE
```

Exact equality is false for a strict inequality. Uncertain boundary contact stays incomplete.

### Source boundary

The current T47 source model proves the **declared exact formal expression**. It does not authenticate an arbitrary measurement, external backend output, or physical norm. Mapping those into exact leaves requires a package/connector source validator.

This is why the engine does not yet expose the T43 norm-tail rule or approximate T46 seam remainder as automatically proof-bearing.

Dedicated schema:

```text
challenge_engine/schema/source_bound_numerics.schema.json
```

See `SOURCE_BOUND_NUMERICS_AUDIT.md` and `CONNECTOR_CONTRACT.md`.

## First-visible-jet seam quotient

Protocol:

```text
first-visible-jet-seam-quotient-v1
```

This does **not** redefine field division by zero. Raw `1/0` and raw algebraic `0/0` remain invalid.

Current proof-bearing model:

```text
exact_polynomial_jet
```

For exact vanishing polynomial jets:

```text
numerator order > denominator order    FINITE_QUOTIENT_ZERO
orders equal                            FINITE_SEAM_QUOTIENT
numerator order < denominator order    DIVERGENT_NO_FINITE_QUOTIENT
all denominator jets zero              INCOMPLETE_FLAT_OR_UNRESOLVED
```

The general `analytic_with_validated_remainder` model remains incomplete until a source-bound remainder adapter establishes the Theorem-46 hypotheses.

See `SEAM_QUOTIENT_AUDIT.md`.

## Burden and finite-to-limit gates

The existing burden and completion gates remain part of the declared challenge contract. Exact connector decimal comparison prevents binary-rounding boundary promotion. A finite-to-limit gate still requires its declared completion error.

These generic contract fields are not, by themselves, a universal external evidence-authentication system. When a domain requires provenance for such fields, the selected package/connector must supply the corresponding adapter.

## External trust boundary

The engine tests declared closure. It does not automatically authenticate real-world evidence, external numerical backends, measurements, signatures or arbitrary source claims merely because they arrive in valid JSON.

T47 closes the **internal formal derivation** of an admitted numerical enclosure/tail. External-world source mapping remains a separate obligation.

The implementation fingerprint is likewise an integrity commitment under an externally pinned expected release, not an authenticity oracle if the executable and its reported hash are both attacker-controlled.

## Resource boundary

The T47 proof trace has a 256-node protocol limit. Global input-byte, nesting-depth, numeric digit/exponent, CPU/memory, and request-rate denial-of-service hardening remains a separate pre-public-endpoint engineering gate.

Resource-exhaustion testing should remain outside a public Challenge unless explicitly authorized.

## Release verification

Foundational theorem/audit evidence:

```text
236,456 exact/random/exhaustive adversarial cases
```

Current T47 Challenge Engine development suite:

```text
131 unit/adversarial tests
```

These counts are intentionally separate.

Current audit sequence:

```text
PASS_FINAL_CHALLENGE_SEAL_AUDIT
PASS_EXACT_RATIONAL_ENCLOSURE_AUDIT
PASS_EXACT_FINITE_JET_SEAM_QUOTIENT_AUDIT
PASS_SOURCE_BOUND_NUMERICS_T47_AUDIT
```

## Rights boundary

The Challenge protocol creates no new licence. Repository use remains governed by `LICENSE`, `PATENT_NOTICE.md`, `COPYRIGHT_NOTICE.md`, and any separate written challenge authorization.

## Key files

- `CONNECTOR_CONTRACT.md`
- `PUBLIC_CHALLENGE_SCOPE.md`
- `SOURCE_BOUND_NUMERICS_AUDIT.md`
- `schema/source_bound_numerics.schema.json`
- `ARITHMETIC_ENCLOSURE_AUDIT.md`
- `SEAM_QUOTIENT_AUDIT.md`
- `FINAL_SEAL_AUDIT.md`
