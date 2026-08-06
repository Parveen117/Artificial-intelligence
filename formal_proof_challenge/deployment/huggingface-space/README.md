---
title: Break the Formal Proof Gate
emoji: 🔐
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
fullWidth: true
header: mini
short_description: Red-team a finite formal-proof verifier with ECL, IEL, tamper, replay, and public-anchor receipts.
---

# Break the Formal Proof Gate

A public red-team challenge for finite typed derivations.

A real break is an invalid proof inside the admitted JSON grammar that receives `VALID_PROOF`. Unsupported prose and unknown rules fail closed.

The hosted app emits:

- a deterministic formal-proof certificate;
- an ECL-style `COMMIT` or `REJECT` decision;
- an IEL-style append-only audit transition;
- a SHA-256 receipt with replay and tamper checks;
- a public ledger-head anchor at `/api/anchor`.

This is a research demonstration, not a digital signature, identity proof, trusted timestamp, consensus system, or legal notarization service.
