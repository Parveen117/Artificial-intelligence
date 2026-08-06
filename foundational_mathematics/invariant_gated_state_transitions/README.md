# Foundational Mathematics: Invariant-Gated State Transitions

This folder contains the mathematics-only foundational paper for guarded state transitions, target-faithful completion, and persistent state records.

## Paper

**Invariant-Gated State Transitions: Exact Admission, Flow Completion, Curvature, and Persistent Records**  
Monty Dabas, 2026.

The finite guarded-record core is theorem driven:

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

The stronger finite-to-infinite spine is downstream of that core:

14. positive-form carrier completion;
15. involution-graded bilateral flow and observer jets;
16. corrected transported finite-to-infinite operator completion with explicit error bounds;
17. no-hidden-memory completion from a vanishing faithfulness residual;
18. variationally minimal faithful observer rank and Hilbert-Schmidt tail;
19. exact infinite-to-finite inertia, kernel, and normalized margin;
20. outward finite promotion using both the finite matrix top and a proved completion error.

The key logical order is:

```text
positive form
-> completed carrier
-> bilateral exponential flow
-> observer jets
-> transported finite packets
-> operator-norm completion
-> target-faithful finite memory
-> variationally minimal observer
-> finite Hermitian obstruction
-> beta < 1 reserve
```

The ambient carrier may be infinite-dimensional. A finite certificate is allowed only after the target-relevant adverse information has been proved to lie in a finite observer range. The matrix size is therefore determined by the target-relevant obstruction rank, not by arbitrary truncation.

The earlier Hilbert finite-channel formula is retained as a representation corollary. When a positive source `S` and a finite channel map `V` already satisfy `V = S^(1/2) C`, one has

```text
S - V V* >= 0  <=>  C* C <= I.
```

When `S` is boundedly invertible this becomes the familiar inverse form

```text
B = V* S^(-1) V.
```

The paper treats that matrix as downstream of completion and observer derivation, not as a device for guessing the correct finite dimension.

This directory is intentionally mathematics only. It contains no device architecture, fabrication claim, thermodynamic embodiment, domain-specific terminal problem, or later-framework naming.

## Adversarial audits

Finite-core audit:

```bash
python audit/run_adversarial_audit.py
```

```text
PASS_FOUNDATIONAL_MATH_ADVERSARIAL_AUDIT
seed = 20260807
cases = 140448
false commits = 0
```

Hilbert representation audit:

```bash
python audit/run_hilbert_extension_audit.py
```

```text
PASS_HILBERT_FINITE_CHANNEL_EXTENSION_AUDIT
seed = 20260824
cases = 41000
```

Native flow-completion audit:

```bash
python audit/run_native_flow_completion_audit.py
```

```text
PASS_NATIVE_FLOW_COMPLETION_AUDIT
seed = 20260825
cases = 55008
```

Combined reproducible adversarial case count: **236456**.

The native audit includes null-direction controls, wrong-involution controls, exact nilpotent bilateral flows, operator-limit Gram error bounds, persistent hidden-memory controls, variational observer tails, exact inertia/kernel/margin fixtures, and finite-top-without-completion-error counterexamples.

The repository workflow `.github/workflows/foundational-math-audit.yml` runs all three audit families when this mathematics package changes.

## Build

```bash
cd paper
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```
