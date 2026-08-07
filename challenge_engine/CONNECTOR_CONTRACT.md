# Challenge Engine Connector Contract

Protocol version: `1.0`  
Engine version: `1.2.0` release candidate  
Arithmetic protocol: `exact-rational-directed-enclosure-v1`  
Seam protocol: `first-visible-jet-seam-quotient-v1`  
Source-bound numerical protocol: `source-bound-proof-carrying-numerics-v1`

This document defines the stable local process interface intended for connectors, CI systems, and other tools.

## What the connector is connecting to

The engine evaluates a **declared claim-to-evidence closure contract**. It does not treat `target.statement` as unrestricted natural-language semantics. By default the statement is payload identifying the target. A connector that wants language semantics evaluated must declare a semantic adapter.

A red-team connector should therefore think in these terms:

```text
TOE + claim + scope + threat model + evidence + adapters + obligations + success criterion
```

not:

```text
arbitrary English prompt -> universal truth verdict
```

## Strict JSON and numeric boundary

Connector input is strict interoperable JSON. Before evaluation the process rejects duplicate object keys and non-standard `NaN`, `Infinity`, and `-Infinity` tokens. Explicit malformed package/mode selections do not silently become defaults.

Ordinary finite decimal JSON tokens retain their original numeric lexeme so exact declared-value comparisons do not depend on a later binary floating representation. For genuinely arbitrary-precision proof values, use quoted exact decimal/rational strings in the numerical certificate fields.

## Discover capabilities

```bash
python challenge_engine/challenge.py --capabilities --compact
```

The result publishes package manifests, terminal states, parser/numerical protocols, seam-quotient boundary, source-bound operations/tail rules, the current implementation-manifest SHA-256, and stdin/stdout behavior.

## Evaluate by file or stdin

```bash
python challenge_engine/challenge.py challenge.json --compact
cat challenge.json | python challenge_engine/challenge.py - --compact
```

The process writes one JSON object to stdout.

## Minimum input

```json
{
  "challenge_id": "external-001",
  "target": {"statement": "The declared target to test."}
}
```

If `package` is omitted, `math` is used. If `mode` is omitted, the selected package default is used. Explicit blank/null/Boolean/unknown package or mode values are invalid rather than omissions.

## Natural-language semantics

Default:

```json
"semantics": {"mode": "payload_only"}
```

To request semantic interpretation:

```json
{
  "semantics": {"mode": "adapter_declared"},
  "semantic_adapter": {"id": "semantic-adapter-v1", "status": "pass"}
}
```

Requesting semantic interpretation without a closed adapter returns `SEMANTICS_NOT_IN_SCOPE`.

## Break conditions

Machine-readable break classes are:

```text
false_acceptance
blindness_escape
scope_escape
negative_control_escape
invalid_promotion
flow_consistency_escape
ledger_integrity_failure
```

## Challenge Genesis

Every valid evaluation emits `CHALLENGE_GENESIS` with:

```text
accepted_claims = 0
parent = null
rules_frozen = true
```

Genesis freezes rules, not outcomes. The contract commits target/scope/threat model, package/mode, adapter and obligation declarations, package-manifest SHA-256, parser/arithmetic declarations, numerical/seam certificates when present, and the current `implementation_manifest_sha256`.

The implementation fingerprint is a deliberate T47 hardening. It commits the parser/validator implementation used to interpret the rules, so a changed interpreter does not masquerade as the same frozen Genesis.

A connector may pin an agreed Genesis:

```json
"genesis": {"expected_hash": "<64-hex-sha256>"}
```

Because the T47 implementation fingerprint was introduced before the final v1.2.0 tag/archive, pre-T47 Genesis hashes are not release-stable pins. Pin the final release implementation.

## Challenge Evaluation

Every valid result also emits `CHALLENGE_EVALUATION`, binding:

- Genesis hash;
- normalized input hash;
- result and computed checks;
- optional parent Evaluation hash;
- its own SHA-256 evaluation hash.

The pure engine remains stateless. Parent existence, event uniqueness, ordering, and cross-request replay rejection require a persistent connector/ledger.

## Security target binding

Authorization-gated packages require:

```json
{
  "scope": {
    "authorization": "declared",
    "target": "local-demo-service"
  },
  "target": {
    "toe": "local-demo-service",
    "statement": "The declared property"
  }
}
```

`target.toe` must equal `scope.target`.

## Legacy arithmetic certificate

The legacy numerical carrier remains:

```text
exact-rational-directed-enclosure-v1
```

Supported kinds remain:

```text
exact_rational
exact_decimal
directed_interval
ball
raw_float
```

The old arithmetic layer still parses these objects and performs outward consistency calculations. T47 changes their **formal trust status**.

Without a T47 source proof, the only intrinsically proof-bearing legacy numerical cases are:

```text
exact_rational with analytic_tail = 0
exact_decimal  with analytic_tail = 0
```

The following do not formally promote merely because the participant supplied a radius or tail:

```text
directed_interval
ball
raw_float with radius
exact value with nonzero analytic_tail
```

If those objects are otherwise consistent, the formal result is held at `INCOMPLETE`. Disjoint independent enclosures can still fail. Overlap remains only a necessary consistency check, not backend authentication.

Thus this legacy example:

```json
"arithmetic_certificate": {
  "kind": "ball",
  "center": "0.93",
  "radius": "0.01",
  "analytic_tail": "0.04",
  "threshold": "1"
}
```

is no longer self-certifying. A field called `radius` is not evidence of how that radius was obtained.

## T47 source-bound proof-carrying numerics

The proof-bearing numerical path is:

```text
source-bound-proof-carrying-numerics-v1
```

Current source model:

```text
exact_expression_v1
```

