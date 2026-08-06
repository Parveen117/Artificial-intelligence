# Native Flow-Completion Adversarial Audit

This audit attacks the theorem spine T14--T20 introduced after the finite guarded-record core.

The purpose is not to numerically "prove" an infinite-dimensional theorem. The proofs remain analytic. The executable packet instead checks exact algebraic shadows, assumption-breaking controls, finite-rank inertia identities, and the rule that a finite matrix cannot be promoted to a limiting certificate without carrying its completion error.

## Pinned run

```text
PASS_NATIVE_FLOW_COMPLETION_AUDIT
seed = 20260825
exact/random/negative-control cases = 55008
```

Run with:

```bash
python audit/run_native_flow_completion_audit.py
```

## Coverage

- **T14 positive-form completion:** rational semidefinite-form fixtures verify that descended maps annihilate null directions; negative controls deliberately act nontrivially on a zero-form vector.
- **T15 bilateral flow and observer jets:** exact nilpotent exponential packets verify involution conjugacy, alternating jet parity, nested observer kernels, and exact finite reconstruction; wrong-involution controls must fail bilateral conjugacy.
- **T16 transported operator limit:** diagonal rational packets verify the exact operator-norm Gram error inequalities for recognized, memory, and signed channels.
- **T17 no-hidden-memory completion:** vanishing observer-complement residues converge to a finite faithful range; persistent complement mass is retained as a negative control.
- **T18 variational observer:** diagonal singular-value packets exhaust all coordinate projections and reproduce the exact tail-energy minimum and the zero-action rank criterion.
- **T19 finite obstruction:** exact diagonalized finite-rank models verify equality of negative index, threshold kernel multiplicity, and normalized source-relative margin.
- **T20 outward promotion:** finite matrix tops are combined with completion-error bounds; negative controls exhibit cases in which the finite top is below one while the limiting top is above one.

## Claim discipline

The audit does not assert that every infinite-dimensional problem has finite target-relevant rank. T17--T18 make finite rank an obligation. It does not treat a fixed finite truncation as a limiting proof. T20 explicitly requires an outward completion error. It does not infer a physical, arithmetic, or thermodynamic interpretation from the abstract flow or finite Hermitian matrix.

The public paper remains mathematics only. The theorem source is written in application-neutral language and does not name the domain-specific programme from which these abstract structures were distilled.
