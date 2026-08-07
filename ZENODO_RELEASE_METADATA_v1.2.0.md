# Zenodo release metadata: v1.2.0

Use this as the copy/paste release record for the final audited Challenge Engine snapshot after Theorem-47 integration.

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

## Release snapshot rule

The separately verified source-bound numerical theorem is on:

```text
Parveen117/Recognition-Kernel-Framework
main e0e0d051fecf9d7a87fe6386864c7153dd614324
```

Its proof packet passed the RKF proof-lab matrix on Python 3.11 and 3.12 and the independent Recognition Kernel Review workflow.

The AI release archive must be created from the **final Artificial-intelligence `main` commit after Theorem-47 integration and post-merge CI**. Do not archive the older pre-T47 snapshots `b4444a9...` or `dd1503d...` as the final v1.2.0 release.

Record the exact final AI commit here only after the T47 PR/merge and all three post-main workflows have passed.

## Description

Artificial Intelligence Trust Enablement v1.2.0 provides a connector-ready, fail-closed Challenge Engine for declared claim-to-evidence closure contracts. The engine does not claim unrestricted natural-language truth. It supports exploratory, adversarial and certified modes; mathematics, logic, code and authorization-gated security-audit packages; formal/non-formal evidence boundaries; strict JSON parsing; exact decimal-lexeme preservation; machine-bound security scope; SHA-256 Challenge Genesis and Challenge Evaluation records; observer-flow, burden and finite-to-limit gates; theorem-backed numerical checks; and explicit rights/replay/external-source boundaries.

The release includes the exact arithmetic protocol `exact-rational-directed-enclosure-v1` and the newer source-bound numerical protocol `source-bound-proof-carrying-numerics-v1`, derived from Recognition-Kernel Theorem 47. The T47 engine subset uses exact rational interval proof DAGs. Every operation enclosure is recomputed from previously verified dependencies, so a participant may widen an interval but cannot obtain certification by shrinking it below the verifier-computed enclosure. Interval division is rejected when the denominator enclosure contains zero.

The initial proof-bearing source model is `exact_expression_v1`, with exact operations `add`, `sub`, `mul`, `neg`, and `div`. The current proof-bearing tail rules are `zero` and `geometric_tail`. For a geometric tail, the first omitted magnitude and ratio upper bound must reference verified DAG nodes, and the engine computes the final tail itself. Participant-supplied approximate radii or analytic tails therefore no longer become proof-bearing merely because they are syntactically valid.

Legacy arithmetic certificates remain readable for compatibility. Exact rational/decimal singleton values with zero analytic tail remain intrinsically exact. Directed intervals, balls, bounded raw floats, and exact values with a participant-supplied nonzero analytic tail are held at `INCOMPLETE` when they would otherwise promote without T47 source proof. Disjoint independent enclosures may still fail; overlap remains a consistency check rather than backend authentication.

The T47 strict-boundary rule distinguishes mathematical falsity from numerical uncertainty: `U < threshold` passes; `L >= threshold` fails; an exact singleton equal to the threshold fails a strict `<` claim; and a non-singleton enclosure touching/crossing the threshold remains incomplete.

Every Challenge Genesis now commits an `implementation_manifest_sha256` covering the current parser/engine numerical layers, primary Challenge schema, and package manifests. This intentionally advances pre-T47 Genesis hashes before the final release. The fingerprint is an integrity commitment under an externally pinned expected release, not an external authenticity oracle if the executable itself is untrusted.

The release also retains `first-visible-jet-seam-quotient-v1`. Raw algebraic `1/0` and `0/0` remain invalid. The proof-bearing seam implementation remains limited to exact polynomial jets; equal first-visible orders give the exact leading-coefficient quotient, higher numerator order gives zero, lower numerator order gives no finite quotient, and all-zero denominator jets remain `INCOMPLETE_FLAT_OR_UNRESOLVED`. Approximate seam remainders remain incomplete until their source bounds are connected to an admitted validator. Theorem 47 supplies that trust architecture but does not authenticate arbitrary remainder fields by itself.

The current T47 development Challenge Engine suite reports **131 unit/adversarial tests** successfully. Separately, the foundational mathematics/audit layer records **236,456 exact/random/exhaustive adversarial cases**. These counts are intentionally separate because they represent different evidence classes.

Current audit sequence:

```text
PASS_FINAL_CHALLENGE_SEAL_AUDIT
PASS_EXACT_RATIONAL_ENCLOSURE_AUDIT
PASS_EXACT_FINITE_JET_SEAM_QUOTIENT_AUDIT
PASS_SOURCE_BOUND_NUMERICS_T47_AUDIT
```

The release does not claim unrestricted English-language understanding, universal semantic truth, universal correctness, correctness/authenticity of arbitrary external numerical backends, universal real-world source validation, universal source completeness, external executable authenticity from an internally reported hash, stateless replay rejection, or complete denial-of-service/resource-exhaustion hardening. Global input-byte, nesting-depth, numeric digit/exponent, CPU/memory and request-rate controls remain a separate pre-public-endpoint engineering gate.

Repository use remains governed by `LICENSE`, `PATENT_NOTICE.md`, `COPYRIGHT_NOTICE.md`, and any separately declared challenge authorization/scope. The Challenge protocol itself grants no additional copyright, patent, deployment, benchmarking, or derivative-work rights.

## Keywords

- artificial intelligence
- AI safety
- challenge engine
- adversarial testing
- formal verification
- fail-closed evaluation
- proof-carrying numerics
- validated numerics
- interval arithmetic
- exact rational arithmetic
- source validation
- theorem-backed verification
- indeterminate limits
- seam quotient
- challenge genesis
- challenge evaluation
- trustworthy AI

## Important release files

- `challenge_engine/CONNECTOR_CONTRACT.md`
- `challenge_engine/PUBLIC_CHALLENGE_SCOPE.md`
- `challenge_engine/SOURCE_BOUND_NUMERICS_AUDIT.md`
- `challenge_engine/schema/source_bound_numerics.schema.json`
- `challenge_engine/ARITHMETIC_ENCLOSURE_AUDIT.md`
- `challenge_engine/SEAM_QUOTIENT_AUDIT.md`
- `challenge_engine/examples/source_bound_numerics_challenge.json`
- `challenge_engine/examples/arithmetic_ball_challenge.json`
- `challenge_engine/examples/seam_quotient_challenge.json`
- `RELEASE_NOTES_v1.2.0.md`
- `foundational_mathematics/invariant_gated_state_transitions/`

## DOI handling

The repository currently carries `10.5281/zenodo.21300179` in `CITATION.cff` and the README badge. Before publishing the new Zenodo version, verify in the Zenodo UI whether this is the concept DOI or an older version DOI. After Zenodo mints the v1.2.0 version DOI, use the newly minted DOI for that immutable version while retaining the concept DOI as the stable all-versions reference when appropriate.
