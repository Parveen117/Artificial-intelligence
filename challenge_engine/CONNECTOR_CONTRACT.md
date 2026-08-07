# Challenge Engine Connector Contract

Protocol version: `1.0`
Engine version: `1.2.0`
Arithmetic protocol: `exact-rational-directed-enclosure-v1`
Seam quotient protocol: `first-visible-jet-seam-quotient-v1`

This document defines the stable local process interface intended for connectors, CI systems and other tools.

## What the connector is connecting to

The engine evaluates a **declared claim-to-evidence closure contract**.

It does not treat `target.statement` as unrestricted natural-language semantics. By default the statement is a payload/label identifying the target. A connector that wants language semantics evaluated must declare a semantic adapter.

A red-team connector should therefore think in these terms:

```text
TOE + claim + scope + threat model + evidence + adapters + obligations + success criterion
```

not:

```text
arbitrary English prompt -> universal truth verdict
```

## Strict JSON and numeric boundary

Connector input is strict interoperable JSON. Before challenge evaluation the process rejects:

- duplicate object keys at any nesting level;
- `NaN`, `Infinity`, and `-Infinity` tokens;
- malformed explicit package/mode selections instead of silently replacing them with defaults.

Ordinary finite decimal JSON tokens retain their original numeric lexeme so exact declared-value threshold and canonical-contract decisions do not depend on a later binary floating representation. Numerically equivalent finite-decimal spellings canonicalize to the same exact rational value for Genesis.

For genuinely arbitrary-precision proof values, use quoted exact decimal/rational strings inside the relevant certificate. A connector should not expect an ordinary platform float to preserve an unlimited decimal token merely because JSON looked very serious about it.

## Discover capabilities

```bash
python challenge_engine/challenge.py --capabilities --compact
```

Output is one JSON object containing engine/schema versions, default package, installed package manifests and SHA-256 commitments, terminal results, accepted break conditions, semantic default, Genesis/evaluation capabilities, arithmetic protocol, seam-quotient protocol, and stdin/stdout support. No network call is made by the engine.

## Evaluate by file

```bash
python challenge_engine/challenge.py /path/to/challenge.json --compact
```

## Evaluate by stdin

```bash
python challenge_engine/challenge.py - --compact
```

Send exactly one JSON object on stdin. Read exactly one JSON object on stdout.

## Minimum input

```json
{
  "challenge_id": "external-001",
  "target": {"statement": "The declared target to test."}
}
```

If `package` is **omitted**, `math` is used. If `mode` is **omitted**, the selected package's default mode is used. If `semantics` is omitted, `payload_only` is used. Explicit blank, null, Boolean, unknown or otherwise malformed package/mode values are not omissions and fail closed as `INVALID`.

For adversarial/certified operation, declare a threat model. Without one the result remains `INCOMPLETE`.

Input schema: `schema/challenge.schema.json`.

For authorization-gated packages such as `security_audit`, bind the target of evaluation explicitly:

```json
{
  "scope": {
    "authorization": "declared",
    "target": "local-demo-service"
  },
  "target": {
    "toe": "local-demo-service",
    "statement": "The declared security property"
  }
}
```

`target.toe` must match `scope.target`.

## Natural-language semantics

Default:

```json
"semantics": {"mode": "payload_only"}
```

In this mode an ambiguous, adversarial or witty English sentence does not redefine the theorem-backed challenge. The engine evaluates only the declared adapters/evidence/obligations.

To request semantic interpretation:

```json
{
  "semantics": {"mode": "adapter_declared"},
  "semantic_adapter": {"id": "semantic-adapter-v1", "status": "pass"}
}
```

If semantic interpretation is requested without a closed adapter, the terminal result is `SEMANTICS_NOT_IN_SCOPE`.

## Break conditions

The protocol recognizes:

```text
false_acceptance
blindness_escape
scope_escape
negative_control_escape
invalid_promotion
flow_consistency_escape
ledger_integrity_failure
```

A package-specific challenge may choose the subset relevant to its target. These values define what success for the challenger means before evaluation begins.

## Challenge Genesis / ledger initiation

Every result contains a `CHALLENGE_GENESIS` record with:

```text
accepted_claims = 0
parent = null
rules_frozen = true
```

Genesis means the **rules of engagement are committed before candidate evaluation**. It is not a positive verdict on the target.

The canonical hash commits to the contract declaration, selected package-manifest hash, parser/arithmetic contracts, exact connector numeric declarations, and declared arithmetic/seam-quotient certificates. Outcome statuses do not redefine the original rules.

A connector may pin a previously agreed contract:

```json
"genesis": {"expected_hash": "<64-hex-sha256>"}
```

A mismatch fails `genesis_integrity`. Malformed pins are `INVALID`.

