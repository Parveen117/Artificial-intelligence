# Proof-Carrying Numerical Hallucination Audit

Status: **PASS_PROOF_CARRYING_NUMERIC_HALLUCINATION_AUDIT**

Engine: Challenge Engine `1.2.0`
Protocol: `proof-carrying-numeric-closure-v1`
Mathematical-hallucination class: `formal_numeric_overclaim`

## Purpose

This audit treats numerical overclaim as a special case of mathematical hallucination.

The failure pattern is:

```text
claimed mathematical certainty
>
certainty established by the admitted source/proof trace
```

Examples include a participant-supplied radius treated as self-validating, an analytic tail declared without a theorem-derived rule, an omitted live dependency, a narrowed interval that excludes the verifier-computed enclosure, or a strict equality incorrectly promoted as a strict pass.

## Proof-bearing release subset

The release adapter accepts a finite exact-rational proof DAG with:

```text
source class: exact_contract
operations: add, sub, mul, neg, div
admitted tail rules: zero, geometric_tail
```

Each operation is recomputed outward from dependency intervals. A participant may widen an interval but cannot shrink it below the verifier-computed enclosure.

Division is rejected if the denominator enclosure contains zero.

The `source_complete` gate must be true. If source completeness/no-blindness is open, the numerical claim remains `INCOMPLETE` even when every arithmetic step is locally valid.

## Radius and tail trust boundary

A field named `radius`, `validated_radius`, `analytic_tail`, `remainder`, `backend`, or similar does not prove its own correctness.

Legacy approximate `ball`, `directed_interval`, or `raw_float` arithmetic certificates cannot self-promote to `CERTIFIED` merely because they contain a favorable radius/tail. They require the proof-carrying provenance gate or another admitted source validator.

Exact rational or finite-decimal primitive values with zero analytic tail retain the exact compatibility path.

Overlapping independent enclosures remain a useful consistency check, but overlap alone is not proof that either enclosure contains the target.

## Strict-bound classification

For a verified final interval `[L,U]` and strict claim `x < threshold`:

```text
U < threshold                 PASS
L >= threshold                FAIL
L < threshold <= U            INCOMPLETE
```

Thus an exact singleton equal to the threshold fails the strict claim. A non-singleton interval merely touching the threshold remains incomplete because refinement may decide it.

## Genesis binding

When `proof_carrying_numeric` is declared, Challenge Genesis commits:

```text
proof_carrying_numeric_protocol
proof_carrying_numeric certificate
numeric_validator_manifest_sha256
```

Changing the trace changes Genesis. The validator manifest hash is an integrity commitment, not a self-authenticating external trust anchor.

## Verification

The dedicated suite covers:

- exact source-bound trace certification;
- forged/narrowed interval rejection;
- denominator-zero enclosure rejection;
- source-completeness/no-blindness hold-open;
- exact strict equality failure;
- uncertain boundary contact incompleteness;
- theorem-style geometric tail recomputation;
- unadmitted participant tail rejection;
- legacy ball/radius self-certification rejection;
- exact zero-tail compatibility;
- Genesis mutation under proof-trace changes;
- capability publication of the mathematical-hallucination class.

The full Challenge Engine suite on the hardened PR head reports:

```text
Ran 124 tests
OK
```

## Claim boundary

This audit establishes fail-closed detection of a declared class of formal numerical overclaim. It does not establish:

- universal mathematical truth;
- universal proof checking;
- authenticity of arbitrary external measurements or backend software;
- universal source-completeness inference;
- correctness of every transcendental/solver operation;
- network rate limiting or resource-exhaustion resistance;
- a self-authenticating implementation hash.

**Release status: `PASS_PROOF_CARRYING_NUMERIC_HALLUCINATION_AUDIT`.**
