# Artificial Intelligence Trust Enablement v1.2.0

Release date: 2026-08-07

## Release status

Version 1.2.0 remains a pre-tag release candidate while the final hostile hardening sequence is completed. The current candidate includes Theorem-47 source-bound proof-carrying numerical validation in addition to the earlier parser/ledger, arithmetic-enclosure, and seam-quotient hardening.

The final GitHub tag / Zenodo archive must be created from the final `main` commit after this T47 integration and its post-merge CI. Do not archive an older pre-T47 commit merely because it once enjoyed the flattering title “final.” Humans have used that filename before.

## Theorem source

Recognition-Kernel Theorem 47 is on:

```text
Parveen117/Recognition-Kernel-Framework
main e0e0d051fecf9d7a87fe6386864c7153dd614324
```

The T47 proof packet passed the RKF proof-lab matrix on Python 3.11 and 3.12 and the independent Recognition Kernel Review workflow.

The theorem chain relevant to the numerical trust layer is:

```text
T34 common-chart source binding
-> T38 source-relative domination
-> T39 no-blindness
-> T43 explicit remainder
-> T44 body-tail preservation
-> T45 arithmetic + analytic enclosure
-> T46 seam quotient
-> T47 source-bound proof-carrying numerical validation
```

## Challenge Engine scope

The engine remains a fail-closed evaluator of declared claim-to-evidence closure contracts, not a universal natural-language truth oracle.

Core release features include:

- `math`, `logic`, `code`, and authorization-gated `security_audit` packages;
- exploratory, adversarial, and certified modes;
- strict JSON with duplicate-key and nonstandard-number rejection;
- exact connector decimal-lexeme preservation;
- Challenge Genesis and Challenge Evaluation SHA-256 records;
- package-manifest commitment and Genesis pinning;
- target-of-evaluation binding for scoped security challenges;
- observer-flow, burden and finite-to-limit gates;
- exact rational/decimal numerical carriers;
- fail-closed legacy approximate arithmetic;
- T47 source-bound proof-carrying numerical traces;
- T46 exact finite-jet seam quotient classification;
- explicit replay, external-source and rights boundaries.

## T47 source-bound numerical hardening

The previous arithmetic layer correctly carried:

```text
arithmetic radius + analytic tail
```

outward, but a participant could still submit a syntactically valid radius/tail. T47 closes that formal-promotion gap for an admitted exact proof-carrying subset.

New protocol:

```text
source-bound-proof-carrying-numerics-v1
```

Initial source model:

```text
exact_expression_v1
```

Admitted exact interval-DAG operations:

```text
add
sub
mul
neg
div
```

At each operation node the engine recomputes the exact rational enclosure. The participant may provide a wider enclosure but cannot shrink it below the verifier-computed result.

Division is rejected when the denominator enclosure contains zero.

Current proof-bearing tail rules:

```text
zero
geometric_tail
```

For a geometric tail the first omitted magnitude and ratio upper bound must be verified DAG nodes; the engine derives the tail itself.

The strict T47 threshold logic is:

```text
U < threshold                  PASS
L >= threshold                 FAIL
L = U = threshold              FAIL for strict <
L < threshold <= U             INCOMPLETE
```

Thus exact equality is recognized as falsity of a strict inequality, while uncertain boundary contact remains incomplete.

## Legacy arithmetic compatibility change

The legacy protocol `exact-rational-directed-enclosure-v1` remains readable, but its proof-bearing behavior is tightened.

Still intrinsically exact:

```text
exact_rational + analytic_tail = 0
exact_decimal  + analytic_tail = 0
```

Held at `INCOMPLETE` when it would otherwise promote without source proof:

```text
directed_interval
ball
raw_float with participant radius
exact value with participant nonzero analytic_tail
```

Independent-enclosure overlap remains a consistency check only. Disjoint enclosures can fail; overlapping participant claims do not authenticate one another.

The old `arithmetic_ball_challenge.json` example is therefore intentionally incomplete under T47. The new `source_bound_numerics_challenge.json` example is the proof-bearing numerical example.

## Implementation fingerprint

Every Challenge Genesis now commits the current:

```text
implementation_manifest_sha256
```

The manifest fingerprints the parser/current engine numerical layers, primary schema, and installed package manifests. This deliberately advances pre-T47 Genesis hashes before release.

The fingerprint provides implementation integrity under an externally pinned expected release. It is not an authenticity oracle if an attacker controls both executable and the hash it reports.

## Seam-quotient boundary

The T46 protocol remains:

```text
first-visible-jet-seam-quotient-v1
```

Raw algebraic `1/0` and `0/0` remain invalid. Exact polynomial jets are classified by first-visible order. Flat/unresolved denominator jets remain incomplete. Approximate/remainder-bearing seams remain incomplete until their remainder sources are bound by an admitted validator. T47 supplies the architecture for that future step but does not magically validate arbitrary remainder fields.

## Verification evidence

Current T47 development Challenge Engine suite:

```text
Ran 131 tests
OK
```

The foundational mathematics/audit campaign remains separately recorded at:

```text
236,456 exact/random/exhaustive adversarial cases
```

The two counts remain separate because they are different evidence classes.

Current audit sequence:

```text
PASS_FINAL_CHALLENGE_SEAL_AUDIT
PASS_EXACT_RATIONAL_ENCLOSURE_AUDIT
PASS_EXACT_FINITE_JET_SEAM_QUOTIENT_AUDIT
PASS_SOURCE_BOUND_NUMERICS_T47_AUDIT
```

## Remaining pre-public-endpoint boundaries

The release does not claim:

- unrestricted English-language truth;
- arbitrary real-world evidence authenticity;
- correctness of arbitrary external numerical backends;
- universal source-completeness validation;
- proof of arbitrary participant-supplied norm/remainder premises;
- external executable authenticity from an internal hash alone;
- stateless replay rejection;
- complete input-size/nesting/digit/exponent/CPU/memory/request-rate denial-of-service hardening.

The last item remains the next engineering hardening gate after T47.

## Reproducibility entry points

```bash
python challenge_engine/challenge.py --capabilities --compact
python -m unittest discover -s challenge_engine/tests -v
python challenge_engine/challenge.py challenge_engine/examples/math_challenge.json --compact
python challenge_engine/challenge.py challenge_engine/examples/arithmetic_ball_challenge.json --compact
python challenge_engine/challenge.py challenge_engine/examples/source_bound_numerics_challenge.json --compact
python challenge_engine/challenge.py challenge_engine/examples/seam_quotient_challenge.json --compact
python challenge_engine/challenge.py challenge_engine/examples/nonformal_behavioral_challenge.json --compact
python challenge_engine/challenge.py challenge_engine/examples/security_audit_challenge.json --compact
```

Important files:

- `challenge_engine/SOURCE_BOUND_NUMERICS_AUDIT.md`
- `challenge_engine/schema/source_bound_numerics.schema.json`
- `challenge_engine/ARITHMETIC_ENCLOSURE_AUDIT.md`
- `challenge_engine/SEAM_QUOTIENT_AUDIT.md`
- `challenge_engine/CONNECTOR_CONTRACT.md`
- `challenge_engine/PUBLIC_CHALLENGE_SCOPE.md`
