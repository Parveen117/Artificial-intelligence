# Recognition Null Kernel Engine (RNKE)

## A General Verification Machine

The **Recognition Null Kernel Engine (RNKE)** is a foundational verification architecture for formalizable trust systems. It converts claims, evidence, dependencies, admissible transitions, unresolved obligations, and persistent records into a finite, executable verification process.

RNKE is built on three principles.

### 1. Null-as-Cut

Verification begins from a structured genesis condition containing no admitted claims but a fixed rule structure. The null state is operational: it marks the boundary from which admissible state is constructed. This does **not** redefine arithmetic zero.

### 2. Recognition Before Commitment

A claim is promoted only when its required evidence, dependencies, invariants, and proof obligations close. Assertion alone has no authority. An unsupported, contradictory, or incompletely justified claim remains rejected or unresolved rather than being promoted by confidence, repetition, or presentation.

### 3. Persistent Verification History

Accepted, rejected, refuted, and unresolved events remain bound to a tamper-evident verification history. The record is intended to preserve the lineage of a decision so that later mutation, inconsistent replay, or rule substitution can be detected when the relevant persistent connector/ledger is present.

## Abstract verification contract

A domain adapter presents a typed verification problem to RNKE. At the abstract level one may write

\[
\mathcal V(C,E,D,R,S)
\longrightarrow
\{\mathrm{ADMIT},\mathrm{REJECT},\mathrm{INCOMPLETE}\},
\]

where:

- \(C\) is a claim or proposed transition;
- \(E\) is its evidence;
- \(D\) is the declared dependency structure;
- \(R\) is the governing rule/validator set; and
- \(S\) is the already committed state and lineage.

The kernel does not require the domain objects to be mathematical equations. It requires that the relevant claims, evidence, dependencies, admissible transitions, and verification obligations can be represented explicitly enough for the selected adapter to check them.

RNKE is therefore **more general than a proof checker and more structured than a hash chain**. A mathematical verifier, numerical-certification engine, code/specification checker, compliance system, provenance system, or evidence-gated AI system can each be expressed as a domain-specific realization of the same claim-to-evidence closure architecture.

This is a statement about the architecture. It is **not** a claim that every possible real-world domain has already been fully modeled, that external evidence is automatically authentic, or that every adapter is correct merely because it conforms to the RNKE interface.

## The Formal Proof Challenge is a special case

The current public Challenge Engine deliberately begins with mathematical and formal-system attacks because they provide unusually sharp ground truth: rules can be declared exactly, proof obligations can be inspected, numerical error can be bounded, and false certainty can often be exposed without appealing to noisy measurements.

For mathematics, the challenge can be read as **mathematical hallucination detection**. The attack succeeds if a conclusion is promoted even though its admitted proof flow does not justify it. Examples include:

- a missing or unsupported lemma;
- a hidden dependency or source substitution;
- a claimed strict inequality not established by the verified bound;
- fabricated numerical precision or an unverified radius/tail;
- discarded remainder or incomplete convergence step;
- an illegal division-by-zero step;
- a proof transition not entailed by the admitted rules.

The Challenge therefore tests the inequality

\[
\text{claimed closure strength}
\;\le\;
\text{verified evidence strength}.
\]

A **formal numeric overclaim** is one special case of this broader mathematical-hallucination class.

The current Challenge is consequently a **benchmark and gateway**, not the definition of RNKE:

\[
\boxed{
\text{RNKE}
\supset
\text{formal-system verification}
\supset
\text{mathematical hallucination detection}
\supset
\text{current public Challenge}.
}
\]

## Candidate application domains

The same architecture can be adapted to domains in which the relevant state, evidence, dependencies, transition rules, and provenance obligations are formalized. Candidate domains include:

- **AI safety:** evidence-gated outputs, mathematical/formal hallucination detection, release control, provenance-aware evaluation;
- **software and cybersecurity:** specification checks, tamper-evident logs, replay-aware authentication, authorized security-audit certificates;
- **finance:** auditable transaction/compliance transitions and evidence-bound records;
- **scientific research:** provenance, reproducibility obligations, automated replication checks, and priority records;
- **biotechnology:** formalized provenance and approval/workflow records where measurement authenticity is supplied by trusted acquisition layers;
- **law and governance:** rule-bound records, dependency-aware decisions, and auditable state transitions where the legal semantics are explicitly modeled;
- **supply chains:** provenance, custody/state transitions, cold-chain or counterfeit evidence when trusted sensing/attestation is available.

These are **application directions**, not claims that the present repository has already completed or validated every listed domain adapter. In physical or empirical domains RNKE can verify the declared evidence chain only to the extent that the acquisition, attestation, and domain-model assumptions themselves are authenticated.

## Public Challenge statement

The most concise public statement is:

> **The Challenge demonstrates RNKE. It does not define RNKE.**
>
> The current benchmark asks whether an attacker can make the engine promote a mathematical or formal conclusion whose declared evidence, dependency chain, numerical enclosure, or proof obligations do not actually close.

And the corresponding design principle is:

> **Do not trust the claim. Verify the transition.**

## Claim boundary

RNKE does not claim unrestricted natural-language understanding, universal semantic truth, universal mathematical truth, automatic real-world source authenticity, correctness of arbitrary external adapters/backends, immunity to every implementation vulnerability, or an "unbreakable" system. Certification is always relative to the declared formal contract and to the source/authentication assumptions that the relevant adapter has actually closed.

Private hardware/device-enabling material is outside this public introduction and outside the scope of the present public release.