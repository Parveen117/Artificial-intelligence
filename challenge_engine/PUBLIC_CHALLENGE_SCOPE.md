# Public Challenge Scope Template

This document defines the technical scope to publish alongside a public Challenge invitation. It does **not** replace or modify the repository `LICENSE`, `PATENT_NOTICE.md`, or `COPYRIGHT_NOTICE.md`, and it does not by itself grant repository-use rights beyond those documents or a separate written authorization.

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

`target.toe` must match `scope.target`. Authorization for one target is not authorization for another target with conveniently similar prose.

## Challenge objective

A participant should attempt to demonstrate a meaningful break of the declared claim-to-evidence closure contract. A meaningful break is one of the machine-readable break classes published by the engine:

- `false_acceptance`
- `blindness_escape`
- `scope_escape`
- `negative_control_escape`
- `invalid_promotion`
- `flow_consistency_escape`
- `ledger_integrity_failure`

Natural-language ambiguity, rhetorical tricks, or semantic disagreement are not a break unless the selected package explicitly declares a semantic adapter and the challenge concerns that adapter.

For numerical challenges, a meaningful break includes demonstrating that the engine grants a strict promotion even though the declared outward arithmetic enclosure plus analytic tail reaches or crosses the threshold, or that mutually disjoint claimed certified paths are nevertheless accepted as compatible.

For the seam-quotient protocol, a meaningful break includes making raw division by zero receive a finite certified value, making an unresolved all-zero denominator jet receive a finite value, making a divergent order mismatch receive a finite quotient, or making an approximate/remainder-bearing seam certify without its required validator.

## Allowed technical interaction

For a publicly activated endpoint, the invitation should state exactly which of the following are permitted:

- submit Challenge Package JSON to the designated endpoint;
- inspect returned machine-readable results, Challenge Genesis records and Challenge Evaluation records;
- vary targets, evidence, obligations, negative controls, flow probes, burden values, completion values, arithmetic certificates, seam-quotient certificates and threat-model fields within the published protocol;
- attempt malformed, adversarial, boundary, mutation, parser-differential and fail-closed test cases against the designated Challenge interface;
- attempt duplicate-key, exact-decimal, rational, interval/ball and numeric-boundary inputs against the documented connector interface without resource-exhaustion behavior;
- attempt invalid arithmetic promotion using missing radii, exact equality, negative radii, malformed rational denominators or disjoint certified enclosures;
- attempt seam-quotient attacks using unequal first-visible orders, all-zero denominator jets, nonzero endpoints, missing seam identity, zero rational denominators, and unvalidated approximate remainder claims;
- report reproducible findings with the relevant release/version, Genesis hash and Evaluation hash.

Do not infer authorization for any activity not explicitly listed in the public invitation.

## Out of scope unless separately authorized

- third-party systems or infrastructure;
- destructive testing;
- denial-of-service or resource-exhaustion attacks;
- credential theft, social engineering, or access-control bypass outside the designated test environment;
- deployment, redistribution, modification, or competing benchmarking of repository code where the repository licence does not permit it;
- attacks on unrelated services, accounts, networks, or data;
- claims that unrestricted English semantics are part of the engine when `semantics.mode = payload_only`;
- treating a participant-supplied evidence status as independently authenticated when the selected connector/package provides no provenance or attestation mechanism;
- treating a participant-supplied interval, ball, radius, analytic tail or remainder as independently validated merely because the field is present. Backend/source validation is a separate connector/package obligation;
- treating the stateless engine as a replay database. Replay rejection requires the persistent connector/ledger to remember prior Evaluation hashes.

## Evidence standard for a reported break

A report should include:

1. release/version and source commit;
2. Challenge Package input or a minimal reproducer;
3. returned result JSON;
4. Challenge Genesis hash;
5. Challenge Evaluation hash;
6. expected outcome under the declared contract;
7. observed outcome;
8. the break class being claimed;
9. for a numerical break, the exact rational/decimal/enclosure values and arithmetic/analytic uncertainty channels involved;
10. for a seam-quotient break, the seam identity, model, exact coefficient arrays and expected first-visible-order classification;
11. enough information to reproduce the result without expanding scope.

A parser error or crash is a software defect if it violates the documented connector contract, but it is not automatically a theorem-level false acceptance.

## Genesis and rules of engagement

Challenge Genesis freezes the declared rules before evaluation:

```text
accepted_claims = 0
parent = null
rules_frozen = true
```

The sealed Genesis commits the selected package manifest, parser/arithmetic contract, exact connector numeric declarations, and any declared arithmetic or seam-quotient certificate.

If a participant changes a committed target, scope, threat model, adapter identity, enabled gate, threshold, arithmetic enclosure, analytic tail, seam identity, seam coefficients, package rules, or scoped TOE identifier, the Genesis commitment should change. Changing an outcome/status under the same rules should not redefine Genesis.

## Evaluation record and replay boundary

Each run emits a hash-bound `CHALLENGE_EVALUATION` record. This binds the frozen Genesis to the normalized evaluated input, computed checks, and result. An optional parent Evaluation hash can be used by a persistent connector/ledger to create an append-only outcome chain.

The engine is stateless. It validates and carries a parent hash but cannot independently prove that the parent exists, that the submitted event is new, or that a historical valid Evaluation is not being replayed. A public deployment that promises replay rejection must implement persistent Evaluation-hash storage or equivalent ledger state outside the pure evaluation engine.

## Numerical boundary expectation

Exact finite decimals are interpreted by declared value for strict threshold decisions. Thus

```text
0.1 + 0.7 = 0.8
```

is a boundary, not a pass.

For an approximate numerical result the current declared arithmetic rule is:

```text
enclosure_upper + analytic_tail < threshold
```

A raw floating-point centre without an outward radius remains incomplete. Independent claimed scalar enclosures must have a nonempty common intersection. External validation of a claimed radius/tail is a separate trust obligation and must not be inferred from the field name.

## Seam-quotient boundary expectation

The seam protocol is not algebraic division by zero. In particular:

```text
1/0                           invalid
raw 0/0                       invalid
exact equal-order seam jets   leading-coefficient ratio
numerator higher order        zero quotient
numerator lower order         divergent / no finite quotient
all denominator jets zero     incomplete / unresolved
approximate remainder model   incomplete until validator closure
```

A participant may attack these distinctions. A valid finding would show the engine crossing one of these fail-closed boundaries, not merely observe that the classical symbol `0/0` is indeterminate.

## Participation and rights boundary

The public invitation should identify the exact endpoint and operational permission being offered. This protocol document does not grant a general licence to copy, modify, deploy, host, benchmark, redistribute, commercialize, or create derivative works from repository materials. Those matters remain governed by the existing repository rights notices and any separate written authorization issued for the Challenge.
