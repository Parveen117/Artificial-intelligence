# Artificial Intelligence Trust Enablement v1.2.0

Release date: 2026-08-07

## Release focus

Version 1.2.0 promotes the repository from a primarily AI trust-enablement implementation to a connector-ready, fail-closed Challenge Engine backed by foundational theorem and adversarial-audit layers.

The Challenge is defined narrowly: **break the declared claim-to-evidence closure contract, not the prose used to label the target.** Natural-language semantics are payload-only by default and enter the evaluation only through an explicitly declared semantic adapter.

## Challenge Engine

The release provides:

- `math` as the default package;
- `logic`, `code`, and authorization-gated `security_audit` packages;
- `exploratory`, `adversarial`, and `certified` modes;
- machine-readable threat models and break classes;
- explicit formal/non-formal evidence boundaries;
- strict connector JSON with duplicate-key and NaN/Infinity rejection;
- exact connector decimal-lexeme preservation for declared-value decisions;
- SHA-256 `CHALLENGE_GENESIS` records with zero accepted claims and frozen rules of engagement;
- package-manifest hashing inside Genesis so package-rule mutation changes the commitment;
- genesis pinning to detect later rule mutation;
- SHA-256 `CHALLENGE_EVALUATION` records binding each input/result under its Genesis;
- optional evaluation-parent hashes for connector/ledger chaining;
- observer-flow probes and first-recognition-order checks;
- bilateral-defect and remainder controls;
- burden/reserve gates;
- finite-to-limit promotion requiring strict outward reserve;
- `exact_rational`, `exact_decimal`, `directed_interval`, `ball`, and bounded `raw_float` arithmetic certificates;
- separate arithmetic-radius and analytic-tail channels;
- optional independent-enclosure common-intersection checks;
- raw floating-point centres without a validated outward radius held at `INCOMPLETE`;
- machine binding of `target.toe` to authorized `scope.target` for scoped packages;
- stable JSON stdin/stdout connector behavior;
- explicit external evidence-authenticity and replay boundaries;
- fail-closed authorization for the security-audit package.

Meaningful break classes are:

- `false_acceptance`;
- `blindness_escape`;
- `scope_escape`;
- `negative_control_escape`;
- `invalid_promotion`;
- `flow_consistency_escape`;
- `ledger_integrity_failure`.

## Final hostile audits

The first hostile release pass found and repaired concrete weaknesses involving duplicate identifiers, implicit/empty evidence, failed-evidence masking, malformed numeric inputs, flow-probe ambiguity, Python truthiness, and incomplete Genesis commitment of enabled gates.

The final seal then targeted a different class of attacks and found further real issues: duplicate JSON-key parser differentials, non-standard JSON numbers, silent fallback from malformed package/mode values, package path/name abuse, scoped TOE mismatch, missing package-manifest commitment, missing evaluation-outcome hashes, and a binary floating-point threshold error that could turn the exact boundary `0.1 + 0.7 = 0.8` into a false strict pass.

The arithmetic-enclosure pass then generalized that patch into a typed numerical contract. Exact integers/rationals/finite decimals occupy the zero-radius sector; approximate numerical results require directed intervals or validated balls; analytic truncation/completion tails remain separate; and strict promotion is granted only when the outward arithmetic upper bound plus analytic tail remains below the threshold. Long decimal lexemes, arbitrary-precision exact strings, raw-float missing-radius cases, interval/ball boundaries, independent enclosure disagreement, and rational-denominator failures are included in the hostile suite.

Final audit statuses:

```text
PASS_FINAL_CHALLENGE_SEAL_AUDIT
PASS_EXACT_RATIONAL_ENCLOSURE_AUDIT
```

Challenge Engine workflow:

```text
Ran 98 tests
OK
```

The foundational mathematics/audit layer remains separately recorded at:

```text
236,456 exact/random/exhaustive adversarial cases
```

The two counts are intentionally not collapsed into one homogeneous number because they represent different kinds of evidence.

## Numerical claim boundary

The public arithmetic protocol is:

```text
exact-rational-directed-enclosure-v1
```

For a scalar upper-threshold certificate, the rule is:

```text
enclosure_upper + analytic_tail < threshold
```

Exact values have zero arithmetic radius. Arbitrary-precision exact values should be carried as quoted decimal/rational strings. A raw floating-point centre is not proof-bearing without a separately validated outward radius. An external interval/ball backend is not authenticated merely because it supplies a radius; backend validity and provenance remain connector/package obligations.

## General claim boundary

This release does not claim unrestricted English-language understanding, universal semantic truth, universal correctness, automatic authentication of participant-supplied evidence, universal numerical stability, or stateless replay detection. The Challenge Engine evaluates closure relative to the declared package, adapters, evidence, scope, obligations, arithmetic enclosures, thresholds, and threat model.

Non-formal evidence is admissible in exploratory and adversarial modes, but it does not become a formal certificate without the formal-promotion requirements of the selected package.

`CHALLENGE_EVALUATION` gives each evaluated input/result a reproducible hash and optional parent link. Detecting reuse of an old valid evaluation as a new request requires persistent connector/ledger memory.

## Rights boundary

The Challenge protocol does not create a new licence. Repository use remains governed by `LICENSE`, `PATENT_NOTICE.md`, `COPYRIGHT_NOTICE.md`, and any separately issued written challenge authorization or scope.

## Reproducibility entry points

```bash
python challenge_engine/challenge.py --capabilities --compact
python -m unittest discover -s challenge_engine/tests -v
python challenge_engine/challenge.py challenge_engine/examples/math_challenge.json --compact
python challenge_engine/challenge.py challenge_engine/examples/arithmetic_ball_challenge.json --compact
python challenge_engine/challenge.py challenge_engine/examples/nonformal_behavioral_challenge.json --compact
python challenge_engine/challenge.py challenge_engine/examples/security_audit_challenge.json --compact
```

See:

- `challenge_engine/README.md`
- `challenge_engine/RED_TEAM_RULES.md`
- `challenge_engine/CONNECTOR_CONTRACT.md`
- `challenge_engine/FINAL_ADVERSARIAL_RELEASE_AUDIT.md`
- `challenge_engine/FINAL_SEAL_AUDIT.md`
- `challenge_engine/ARITHMETIC_ENCLOSURE_AUDIT.md`
- `foundational_mathematics/invariant_gated_state_transitions/`
