# Artificial Intelligence Trust Enablement v1.2.0

Release date: 2026-08-07

## Verified source state

The post-Theorem-47 source-bound numerical theorem is verified on `Recognition-Kernel-Framework/main` at:

```text
1e4b75eebe634e6de3472aa25d9a0b557da39715
```

The RKF proof-lab CI and independent Recognition Kernel Review both passed on that exact commit.

The AI Challenge Engine integration is being verified through PR #16. The hardened PR head carries the proof-carrying numerical provenance gate and reports 124 Challenge Engine tests passing before final documentation synchronization. The eventual GitHub release / Zenodo archive must be cut from the final post-merge `main`, not from an older pre-proof-carrying snapshot.

## Release focus

Version 1.2.0 promotes the repository from a primarily AI trust-enablement implementation to a connector-ready, fail-closed Challenge Engine backed by foundational theorem and adversarial-audit layers.

The Challenge is defined narrowly: **break the declared claim-to-evidence closure contract, not the prose used to label the target.** Natural-language semantics are payload-only by default and enter the evaluation only through an explicitly declared semantic adapter.

For mathematics, a new adversarial subclass is now explicit: **formal numeric overclaim**. This is a special case of mathematical hallucination in which a conclusion claims more numerical certainty than its admitted source trace, remainder proof, or dependency closure establishes.

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
- package-manifest hashing inside Genesis;
- genesis pinning to detect later rule mutation;
- SHA-256 `CHALLENGE_EVALUATION` records binding each input/result under its Genesis;
- observer-flow probes, burden/reserve gates and finite-to-limit checks;
- exact-rational / interval-ball arithmetic certificate support;
- separate arithmetic-radius and analytic-tail channels;
- proof-carrying numerical provenance for formal numeric-overclaim detection;
- source-completeness/no-blindness gating of proof traces;
- first-visible-jet seam-quotient protocol for an exact finite-jet class of apparent `0/0` limits;
- explicit rejection of raw algebraic `1/0` and raw algebraic `0/0` as finite values;
- fail-closed handling of unresolved flat denominator jets and unvalidated approximate seam remainders;
- machine binding of `target.toe` to authorized `scope.target` for scoped packages;
- stable JSON stdin/stdout connector behavior;
- explicit external evidence-authenticity and replay boundaries.

Meaningful break classes remain `false_acceptance`, `blindness_escape`, `scope_escape`, `negative_control_escape`, `invalid_promotion`, `flow_consistency_escape`, and `ledger_integrity_failure`.

## Hostile audit sequence

The first hostile release pass repaired duplicate identifiers, implicit/empty evidence, failed-evidence masking, malformed numeric inputs, flow-probe ambiguity, Python truthiness, and incomplete Genesis commitment of enabled gates.

The parser/ledger seal then repaired duplicate JSON-key differentials, non-standard JSON numbers, malformed package/mode fallback, package path abuse, scoped TOE mismatch, missing package-manifest commitment, missing evaluation-outcome hashes, and a binary floating-point threshold false-pass route.

The arithmetic-enclosure pass added the typed exact-rational / directed-enclosure contract, long-decimal preservation, interval/ball checks, explicit arithmetic/tail separation, missing-radius controls, and independent-enclosure consistency.

The seam-quotient pass consumed the separately verified first-visible-jet theorem and kept raw field division by zero invalid.

The source-bound numerical pass then closed the most important remaining numerical trust membrane. A participant-supplied radius, analytic tail, backend label, or overlapping set of claimed enclosures is no longer sufficient for certification. Approximate numerical promotion requires the generic protocol:

```text
proof-carrying-numeric-closure-v1
```

The currently admitted proof-bearing subset uses exact rational interval DAGs, operations `add/sub/mul/neg/div`, source-completeness closure, and `zero` or `geometric_tail` tail rules. Division fails if the denominator enclosure contains zero. A declared node interval narrower than the verifier-computed enclosure fails. Unsupported source/tail classes remain incomplete rather than becoming proof by nomenclature.

Strict boundary handling is certainty-aware:

```text
verified upper < threshold                pass
verified lower >= threshold               fail
verified interval straddles/touches bound incomplete
```

Thus exact equality fails a strict inequality, while uncertain boundary contact remains incomplete.

Current audit statuses:

```text
PASS_FINAL_CHALLENGE_SEAL_AUDIT
PASS_EXACT_RATIONAL_ENCLOSURE_AUDIT
PASS_EXACT_FINITE_JET_SEAM_QUOTIENT_AUDIT
PASS_PROOF_CARRYING_NUMERIC_HALLUCINATION_AUDIT
```

Current Challenge Engine hardened PR-head workflow:

```text
Ran 124 tests
OK
```

The foundational mathematics/audit layer remains separately recorded at:

```text
236,456 exact/random/exhaustive adversarial cases
```

The two counts are intentionally not collapsed into one homogeneous number because they represent different kinds of evidence.

## Numerical claim boundary

The low-level arithmetic protocol remains:

```text
exact-rational-directed-enclosure-v1
```

The proof-carrying promotion layer is:

```text
proof-carrying-numeric-closure-v1
```

Exact primitive rational/finite-decimal values with zero analytic tail retain the exact compatibility path. Nonzero tails and approximate radius/enclosure claims require admitted source-bound validation before formal promotion. Independent-enclosure overlap is a necessary consistency check only; it is not sufficient proof of target containment.

The validator manifest hash is committed into Challenge Genesis when a proof-carrying numeric trace is declared. This is an integrity commitment, not a self-authenticating external trust anchor. Executable/release authenticity still requires an external commit/archive/signature or equivalent deployment pin.

## Seam-quotient claim boundary

The seam protocol is:

```text
first-visible-jet-seam-quotient-v1
```

It is a theorem-backed limit classification for declared vanishing functions on a named seam, not a redefinition of field arithmetic. The exact finite-jet adapter cannot resolve flat-function cases and does not claim uniqueness across genuinely different seams. The general quantitative quotient enclosure remains gated until its remainder and denominator-separation hypotheses are source-validated.

## General claim boundary

This release does not claim unrestricted English-language understanding, universal semantic truth, universal mathematical truth, universal proof checking, automatic authentication of participant-supplied evidence, universal numerical stability, correctness of arbitrary external numerical backends, universal source completeness, or stateless replay detection.

`CHALLENGE_EVALUATION` gives each evaluated input/result a reproducible hash and optional parent link. Detecting reuse of an old valid evaluation as a new request requires persistent connector/ledger memory.

Resource-exhaustion controls such as maximum input bytes, nesting depth, numeric token size, proof-DAG node count and validation-work budget remain a separate engineering hardening gate.

## Rights boundary

The Challenge protocol does not create a new licence. Repository use remains governed by `LICENSE`, `PATENT_NOTICE.md`, `COPYRIGHT_NOTICE.md`, and any separately issued written challenge authorization or scope.

## Reproducibility entry points

```bash
python challenge_engine/challenge.py --capabilities --compact
python -m unittest discover -s challenge_engine/tests -v
python challenge_engine/challenge.py challenge_engine/examples/math_challenge.json --compact
python challenge_engine/challenge.py challenge_engine/examples/arithmetic_ball_challenge.json --compact
python challenge_engine/challenge.py challenge_engine/examples/seam_quotient_challenge.json --compact
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
- `challenge_engine/SEAM_QUOTIENT_AUDIT.md`
- `challenge_engine/PROOF_CARRYING_NUMERIC_HALLUCINATION_AUDIT.md`
- `foundational_mathematics/invariant_gated_state_transitions/`
