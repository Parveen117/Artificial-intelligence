# Recognition Null Kernel Engine (RNKE)

## Artificial Intelligence Trust Enablement and Challenge Engine

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21300179.svg)](https://doi.org/10.5281/zenodo.21300179)

This repository contains a deployable AI trust-enablement service and the public Challenge Engine for the **Recognition Null Kernel Engine (RNKE)** verification architecture. The implemented stack includes hallucination-residue evaluation, confidence-collapse detection, release control, certificate generation, ECL-style finality, Lambda-Laplace analytic diagnostics, topological-memory / winding-sector diagnostics, Future Arrow forecasting, and theorem-backed challenge testing.

> **Patent status.** This repository is associated with inventor-controlled patent filings and related intellectual-property rights. Publication does not grant any patent license. See [`PATENT_NOTICE.md`](PATENT_NOTICE.md).
>
> **Copyright and license boundary.** This is a public technical inspection and citation release, not an unrestricted open-source grant. All rights are reserved unless a separate written license states otherwise. See [`LICENSE`](LICENSE) and [`COPYRIGHT_NOTICE.md`](COPYRIGHT_NOTICE.md).
>
> **Public release boundary.** This repository is a selected public technical release and does not reproduce the complete private filing, research, hardware, or internal development record. See [`docs/PUBLIC_RELEASE_BOUNDARY.md`](docs/PUBLIC_RELEASE_BOUNDARY.md).

## RNKE: a general verification machine

RNKE is a foundational verification architecture for **formalizable trust systems**. A domain adapter presents explicit claims, evidence, dependencies, governing rules, admissible transitions, and committed state. The verification kernel then decides whether the proposed transition is admitted, rejected, or remains incomplete.

The architecture is organized around three principles:

1. **Null-as-Cut.** Verification begins from a structured genesis condition containing no admitted claims but a fixed rule structure. The null state is operational; this does not redefine arithmetic zero.
2. **Recognition Before Commitment.** A claim is promoted only when its required evidence, dependencies, invariants, and proof obligations close. Assertion alone has no authority.
3. **Persistent Verification History.** Accepted, rejected, refuted, and unresolved events can remain bound to a tamper-evident lineage so that rule mutation, inconsistent replay, or historical alteration can be detected when the required persistent connector/ledger is present.

Abstractly, the interface is

```text
V(claim, evidence, dependencies, rules, committed_state)
    -> ADMIT | REJECT | INCOMPLETE
```

RNKE is therefore more general than a mathematical proof checker and more structured than a hash chain. A proof checker, numerical verifier, code/specification checker, compliance engine, provenance system, or evidence-gated AI can each be expressed as a domain adapter of the same claim-to-evidence closure architecture.

This is a statement about the architecture, **not** a claim that every possible real-world domain has already been modeled or validated. External evidence, measurements, sensors, legal facts, or numerical backends still require the source/authentication obligations declared by their adapters.

The full publication-safe framing is in [`RNKE_PUBLIC_INTRODUCTION.md`](RNKE_PUBLIC_INTRODUCTION.md).

### The public Challenge is a special case

The present Challenge Engine deliberately starts with mathematics and other formal systems because they provide unusually sharp adversarial ground truth. In the mathematical package, the challenge is a form of **mathematical hallucination detection**: can an attacker make the engine promote a conclusion whose proof flow, dependency chain, numerical enclosure, or remainder obligations do not actually close?

A formal numeric overclaim is one subclass of this larger failure. Missing lemmas, hidden dependencies, fabricated precision, unjustified convergence, discarded remainders, illegal division-by-zero steps, and unsupported proof transitions are other examples of the same structural problem: the claimed conclusion outruns the verified evidence.

The scope relation is therefore:

```text
RNKE
  -> formal-system verification
      -> mathematical hallucination detection
          -> current public Challenge
```

**The Challenge demonstrates RNKE. It does not define RNKE.**

Candidate application domains include AI safety, software/cybersecurity, finance/compliance, scientific provenance, biotechnology workflows, law/governance records, and supply-chain provenance where the required semantics and source-authentication layers are explicitly supplied. These are application directions, not claims that every listed adapter is already completed.

> **Design principle:** Do not trust the claim. Verify the transition.

The production-oriented package is in `ai_trust_enablement/`. It provides:

- deterministic AI answer evaluation from context, prompt, and answer,
- concrete state signatures with `phase_value`, `scale_value`, and `seam_memory_value`,
- open-residue classification into `RECOGNITION`, `BOUNDED_RESIDUE`, or `ACTIONABLE_RESIDUE`,
- Lambda-Laplace diffusion, seam, heat-trace, and spectral-gap diagnostics,
- temporal topological-memory diagnostics for winding-sector and memory-transition detection,
- Future Arrow probability-cone forecasting after recognition or memory-transition events,
- machine-readable certificates and JSON schema,
- HTTP API service with health/version/schema/evaluate/batch/release/resolve/lambda-laplace/topological-memory/future-arrow endpoints,
- answer release, repair, retrieval-resolution, and ECL-style finality commit support,
- Docker and docker-compose deployment files,
- no-dependency regression tests.

## Challenge Engine v1.2.0

`challenge_engine/` is the external testing front door. It accepts a machine-readable Challenge Package and keeps three evidence levels separate:

- `exploratory` for empirical or black-box evidence,
- `adversarial` for a predeclared target, threat model, negative controls and break conditions,
- `certified` for challenges that additionally close formal support and the selected formal adapter.

The Challenge is **not** “make the English sentence confusing.” The object under attack is the declared claim-to-evidence closure contract. Natural-language text is payload by default; unrestricted English semantics are not claimed unless a semantic adapter is explicitly declared and closed.

Every evaluation emits a SHA-256 `CHALLENGE_GENESIS` record with `accepted_claims = 0`, `parent = null`, and `rules_frozen = true`. Genesis freezes the rules of engagement before outcomes are evaluated; it does not accept the claim. The Genesis contract commits the installed package manifest, parser/arithmetic contract, exact connector numeric declarations, and any declared arithmetic or seam-quotient certificate.

Each evaluated input/result also emits a SHA-256 `CHALLENGE_EVALUATION` record binding the Genesis hash, normalized input hash, result, and computed checks. An optional parent evaluation hash allows an external connector or persistent ledger to chain outcomes. The engine is stateless, so cross-request replay detection remains the responsibility of that persistent connector/ledger.

Connector JSON is strict: duplicate object keys and non-standard `NaN`/`Infinity` tokens are rejected. Ordinary finite decimal tokens preserve their declared lexeme for exact threshold and canonical-contract decisions. Explicit malformed package or mode values do not silently fall back to defaults. Authorization-gated security challenges bind `target.toe` to the authorized `scope.target` identifier.

The numerical interface is fail-closed. Exact integers/rationals/finite decimals occupy the zero-arithmetic-radius sector. Approximate results can be represented as directed intervals or balls, with arithmetic uncertainty kept separate from analytic/truncation uncertainty. The proof-carrying layer `proof-carrying-numeric-closure-v1` requires an admitted source-bound validation trace before approximate numerical evidence may promote a formal claim. A participant-supplied radius, analytic tail, backend label, or overlapping set of claimed enclosures does not self-validate. Arbitrary external backend/source authenticity remains a separate trust obligation unless its adapter closes that obligation. See [`challenge_engine/ARITHMETIC_ENCLOSURE_AUDIT.md`](challenge_engine/ARITHMETIC_ENCLOSURE_AUDIT.md) and [`challenge_engine/PROOF_CARRYING_NUMERIC_HALLUCINATION_AUDIT.md`](challenge_engine/PROOF_CARRYING_NUMERIC_HALLUCINATION_AUDIT.md).

### First-visible-jet seam quotient

The Challenge Engine also exposes the exact finite-jet subset of the Recognition-Kernel first-visible-jet seam quotient theorem through:

```text
first-visible-jet-seam-quotient-v1
```

This does **not** redefine ordinary division by zero. Raw `1/0` and raw algebraic `0/0` remain invalid. For two exact vanishing polynomial jets on one named seam, the engine compares their first nonzero orders:

```text
numerator order > denominator order    quotient -> 0
orders equal                            quotient -> leading numerator / leading denominator
numerator order < denominator order    no finite quotient
all denominator jets zero              INCOMPLETE_FLAT_OR_UNRESOLVED
```

The general analytic/remainder-bearing seam model remains `INCOMPLETE` until a trusted remainder/denominator-separation validator closes the hypotheses. A participant cannot promote a quotient merely by submitting a field called `claimed_remainder`.

See [`challenge_engine/SEAM_QUOTIENT_AUDIT.md`](challenge_engine/SEAM_QUOTIENT_AUDIT.md).

The default package is `math`; `logic`, `code`, and authorization-gated `security_audit` packages are included. A connector can discover the contract with:

```bash
python challenge_engine/challenge.py --capabilities --compact
```

or stream one JSON challenge through stdin:

```bash
python challenge_engine/challenge.py - --compact
```

Meaningful break classes include false acceptance, blindness escape, scope escape, negative-control escape, invalid promotion, flow-consistency escape, and ledger-integrity failure. See [`challenge_engine/RED_TEAM_RULES.md`](challenge_engine/RED_TEAM_RULES.md) and [`challenge_engine/CONNECTOR_CONTRACT.md`](challenge_engine/CONNECTOR_CONTRACT.md).

### Verification boundary

The foundational mathematics package currently carries **236,456 exact/random/exhaustive adversarial cases** across the finite core, Hilbert finite-channel extension, and native flow-completion extension. The current Challenge Engine workflow carries **124 unit/adversarial tests** after parser/ledger, arithmetic-enclosure, exact seam-quotient, and proof-carrying numerical-provenance hardening. These are intentionally reported separately because software unit tests and mathematical/adversarial cases are not the same kind of evidence.

Current audit statuses:

```text
PASS_FINAL_CHALLENGE_SEAL_AUDIT
PASS_EXACT_RATIONAL_ENCLOSURE_AUDIT
PASS_EXACT_FINITE_JET_SEAM_QUOTIENT_AUDIT
PASS_PROOF_CARRYING_NUMERIC_HALLUCINATION_AUDIT
```

The audit series found and repaired concrete issues including duplicate-key parser differentials, malformed default fallback, package path abuse, scoped TOE mismatch, missing package-manifest commitment, missing evaluation-outcome hashes, binary floating-point boundary errors, long-decimal loss before exact comparison, missing-radius behavior, incompatible numeric enclosures, unsafe finite-jet interpretations of apparent `0/0` forms, self-validating numerical-radius/tail assumptions, and incorrect strict-bound treatment under uncertainty.

The audits do not claim universal correctness, unrestricted semantic truth, universal numerical stability, correctness of arbitrary external interval/ball backends, real-world authenticity of self-asserted evidence, universal source completeness, stateless replay detection, or resistance to all resource-exhaustion attacks. They establish fail-closed behavior against the documented attack classes and leave external evidence/backend authenticity, deployment resource budgets, and replay memory to the relevant connector/package or persistent ledger unless separately authenticated.

## Quick start

```bash
python ai_trust_enablement/run_enablement_tests.py
python ai_trust_enablement/server.py
```

In another terminal:

```bash
curl -s http://127.0.0.1:8080/v1/evaluate \
  -H 'Content-Type: application/json' \
  --data @examples/evaluate_request.json
```

## Docker

```bash
docker build -t ai-trust-enable:latest .
docker run --rm -p 8080:8080 ai-trust-enable:latest
```

Set `AI_TRUST_API_TOKEN` before exposing the service beyond localhost.

## ECL finality bridge

The AI Trust stack can seal recognition, repair, release, retrieval-resolution, Lambda-Laplace, topological-memory, or Future Arrow certificates into an append-only ECL-style finality ledger.

```python
from dataclasses import asdict
from ai_trust_enablement.ai_hallucination_recognition_engine import AIHallucinationRecognitionEngine
from ai_trust_enablement.ecl_commit_adapter import ECLCommitAdapter

engine = AIHallucinationRecognitionEngine()
certificate = asdict(engine.evaluate(
    reference_text="The Eiffel Tower is located in Paris. It was completed in 1889.",
    prompt="Answer using only the supplied context.",
    answer="The Eiffel Tower is located in Berlin. It was completed in 1789.",
))

commit = ECLCommitAdapter().commit_certificate(certificate)
print(commit.to_dict())
```

This creates a chained finality record with certificate hash, proposal hash, positive entropy delta, previous commit pointer, and commit hash. See `docs/ECL_FINALITY_INTEGRATION.md`.

## Lambda-Laplace analytic layer

The Lambda-Laplace layer evaluates lambda trajectories through diffusion, skew drift, entropic drift, heat-trace proxy, and seam/spectral-gap diagnostics. It emits an `AI_LAMBDA_LAPLACE_CERTIFICATE`.

```bash
python ai_trust_enablement/lambda_laplace_operator.py --demo
```

Lambda-Laplace provides analytic seam evidence before topological-memory diagnostics mark a winding-sector transition. See `docs/LAMBDA_LAPLACE_INTEGRATION.md`.

## Topological-memory / winding-sector layer

The topological-memory layer evaluates a phase trajectory, computes winding-sector movement, and emits an `AI_TOPOLOGICAL_MEMORY_CERTIFICATE` when the trajectory crosses a memory/sector seam.

This extends the service from one-answer hallucination detection to temporal recognition-drift detection. See `docs/TOPOLOGICAL_MEMORY_INTEGRATION.md`.

## Future Arrow forecasting layer

The Future Arrow Operator projects the current recognition or topological-memory state forward into a probability-coated future cone and emits an `AI_FUTURE_ARROW_CERTIFICATE`.

```bash
python ai_trust_enablement/future_arrow_operator.py --demo
```

Future Arrow estimates where the recognition trajectory may go next. ECL can seal either actual events or forecast certificates. See `docs/FUTURE_ARROW_INTEGRATION.md`.

## Documentation

- `RNKE_PUBLIC_INTRODUCTION.md` - publication-safe RNKE definition, Challenge special-case relation, candidate applications, and claim boundary.
- `challenge_engine/README.md` - challenge definition, packages, modes, genesis, flow probes, arithmetic and seam-quotient checks.
- `challenge_engine/RED_TEAM_RULES.md` - red-team rules of engagement and meaningful break classes.
- `challenge_engine/CONNECTOR_CONTRACT.md` - stable connector stdin/stdout, arithmetic and seam-quotient contract.
- `challenge_engine/FINAL_ADVERSARIAL_RELEASE_AUDIT.md` - first hostile pre-release audit.
- `challenge_engine/FINAL_SEAL_AUDIT.md` - parser, threshold, scoped-TOE, Genesis and evaluation-ledger seal audit.
- `challenge_engine/ARITHMETIC_ENCLOSURE_AUDIT.md` - exact-rational, long-decimal, interval/ball and outward-promotion audit.
- `challenge_engine/SEAM_QUOTIENT_AUDIT.md` - exact finite-jet apparent-`0/0` classification and integration audit.
- `challenge_engine/PROOF_CARRYING_NUMERIC_HALLUCINATION_AUDIT.md` - source-bound numerical provenance and formal-overclaim audit.
- `ai_trust_enablement/README.md` - enablement walkthrough and glossary.
- `docs/DEPLOYMENT.md` - deployment guide.
- `docs/PRODUCTION_CHECKLIST.md` - production readiness checklist.
- `docs/ECL_FINALITY_INTEGRATION.md` - AI certificate to ECL-style finality commit bridge.
- `docs/LAMBDA_LAPLACE_INTEGRATION.md` - Lambda-Laplace analytic diffusion and seam diagnostics.
- `docs/TOPOLOGICAL_MEMORY_INTEGRATION.md` - topological-memory / winding-sector diagnostics.
- `docs/FUTURE_ARROW_INTEGRATION.md` - Future Arrow probability-cone forecasting.
- `docs/PUBLIC_RELEASE_BOUNDARY.md` - public release scope and exclusions.
- `PATENT_NOTICE.md` - patent-rights notice.
- `COPYRIGHT_NOTICE.md` - copyright ownership and restriction notice.
- `LICENSE` - all-rights-reserved repository license boundary.
- `CITATION.cff` - citation metadata for academic and technical references.

## Citation

Dabas, M. (2026). *Recognition Null Kernel Engine (RNKE): Challenge Engine and Foundational Verification* (Version 1.2.0). Zenodo. DOI: 10.5281/zenodo.21300179.

## Status

Version 1.2.0 is the audited Challenge Engine release candidate plus the existing AI trust-enablement stack. It is intended for technical inspection, citation, reproducibility review, and challenge evaluation within the repository licence and any separately declared authorization/scope. It is not a standalone truth oracle and not a substitute for domain validation.

This public release is a technical and citation layer associated with inventor-controlled intellectual-property materials.
