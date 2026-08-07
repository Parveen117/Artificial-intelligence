# Public Challenge Scope Template

This document defines the technical scope to publish alongside a public Challenge invitation. It does **not** replace or modify `LICENSE`, `PATENT_NOTICE.md`, or `COPYRIGHT_NOTICE.md`, and it does not itself grant repository-use rights beyond those documents or separate written authorization.

## Target of evaluation

The designated Challenge Engine endpoint or connector instance running the published release candidate.

For authorization-gated packages, the machine-readable target must be bound explicitly:

```json
{
  "scope": {
    "authorization": "declared",
    "target": "designated-endpoint"
  },
  "target": {
    "toe": "designated-endpoint",
    "statement": "The declared property under test"
  }
}
```

`target.toe` must match `scope.target`.

## Challenge objective

A participant should attempt to demonstrate a meaningful break of the declared claim-to-evidence closure contract. Published break classes are:

- `false_acceptance`
- `blindness_escape`
- `scope_escape`
- `negative_control_escape`
- `invalid_promotion`
- `flow_consistency_escape`
- `ledger_integrity_failure`

Natural-language ambiguity is not a break unless the selected package explicitly places semantic interpretation in scope through an admitted semantic adapter.

## Numerical challenge boundary after Theorem 47

The previous legacy arithmetic carrier remains available for compatibility, but participant-supplied approximate radii/tails are no longer self-certifying.

Without a T47 source proof, only these legacy cases are intrinsically exact:

```text
exact_rational + zero analytic tail
exact_decimal  + zero analytic tail
```

A participant-supplied `ball`, `directed_interval`, bounded `raw_float`, or nonzero `analytic_tail` that would otherwise promote is held at `INCOMPLETE` unless it is migrated to the proof-carrying source-bound protocol.

The new protocol is:

```text
source-bound-proof-carrying-numerics-v1
```

Current source model:

```text
exact_expression_v1
```

The engine verifies a finite exact-rational interval DAG. For every operation node, the participant-declared interval must contain the verifier-computed interval. A narrower forged interval fails.

Admitted operations:

```text
add
sub
mul
neg
div
```

Interval division is permitted only when the denominator enclosure excludes zero.

Current proof-bearing tail rules:

```text
zero
geometric_tail
```

For a geometric tail, the first omitted magnitude and ratio upper bound must reference verified DAG nodes, and the engine derives the tail itself.

The strict upper-bound terminal rule is:

```text
U < threshold                  PASS
L >= threshold                 FAIL
L = U = threshold              FAIL for strict <
L < threshold <= U             INCOMPLETE
```

This distinction is a valid challenge target. A break includes obtaining a strict certification from a forged narrow DAG interval, an interval division whose denominator contains zero, an unsupported source model, a participant-asserted legacy radius/tail without source proof, or a source-bound enclosure that reaches/crosses the threshold.

## Implementation Genesis boundary

Every final release Genesis commits `implementation_manifest_sha256`. This binds the rules to the parser/validator implementation used to interpret them.

A meaningful integrity break includes demonstrating that a materially changed committed parser/validator implementation can produce the same final-release implementation fingerprint or pass a correctly pinned Genesis without the expected implementation.

The fingerprint is not an external authenticity oracle. The published Git commit, immutable archive, signature, attestation, or equivalent external pin remains the expected-value anchor.

## Seam-quotient boundary

The seam protocol remains:

```text
first-visible-jet-seam-quotient-v1
```

Raw algebraic `1/0` and raw algebraic `0/0` remain invalid. The proof-bearing release model is `exact_polynomial_jet`.

```text
numerator order > denominator order    finite quotient zero
orders equal                            leading-coefficient quotient
numerator order < denominator order    divergent / no finite quotient
all denominator jets zero              incomplete / unresolved
approximate remainder model            incomplete until source validator closure
```

Theorem 47 supplies the source-bound trust architecture needed by a future approximate seam adapter, but it does not automatically validate arbitrary remainder fields.

## Allowed technical interaction

For a publicly activated endpoint, the invitation should state exactly which activities are permitted. Typical permitted interaction may include:

- submit Challenge Package JSON to the designated endpoint;
- inspect returned results, Challenge Genesis and Challenge Evaluation records;
- vary declared targets, evidence, obligations, negative controls, flow probes, burden/completion values, legacy arithmetic certificates, source-bound numerical traces, seam certificates, and threat-model fields within the published protocol;
- test malformed/boundary/mutation/parser-differential cases without resource exhaustion;
- test exact decimal/rational boundaries;
- test T47 DAG dependency ordering, duplicate IDs, forged interval narrowing, division-zero enclosure gates, unsupported source models, tail-rule conditions, threshold contact, and Genesis fingerprint/pinning;
- test Theorem-46 order mismatch, flat-denominator incompleteness, missing seam identity, and unvalidated approximate remainders;
- report reproducible findings with release commit, input, result, Genesis hash and Evaluation hash.

Do not infer authorization for activity not explicitly listed in the public invitation.

## Out of scope unless separately authorized

- third-party systems or infrastructure;
- destructive testing;
- denial-of-service or resource-exhaustion testing;
- credential theft, social engineering, or access-control bypass outside the designated test environment;
- deployment, redistribution, modification, or competing benchmarking where repository rights do not permit it;
- attacks on unrelated services, accounts, networks or data;
- treating unrestricted English semantics as claimed when `semantics.mode = payload_only`;
- treating a participant-supplied external measurement/backend/norm claim as authenticated unless the selected package/connector actually provides that source validator;
- treating an internally reported implementation hash as external authenticity when the executable itself is untrusted;
- treating the stateless engine as a replay database.

## Evidence standard for a reported break

A report should include:

1. release/version and exact source commit;
2. Challenge Package input or minimal reproducer;
3. returned result JSON;
4. Challenge Genesis hash;
5. Challenge Evaluation hash;
6. implementation-manifest SHA-256;
7. expected outcome under the declared contract;
8. observed outcome;
9. claimed break class;
10. for a T47 numerical finding, the exact node intervals, dependency graph, tail rule, threshold and expected verifier-derived enclosure;
11. for a seam finding, seam identity, model, coefficient arrays and expected first-visible classification;
12. enough information to reproduce without expanding scope.

A crash/parser error can be a software defect if it violates the connector contract, but is not automatically a theorem-level false acceptance.

## Replay boundary

Each run emits a hash-bound `CHALLENGE_EVALUATION`. The engine is stateless. A deployment promising replay rejection must provide persistent Evaluation-hash storage or equivalent ledger state outside the pure evaluator.

## Resource boundary

The T47 proof DAG currently has a 256-node protocol limit. This is **not** complete endpoint resource hardening. Global input-byte, nesting-depth, numeric-digit/exponent, CPU/memory, and request-rate controls remain a separate pre-public-endpoint engineering obligation. Resource-exhaustion attacks are therefore out of scope unless separately authorized.

## Participation and rights boundary

The public invitation should identify the exact endpoint and operational permission offered. This protocol document does not grant a general licence to copy, modify, deploy, host, benchmark, redistribute, commercialize, or create derivative works from repository materials.
