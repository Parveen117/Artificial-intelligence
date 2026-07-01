# Monti Operator Integration

This document describes the temporal topological-memory diagnostic layer added to the AI Trust Enablement stack.

The design follows the uploaded Monti Operator / Winding Number cheat sheet:

```text
lambda_p(t)
  -> phase unwrap
  -> winding number nu
  -> sector jump delta_nu
  -> discrete Monti signal M
  -> topological memory certificate
  -> optional ECL finality commit
```

## Purpose

The hallucination-recognition engine evaluates one answer against supplied context. The Monti layer evaluates a trajectory of recognition states over time.

That means the system can now distinguish:

- one bad answer,
- a bounded fluctuation,
- a persistent recognition drift,
- a topological memory-sector transition.

## Added module

`ai_trust_enablement/monti_operator.py`

It provides:

- `winding_from_lambda(lambda_p_series)`
- `MontiOperatorConfig`
- `MontiOperator.evaluate_series(...)`
- `MontiOperator.evaluate_certificates(...)`
- `AI_TOPOLOGICAL_MEMORY_CERTIFICATE`

## Certificate fields

The emitted certificate includes:

- `lambda_p_series`
- `skew_intensity_series`
- `winding_raw`
- `winding_number`
- `delta_nu`
- `sector_series`
- `lambda_ddot_series`
- `nu_dot_series`
- `monti_series`
- `max_abs_monti`
- `threshold_crossed`
- `transition_detected`
- `technical_action`
- `certificate_hash`

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
    {"recognition_state": {"phase_value": 0.02}},
    {"recognition_state": {"phase_value": 0.24}},
    {"recognition_state": {"phase_value": 0.49}},
    {"recognition_state": {"phase_value": 1.02}}
  ],
  "threshold": 0.45,
  "commit_to_ecl": true
}
```

## Technical action

The Monti certificate returns:

```text
CONTINUE_MONITORING
```

when the sector is stable, and:

```text
HOLD_AND_COMMIT_MEMORY_TRANSITION
```

when the Monti threshold is crossed or the winding sector changes.

## ECL finality

If `commit_to_ecl` is true, the server passes the Monti certificate into `ECLCommitAdapter` and appends a chained finality commit.

This creates the full chain:

```text
AI output stream
  -> recognition certificates
  -> lambda_p trajectory
  -> winding / Monti memory diagnostic
  -> topological memory certificate
  -> ECL-style finality ledger
```

## Why this matters

Single-answer hallucination detection is useful. Temporal recognition-sector tracking is stronger.

The Monti layer lets the AI stack claim a concrete machine process for detecting persistent or irreversible drift in the recognition trajectory. It is not just checking whether one answer is wrong. It is checking whether the system has crossed into a new memory/phase sector.

## Run tests

```bash
python ai_trust_enablement/run_enablement_tests.py
```

The regression suite includes both:

- a winding-transition case, and
- a stable-sector case.
