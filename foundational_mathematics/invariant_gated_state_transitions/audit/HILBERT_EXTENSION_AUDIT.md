# Hilbert Representation-Corollary Audit

This audit targets the earlier finite-channel Hilbert formulas retained in the mathematics-only foundational paper after the stronger flow-completion spine.

## Position in the paper

The Hilbert compression is no longer the primary finite-to-infinite theorem. The primary route is T14--T20: positive-form completion, bilateral observer flow, transported operator completion, no-hidden-memory faithfulness, variational observer derivation, exact finite obstruction, and outward completion error.

The present audit checks downstream representation consequences once a finite channel map is already available.

## H1: finite-channel compression

The audit checks finite exact shadows of

`S - V V* = S^(1/2) (I - C C*) S^(1/2)`

with `V = S^(1/2) C`, including non-diagonal rational channel rotations. It also checks the strictly positive inverse form

`B = V* S^(-1) V = C* C`.

Positive cases use contractive channels. Negative cases construct a top singular channel with norm greater than one and an exact witness for negativity. Separate controls place an adverse channel in `ker S`, demonstrating why the source-support hypothesis cannot simply be omitted.

## H2: target-repair dimension shadow

Controlled blind subspaces are generated exactly. A full-rank repair closes the target defect, while a lower-rank supplement fails by rank. The stronger variational derivation of observer rank is tested separately in the native flow-completion audit.

## H3: strict reserve

The audit verifies

`S - V V* >= (1 - beta) S`

and uses an exact top singular channel to attain the bound.

## H4: projection-defect positivity

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
cases = 41000
```

The complete mathematics package now carries three independent audit families. Their combined pinned count is 236456 exact/random/negative-control cases.
