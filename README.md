# Recognition Null Kernel Engine (RNKE)

## Artificial Intelligence Trust Enablement and Challenge Engine

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21300179.svg)](https://doi.org/10.5281/zenodo.21300179)

This repository contains a deployable AI trust-enablement service and the public Challenge Engine for the **Recognition Null Kernel Engine (RNKE)** verification architecture. The implemented stack includes Proof-Before-Action agent gating, mathematical hallucination/formal-overclaim testing, release control, certificate generation, ECL-style finality, Lambda-Laplace diagnostics, topological-memory diagnostics, Future Arrow forecasting, and theorem-backed challenge testing.

> **Patent status.** This repository is associated with inventor-controlled patent filings and related intellectual-property rights. Publication does not grant any patent license. See [`PATENT_NOTICE.md`](PATENT_NOTICE.md).
>
> **Copyright and license boundary.** This is a public technical inspection and citation release, not an unrestricted open-source grant. All rights are reserved unless a separate written license states otherwise. See [`LICENSE`](LICENSE) and [`COPYRIGHT_NOTICE.md`](COPYRIGHT_NOTICE.md).
>
> **Public release boundary.** This repository is a selected public technical release and does not reproduce the complete private filing, research, hardware, or internal development record. See [`docs/PUBLIC_RELEASE_BOUNDARY.md`](docs/PUBLIC_RELEASE_BOUNDARY.md).

## RNKE: a general verification machine

RNKE is a foundational verification architecture for **formalizable trust systems**. A domain adapter presents explicit claims or proposed transitions, evidence, dependencies, governing rules, and committed state. The verification kernel then decides whether the proposed transition is admitted, rejected, or remains incomplete.

The architecture is organized around three principles:

1. **Null-as-Cut.** Verification begins from a structured genesis condition containing no admitted claims but a fixed rule structure. The null state is operational; this does not redefine arithmetic zero.
2. **Recognition Before Commitment.** A claim or action is promoted only when its required evidence, authority, dependencies, invariants, and proof obligations close. Assertion or model confidence alone has no authority.
3. **Persistent Verification History.** Accepted, rejected, refuted, and unresolved events can remain bound to a tamper-evident lineage so that rule mutation, inconsistent replay, or historical alteration can be detected when the required persistent connector/ledger is present.

Abstractly, the interface is:

```text
V(claim_or_transition, evidence, dependencies, rules, committed_state)
    -> ADMIT | REJECT | INCOMPLETE
```

RNKE is therefore more general than a mathematical proof checker and more structured than a hash chain. A proof checker, numerical verifier, agent-action gate, code/specification checker, compliance engine, provenance system, or evidence-gated AI can each be expressed as a domain adapter of the same recognition-before-commitment architecture.

This is a statement about the architecture, **not** a claim that every possible real-world domain has already been modeled or validated. External evidence, identities, measurements, sensors, legal facts, numerical backends, and physical actuators still require the source/authentication obligations declared by their adapters.

The full publication-safe framing is in [`RNKE_PUBLIC_INTRODUCTION.md`](RNKE_PUBLIC_INTRODUCTION.md).

## 🔥 Main Challenge: Proof Before Action

> **Make an AI agent execute an action whose frozen authority/evidence chain does not close.**

This is the flagship executable RNKE challenge.

An upstream model is allowed to hallucinate, misunderstand a request, follow hostile retrieved text, or propose the wrong tool call. Those failures are not automatically a break. The proposal itself has no authority.

The first executable protocol is:

```text
proof-before-action-v1
```

The current exact-action gate checks the declared principal and agent, exact tool/operation/resource, SHA-256 binding of the complete executable parameters, delegation continuity, committed validity epoch, revocation state, request-nonce freshness, and exact-action human confirmation when required.

Only:

```text
ADMIT
```

is executable. `REJECT`, `INCOMPLETE`, and `INVALID` do not cross the RNKE execution boundary.

The deliberately provocative part is also the useful part:

> **Natural-language/model output may propose an action but cannot enlarge authority.**

So a prompt injection does not have to be perfectly understood or labeled malicious. If it changes the proposed action, that candidate still has to close independently against the frozen authority rules.

Run the baseline:

```bash
python challenge_engine/challenge.py challenge_engine/examples/agent_action_challenge.json --compact
```

The baseline deliberately contains hostile retrieved text but an exactly authorized executable action. Then mutate the candidate action, request nonce, approval, or prompt payload under the same frozen authority contract and try to obtain an unauthorized `ADMIT`.

The complete rules and initial audit are in:

- [`challenge_engine/MAIN_CHALLENGE.md`](challenge_engine/MAIN_CHALLENGE.md)
- [`challenge_engine/PROOF_BEFORE_ACTION_AUDIT.md`](challenge_engine/PROOF_BEFORE_ACTION_AUDIT.md)
- [`challenge_engine/RED_TEAM_RULES.md`](challenge_engine/RED_TEAM_RULES.md)

### Initial self-red-team result

Before promoting this challenge, the exact gate was attacked with directed cases plus a deterministic mutation campaign:

```text
15 directed core adversarial cases: PASS
20,000 deterministic hostile mutations
20 mutation classes
unauthorized ADMIT: 0
```

The campaign includes tool/operation/resource escape, parameter tampering, wrong principal/agent, forged action binding, revoked/expired grants, nonce replay, missing authority, stale confirmation, delegation escalation, broken delegation lineage, cyclic delegation, and malformed committed replay state.

The repository CI reruns the mutation campaign together with the existing Challenge Engine tests.

### Genesis freezes authority, not the attack

A self-audit exposed an important distinction: freezing the complete candidate into Genesis would make the red-team exercise artificial. The corrected model freezes the **authority/rule view** while leaving the attack candidate variable.

For Proof Before Action:

```text
candidate mutation      -> same Genesis, new evaluation
authority/rule mutation -> different Genesis
```

`action`, `request_nonce`, `approval`, and `proposal_context` are evaluation inputs bound by `CHALLENGE_EVALUATION`. Principal/agent declarations, committed authority state, delegation grants, terminal grant, confirmation policy, protocol, and validator identity belong to the frozen authority view.

That means an attacker can genuinely mutate the proposed action under a pinned Genesis and test the gate itself rather than merely triggering a different contract hash.

## RNKE special cases

The flagship challenge demonstrates RNKE; it does not define RNKE.

### Special case I: mathematical verification

Mathematics remains an implemented sharp-ground-truth specialization:

```text
proof/evidence closure -> theorem commitment
```

The mathematical challenge asks whether an invalid or unsupported conclusion can escape proof-flow, dependency, numerical-enclosure, convergence, remainder, or seam obligations. Missing lemmas, fabricated precision, unjustified convergence, discarded remainders, illegal algebraic division-by-zero, and unsupported proof transitions are examples of the same structural failure: the claimed conclusion outruns verified evidence.

### Special case II: Proof of Work

Proof of Work is the next intended specialization:

```text
work/evidence closure -> state commitment
```

The target is not to invent another hash function or casually declare victory over blockchain consensus. A PoW adapter would ask whether a candidate state can be committed when work, ancestry, frozen rule, and state-transition obligations do not close. It remains a development direction until separately implemented and audited.

The intended hierarchy is therefore:

```text
RNKE
  -> Proof Before Action        [flagship executable challenge]
  -> mathematical verification [implemented special case]
  -> Proof of Work              [next special-case adapter]
```

> **Design principle:** Do not trust the claim. Verify the transition.

## AI trust-enablement stack

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
- `certified` for challenges that additionally close formal support and the selected package's promotion requirements.

Included packages are `agent_action`, `math`, `logic`, `code`, and authorization-gated `security_audit`. The default package remains `math` for backward compatibility; the flagship public challenge is `agent_action` / Proof Before Action.

The Challenge is **not** “make the English sentence confusing.” Natural-language text is payload by default; unrestricted English semantics are not claimed unless a semantic adapter is explicitly declared and closed.

Every evaluation emits a SHA-256 `CHALLENGE_GENESIS` record with:

```text
accepted_claims = 0
parent = null
rules_frozen = true
```

Each evaluated input/result also emits a SHA-256 `CHALLENGE_EVALUATION` record binding the Genesis hash, normalized input hash, result, and computed checks. An optional parent evaluation hash allows an external connector or persistent ledger to chain outcomes. The engine is stateless, so cross-request replay detection remains the responsibility of that persistent connector/ledger.

Connector JSON is strict: duplicate object keys and non-standard `NaN`/`Infinity` tokens are rejected. Ordinary finite decimal tokens preserve their declared lexeme for exact threshold and canonical-contract decisions. Explicit malformed package or mode values do not silently fall back to defaults.

Meaningful break classes include false acceptance, blindness escape, scope escape, negative-control escape, invalid promotion, flow-consistency escape, and ledger-integrity failure.

Discover the machine-readable contract with:

```bash
python challenge_engine/challenge.py --capabilities --compact
```

or stream one challenge through stdin:

```bash
python challenge_engine/challenge.py - --compact
```

## Mathematical proof-carrying layers

### Proof-carrying numerical closure

The numerical interface is fail-closed. Exact integers/rationals/finite decimals occupy the zero-arithmetic-radius sector. Approximate results can be represented as directed intervals or balls, with arithmetic uncertainty kept separate from analytic/truncation uncertainty.

The layer:

```text
proof-carrying-numeric-closure-v1
```

requires an admitted source-bound validation trace before approximate numerical evidence may promote a formal claim. A participant-supplied radius, analytic tail, backend label, or overlapping set of claimed enclosures does not self-validate.

See [`challenge_engine/ARITHMETIC_ENCLOSURE_AUDIT.md`](challenge_engine/ARITHMETIC_ENCLOSURE_AUDIT.md) and [`challenge_engine/PROOF_CARRYING_NUMERIC_HALLUCINATION_AUDIT.md`](challenge_engine/PROOF_CARRYING_NUMERIC_HALLUCINATION_AUDIT.md).

### First-visible-jet seam quotient

The Challenge Engine exposes the exact finite-jet subset of the Recognition-Kernel first-visible-jet seam quotient theorem through:

```text
first-visible-jet-seam-quotient-v1
```

This does **not** redefine ordinary division by zero. Raw `1/0` and raw algebraic `0/0` remain invalid. For two exact vanishing polynomial jets on one named seam:

```text
numerator order > denominator order    quotient -> 0
orders equal                            quotient -> leading numerator / leading denominator
numerator order < denominator order    no finite quotient
all denominator jets zero              INCOMPLETE_FLAT_OR_UNRESOLVED
```

The general analytic/remainder-bearing seam model remains `INCOMPLETE` until a trusted remainder/denominator-separation validator closes the hypotheses.

See [`challenge_engine/SEAM_QUOTIENT_AUDIT.md`](challenge_engine/SEAM_QUOTIENT_AUDIT.md).

## Verification boundary

The foundational mathematics package currently records **236,456 exact/random/exhaustive adversarial cases** across the finite core, Hilbert finite-channel extension, and native flow-completion extension. Software tests and mathematical/adversarial cases are intentionally reported separately because they are different forms of evidence.

Current established audit statuses include:

```text
PASS_FINAL_CHALLENGE_SEAL_AUDIT
PASS_EXACT_RATIONAL_ENCLOSURE_AUDIT
PASS_EXACT_FINITE_JET_SEAM_QUOTIENT_AUDIT
PASS_PROOF_CARRYING_NUMERIC_HALLUCINATION_AUDIT
```

The audit series found and repaired concrete issues including parser differentials, malformed fallback behavior, package path abuse, scoped TOE mismatch, missing manifest/outcome commitments, floating-point boundary errors, long-decimal loss, missing-radius behavior, incompatible enclosures, unsafe finite-jet interpretations, self-validating numerical assumptions, and strict-bound errors under uncertainty.

The audits do not claim universal correctness, unrestricted semantic truth, universal numerical stability, real-world authenticity of self-asserted evidence, universal source completeness, universal agent security, stateless replay detection, or resistance to all resource-exhaustion attacks.

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

The AI Trust stack can seal recognition, repair, release, retrieval-resolution, Lambda-Laplace, topological-memory, or Future Arrow certificates into an append-only ECL-style finality ledger. See [`docs/ECL_FINALITY_INTEGRATION.md`](docs/ECL_FINALITY_INTEGRATION.md).

## Lambda-Laplace, topological memory, and Future Arrow

- Lambda-Laplace evaluates lambda trajectories through diffusion, skew drift, entropic drift, heat-trace proxy, and seam/spectral-gap diagnostics. See [`docs/LAMBDA_LAPLACE_INTEGRATION.md`](docs/LAMBDA_LAPLACE_INTEGRATION.md).
- Topological memory evaluates phase trajectories and winding-sector movement. See [`docs/TOPOLOGICAL_MEMORY_INTEGRATION.md`](docs/TOPOLOGICAL_MEMORY_INTEGRATION.md).
- Future Arrow projects current recognition/topological-memory state into a probability-coated future cone. See [`docs/FUTURE_ARROW_INTEGRATION.md`](docs/FUTURE_ARROW_INTEGRATION.md).

## Documentation

- `RNKE_PUBLIC_INTRODUCTION.md` - publication-safe RNKE definition and claim boundary.
- `challenge_engine/MAIN_CHALLENGE.md` - flagship Proof-Before-Action challenge.
- `challenge_engine/PROOF_BEFORE_ACTION_AUDIT.md` - initial self-red-team campaign and security boundary.
- `challenge_engine/README.md` - Challenge Engine package/mode/protocol reference.
- `challenge_engine/RED_TEAM_RULES.md` - red-team rules of engagement and meaningful break classes.
- `challenge_engine/CONNECTOR_CONTRACT.md` - connector stdin/stdout contract.
- `challenge_engine/FINAL_ADVERSARIAL_RELEASE_AUDIT.md` - hostile pre-release audit.
- `challenge_engine/FINAL_SEAL_AUDIT.md` - parser, threshold, scoped-TOE, Genesis and evaluation-ledger audit.
- `challenge_engine/ARITHMETIC_ENCLOSURE_AUDIT.md` - arithmetic enclosure audit.
- `challenge_engine/SEAM_QUOTIENT_AUDIT.md` - exact finite-jet seam audit.
- `challenge_engine/PROOF_CARRYING_NUMERIC_HALLUCINATION_AUDIT.md` - source-bound numerical provenance audit.
- `ai_trust_enablement/README.md` - enablement walkthrough and glossary.
- `docs/DEPLOYMENT.md` - deployment guide.
- `docs/PRODUCTION_CHECKLIST.md` - production readiness checklist.
- `docs/PUBLIC_RELEASE_BOUNDARY.md` - public release scope and exclusions.
- `PATENT_NOTICE.md`, `COPYRIGHT_NOTICE.md`, `LICENSE` - rights and use boundary.
- `CITATION.cff` - citation metadata.

## Citation

Dabas, M. (2026). *Recognition Null Kernel Engine (RNKE): Challenge Engine and Foundational Verification* (Version 1.2.0). Zenodo. DOI: 10.5281/zenodo.21300179.

## Status

Version 1.2.0 is the audited Challenge Engine release line plus the AI trust-enablement stack. Proof Before Action is an adversarially tested extension in this release path. It is intended for technical inspection, citation, reproducibility review, and challenge evaluation within the repository licence and any separately declared authorization/scope. It is not a standalone truth oracle, a universal agent-security guarantee, or a substitute for domain validation.

This public release is a technical and citation layer associated with inventor-controlled intellectual-property materials.