Current admitted operations:

```text
add
sub
mul
neg
div
```

A certificate is shaped as:

```json
"source_bound_numerics": {
  "protocol": "source-bound-proof-carrying-numerics-v1",
  "source_model": "exact_expression_v1",
  "nodes": [
    {
      "id": "a",
      "kind": "exact_contract",
      "value": "1/3",
      "interval": {"lower": "1/3", "upper": "1/3"}
    },
    {
      "id": "b",
      "kind": "exact_contract",
      "value": "1/6",
      "interval": {"lower": "1/6", "upper": "1/6"}
    },
    {
      "id": "root",
      "kind": "op",
      "op": "add",
      "deps": ["a", "b"],
      "interval": {"lower": "49/100", "upper": "51/100"}
    }
  ],
  "root": "root",
  "tail": {"rule": "zero"},
  "threshold": "4/5"
}
```

For each operation node the engine recomputes the canonical exact rational interval from already-verified dependency intervals. The declared node interval may be wider but cannot be narrower than the verifier-computed enclosure.

The current trace limit is 256 nodes.

### Division rule

Division is admitted only when the denominator interval excludes zero:

```text
0 in denominator enclosure -> no certified division step
```

This does not alter ordinary algebraic division by zero and does not replace the separate Theorem-46 seam quotient.

### Tail rules

Current proof-bearing tail rules are:

```text
zero
geometric_tail
```

For `geometric_tail`, both the first omitted magnitude and ratio upper bound must reference verified DAG nodes:

```json
"tail": {
  "rule": "geometric_tail",
  "first_omitted_node": "first",
  "ratio_upper_node": "ratio"
}
```

If the verified ratio enclosure satisfies `0 <= q < 1`, the engine derives:

```text
tau = first_omitted_upper / (1 - ratio_upper)
```

The participant does not supply the final tail value.

The separately verified RKF Theorem 47 also proves a rational exponential upper rule and a Theorem-43 jet-tail construction. Those specialized rules remain out of the proof-bearing connector protocol until their norm/source hypotheses are bound by an admitted package-specific validator.

### Strict threshold semantics

After arithmetic and tail uncertainty are carried outward into `[L,U]`:

```text
U < threshold                  PASS
L >= threshold                 FAIL
L = U = threshold              FAIL for a strict < claim
L < threshold <= U             INCOMPLETE
```

Exact equality is mathematical falsity of a strict inequality, not uncertainty. A non-singleton enclosure touching the boundary remains incomplete because refinement may still decide it.

### Source boundary

`exact_expression_v1` proves the declared formal numeric expression. It does not prove that an arbitrary measurement, external backend result, or physical norm is correctly mapped into an exact leaf. External-world mapping requires the relevant package/connector source validator.

Legacy `arithmetic_certificate` and `source_bound_numerics` are mutually exclusive in one request.

Dedicated schema:

```text
challenge_engine/schema/source_bound_numerics.schema.json
```

## First-visible-jet seam quotient

The seam protocol is:

```text
first-visible-jet-seam-quotient-v1
```

Raw `1/0` and raw algebraic `0/0` remain invalid. The proof-bearing release model is `exact_polynomial_jet`.

For exact vanishing polynomial jets, if `r_A` and `r_B` are first nonzero coefficient orders:

```text
r_A > r_B                         FINITE_QUOTIENT_ZERO
r_A = r_B                         FINITE_SEAM_QUOTIENT = a_r / b_r
r_A < r_B                         DIVERGENT_NO_FINITE_QUOTIENT
all declared denominator jets 0   INCOMPLETE_FLAT_OR_UNRESOLVED
```

The approximate `analytic_with_validated_remainder` model remains `INCOMPLETE_REMAINDER_VALIDATION` until its reduced-function remainder sources are actually bound through an admitted source validator. T47 supplies the trust architecture but does not make arbitrary remainder claims true.

## Implementation fingerprint boundary

The engine publishes `implementation_manifest_sha256` in capabilities and commits it into every Genesis. The manifest covers the current strict parser, engine compatibility/current numerical layers, primary Challenge schema, and installed package manifests.

This is an integrity commitment. It is **not** an external authenticity oracle. If an attacker controls both executable and reported hash, the hash alone is not a trust anchor. The public Git commit, immutable archive, signature, attestation, or equivalent external pin must anchor the expected fingerprint when executable authenticity matters.

## Output additions

T47-capable results may include:

```json
{
  "implementation_manifest_sha256": "...",
  "source_bound_numerics_protocol": "source-bound-proof-carrying-numerics-v1",
  "source_bound_numerics_summary": {
    "proof_bearing": true,
    "root_lower": "7/10",
    "root_upper": "7/10",
    "analytic_tail": "1/50",
    "final_upper": "18/25",
    "threshold": "4/5",
    "classification": "STRICT_PASS"
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

## External trust and replay boundaries

The engine evaluates declared closure. Real-world evidence authenticity, signatures, sandboxing, remote attestation, external numerical-backend correctness, or arbitrary source truth remain connector/package obligations unless explicitly wired into an admitted validator.

The engine is stateless. Cross-request replay rejection remains a persistent ledger responsibility.

## Permission boundary

The connector protocol grants no additional permission to use, deploy, benchmark, modify, copy, commercialize, or otherwise exploit repository materials. Repository `LICENSE`, `PATENT_NOTICE.md`, and any separate written challenge authorization govern permitted use.

See also:

- `SOURCE_BOUND_NUMERICS_AUDIT.md`
- `ARITHMETIC_ENCLOSURE_AUDIT.md`
- `SEAM_QUOTIENT_AUDIT.md`
- `PUBLIC_CHALLENGE_SCOPE.md`
