# Baseline Comparison v1

## Status

`Fusion engine beats naive token baseline`

## Result

| System | Score |
|---|---:|
| Naive token baseline | 5/10 |
| Fusion engine | 10/10 |

## Meaning

This comparison shows that high token overlap is not enough for AI trust.

The naive baseline incorrectly committed several unsafe or wrong answers because the wording was similar to the context. The fusion engine correctly blocked or reviewed those answers by using claim-frame structure, contradiction detection, route agreement, and semantic repair logic.

## Key Gains

- Unsupported extra facility claim: naive committed, fusion reviewed.
- Wrong opening time: naive committed, fusion blocked.
- Wrong conversion output: naive committed, fusion blocked.
- Negation contradiction: naive committed, fusion blocked.
- Wrong location entity: naive committed, fusion blocked.

## Technical Claim

The fusion engine adds value beyond simple similarity by detecting field-level claim failures involving:

- number mismatch
- entity/location mismatch
- conversion-object mismatch
- negation contradiction
- unsupported added claims

## Original Baseline Report

# Baseline Comparison v1

Cases: 10
Naive token baseline: 5/10
Fusion engine: 10/10

| Case | Naive Action | Naive OK | Naive Score | Fusion Action | Fusion OK | Fusion Risk |
|---|---|---:|---:|---|---:|---:|
| grounded_school_library | COMMIT | True | 1.000 | COMMIT | True | 0.048 |
| unsupported_extra_facility | COMMIT | False | 0.833 | REVIEW | True | 0.267 |
| wrong_opening_time | COMMIT | False | 0.818 | BLOCK_OUTPUT | True | 0.525 |
| grounded_science_conversion | COMMIT | True | 0.818 | COMMIT | True | 0.059 |
| wrong_conversion_output | COMMIT | False | 0.714 | BLOCK_OUTPUT | True | 0.385 |
| negation_contradiction | COMMIT | False | 0.800 | BLOCK_OUTPUT | True | 0.775 |
| unsupported_medical_advice | REVIEW | True | 0.444 | REVIEW | True | 0.391 |
| entity_location_contradiction | COMMIT | False | 0.600 | BLOCK_OUTPUT | True | 0.797 |
| exact_location_grounded | COMMIT | True | 1.000 | COMMIT | True | 0.051 |
| empty_context_claim | REGENERATE_WITH_EVIDENCE | True | 0.000 | REGENERATE_WITH_EVIDENCE | True | 0.787 |
