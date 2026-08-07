# Artificial Intelligence Trust Enablement v1.2.0

Release date: 2026-08-07

## Release focus

Version 1.2.0 promotes the repository from a primarily AI trust-enablement implementation to a connector-ready, fail-closed Challenge Engine backed by the foundational theorem and adversarial-audit layers.

The Challenge is defined narrowly: **break the declared claim-to-evidence closure contract, not the prose used to label the target.** Natural-language semantics are payload-only by default and enter the evaluation only through an explicitly declared semantic adapter.

## Challenge Engine

The release provides:

- `math` as the default package;
- `logic`, `code`, and authorization-gated `security_audit` packages;
- `exploratory`, `adversarial`, and `certified` modes;
- machine-readable threat models and break classes;
- explicit formal/non-formal evidence boundaries;
- SHA-256 `CHALLENGE_GENESIS` records with zero accepted claims and frozen rules of engagement;
- genesis pinning to detect later rule mutation;
- observer-flow probes and first-recognition-order checks;
- bilateral-defect and remainder controls;
- burden/reserve gates;
- finite-to-limit promotion requiring `finite_upper + completion_error < threshold`;
- stable JSON stdin/stdout connector behavior;
- explicit external evidence-authenticity boundary;
- fail-closed authorization for the security-audit package.

Meaningful break classes are:

- `false_acceptance`;
- `blindness_escape`;
- `scope_escape`;
- `negative_control_escape`;
- `invalid_promotion`;
- `flow_consistency_escape`;
- `ledger_integrity_failure`.

## Final hostile audit

The final adversarial release pass found and repaired concrete weaknesses involving duplicate identifiers, implicit/empty evidence, failed-evidence masking, malformed numeric inputs, flow-probe ambiguity, Python truthiness, and incomplete genesis commitment of enabled gates.

Final status:

```text
PASS_FINAL_CHALLENGE_RELEASE_AUDIT
```

Challenge Engine workflow:

```text
Ran 57 tests
OK
```

The 57 release tests include 35 dedicated hostile pre-release attacks.

The foundational mathematics/audit layer remains separately recorded at:

```text
236,456 exact/random/exhaustive adversarial cases
```

The two counts are intentionally not collapsed into one homogeneous number because they represent different kinds of evidence.

## Claim boundary

This release does not claim unrestricted English-language understanding, universal semantic truth, universal correctness, or automatic authentication of participant-supplied evidence. The Challenge Engine evaluates closure relative to the declared package, adapters, evidence, scope, obligations, thresholds, and threat model.

Non-formal evidence is admissible in exploratory and adversarial modes, but it does not become a formal certificate without the formal-promotion requirements of the selected package.

## Rights boundary

The Challenge protocol does not create a new licence. Repository use remains governed by `LICENSE`, `PATENT_NOTICE.md`, `COPYRIGHT_NOTICE.md`, and any separately issued written challenge authorization or scope.

## Reproducibility entry points

```bash
python challenge_engine/challenge.py --capabilities --compact
python -m unittest discover -s challenge_engine/tests -v
python challenge_engine/challenge.py challenge_engine/examples/math_challenge.json --compact
python challenge_engine/challenge.py challenge_engine/examples/nonformal_behavioral_challenge.json --compact
python challenge_engine/challenge.py challenge_engine/examples/security_audit_challenge.json --compact
```

See:

- `challenge_engine/README.md`
- `challenge_engine/RED_TEAM_RULES.md`
- `challenge_engine/CONNECTOR_CONTRACT.md`
- `challenge_engine/FINAL_ADVERSARIAL_RELEASE_AUDIT.md`
- `foundational_mathematics/invariant_gated_state_transitions/`
