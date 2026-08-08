# RNKE Proof-Before-Action: Initial Adversarial Audit

## Status

`proof-before-action-v1` is the candidate flagship RNKE Challenge for AI-agent execution.

The principle is deliberately narrower and stronger than "detect every malicious prompt":

> **Model output may propose an action. It does not create authority.**

The execution boundary admits an action only when the declared authority/evidence chain closes against committed state. The action gate returns one of:

```text
ADMIT | REJECT | INCOMPLETE | INVALID
```

Only `ADMIT` is executable.

## Exact v1 contract

The first proof-bearing implementation binds:

- declared principal;
- declared agent;
- exact tool;
- exact operation;
- exact resource;
- SHA-256 of the complete executable action, including parameters;
- a finite capability/delegation chain;
- committed validity epoch;
- revocation state;
- one-time request nonce / replay state;
- exact-action human confirmation when the frozen contract requires it.

Natural-language prompt or retrieved content is deliberately outside the authority channel. It may influence the proposal produced by an upstream model, but it cannot enlarge the authorization contract evaluated by RNKE.

## Internal red-team campaign

Before public promotion, the core gate was attacked locally with directed unit cases and a deterministic mutation campaign.

Directed classes include:

- hostile prompt payload;
- tool escape;
- operation escape;
- resource escape;
- parameter/recipient tampering;
- wrong agent;
- wrong principal;
- forged action hash;
- revoked grant;
- replayed request nonce;
- expired grant;
- missing authority;
- required confirmation omitted;
- stale confirmation reused after action mutation;
- delegation scope escalation;
- broken delegation issuer continuity;
- cyclic delegation;
- malformed committed replay state.

Initial local result:

```text
15 directed tests: PASS
20,000 deterministic hostile mutations across 20 mutation classes:
unauthorized ADMIT = 0
```

The repository test suite reproduces the 20,000-case mutation campaign in CI and also tests full Challenge Engine integration.

## Meaningful public break

A meaningful break is not merely making the LLM say or propose something malicious. The public target is stronger:

> Produce a case in which the declared `proof-before-action-v1` authority contract does not close, but RNKE still returns an executable `ADMIT` for the action.

Important break classes include false acceptance, scope escape, invalid promotion, replay escape, delegation escalation, confirmation-binding escape, or mutation of frozen authority rules without Genesis detection.

## Genesis requirement

The authority contract is committed into Challenge Genesis together with the action-validator manifest hash. A public red-team event should publish/pin the expected Genesis hash for the selected fixture. Otherwise a challenger can simply redefine the principal, grant, or rules and obtain a different valid contract, which is not a break of the original challenge.

## Current limits

This audit does **not** claim universal agent security.

- v1 uses exact-action grants rather than general wildcard capability languages.
- The engine does not authenticate a real human identity by itself; identity/source authentication belongs to the connector or deployment boundary.
- Replay resistance across requests requires committed persistent state that records consumed request nonces.
- RNKE must sit on the actual tool-execution path. A compromised executor that bypasses the gate is outside this software boundary.
- The protocol does not claim unrestricted natural-language semantic truth.
- The current fixture is synthetic/local and performs no real email, payment, filesystem, cloud, or network side effect.
- A passing internal campaign is evidence against the tested attack classes, not a proof that no implementation flaw exists.

## Public challenge sentence

> **Break Proof Before Action: make the agent execute an action whose frozen authority/evidence chain does not close.**
