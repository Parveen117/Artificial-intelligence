# Challenge Engine: Red-Team Rules of Engagement

## What the Challenge is

The Challenge is an attempt to break a **declared claim-to-evidence closure contract**.

It is not a contest to confuse the wording of `target.statement`.

A challenge contract declares, before evaluation:

- the target of evaluation (TOE);
- the claim/property being tested;
- authorized scope when the selected package requires it;
- the threat-model goal and accepted break conditions;
- evidence channels;
- mandatory obligations;
- negative controls;
- adapter identities;
- declared thresholds and completion tolerances.

The engine then asks whether that declared contract closes without an escaped blind direction, failed control, scope violation, unsupported promotion, or other listed break condition.

## What counts as a break

A meaningful break is one or more of the following machine-readable conditions:

- `false_acceptance`: an invalid or unsupported case receives an accepting result;
- `blindness_escape`: a target-changing state remains invisible under a claimed-faithful observation contract;
- `scope_escape`: a scoped package operates outside its declared authorized target;
- `negative_control_escape`: a deliberately invalid/mutated fixture is not detected;
- `invalid_promotion`: evidence is promoted beyond the level justified by its adapter, burden, or completion bounds;
- `flow_consistency_escape`: declared target visibility or bilateral flow consistency breaks while the challenge still passes;
- `ledger_integrity_failure`: the frozen rules of engagement can be changed without changing/detecting the genesis commitment.

A parser crash, malformed JSON, or an intentionally ambiguous English sentence is a software/schema bug only if it violates the documented protocol. It is not by itself a break of the theorem-backed claim-to-evidence model.

## Natural-language semantics boundary

By default:

```text
target.statement = payload / label
semantics.mode = payload_only
```

The engine does **not** claim unrestricted English-language understanding or semantic equivalence checking.

If a package wants natural-language semantics to participate in the challenge, it must declare:

```json
{
  "semantics": {"mode": "adapter_declared"},
  "semantic_adapter": {"id": "declared-adapter", "status": "pass"}
}
```

Without a closed semantic adapter, a request for semantic interpretation returns `SEMANTICS_NOT_IN_SCOPE` rather than pretending that prose has become a formal certificate.

This does not prevent non-formal testing. Black-box traces, fuzz summaries, measurements, model outputs, logs and other empirical evidence may enter exploratory/adversarial modes through their declared package/adapter boundary. They remain evidence unless and until formal-promotion obligations close.

## Challenge Genesis: ledger initiation

Every evaluation emits a `CHALLENGE_GENESIS` object.

Genesis means **the rules of engagement are frozen before candidate evaluation**. It does not mean that the claim is accepted.

At genesis:

```text
accepted_claims = 0
parent = null
rules_frozen = true
```

The genesis SHA-256 commits to the contract declaration, including package/mode, target, scope, threat model, semantic mode, required/declarative obligation identifiers, negative-control identifiers, evidence references, adapter identities and declared thresholds.

Outcome statuses are intentionally not part of the frozen genesis contract. A challenger can change evidence/test outcomes without redefining the rules. Changing the target, scope, threat model, adapter identity, or other committed rule changes the genesis hash.

A connector may pin a previously agreed genesis value:

```json
{
  "genesis": {
    "expected_hash": "<sha256>"
  }
}
```

A mismatch fails `genesis_integrity`.

## Testing modes

`exploratory` accepts empirical/non-formal observations and returns `OBSERVED` when its declared obligations close.

`adversarial` requires a threat model and negative controls and returns `ADVERSARIAL_PASS` only for the declared adversarial contract. It is not automatically a proof.

`certified` additionally requires formal support and the selected package's formal-promotion requirements. Only this mode can return `CERTIFIED`.

## Security package

`security_audit` is for authorized defensive assessment. The machine-readable scope gate remains mandatory. A challenge contract does not authorize activity that is otherwise unauthorized.

## Licence and permission boundary

This document describes the Challenge protocol; it does not grant permission to use the repository.

The repository `LICENSE`, `PATENT_NOTICE.md`, and any separate written challenge authorization govern permitted use. Activating a public challenge should therefore be accompanied by whatever explicit written permission/scope the rights holder intends participants to have. The Challenge protocol itself grants no additional copyright, patent, deployment, benchmarking, or derivative-work rights.
