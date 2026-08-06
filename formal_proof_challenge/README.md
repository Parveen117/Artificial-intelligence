# Break the Formal Proof Gate

A no-dependency public challenge for one narrow claim:

> A proof is not valid because it sounds intelligent. Every admitted step must be licensed by the declared finite calculus, the dependency graph must be acyclic, and the conclusion must equal the target.

## What counts as a break?

A real break is an **invalid derivation written in the admitted JSON grammar that receives `VALID_PROOF`**.

These are not breaks:

- unsupported prose;
- malformed JSON;
- an unknown proof rule;
- a formula outside the declared grammar.

Those inputs correctly fail closed as `PARSE_NOT_ADMITTED`.

## Supported v1 rules

```text
ASSUMPTION
ARITHMETIC_EVAL
EQ_SYMMETRY
EQ_TRANSITIVITY
AND_INTRO
AND_ELIM_LEFT
AND_ELIM_RIGHT
MODUS_PONENS
```

Terms use integer constants, variables, negation, addition, subtraction and multiplication. Formulas use atoms, equality/order relations, negation, conjunction, disjunction and implication.

## Run the challenge

```bash
python -m formal_proof_challenge.app
```

Open `http://127.0.0.1:8081`.

The interface includes valid arithmetic, valid modus ponens, false arithmetic, unsupported lemma, circular proof and target-mismatch fixtures. `Tamper one step` changes a valid arithmetic certificate into a deterministic rejection.

## CLI

```bash
python -m formal_proof_challenge.verifier \
  formal_proof_challenge/fixtures/valid_arithmetic.json
```

A valid proof exits `0`. A rejected proof exits `2`.

## Tests

```bash
python -m unittest tests.test_formal_proof_challenge -v
```

## Certificate boundary

The certificate proves only that the supplied proof closes under the declared finite rule set. It does not establish that the assumptions are true in the external world, that the rule set is complete, or that arbitrary natural-language mathematics has been understood.
