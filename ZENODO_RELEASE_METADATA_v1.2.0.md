# Zenodo release metadata: v1.2.0

Use this as the copy/paste release record for the audited RNKE / Challenge Engine snapshot.

## Title

Recognition Null Kernel Engine (RNKE) v1.2.0: Challenge Engine and Foundational Verification

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

## Release snapshot rule

The latest separately verified source-bound numerical theorem is present on `Parveen117/Recognition-Kernel-Framework/main` at:

```text
1e4b75eebe634e6de3472aa25d9a0b557da39715
```

Both RKF proof-lab CI and the independent Recognition Kernel Review passed on that exact commit.

The proof-carrying numerical integration was merged to `Parveen117/Artificial-intelligence/main` at `56011af8e01e98325e8ee86c532ded93c918c488`. The publication-safe RNKE framing was subsequently merged through PR #17 at:

```text
b41c96415bc7556992065c1e90cb4ca31fa0de71
```

The GitHub release / Zenodo archive must be cut from this publication-framed lineage or a later verified `main` commit that contains it. Do not archive an older pre-RNKE-framing snapshot.

## Description

Recognition Null Kernel Engine (RNKE) v1.2.0 is a public technical release of a general verification architecture for formalizable trust systems. A domain adapter presents explicit claims, evidence, dependencies, governing rules, admissible transitions, and committed state; RNKE evaluates whether the declared transition may be admitted, must be rejected, or remains incomplete under the selected verification contract.

RNKE is organized around three public principles: **Null-as-Cut**, in which verification begins from a structured genesis condition containing no admitted claims but a frozen rule structure; **Recognition Before Commitment**, in which a claim cannot promote itself and must close its declared evidence, dependency, invariant and proof obligations; and **Persistent Verification History**, in which accepted, rejected, refuted and unresolved events can remain bound to a tamper-evident lineage when the required persistent connector/ledger is present.

The current public Challenge Engine is a benchmark of RNKE rather than the full scope of the architecture. It deliberately emphasizes mathematics and other formal systems because they provide unusually sharp adversarial ground truth. In the mathematical package, the challenge is a form of **mathematical hallucination detection**: a break occurs if the engine promotes a conclusion whose admitted proof flow, dependency structure, numerical enclosure, or remainder obligations do not actually justify it. A **formal numeric overclaim** is one subclass of this broader failure.

The release supports exploratory, adversarial and certified modes; mathematics, logic, code and authorization-gated security-audit packages; explicit formal/non-formal evidence boundaries; SHA-256 Challenge Genesis and Challenge Evaluation records; observer-flow probes; burden/reserve checks; finite-to-limit completion gates; strict JSON connector parsing; package-manifest commitment; and scoped target-of-evaluation binding.

The low-level numerical protocol is `exact-rational-directed-enclosure-v1`. Finite connector decimals retain their declared lexemes for exact threshold and canonical-contract decisions. Exact integers/rationals/finite decimals occupy the zero-arithmetic-radius sector, while approximate values may be represented as intervals or balls.

The proof-carrying promotion protocol is `proof-carrying-numeric-closure-v1`. Its current proof-bearing subset verifies exact-rational interval DAGs with `exact_contract` source leaves, `add/sub/mul/neg/div` operations, an explicit source-completeness/no-blindness gate, and `zero` or `geometric_tail` analytic-tail rules. A participant may widen a computed enclosure but cannot shrink it below the verifier-computed enclosure. Division fails if the denominator enclosure contains zero. Unsupported source/tail classes remain incomplete.

A participant-supplied radius, analytic tail, backend label, or overlapping set of claimed enclosures does not self-validate. Overlap is consistency evidence only. Exact primitive rational/finite-decimal values with zero analytic tail retain the exact compatibility path.

Strict numerical classification is certainty-aware. A verified upper strictly below threshold passes. A verified lower at or above threshold fails, including exact equality for a strict claim. A non-singleton verified interval that touches or crosses the threshold while still containing sub-threshold values remains incomplete.

When proof-carrying numerics are declared, Challenge Genesis commits the proof trace, protocol identifier and a validator-manifest SHA-256. This provides implementation-integrity binding under the frozen challenge contract, but is not a self-authenticating external trust anchor.

