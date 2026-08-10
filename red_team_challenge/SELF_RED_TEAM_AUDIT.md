# RNKE Proof Before Action — Pre-Public Self-Red-Team Audit

## Decision

The public challenge was **not** released after the first green launch candidate, and it was **not** released after the first repair merely because the original tests turned green.

Two adversarial rounds were run before release:

1. the first maintainer self-red-team broke exact-action hashing and found a Genesis-boundary defect;
2. a later independent external-style probe set attacked assumptions not covered by the first campaign and exposed additional proof-to-execution carrier seams, unbounded security-state inputs, and two inert public challenge tracks.

Both rounds were allowed to fail CI. The repaired candidate is promoted only after the same failing probes become permanent regression tests and the release package reconstructs one exact Genesis.

## Scope

All attacks used local synthetic actions and repository fixtures. No real email, payment, cloud, account, credential, device, network, or third-party system was targeted.

The flagship target is:

```text
same frozen authority rules
+ materially unauthorized candidate action
+ candidate receives ADMIT
+ action_executable == true
```

The audit also tests whether proof identity and the object actually delivered to an executor remain the same object across parser and runtime-carrier seams.

## Finding SR-1 — Exact numeric action-alias false acceptance

**Pre-fix severity:** critical within the declared exact-action model  
**Status:** repaired and regression-locked

The original Proof-Before-Action action hash delegated number serialization through a binary-float-compatible path. The first self-red-team reproduced three unauthorized executable `ADMIT` outcomes:

1. authority for exact JSON `0.1` also admitted exact candidate `0.10000000000000001`;
2. the same precision collision survived inside a nested parameter object;
3. authority for exact zero also admitted exact candidate `1e-4000`, which underflowed in the binary-float carrier.

These were real authorization breaks. The candidate differed under the declared exact-number contract while the gate still returned executable `ADMIT`.

### First repair

A bounded first-party canonicalizer recovered exact connector decimal lexemes before hashing. That closed precision-collapse and underflow aliases and retained deterministic object ordering, type separation, depth/node/byte limits, cycle rejection, and surrogate-safe encoding.

The first repair was intentionally not treated as final. A second external-style round then attacked the remaining parser-to-executor seam.

## Finding SR-2 — Candidate numeric lexemes leaked into frozen Genesis

**Pre-fix severity:** contract-integrity defect  
**Status:** repaired and regression-locked

The generic exact-number layer recorded connector numeric declarations in Challenge Genesis. For Proof Before Action, however, `action`, `request_nonce`, `approval`, and `proposal_context` are per-evaluation candidate fields.

Before repair, changing an exact decimal inside the candidate action could change Genesis. That violated the intended challenge relation:

```text
candidate mutation      -> same Genesis
authority-rule mutation -> different Genesis
```

`engine_v7.py` now excludes candidate-rooted exact-number declarations from the frozen authority view. Those values remain bound by `CHALLENGE_EVALUATION` and by the executable action hash.

Regression tests verify both directions: every published candidate field leaves Genesis fixed, every frozen authority field changes Genesis, and an unauthorized numeric candidate can preserve the Genesis pin while still being rejected by the gate.

## Finding SR-3 — Proof identity could differ from executable carrier identity

**Pre-fix severity:** high; critical when downstream semantics distinguish the carriers  
**Status:** repaired and regression-locked

The second external-style round found two identity aliases that were not covered by the first exact-decimal campaign:

1. direct Python authority for `+0.0` could be reused by candidate `-0.0` because zero sign was erased by canonicalization;
2. direct Python integer authority `1` could be reused by direct Python float candidate `1.0` because value equality was treated as executable identity.

For authorization, mathematical equality is not sufficient when two runtime objects can drive different downstream semantics. The repaired rule is therefore:

```text
value equivalence does not imply executable-carrier equivalence
```

### Second repair: carrier-stable exact JSON v3

Executable action hashing now uses:

```text
carrier-stable-exact-json-v3
```

The connector/runtime boundary is explicit:

- strict JSON integers and decimals retain their exact numeric lexemes on runtime-compatible wrappers;
- strict-JSON spellings of the same JSON number, including `1`, `1.0`, `1.00`, and `10e-1`, retain one connector-number authority;
- direct API Python integers and floats retain distinct carrier identities;
- signed zero is preserved where the runtime carrier preserves it;
- strings and Booleans remain type-distinct from numbers.

This lets the JSON protocol preserve numeric-value equivalence without silently granting direct-runtime carrier equivalence.

## Finding SR-4 — Exact proof value could outlive a lossy runtime carrier

**Pre-fix severity:** high proof-to-execution seam  
**Status:** repaired and regression-locked

The second round constructed strict JSON decimal `9007199254740993.0`. Its exact lexeme was available to proof/canonicalization logic, while the float-compatible runtime carrier could not represent the same exact value. A similar portability problem exists for integers outside the commonly safe cross-runtime JSON integer range.

This exposed the central seam:

```text
proof recognizes exact value A
executor carrier contains value B
```

