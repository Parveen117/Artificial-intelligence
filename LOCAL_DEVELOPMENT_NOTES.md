# Local Development Notes: AI Trust Enablement

## Why failures happened and what each taught us

### 1. Entity contradiction became REVIEW
Initial smoke suite detected risk but did not block entity contradiction.
Fix: tightened fusion contradiction guard so contradictions block at lower risk.

### 2. Evidence cases crashed with runtime ERROR
Cause: FieldComparison dataclass objects were placed directly into hash payload.
Python JSON serializer could not encode them.
Fix: convert FieldComparison objects with asdict(c) before hashing.

### 3. Unsupported extra claim became COMMIT
Cause: fusion engine allowed low numeric risk to commit even when route-conflict/uncertain reasons existed.
Fix: unsupported/uncertain/route_conflict reasons now trigger REVIEW when risk is non-trivial.

### 4. Wrong conversion output became COMMIT
Cause: conversion object extraction was too coarse. "sound energy" and "electrical energy" were both too close because of the token "energy".
Fix: extract whole conversion target after "into/to" and canonicalize energy type.

## Current status

Smoke suite: 6/6 pass.
Local benchmark: 10/10 pass.

## Next advanced development

Claim Repair Engine v1:
- keep supported claims
- replace contradicted claims using best evidence
- remove unsupported claims
- request retrieval for uncertain/no-evidence claims
- emit repair certificate hash
