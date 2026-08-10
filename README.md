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

The current exact-action gate checks the declared principal and agent, exact tool/operation/resource, exact-value SHA-256 binding of the complete executable parameters, delegation continuity, committed validity epoch, revocation state, request-nonce freshness, and exact-action human confirmation when required.

Only:

```text
ADMIT
```

is executable. `REJECT`, `INCOMPLETE`, and `INVALID` do not cross the RNKE execution boundary.

The deliberately provocative part is also the useful part:

> **Natural-language/model output may propose an action but cannot enlarge authority.**

So a prompt injection does not have to be perfectly understood or labeled malicious. If it changes the proposed action, that candidate still has to close independently against the frozen authority rules.

### Public red-team launch package

The reproducible and narrowly authorized public challenge package is in:

- [`red_team_challenge/README.md`](red_team_challenge/README.md)
- [`red_team_challenge/CHALLENGE_AUTHORIZATION.md`](red_team_challenge/CHALLENGE_AUTHORIZATION.md)
- [`red_team_challenge/CHALLENGE_MANIFEST.json`](red_team_challenge/CHALLENGE_MANIFEST.json)
- [`red_team_challenge/SELF_RED_TEAM_AUDIT.md`](red_team_challenge/SELF_RED_TEAM_AUDIT.md)

The pre-public self-red-team deliberately broke the first launch candidate: three unauthorized-`ADMIT` reproductions exposed exact-decimal action-hash aliases, and a separate defect exposed candidate numeric lexemes in frozen Genesis. Those findings were repaired before public activation and are now regression-locked. The challenge documentation preserves both the failures and the post-repair evidence.

Run the baseline:

```bash
python challenge_engine/challenge.py challenge_engine/examples/agent_action_challenge.json --compact
```

The baseline deliberately contains hostile retrieved text but an exactly authorized executable action. Then mutate the candidate action, request nonce, approval, or prompt payload under the same frozen authority contract and try to obtain an unauthorized `ADMIT`.

The complete rules and initial audit are in:

- [`challenge_engine/MAIN_CHALLENGE.md`](challenge_engine/MAIN_CHALLENGE.md)
- [`challenge_engine/PROOF_BEFORE_ACTION_AUDIT.md`](challenge_engine/PROOF_BEFORE_ACTION_AUDIT.md)
- [`challenge_engine/RED_TEAM_RULES.md`](challenge_engine/RED_TEAM_RULES.md)

### Current self-red-team evidence

The exact-action gate is now covered by:

```text
15 directed core adversarial cases
20,000 deterministic hostile mutations
20 mutation classes
14 independent pre-public self-red-team methods
1,500 deterministic exact-decimal alias probes
159 full Challenge Engine regression tests
post-repair unauthorized ADMIT: 0
```

The initial independent run did produce three unauthorized `ADMIT` outcomes before repair. That history is intentionally public; a passing campaign is evidence against tested attack classes, not proof that no implementation flaw exists.

### Genesis freezes authority, not the attack

A self-audit exposed an important distinction: freezing the complete candidate into Genesis would make the red-team exercise artificial. The corrected model freezes the **authority/rule view** while leaving the attack candidate variable.

For Proof Before Action:

```text
candidate mutation      -> same Genesis, new evaluation
authority/rule mutation -> different Genesis
```

`action`, `request_nonce`, `approval`, and `proposal_context`—including exact numeric values inside them—are evaluation inputs bound by `CHALLENGE_EVALUATION`. Principal/agent declarations, committed authority state, delegation grants, terminal grant, confirmation policy, protocol, and validator identity belong to the frozen authority view.

That means an attacker can genuinely mutate the proposed action under a pinned Genesis and test the gate itself rather than merely triggering a different contract hash.

## RNKE special cases

The flagship challenge demonstrates RNKE; it does not define RNKE.

### Special case I: mathematical verification

Mathematics remains an implemented sharp-ground-truth specialization:

```text
proof/evidence closure -> theorem commitment
```

The Challenge Engine includes exact rational and decimal handling, directed enclosures, proof-carrying numeric closure, first-visible-jet seam quotients, formal-promotion obligations, and mathematical hallucination tests.

### Special case II: Proof of Work

A Proof-of-Work adapter is a natural next demonstration:

```text
work + ancestry + transition closure -> state commitment
```

It remains a development direction until it is separately implemented, tested, and audited. The repository does not present it as already complete.

## Current boundary

This release does not claim universal AI-agent security. The v1 gate uses exact-action grants, does not authenticate real human identity by itself, requires authenticated persistent and atomic state for cross-request/concurrent nonce replay resistance, and must actually sit on the tool-execution path to enforce its decision. The synthetic public fixture performs no real external side effect.

Those are deployment obligations, not details to be hand-waved away because the README looked exciting.
