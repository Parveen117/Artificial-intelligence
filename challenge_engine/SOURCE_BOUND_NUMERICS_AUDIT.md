# Source-Bound Proof-Carrying Numerics Audit

Status: **PASS_SOURCE_BOUND_NUMERICS_T47_AUDIT**

Engine: Challenge Engine `1.2.0` release candidate

Protocol:

```text
source-bound-proof-carrying-numerics-v1
```

Theorem source:

```text
Parveen117/Recognition-Kernel-Framework
theorum/47_source_bound_proof_carrying_numerical_validation_theorem.md
main commit e0e0d051fecf9d7a87fe6386864c7153dd614324
```

The RKF Theorem-47 proof packet passed its proof-lab matrix on Python 3.11 and 3.12 and the independent Recognition Kernel Review workflow on that `main` commit.

## Problem closed by this pass

The previous arithmetic-enclosure layer correctly separated an arithmetic radius from an analytic tail and correctly carried both outward. Its remaining trust boundary was that a participant could still submit a syntactically valid radius or tail. The engine could check the consequence of that declaration without proving where the declaration came from.

Theorem 47 changes the promotion rule from:

```text
participant supplies radius/tail -> engine checks arithmetic consequence
```

to:

```text
admitted source -> exact proof DAG -> verifier-derived enclosure/tail -> threshold decision
```

The core rule is:

> **A bound does not validate itself.**

## Proof-bearing release subset

The initial engine source model is:

```text
exact_expression_v1
```

The exact source-bound trace is a finite topologically ordered DAG. Admitted operations are:

```text
add
sub
mul
neg
div
```

Every node carries an exact rational interval. Exact source leaves carry a declared exact value. For an operation node the engine recomputes the canonical outward interval from its already-verified dependencies. The submitted interval may be wider than that canonical enclosure, but never narrower.

The protocol limit is currently:

```text
maximum trace nodes = 256
```

This is a protocol bound for the T47 trace. It is not the complete parser/resource-exhaustion hardening still planned for the public endpoint.

## Division boundary

Interval division is admitted only when the denominator enclosure excludes zero.

```text
0 in denominator enclosure -> no certified division step
```

This is distinct from the Theorem-46 seam quotient. Raw algebraic division by zero remains invalid.

## Tail rules

The engine currently admits:

```text
zero
geometric_tail
```

For `geometric_tail`, the first omitted magnitude and ratio upper bound must themselves reference already-verified DAG nodes. If

```text
0 <= q < 1
```

then the engine derives

```text
tau = first_omitted_upper / (1 - ratio_upper)
```

rather than accepting a participant-supplied final `analytic_tail` scalar.

The RKF theorem packet separately verifies an exact-rational upper rule for the exponential series and a Theorem-43 jet-tail construction. Those more specialized tail rules are not yet exposed as proof-bearing engine adapters until their source/norm hypotheses are bound by a package-specific validator.

## Legacy arithmetic change

Legacy `arithmetic_certificate` remains supported for compatibility, but its formal trust behavior is tightened.

Proof-bearing without T47:

```text
exact_rational + analytic_tail = 0
exact_decimal  + analytic_tail = 0
```

Held at `INCOMPLETE` when it would otherwise promote:

```text
directed_interval
ball
raw_float with participant radius
exact value with participant nonzero analytic_tail
```

A disjoint independent-enclosure check can still fail a legacy certificate. Overlap remains only a consistency check; it no longer authenticates the backend or radius.

The old ball example is therefore now intentionally `INCOMPLETE`, while the new `source_bound_numerics_challenge.json` example is `CERTIFIED` through the T47 proof path.

## Certainty-aware strict boundary

For the T47 strict upper-threshold relation, an exact equality is no longer called epistemically open.

```text
final_upper < threshold                         PASS
final_lower >= threshold                        FAIL
exact singleton == threshold                    FAIL
final_lower < threshold <= final_upper          INCOMPLETE
```

Thus an exact value equal to the boundary fails a strict `<` claim, while a non-singleton enclosure touching/crossing the boundary remains incomplete because refinement may still decide it.

## Implementation fingerprint

Every Challenge Genesis now commits:

```text
implementation_manifest_sha256
implementation_manifest_protocol
```

The implementation manifest hashes the current parser/engine compatibility and numerical layers, the primary Challenge schema, and installed package manifests. This intentionally advances pre-T47 Genesis hashes. The decision was made before the v1.2.0 release/tag so the final frozen contract does not pretend parser/validator semantics are unchanged when the interpreter changes.

This fingerprint is an integrity commitment, not an external authenticity oracle. If an attacker controls both executable and reported hash, the internal hash alone is not a trust anchor. The published Git commit / immutable archive / external signature or attestation remains the external pin.

## Adversarial cases added

The T47 engine suite covers:

- exact source-bound DAG certification;
- verified wider enclosure and derived radius;
- forged narrower interval rejection;
- interval division with zero in the denominator enclosure;
- duplicate node identifiers;
- forward/cyclic dependencies;
- unsupported source model held open;
- verifier-derived geometric tail;
- invalid geometric ratio;
- exact strict-boundary failure;
- uncertain boundary contact remaining incomplete;
- legacy ball downgrade;
- legacy raw float plus participant radius downgrade;
- legacy exact nonzero-tail downgrade;
- legacy exact zero-tail compatibility;
- mutual exclusion of legacy and T47 numerical certificate forms;
- Genesis implementation-fingerprint commitment;
- post-fingerprint Genesis pin round trip;
- capability publication of the T47 protocol.

## Verification result

On development head `a3c7b3841d4b0d41ff3e7441d092c0488b9e7c64`, the Challenge Engine workflow completed successfully after the T47 schema addition.

The unit/adversarial suite reports:

```text
Ran 131 tests
OK
```

The separately reported foundational mathematics/audit evidence remains:

```text
236,456 exact/random/exhaustive adversarial cases
```

These numbers remain separate because theorem/audit cases and software unit/adversarial tests are different evidence classes.

## Remaining boundaries

This audit does **not** establish:

- truth of arbitrary external measurements;
- authenticity of an arbitrary external numerical backend;
- a universal source-completeness oracle;
- that any participant-supplied external norm bound is true merely because it is represented as an exact leaf;
- proof-bearing Theorem-43 norm hypotheses without a source adapter;
- proof-bearing approximate Theorem-46 seam remainders without a source adapter;
- complete input-size, nesting-depth, digit/exponent, CPU, memory, or request-rate denial-of-service hardening;
- external executable authenticity from an internally reported hash alone.

**Release status for the implemented T47 subset: `PASS_SOURCE_BOUND_NUMERICS_T47_AUDIT`.**
