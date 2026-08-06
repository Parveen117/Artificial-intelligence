# Hilbert Finite-Channel Extension Audit

This audit targets the arbitrary-Hilbert-space theorem family T14--T17 in the mathematics-only foundational paper.

## Claim boundary

The extension does **not** claim that every infinite-dimensional problem reduces to a fixed finite matrix. It proves a conditional reduction when the target-relevant adverse information factors through finitely many channels. The certificate dimension is the channel/defect dimension `m`.

## T14: finite-channel Hilbert-space compression

The audit checks finite exact shadows of

`S - V V* = S^(1/2) (I - C C*) S^(1/2)`

with `V = S^(1/2) C`, including non-diagonal rational channel rotations. It also checks the strictly positive inverse form

`B = V* S^(-1) V = C* C`.

Positive cases use contractive channels. Negative cases construct a top singular channel with norm greater than one and an exact witness for negativity. Separate controls place an adverse channel in `ker S`, demonstrating why the source-support hypothesis cannot simply be omitted.

## T15: minimal target-repair dimension

Controlled blind subspaces of dimension `r` are generated exactly. An `r`-channel repair closes the target defect, while every `(r-1)`-channel supplement fails by rank.

## T16: strict reserve

The audit verifies

`S - V V* >= (1 - beta) S`

and uses an exact top singular channel to attain the bound, so the reserve is tested for sharpness rather than only positivity.

## T17: projection-defect positivity

For exact rational response matrices and orthogonal coordinate projections, the audit checks

`K = R* (I-P) R = G_total - G_source`

and verifies every sampled quadratic form as the squared norm of the projected residual.

## Reproducibility

Run:

```bash
python audit/run_hilbert_extension_audit.py
```

Pinned result:

```text
PASS_HILBERT_FINITE_CHANNEL_EXTENSION_AUDIT
seed = 20260824
exact/random/exhaustive cases = 41000
```

The finite-core audit remains separate. Together the two reproducible audits contain 181448 exact/random/exhaustive cases.