A certificate for `A` must never authorize execution of `B` merely because the parser preserved evidence about `A` somewhere beside the carrier.

The gate now performs a carrier-fidelity check before execution:

- an exact connector decimal whose runtime float carrier represents a different value is `INVALID` and non-executable;
- action integers outside the cross-runtime safe JSON integer range `[-9007199254740991, 9007199254740991]` are `INVALID` and non-executable;
- zero sign is included in the fidelity comparison where relevant.

This is the stronger invariant produced by the failure:

> **Proof-to-Execution Identity:** An action may cross the execution boundary only if the object certified by the authorization representation is identical, under the declared carrier semantics, to the object available to the executor.

## Finding SR-5 — Security-relevant state was insufficiently bounded

**Pre-fix severity:** robustness / denial-of-service boundary; fail-closed requirement  
**Status:** repaired and regression-locked

External probes supplied:

- a 65,537-character request nonce;
- a replay-state list with 10,001 entries.

The old gate validated shape but did not impose explicit resource bounds. These were not demonstrated unauthorized-`ADMIT` breaks by themselves, but an execution gate should not accept unbounded security-state structures and hope the surrounding system remains cheerful.

The validator manifest now binds explicit limits:

- request nonce: non-empty, at most 4,096 UTF-8 bytes;
- replay/revocation lists: at most 10,000 entries;
- state tokens: non-empty, duplicate-free, at most 4,096 UTF-8 bytes each;
- action canonicalization: existing depth, node, and byte bounds remain enforced.

Violations fail closed as `INVALID` and non-executable. Because the limits are part of validator identity, changing them changes the frozen Challenge Genesis.

## Finding SR-6 — Two advertised public attack tracks were inert

**Pre-fix severity:** challenge-contract defect  
**Status:** repaired

The public manifest advertised replay and approval/confirmation attack surfaces, but the original baseline fixture contained:

```text
used_request_nonces = []
confirmation_required = false
```

A participant therefore could not meaningfully exercise those advertised tracks under the pinned frozen state.

The repaired baseline now contains a previously consumed synthetic nonce while the baseline request remains fresh, and it requires a valid exact-action approval. Consequently:

- mutating the candidate nonce can exercise replay behavior against non-empty frozen replay state;
- mutating/removing approval can exercise the confirmation binding;
- the clean baseline still closes to executable `ADMIT`.

## External-style probe accounting

The second round added eight independent test methods:

```text
1  signed-zero authority reuse
2  direct int/float carrier authority reuse
3  exact-decimal/runtime-float mismatch
4  unsafe cross-runtime action integer
5  oversized request nonce
6  oversized replay-state list
7  inert replay public fixture
8  inert confirmation public fixture
```

Before the second repair these probes exposed the corresponding gaps. After repair:

```text
8 / 8 external-style probes: PASS
```

The complete regression directory now contains the previously published 159-test suite plus these eight methods:

```text
167 combined regression tests: PASS
```

The inherited adversarial campaigns remain:

```text
1,500 deterministic exact-decimal alias probes: PASS
20,000 deterministic hostile mutations: PASS
post-repair unauthorized ADMIT in tested campaigns: 0
```

## Exact repaired release-candidate evidence

On repaired head `f9664137a80e7f092797357f98b3bff7d7248961`, RNKE Public Red-Team Challenge workflow run `31408704528` completed successfully. The run passed:

- complete Challenge Engine regression suite;
- reconstructed baseline Genesis reporting;
- public launch release check;
- submission verifier self-test;
- submitted reproduction-package validation;
- credential-like-material scan.

The reconstructed repaired baseline Genesis is:

```text
b8d4c3d2b451ea20f96786832c88a38065fb31afe4b36af4d3a42f659430371f
```

That digest is the release pin for the repaired authority/rule contract.

## What remains outside this local proof boundary

This audit does not establish universal agent security.

- Persistent and concurrent cross-request nonce replay resistance requires authenticated, persistent, atomic committed state at the connector/deployment layer.
- Real principal, approver, evidence, and sensor identity require source authentication outside this pure evaluator.
- RNKE must sit on the real execution path; an executor that bypasses the gate is outside this software boundary.
- Cross-language adapters must preserve the declared numeric/carrier contract rather than silently coercing values before RNKE receives them.
- Resource limits reduce local attack surface but do not constitute a universal denial-of-service proof.

## Release rule

The challenge may be promoted only after all of the following bind to one exact release candidate:

1. repaired engine and validator identities are pinned;
2. the baseline Genesis is reconstructed and repinned;
3. original and external-style red-team probes all pass;
4. complete Challenge Engine, proof-pack, service, and public red-team workflows pass or expose no unresolved release-blocking failure;
5. submission verifier self-test passes;
6. public challenge replay and confirmation tracks are live rather than inert;
7. the PR remains open, non-draft, and mergeable;
8. merge remains a separate explicit action.

The purpose of red teaming is not to preserve a green badge. It is to make hidden disagreement visible before commitment, then turn each discovered seam into a permanent executable obligation.
