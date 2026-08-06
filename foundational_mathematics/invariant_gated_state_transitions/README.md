# Foundational Mathematics: Invariant-Gated State Transitions

This folder contains the mathematics-only foundational paper for guarded state transitions and persistent state records.

## Paper

**Invariant-Gated State Transitions: Exact Admission, Curvature, and Persistent Records**  
Monty Dabas, 2026.

The finite guarded-record core develops the result as a theorem chain rather than as a single system claim:

1. structured initial datum;
2. invariant transition bound;
3. candidate-validator separation;
4. exact target determination;
5. exact observation completion and bounded target support;
6. path-order curvature;
7. finite proof admission;
8. all-obligation threshold and disturbance margin;
9. clock-independent fixed-state selection;
10. exact COMMIT/HOLD/REJECT trichotomy;
11. exact refinement;
12. replay-complete append-only persistence;
13. persistent-record theorem.

The paper now also contains an arbitrary-Hilbert-space extension of the target-support layer:

14. finite-channel Hilbert-space compression;
15. minimal target-repair dimension;
16. strict finite-channel reserve;
17. projection-defect positivity.

The central extension is deliberately conditional rather than magical: if the target-relevant adverse information factors through `m` channels, the ambient Hilbert-space positivity problem is equivalent to an `m x m` Hermitian certificate. Five dimensions are therefore a five-channel consequence, not a claim that every infinite-dimensional problem reduces to five dimensions.

When the positive source operator is boundedly invertible, the Hermitian compression takes the classical inverse form `B = V* S^{-1} V`; the paper treats this as a Birman-Schwinger/Schur-complement identification of the more general minimum-source-lift theorem.

This directory is intentionally mathematics only. It contains no device architecture, fabrication claim, thermodynamic embodiment, or later-framework terminology.

## Adversarial audits

Finite-core audit:

```bash
python audit/run_adversarial_audit.py
```

Pinned status:

```text
PASS_FOUNDATIONAL_MATH_ADVERSARIAL_AUDIT
seed = 20260807
exact/random/exhaustive cases = 140448
false commits = 0
```

Hilbert finite-channel extension audit:

```bash
python audit/run_hilbert_extension_audit.py
```

Pinned status:

```text
PASS_HILBERT_FINITE_CHANNEL_EXTENSION_AUDIT
seed = 20260824
exact/random/exhaustive cases = 41000
```

Combined adversarial case count: **181448**.

The extension audit checks exact factorization, the inverse-form matrix shadow, positive and negative spectral channels, failure outside the source support, minimal repair rank, sharp reserve witnesses, and positive projection-defect Gram identities.

The existing repository workflow reruns the finite-core adversarial audit whenever this mathematics package changes. The Hilbert extension audit is separately reproducible from the command above and is pinned in `audit/hilbert_extension_result.json`.

## Build

```bash
cd paper
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```
