# Zenodo release metadata: v1.2.0

Use this as the copy/paste release record for the audited Challenge Engine snapshot.

## Title

Artificial Intelligence Trust Enablement v1.2.0: Challenge Engine and Foundational Verification

## Version

1.2.0

## Publication date

2026-08-07

## Creator

Monty Dabas  
Independent Researcher  
ORCID: 0009-0005-6948-209X

## Resource type

Software

## Description

Artificial Intelligence Trust Enablement v1.2.0 adds a connector-ready, fail-closed Challenge Engine to the existing AI trust-enablement repository. The engine evaluates declared claim-to-evidence closure contracts rather than unrestricted natural-language truth. It supports exploratory, adversarial and certified modes; mathematics, logic, code and authorization-gated security-audit packages; explicit formal/non-formal evidence boundaries; SHA-256 Challenge Genesis and Challenge Evaluation records; observer-flow probes; burden/reserve checks; finite-to-limit completion gates; strict JSON connector parsing; package-manifest commitment; and scoped target-of-evaluation binding.

The release includes the numerical protocol `exact-rational-directed-enclosure-v1`. Finite connector decimals retain their declared lexemes for exact threshold and canonical-contract decisions. Exact integers/rationals/finite decimals occupy the zero-arithmetic-radius sector; arbitrary-precision exact values may be supplied as quoted decimal or rational strings; approximate values may be represented as directed intervals or balls. Arithmetic uncertainty and analytic/truncation uncertainty remain separate. The declared scalar closure rule is `enclosure_upper + analytic_tail < threshold`; equality is not a strict promotion. External numerical-backend, radius and analytic-tail provenance are not authenticated merely because a participant supplies such fields, and remain source/adapter trust obligations pending the dedicated validator layer.

The release also adds `first-visible-jet-seam-quotient-v1`, consuming the separately verified Recognition-Kernel First-Visible-Jet Seam Quotient Closure Theorem. This protocol does not redefine ordinary division by zero. Raw algebraic `1/0` and `0/0` remain invalid. The proof-bearing implementation is intentionally limited to exact polynomial jets for two vanishing functions on one declared seam. Equal first-visible orders give the exact leading-coefficient ratio; a higher numerator order gives quotient zero; a higher denominator order gives no finite quotient; and all-zero declared denominator jets remain `INCOMPLETE_FLAT_OR_UNRESOLVED`. The more general analytic/remainder-bearing seam model remains incomplete until a trusted remainder and denominator-separation validator closes the theorem hypotheses.

Multiple hostile release passes tested duplicate identifiers and keys, malformed/non-standard numbers, package/mode fallback, package path abuse, exact threshold boundaries, scoped TOE mismatch, package-manifest mutation, Genesis integrity, evaluation-result chaining, long exact decimal declarations, rational normalization, interval/ball boundaries, missing floating-point radii, disjoint enclosures, zero denominators, exact first-visible-jet quotient classification, order mismatch, flat-denominator incompleteness, seam Genesis mutation, and attempted promotion of unvalidated approximate seam remainders.

The current Challenge Engine workflow completes **112 unit/adversarial tests** successfully. Separately, the foundational mathematics/audit layer records **236,456 exact/random/exhaustive adversarial cases**. These counts are reported separately because they represent different forms of verification evidence.

Current release audit statuses:

```text
PASS_FINAL_CHALLENGE_SEAL_AUDIT
PASS_EXACT_RATIONAL_ENCLOSURE_AUDIT
PASS_EXACT_FINITE_JET_SEAM_QUOTIENT_AUDIT
```

The release does not claim unrestricted English-language understanding, universal semantic truth, universal correctness, universal numerical stability, correctness of arbitrary external numerical backends, automatic authentication of participant-supplied evidence/radii/tails/remainders, a universal algebraic value for `0/0`, uniqueness across genuinely different seams, or stateless replay detection. Challenge Evaluation hashes make individual outcomes reproducible, while replay rejection and external evidence/backend validation remain persistent connector/package responsibilities unless separately authenticated.

Repository use remains governed by the repository LICENSE, PATENT_NOTICE.md, COPYRIGHT_NOTICE.md, and any separately declared challenge authorization/scope. The Challenge protocol itself grants no additional copyright, patent, deployment, benchmarking, or derivative-work rights.

## Keywords

- artificial intelligence
- AI safety
- hallucination detection
- challenge engine
- adversarial testing
- red teaming
- formal verification
- fail-closed evaluation
- validated numerics
- interval arithmetic
- ball arithmetic
- exact rational arithmetic
- indeterminate limits
- seam quotient
- first-visible jet
- machine-readable certificates
- challenge genesis
- challenge evaluation
- persistent records
- trustworthy AI

## Important release files

- `challenge_engine/README.md`
- `challenge_engine/RED_TEAM_RULES.md`
- `challenge_engine/CONNECTOR_CONTRACT.md`
- `challenge_engine/FINAL_ADVERSARIAL_RELEASE_AUDIT.md`
- `challenge_engine/FINAL_SEAL_AUDIT.md`
- `challenge_engine/ARITHMETIC_ENCLOSURE_AUDIT.md`
- `challenge_engine/SEAM_QUOTIENT_AUDIT.md`
- `challenge_engine/examples/arithmetic_ball_challenge.json`
- `challenge_engine/examples/seam_quotient_challenge.json`
- `RELEASE_NOTES_v1.2.0.md`
- `foundational_mathematics/invariant_gated_state_transitions/`

## DOI handling

The repository currently carries `10.5281/zenodo.21300179` in `CITATION.cff` and the README badge. Before publishing the new Zenodo version, verify in the Zenodo UI whether this is the concept DOI or an older version DOI. After Zenodo mints the v1.2.0 version DOI, use the newly minted DOI for that immutable version while retaining the Zenodo concept DOI as the stable all-versions reference when appropriate.
