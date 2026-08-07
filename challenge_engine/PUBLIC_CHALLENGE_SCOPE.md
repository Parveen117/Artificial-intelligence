# Public Challenge Scope Template

This document defines the technical scope to publish alongside a public Challenge invitation. It does **not** replace or modify the repository `LICENSE`, `PATENT_NOTICE.md`, or `COPYRIGHT_NOTICE.md`, and it does not by itself grant repository-use rights beyond those documents or a separate written authorization.

## Target of evaluation

The designated Challenge Engine endpoint or connector instance running the published release candidate.

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

## Allowed technical interaction

For a publicly activated endpoint, the invitation should state exactly which of the following are permitted:

- submit Challenge Package JSON to the designated endpoint;
- inspect returned machine-readable results and Challenge Genesis records;
- vary targets, evidence, obligations, negative controls, flow probes, burden values, completion values, and threat-model fields within the published protocol;
- attempt malformed, adversarial, boundary, mutation, and fail-closed test cases against the designated Challenge interface;
- report reproducible findings with the relevant release/version and genesis hash.

Do not infer authorization for any activity not explicitly listed in the public invitation.

## Out of scope unless separately authorized

- third-party systems or infrastructure;
- destructive testing;
- denial-of-service or resource-exhaustion attacks;
- credential theft, social engineering, or access-control bypass outside the designated test environment;
- deployment, redistribution, modification, or competing benchmarking of repository code where the repository licence does not permit it;
- attacks on unrelated services, accounts, networks, or data;
- claims that unrestricted English semantics are part of the engine when `semantics.mode = payload_only`.

## Evidence standard for a reported break

A report should include:

1. release/version and, when available, source commit;
2. Challenge Package input or a minimal reproducer;
3. returned result JSON;
4. Challenge Genesis hash;
5. expected outcome under the declared contract;
6. observed outcome;
7. the break class being claimed;
8. enough information to reproduce the result without expanding scope.

A parser error or crash is a software defect if it violates the documented connector contract, but it is not automatically a theorem-level false acceptance.

## Genesis and rules of engagement

Challenge Genesis freezes the declared rules before evaluation:

```text
accepted_claims = 0
parent = null
rules_frozen = true
```

If a participant changes a committed target, scope, threat model, adapter identity, enabled gate, or threshold, the genesis commitment should change. Changing an outcome/status under the same rules should not redefine genesis.

## Participation and rights boundary

The public invitation should identify the exact endpoint and operational permission being offered. This protocol document does not grant a general licence to copy, modify, deploy, host, benchmark, redistribute, commercialize, or create derivative works from repository materials. Those matters remain governed by the existing repository rights notices and any separate written authorization issued for the Challenge.
