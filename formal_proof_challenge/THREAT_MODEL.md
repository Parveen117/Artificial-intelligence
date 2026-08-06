# Formal Proof Gate FPG2 Threat Model

## Security goal

FPG2 makes one submitted proof decision replayable and tamper-evident. It binds the formal proof certificate, ECL action, IEL state transition, previous ledger entry and public receipt into one SHA-256 chain.

## Detected conditions

The verifier detects:

- changed proof certificate fields without a matching certificate hash;
- a forged `VALID_PROOF` status while closure flags or errors remain open;
- changed ECL action, classification, policy or decision hash;
- changed IEL payload, state, entropy delta, event index or previous-entry pointer;
- changed receipt fields without a matching receipt hash;
- duplicate proof-certificate replay in the same ledger;
- rule-set or ECL-policy changes inside an existing IEL invariant chain;
- an already-corrupted ledger before a new append.

## Explicit non-goals

FPG2 does not provide:

- a digital signature or signer identity;
- a trusted timestamp;
- distributed consensus or blockchain finality;
- protection against an attacker who controls every stored copy and rewrites the complete chain;
- proof that declared assumptions are externally true;
- proof that the finite rule set is complete or sound beyond its implemented rules;
- parsing of unrestricted natural-language mathematics.

## External anchoring

To detect complete-history replacement, publish or independently retain at least one receipt hash or ledger head hash. Examples include a signed release, an institutional archive, a DOI deposit, a transparency log or another independently controlled storage system.

The public challenge should describe its receipts as **tamper-evident SHA-256 audit receipts**, not signatures, notarizations or universal proof certificates.
