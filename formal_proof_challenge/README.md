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

The interface includes valid arithmetic, valid modus ponens, false arithmetic, unsupported lemma, circular proof and target-mismatch fixtures. `Tamper proof` changes a valid arithmetic certificate into a deterministic rejection.

FPG2 adds four public receipt actions:

- **Seal public receipt**;
- **Verify receipt**;
- **Tamper receipt**;
- **Download receipt**.

## FPG2 finality chain

```text
FormalProofGate certificate
        ↓
ECL decision: COMMIT or REJECT
        ↓
IEL audit transition: State(I,E,theta)
        ↓
SHA-256 receipt and previous-entry binding
        ↓
Tamper and replay verification
```

`VALID_PROOF` receives ECL `COMMIT`. Every other validly parsed certificate receives ECL `REJECT` with its typed rejection codes. Both decisions are appended as lawful audit events. Recording a rejection does not convert the rejected proof into a committed proof.

The IEL-style state obeys:

```text
I_after = I_before
E_after = E_before + positive entropy_delta
theta_after = theta_before + 1
```

`I` binds the rule-set hash and ECL policy hash. A changed rule set cannot silently continue the same ledger.

A receipt binds:

```text
proof certificate hash
ecl decision hash
iel entry hash
previous entry hash
receipt payload hash
replay key
receipt hash
```

The same proof certificate cannot be appended twice. A duplicate attempt returns `REPLAY_REJECTED` without changing the ledger.

## FPG3 hosted red team and external anchor

Hosted mode binds to `0.0.0.0:7860`, exposes health/stats/anchor endpoints, removes local filesystem paths from public responses, and supports a configurable ledger cap and read-only mode.

```bash
FPG_PUBLIC_MODE=1 \
FPG_LEDGER_PATH=/data/formal_proof_public_receipts.jsonl \
python -m formal_proof_challenge.app
```

Public endpoints:

```text
/healthz
/api/config
/api/stats
/api/anchor
```

Build the Docker Space bundle:

```bash
python formal_proof_challenge/deployment/build_hf_space_bundle.py \
  --output dist/formal-proof-gate-space
```

Build and verify an independently publishable ledger checkpoint:

```bash
python -m formal_proof_challenge.anchor \
  --ledger outputs/formal-proof-receipts.jsonl \
  --output latest-anchor.json
python -m formal_proof_challenge.anchor --verify latest-anchor.json
```

The external anchor binds the active calculus, ECL policy, IEL invariant, receipt counts, action totals, receipt Merkle root, final IEL state and ledger head. See [`FPG3_PUBLIC_LAUNCH.md`](FPG3_PUBLIC_LAUNCH.md) for the Space, GitHub Pages, Issue Form, persistence, and launch sequence.

## CLI

Verify a proof:

```bash
python -m formal_proof_challenge.verifier \
  formal_proof_challenge/fixtures/valid_arithmetic.json
```

Seal it into the public receipt ledger:

```bash
python -m formal_proof_challenge.finality \
  formal_proof_challenge/fixtures/valid_arithmetic.json \
  --ledger outputs/formal-proof-receipts.jsonl \
  --output outputs/valid-seal-result.json
```

Seal a deterministic one-step tamper:

```bash
python -m formal_proof_challenge.finality \
  formal_proof_challenge/fixtures/valid_arithmetic.json \
  --tamper-proof \
  --ledger outputs/formal-proof-receipts.jsonl \
  --output outputs/rejected-seal-result.json
```

Verify the full ledger:

```bash
python -m formal_proof_challenge.finality \
  --ledger outputs/formal-proof-receipts.jsonl \
  --verify-ledger
```

## Tests

```bash
python -m unittest tests.test_formal_proof_challenge -v
python -m unittest tests.test_formal_proof_finality -v
python -m unittest tests.test_fpg3_anchor -v
python -m unittest tests.test_fpg3_deployment -v
```

## Certificate boundary

The proof certificate establishes only that the supplied proof closes under the declared finite rule set. It does not establish that the assumptions are true in the external world, that the rule set is complete, or that arbitrary natural-language mathematics has been understood.

The FPG2 receipt is tamper-evident under its recorded SHA-256 chain. It is not a digital signature, identity certificate, trusted timestamp, consensus protocol, cryptocurrency, or legal notarization. A complete chain can be rewritten by an actor who controls every copy unless at least one receipt hash is independently anchored or published.
