# Foundational Mathematics: Invariant-Gated State Transitions

This folder contains the mathematics-only foundational paper for guarded state transitions and persistent state records.

## Paper

**Invariant-Gated State Transitions: Exact Admission, Curvature, and Persistent Records**  
Monty Dabas, 2026.

The paper develops the result as a theorem chain rather than as a single system claim:

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

This directory is intentionally mathematics only. It contains no device architecture, fabrication claim, thermodynamic embodiment, or later-framework terminology.

## Adversarial audit

The theorem chain has a reproducible hostile-review audit under `audit/`.

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

The audit includes exact rational algebra, exhaustive Boolean status enumeration, randomized exact fixtures, assumption-breaking negative controls, and deliberate mutation controls.

The repository workflow `.github/workflows/foundational-math-audit.yml` reruns the adversarial audit whenever this mathematics package changes.

## Build

```bash
cd paper
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```
