# Arithmetic Enclosure Audit

Status: **PASS_EXACT_RATIONAL_ENCLOSURE_AUDIT**

Engine: Challenge Engine `1.2.0`
Arithmetic protocol: `exact-rational-directed-enclosure-v1`

## Problem addressed

The previous final-seal pass correctly prevented the binary floating-point boundary `0.1 + 0.7 < 0.8` from being treated as a strict pass. The remaining question was broader: how should the Challenge Engine accept exact decimals, rational values, arbitrary-precision numerical results, intervals, balls, and ordinary floating-point output without forcing every domain into one arithmetic representation?

The audited solution is a typed arithmetic hierarchy:

```text
exact integer / rational / finite decimal
        -> zero arithmetic radius
validated directed interval / ball
        -> explicit outward arithmetic radius
analytic truncation / completion
        -> separate analytic tail
strict promotion
        -> outward upper + analytic tail < threshold
```

Exact values are the zero-radius sector of the validated enclosure carrier. Irrational or numerically computed values do not have to be converted into fake fractions.

## Connector decimal preservation

Strict connector JSON now preserves the original finite decimal lexeme before ordinary binary floating-point conversion can affect exact threshold or canonical-hash decisions.

For example, the token

```text
0.123456789012345678901234567890123456789
```

retains that exact declared spelling for the arithmetic boundary even though a legacy float-compatible view is also available to the older engine layer.

Equivalent finite-decimal spellings such as `0.1` and `0.10` canonicalize to the same exact rational value for the Challenge Genesis contract.

For truly arbitrary-precision proof values, the public arithmetic-certificate fields accept quoted exact decimal or rational strings. This avoids requiring the legacy float-compatible carrier to hold an arbitrarily large or precise number.

## Proof-bearing arithmetic certificate

The public certificate supports:

```text
exact_rational
exact_decimal
directed_interval
ball
raw_float
```

The current certified scalar relation is:

```text
upper_below_threshold
```

Every proof-bearing approximate certificate declares the arithmetic enclosure and an independent `analytic_tail`. The engine promotes only when the outward upper bound remains strictly below the declared threshold.

A raw floating-point centre without a validated radius returns `INCOMPLETE`. Supplying more printed digits is not accepted as a substitute for an outward error bound.

## Independent-path check

A challenge may supply two or more independently obtained scalar enclosures. The engine requires them to have a nonempty common intersection. Disjoint certified enclosures fail closed because they cannot all contain the same exact scalar target.

This check does not prove that every overlapping backend is correct. It is an adversarial consistency obligation that detects mutually incompatible certificates.

## Genesis and evaluation commitments

The arithmetic protocol, exact connector numeric declarations, and any declared arithmetic certificate are committed into Challenge Genesis. Outcome changes remain separate and are committed through `CHALLENGE_EVALUATION`.

Thus formatting-equivalent exact values do not create artificial rule changes, while a real change in a numerical threshold, enclosure, radius, or analytic tail changes the frozen contract.

## New hostile tests

The arithmetic pass adds tests for:

- preservation of a long connector decimal lexeme;
- exact long-decimal threshold equality;
- equivalent decimal spellings producing the same canonical Genesis value;
- exact numeric declarations in Genesis;
- exact rational zero-radius promotion;
- arbitrary-precision exact decimal strings;
- ball-boundary non-promotion;
- directed-interval outward failure;
- raw floating point without radius remaining incomplete;
- raw floating point with a validated radius participating as an enclosure;
- disjoint independent enclosures failing;
- overlapping independent enclosures passing;
- zero-denominator rejection;
- arithmetic protocol capability discovery.

## Verification result

On the audited pull-request head, the Challenge Engine workflow reports:

```text
Ran 98 tests
OK
```

The same head also passed:

```text
Challenge Engine      SUCCESS
ai-trust-enable-ci    SUCCESS
CI Proof Pack v5      SUCCESS
```

The foundational mathematics/audit evidence remains separately reported as:

```text
236,456 exact/random/exhaustive adversarial cases
```

The counts are intentionally not collapsed into one homogeneous number.

## Claim boundary

This audit proves neither universal numerical stability nor correctness of an arbitrary external interval/ball implementation. A connector or package that relies on an external numerical backend remains responsible for establishing that its reported enclosure is genuinely outward and applies to the declared exact target.

The engine verifies the declared arithmetic closure contract. It does not bless an unvalidated backend merely because its JSON is tidy.

**Release status: PASS_EXACT_RATIONAL_ENCLOSURE_AUDIT.**
