# Lambda-Laplace Operator Integration

This document describes the Lambda-Laplace analytic layer added before Monti.

The design follows the uploaded Lambda-Laplace note:

```text
Delta_lambda = elliptic diffusion + lambda-skew + entropic drift
```

The operator is used as an analytic hinge connecting thermodynamic lambda geometry, nonreciprocal skew, heat-trace diagnostics, and spectral seam signals.

## Correct placement

Lambda-Laplace does not replace Monti.

```text
Lambda-Laplace Operator
  -> asks whether the lambda trajectory has analytic seam / diffusion / spectral-gap signatures

Monti Operator
  -> asks whether the lambda trajectory crosses a winding-number sector
```

Correct stack:

```text
AI recognition certificate
  -> Lambda-Laplace analytic diffusion / seam diagnostics
  -> Monti spectral-winding certificate
  -> Future Arrow probability cone
  -> optional ECL finality commit
```

## Added module

`ai_trust_enablement/lambda_laplace_operator.py`

It provides:

- `LambdaLaplaceConfig`
- `LambdaLaplaceOperator.evaluate_series(...)`
- `LambdaLaplaceOperator.evaluate_certificates(...)`
- `AI_LAMBDA_LAPLACE_CERTIFICATE`
- CLI demo via `python ai_trust_enablement/lambda_laplace_operator.py --demo`

## Inputs

The operator can accept raw series:

- `lambda_p_series`
- `lambda_v_series`
- `skew_intensity_series`
- `entropy_potential_series`

or prior recognition certificates:

```text
recognition_state.phase_value -> lambda_p
recognition_state.scale_value -> lambda_v
seam_memory.k                -> skew_intensity
recognition_state.open_residue -> entropy potential
```

## Certificate fields

The emitted certificate includes:

- `lambda_geometry`
- `operator_state`
- `spectral_state`
- `heat_state`
- `graph_state`
- `analysis`
- `technical_action`
- `certificate_hash`

Important values:

```text
seam_score
half_integer_trace_strength
lambda_laplace_series
spectral_gap_proxy
heat_trace_proxy
cycle_entropy_proxy
```

## Classifications

```text
LAMBDA_SMOOTH_STABLE
```

Stable lambda diffusion. Pass to Monti as stable input.

```text
LAMBDA_SEAM_SIGNATURE
```

Branch gap, skew, or heat-trace signature indicates a seam-like analytic signal. Feed to Monti.

```text
LAMBDA_DIFFUSION_STRESS
```

The lambda-Laplace series has high diffusion stress. Smooth and recheck trajectory.

```text
LAMBDA_SPECTRAL_GAP_WEAK
```

The spectral-gap proxy is weak. Increase the observation window.

## Technical actions

```text
PASS_TO_MONTI_AS_STABLE_INPUT
FEED_SEAM_SIGNAL_TO_MONTI
SMOOTH_AND_RECHECK_LAMBDA_TRAJECTORY
INCREASE_OBSERVATION_WINDOW
```

## HTTP endpoint

Run the service:

```bash
python ai_trust_enablement/server.py
```

Then call:

```bash
curl -s http://127.0.0.1:8080/v1/lambda-laplace \
  -H 'Content-Type: application/json' \
  --data '{
    "lambda_p_series": [0.00, 0.10, 0.22, 0.37, 0.54, 0.73, 0.95],
    "lambda_v_series": [0.00, 0.05, 0.09, 0.12, 0.18, 0.22, 0.30],
    "skew_intensity_series": [0.0, 0.2, 0.2, 0.4, 0.6, 0.8, 0.9],
    "entropy_potential_series": [0.01, 0.04, 0.08, 0.13, 0.20, 0.27, 0.35],
    "seam_threshold": 0.10,
    "stress_threshold": 0.60,
    "commit_to_ecl": true
  }'
```

A certificate-series call:

```json
{
  "certificates": [
    {"recognition_state": {"phase_value": 0.00, "scale_value": 0.00, "open_residue": 0.01}, "seam_memory": {"k": 0}},
    {"recognition_state": {"phase_value": 0.10, "scale_value": 0.05, "open_residue": 0.04}, "seam_memory": {"k": 1}},
    {"recognition_state": {"phase_value": 0.22, "scale_value": 0.09, "open_residue": 0.08}, "seam_memory": {"k": 1}},
    {"recognition_state": {"phase_value": 0.37, "scale_value": 0.12, "open_residue": 0.13}, "seam_memory": {"k": 2}}
  ],
  "commit_to_ecl": true
}
```

## ECL finality

When `commit_to_ecl` is true, the Lambda-Laplace certificate is sealed as:

```text
AI_LAMBDA_LAPLACE_CERTIFICATE
```

This is an analytic diagnostic finality record, not a topological-transition finality record. Monti remains responsible for the actual winding-sector jump claim.

## Run tests

```bash
python ai_trust_enablement/run_enablement_tests.py
```

The regression suite includes:

- Lambda-Laplace seam detection,
- Lambda-Laplace ECL commit compatibility,
- Monti spectral-winding tests,
- Future Arrow probability-cone tests.
