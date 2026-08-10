# RNKE Proof Before Action — Pre-Public Self-Red-Team Audit

## Decision

The public challenge was **not** released immediately after its first green launch candidate.

Before release, the maintainer attacked the exact candidate/action binding and Challenge Genesis boundary as an adversarial participant. The first independent probe suite deliberately failed CI and reproduced unauthorized executable `ADMIT` outcomes. The challenge remains blocked from the default branch until the repaired engine, new Genesis pin, complete regression suite, and launch verifier all close again.

## Scope

This audit used only local synthetic actions and repository fixtures. It performed no real email, payment, cloud, account, credential, device, or network side effect.

The target was:

```text
same frozen authority rules
+ materially different candidate action
+ candidate receives ADMIT
+ action_executable == true
```

The audit also tested whether candidate data could incorrectly alter the frozen Challenge Genesis.

## Finding SR-1 — Exact numeric action-alias false acceptance

**Pre-fix severity:** critical within the declared exact-action model  
**Status:** repaired and regression-locked before public release

The strict JSON connector preserves the exact lexeme of finite decimal input. However, the original Proof-Before-Action action hash delegated canonicalization to ordinary `json.dumps`. The preserved connector number is float-compatible, so hashing converted it through a binary float representation.

This created three reproducible unauthorized-`ADMIT` vectors in the first self-red-team run:

1. an authority created for exact JSON `0.1` also admitted candidate `0.10000000000000001`;
2. the same precision collision survived inside a nested parameter object;
3. an authority created for exact zero also admitted exact candidate `1e-4000`, which underflowed in the float carrier.

In each reproduction, the proposed candidate was materially different under the connector's exact-number contract, yet the old action hash collided and the gate returned:

```text
action_decision = ADMIT
action_executable = true
```

This was a real pre-release break of the exact-action claim, not merely a parser crash or documentation issue.

### Root causes

Two related numeric alias mechanisms were present:

- binary-float precision collapse;
- binary-float underflow to zero.

### Repair

`challenge_engine/action_gate.py` now uses a bounded first-party canonical JSON serializer for executable actions:

- exact connector decimals are canonicalized from their preserved lexeme;
- numerically equivalent spellings share one authority (`1`, `1.0`, `1.00`, `10e-1`);
- distinct exact values remain distinct even when a binary float would collide;
- numbers, strings, and Booleans remain type-distinct;
- object-key order is deterministic;
- cyclic, over-deep, over-large, and unsupported direct-API values fail closed;
- surrogate-containing strings are escaped deterministically rather than crashing encoding.

The repaired canonicalization identifier is:

```text
exact-decimal-value-canonical-json-v2
```

The validator manifest digest changes when this rule changes, so the old public Genesis cannot silently survive the repair.

## Finding SR-2 — Candidate numeric lexemes leaked into frozen Genesis

**Pre-fix severity:** contract-integrity defect  
**Status:** repaired and regression-locked before public release

The generic exact-number layer records connector decimal declarations in Challenge Genesis. For Proof Before Action, however, `action`, `request_nonce`, `approval`, and `proposal_context` are explicitly per-evaluation candidate fields.

Before repair, an exact decimal inside `action.parameters` entered the generic Genesis record. Consequently, changing only the candidate decimal changed Genesis, even though the public contract promised:

```text
candidate mutation      -> same Genesis
authority-rule mutation -> different Genesis
```

This did not authorize an invalid action by itself, but it made the proposed public red-team boundary inconsistent and could prevent challengers from testing numeric candidate mutations under one pinned authority contract.

### Repair

`challenge_engine/engine_v7.py` now removes exact-number declarations rooted under the four candidate fields from the frozen Genesis view. Those exact values remain bound by `CHALLENGE_EVALUATION` and by the repaired exact action hash.

Regression tests now verify both directions:

- every published candidate field leaves Genesis fixed;
- every published frozen authority field changes Genesis;
- an exact decimal candidate mutation keeps the Genesis pin valid but is rejected by the action gate.

## New independent probes

The self-red-team suite adds 14 test methods, including:

- exact-decimal precision collision;
- nested precision collision;
- underflow-to-zero collision;
- adjacent values beyond ordinary float integer precision;
- equivalent decimal spelling normalization;
- numeric/string/Boolean type separation;
- object-key-order invariance;
- cyclic direct-API input;
- excessive nesting;
- surrogate-safe canonicalization;
- candidate-versus-frozen Genesis separation.

One deterministic campaign adds 1,500 numeric-alias cases:

```text
1,000 underflow probes
500 long-precision probes
post-repair unauthorized ADMIT: 0
```

The inherited Proof-Before-Action campaign still runs:

```text
20,000 deterministic hostile mutations
20 mutation classes
post-repair unauthorized ADMIT: 0
```

At repaired head `a6a752f627975c8295c2bf606bd032cbc526d49d`, Challenge Engine workflow run `31382990948` completed successfully:

```text
159 tests: PASS
```

The launch workflow is intentionally required to fail until the repaired engine blobs and newly reconstructed Challenge Genesis are pinned in the public manifest.

## What remains outside this local proof boundary

This audit does not establish universal agent security.

- The official challenge input is strict JSON, which preserves exact decimal lexemes. A caller that constructs an already-rounded raw Python float has already destroyed source precision before RNKE receives it.
- Cross-request and concurrent nonce replay resistance requires authenticated, persistent, atomic committed state at the connector/deployment layer.
- Real principal, approver, evidence, and sensor identity require source authentication outside this pure evaluator.
- RNKE must sit on the real execution path; an executor that bypasses the gate is outside this software boundary.
- Denial of service and parser crashes are bugs but are not automatically proof of unauthorized execution.

## Release rule

The challenge may be promoted only after all of the following bind to one exact head:

1. repaired engine and validator identities are pinned;
2. the baseline Genesis is reconstructed and repinned;
3. all Challenge Engine, proof-pack, service, and public red-team workflows pass;
4. the submission verifier self-test passes;
5. the PR remains open, non-draft, and mergeable;
6. merge is separately and explicitly authorized.

The purpose of red teaming is not to preserve a green badge. It is to make hidden disagreement visible before commitment.