The release also includes `first-visible-jet-seam-quotient-v1`. This does not redefine ordinary division by zero. Raw algebraic `1/0` and `0/0` remain invalid. The proof-bearing implementation is limited to exact polynomial jets for two vanishing functions on one declared seam; unresolved flat or approximate remainder-bearing cases remain incomplete until their source-bound remainder hypotheses close.

Multiple hostile passes test parser differentials, malformed/non-standard numbers, package/mode fallback, scoped TOE mismatch, Genesis/evaluation integrity, exact threshold boundaries, long decimal declarations, rational normalization, interval/ball boundaries, missing or forged numeric provenance, denominator-zero enclosures, narrowed proof-DAG intervals, source-completeness failures, exact strict-bound equality, uncertain boundary contact, seam quotient classification, flat-denominator incompleteness, and attempted self-promotion of unvalidated numerical radii/tails/remainders.

The current Challenge Engine workflow completes **124 unit/adversarial tests** successfully. Separately, the foundational mathematics/audit layer records **236,456 exact/random/exhaustive adversarial cases**. These counts are reported separately because they represent different forms of verification evidence.

Current release audit statuses:

```text
PASS_FINAL_CHALLENGE_SEAL_AUDIT
PASS_EXACT_RATIONAL_ENCLOSURE_AUDIT
PASS_EXACT_FINITE_JET_SEAM_QUOTIENT_AUDIT
PASS_PROOF_CARRYING_NUMERIC_HALLUCINATION_AUDIT
```

Candidate RNKE application domains include evidence-gated AI, software/specification verification, finance/compliance, scientific provenance, biotechnology workflows, law/governance records, and supply-chain provenance when the required domain semantics and source-authentication layers are supplied. These are application directions of the architecture, not claims that every listed adapter has already been completed or validated.

The release does not claim unrestricted English-language understanding, universal semantic or mathematical truth, universal proof checking, correctness/authenticity of arbitrary external numerical backends or measurements, universal source completeness, a universal algebraic value for `0/0`, uniqueness across genuinely different seams, stateless replay detection, immunity to every implementation vulnerability, or resource-exhaustion resistance. Resource budgets and external executable/source authenticity remain separate deployment hardening obligations.

Private hardware/device-enabling material is outside this public release.

Repository use remains governed by the repository LICENSE, PATENT_NOTICE.md, COPYRIGHT_NOTICE.md, and any separately declared challenge authorization/scope. The Challenge protocol itself grants no additional copyright, patent, deployment, benchmarking, or derivative-work rights.

## Keywords

- Recognition Null Kernel Engine
- RNKE
- verification architecture
- artificial intelligence
- AI safety
- hallucination detection
- mathematical hallucination
- formal numeric overclaim
- challenge engine
- adversarial testing
- red teaming
- formal verification
- proof-carrying numerics
- fail-closed evaluation
- validated numerics
- interval arithmetic
- exact rational arithmetic
- indeterminate limits
- seam quotient
- machine-readable certificates
- challenge genesis
- challenge evaluation
- trustworthy AI

## Important release files

- `RNKE_PUBLIC_INTRODUCTION.md`
- `challenge_engine/README.md`
- `challenge_engine/PUBLIC_CHALLENGE_SCOPE.md`
- `challenge_engine/RED_TEAM_RULES.md`
- `challenge_engine/CONNECTOR_CONTRACT.md`
- `challenge_engine/FINAL_ADVERSARIAL_RELEASE_AUDIT.md`
- `challenge_engine/FINAL_SEAL_AUDIT.md`
- `challenge_engine/ARITHMETIC_ENCLOSURE_AUDIT.md`
- `challenge_engine/SEAM_QUOTIENT_AUDIT.md`
- `challenge_engine/PROOF_CARRYING_NUMERIC_HALLUCINATION_AUDIT.md`
- `challenge_engine/examples/arithmetic_ball_challenge.json`
- `challenge_engine/examples/seam_quotient_challenge.json`
- `RELEASE_NOTES_v1.2.0.md`
- `foundational_mathematics/invariant_gated_state_transitions/`

## DOI handling

The repository currently carries `10.5281/zenodo.21300179` in `CITATION.cff` and the README badge. Before publishing the new Zenodo version, verify in the Zenodo UI whether this is the concept DOI or an older version DOI. After Zenodo mints the v1.2.0 version DOI, use the newly minted DOI for that immutable version while retaining the Zenodo concept DOI as the stable all-versions reference when appropriate.