Legacy requests with no seam-quotient certificate retain the pre-seam Genesis contract. A request that declares a seam certificate commits its protocol, seam identity, model and coefficient arrays into Genesis.

## Challenge Evaluation / outcome record

Every result also contains a hash-bound `CHALLENGE_EVALUATION` record. It binds the Genesis hash, normalized input, result and computed checks. A subsequent request may carry:

```json
"evaluation": {"parent_hash": "<64-hex-sha256>"}
```

The engine validates and carries the parent hash. The engine is intentionally stateless and cannot itself prove parent existence, event uniqueness or cross-request replay rejection. Those are persistent connector/ledger obligations.

## Exact threshold boundary

Burden, flow numeric checks and finite-to-limit threshold decisions use the exact declared decimal lexeme when the request came through the strict connector parser. Thus the mathematical equality

```text
0.1 + 0.7 = 0.8
```

cannot become a false strict pass because of binary rendering.

## Proof-bearing arithmetic certificate

The optional arithmetic certificate supports:

```text
exact_rational
exact_decimal
directed_interval
ball
raw_float
```

The current scalar relation is `upper_below_threshold`, with the declared closure rule:

```text
enclosure_upper + analytic_tail < threshold
```

Exact rational/decimal values occupy the zero-arithmetic-radius sector. Directed intervals and balls carry an outward arithmetic enclosure. A raw float without a radius remains `INCOMPLETE`.

**Important trust boundary:** the engine currently checks closure relative to submitted interval/radius/tail values. It does not, by itself, authenticate an external numerical backend or independently derive every submitted radius/tail. A deployment that represents such values as externally validated must provide the validating adapter/provenance layer. This boundary is being kept explicit rather than promoted by naming ceremony.

Independent scalar enclosures may be supplied. Their common intersection must be nonempty; disjoint claimed certified paths fail closed. Overlap is necessary consistency, not external-backend authentication.

## First-visible-jet seam quotient certificate

The optional seam quotient certificate represents a ratio of two vanishing functions along a declared seam. It does **not** redefine ordinary algebraic division by zero.

Raw scalar:

```text
1/0   invalid
0/0   invalid
```

Current proof-bearing model:

```text
exact_polynomial_jet
```

Example:

```json
"seam_quotient_certificate": {
  "seam_id": "demo-regular-seam",
  "model": "exact_polynomial_jet",
  "relation": "finite_seam_quotient",
  "numerator_coefficients": [0, 0, "2"],
  "denominator_coefficients": [0, 0, "4"]
}
```

Both constant coefficients must be zero. The coefficient arrays describe exact polynomial jets on the named seam. Let `r_A` and `r_B` denote first nonzero coefficient indices. The engine classifies:

```text
r_A > r_B                         FINITE_QUOTIENT_ZERO
r_A = r_B                         FINITE_SEAM_QUOTIENT = a_r / b_r
r_A < r_B                         DIVERGENT_NO_FINITE_QUOTIENT
all declared denominator jets 0   INCOMPLETE_FLAT_OR_UNRESOLVED
```

A zero rational denominator anywhere in the exact coefficient packet is `INVALID`.

The more general model name

```text
analytic_with_validated_remainder
```

is reserved in the schema but is **not proof-bearing yet**. It returns `INCOMPLETE_REMAINDER_VALIDATION`. Participant-supplied fields called `claimed_remainder`, `validated_radius`, or similar do not close the theorem hypothesis merely because a JSON key sounds authoritative.

The reason is mathematical: the general Theorem-46 quotient enclosure requires proved reduced-function remainder bounds and denominator separation. Until a source-bound validator establishes those hypotheses, the engine deliberately refuses numerical promotion for this model.

When seam evidence is present, output additionally contains:

```json
{
  "seam_quotient_protocol": "first-visible-jet-seam-quotient-v1",
  "seam_quotient_summary": {
    "classification": "FINITE_SEAM_QUOTIENT",
    "numerator_order": 2,
    "denominator_order": 2,
    "quotient": "1/2",
    "proof_bearing": true
  }
}
```

## Terminal results and exit codes

```text
OBSERVED                0
ADVERSARIAL_PASS        0
CERTIFIED               0
INCOMPLETE              2
FAILED                  3
INVALID                 4
BLOCKED_SCOPE           5
SEMANTICS_NOT_IN_SCOPE  6
```

## Permission boundary

The connector protocol grants no additional permission to use, deploy, benchmark, modify, copy, commercialize or otherwise exploit repository materials. The repository `LICENSE`, `PATENT_NOTICE.md`, and any separate written challenge authorization govern permitted use.

A public Challenge invitation should state the exact authorization/scope offered to participants. Machine-readable `security_audit` scope does not itself create legal authorization.
