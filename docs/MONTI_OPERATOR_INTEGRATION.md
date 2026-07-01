# Monti Operator Integration

This document describes the spectral-winding topological-memory diagnostic layer added to the AI Trust Enablement stack.

The design follows the uploaded Monti Operator / Winding Number notes:

```text
lambda_p(t)
  -> phase unwrap
  -> winding number nu
  -> spectral flow / sector jump delta_nu
  -> curvature stress M as supporting signal
  -> topological memory certificate
  -> optional ECL finality commit
```

## Correct semantics

Monti is not merely a large-threshold detector.

The primary topological event is the integer winding-sector change:

```text
Delta nu != 0
```

The curvature Monti value `M` remains useful, but it is secondary:

```text
M > M* and Delta nu = 0
  -> curvature stress without topological jump
```

This keeps the implementation aligned with the Monti-Winding reading: spectral flow across a reference angle is the integer change of winding number. The threshold is a stress indicator. The integer jump is the crown. Tiny distinction, massive consequences, naturally.

## Purpose

The hallucination-recognition engine evaluates one answer against supplied context. The Monti layer evaluates a trajectory of recognition states over time.

That means the system can now distinguish:

- one bad answer,
- a bounded fluctuation,
- curvature stress without sector transition,
- persistent recognition drift,
- a topological memory-sector transition.

## Thermo seed interface

The thermodynamic seed gives the lambda interpretation:

```text
lambda_p = phase branch
lambda_v = scale / volume branch
skew_intensity = branch defect / nonreciprocal seam stress
```

For AI trust certificates, the engineering mapping is:

```text
recognition_state.phase_value -> lambda_p
recognition_state.scale_value -> lambda_v
seam_memory.k                -> skew_intensity
open_residue                 -> fallback phase/stress signal
```

This does not claim an AI answer literally has heat capacity. It preserves the structural role from the thermodynamic seed: phase branch, scale branch, and nonreciprocal branch defect.

## Added module

`ai_trust_enablement/monti_operator.py`

It provides:

- `winding_from_lambda(lambda_p_series)`
- `thermo_seed_from_certificate(certificate)`
- `MontiOperatorConfig`
- `MontiOperator.evaluate_series(...)`
- `MontiOperator.evaluate_certificates(...)`
- `AI_TOPOLOGICAL_MEMORY_CERTIFICATE`

## Certificate fields

The emitted certificate includes:

- `thermo_seed`
- `lambda_p_series`
- `lambda_v_series`
- `skew_intensity_series`
- `winding_raw`
- `winding_number`
- `delta_nu`
- `holonomy_phase`
- `holonomy_turns`
- `spectral_flow`
- `spectral_crossing`
- `sector_series`
- `lambda_ddot_series`
- `nu_dot_series`
- `monti_series`
- `max_abs_monti`
- `threshold_crossed`
- `curvature_stress`
- `transition_detected`
- `technical_action`
- `certificate_hash`

## Classifications

The Monti certificate returns one of:

```text
STABLE_TOPOLOGICAL_SECTOR
```

No winding jump and no threshold stress.

```text
CURVATURE_STRESS_WITHOUT_SECTOR_JUMP
```

Curvature stress is present, but there is no integer sector jump. This is a warning/pre-transition state, not the final topological event.

```text
TOPOLOGICAL_MEMORY_TRANSITION
```

An integer winding-sector jump is detected. This is the primary Monti event.

## Technical actions

```text
CONTINUE_MONITORING
```

Stable sector.

```text
FLAG_CURVATURE_STRESS
```

Curvature stress without sector jump.

```text
HOLD_AND_COMMIT_TOPOLOGICAL_JUMP
```

Integer winding jump / spectral-flow transition. This is the event that should be sealed into ECL finality when proof logging is enabled.

## HTTP usage

Run the server:

```bash
python ai_trust_enablement/server.py
```

Then submit raw lambda samples:

```bash
curl -s http://127.0.0.1:8080/v1/monti \
  -H 'Content-Type: application/json' \
  --data '{
    "lambda_p_series": [0.00, 0.15, 0.32, 0.50, 0.74, 1.02, 1.18],
    "skew_intensity_series": [0.0, 0.1, 0.1, 0.2, 0.4, 0.5, 0.5],
    "alpha": 0.25,
    "beta": 0.20,
    "threshold": 0.45,
    "commit_to_ecl": true
  }'
```

Or submit prior AI certificates:

```json
{
  "certificates": [
    {"recognition_state": {"phase_value": 0.02, "scale_value": 0.01}, "seam_memory": {"k": 0}},
    {"recognition_state": {"phase_value": 0.24, "scale_value": 0.03}, "seam_memory": {"k": 1}},
    {"recognition_state": {"phase_value": 0.49, "scale_value": 0.05}, "seam_memory": {"k": 1}},
    {"recognition_state": {"phase_value": 1.02, "scale_value": 0.08}, "seam_memory": {"k": 2}}
  ],
  "threshold": 0.45,
  "commit_to_ecl": true
}
```

## ECL finality

If `commit_to_ecl` is true, the server passes the Monti certificate into `ECLCommitAdapter` and appends a chained finality commit.

This creates the full chain:

```text
AI output stream
  -> recognition certificates
  -> thermo-seeded lambda_p trajectory
  -> winding / spectral-flow diagnostic
  -> Monti topological memory certificate
  -> ECL-style finality ledger
```

## Why this matters

Single-answer hallucination detection is useful. Temporal recognition-sector tracking is stronger.

The Monti layer lets the AI stack claim a concrete machine process for detecting persistent or irreversible drift in the recognition trajectory. It is not just checking whether one answer is wrong. It is checking whether the system has crossed into a new memory/phase sector.

## Run tests

```bash
python ai_trust_enablement/run_enablement_tests.py
```

The regression suite includes:

- a winding/spectral-flow transition case,
- a curvature-stress-without-sector-jump case,
- a stable-sector case,
- an ECL finality classification-priority case.
