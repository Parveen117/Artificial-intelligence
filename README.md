# Artificial Intelligence Trust Enablement

This repository contains a deployable AI hallucination-recognition, confidence-collapse, release-control, ECL-finality, Lambda-Laplace analytic, Topological Memory topological-memory, and Future Arrow forecasting certificate service.

The production-oriented package is in `ai_trust_enablement/`. It provides:

- deterministic AI answer evaluation from context, prompt, and answer,
- concrete state signatures with `phase_value`, `scale_value`, and `seam_memory_value`,
- open-residue classification into `RECOGNITION`, `BOUNDED_RESIDUE`, or `ACTIONABLE_RESIDUE`,
- Lambda-Laplace diffusion, seam, heat-trace, and spectral-gap diagnostics,
- temporal Topological Memory Operator diagnostics for winding-sector and memory-transition detection,
- Future Arrow probability-cone forecasting after recognition or Topological Memory events,
- machine-readable certificates and JSON schema,
- HTTP API service with health/version/schema/evaluate/batch/release/resolve/lambda-laplace/topological_memory/future-arrow endpoints,
- answer release, repair, retrieval-resolution, and ECL-style finality commit support,
- Docker and docker-compose deployment files,
- no-dependency regression tests.

## Quick start

```bash
python ai_trust_enablement/run_enablement_tests.py
python ai_trust_enablement/server.py
```

In another terminal:

```bash
curl -s http://127.0.0.1:8080/v1/evaluate \
  -H 'Content-Type: application/json' \
  --data @examples/evaluate_request.json
```

## Docker

```bash
docker build -t ai-trust-enable:latest .
docker run --rm -p 8080:8080 ai-trust-enable:latest
```

Set `AI_TRUST_API_TOKEN` before exposing the service beyond localhost.

## ECL finality bridge

The AI Trust stack can seal recognition, repair, release, retrieval-resolution, Lambda-Laplace, Topological Memory, or Future Arrow certificates into an append-only ECL-style finality ledger.

```python
from dataclasses import asdict
from ai_trust_enablement.ai_hallucination_recognition_engine import AIHallucinationRecognitionEngine
from ai_trust_enablement.ecl_commit_adapter import ECLCommitAdapter

engine = AIHallucinationRecognitionEngine()
certificate = asdict(engine.evaluate(
    reference_text="The Eiffel Tower is located in Paris. It was completed in 1889.",
    prompt="Answer using only the supplied context.",
    answer="The Eiffel Tower is located in Berlin. It was completed in 1789.",
))

commit = ECLCommitAdapter().commit_certificate(certificate)
print(commit.to_dict())
```

This creates a chained finality record with certificate hash, proposal hash, positive entropy delta, previous commit pointer, and commit hash. See `docs/ECL_FINALITY_INTEGRATION.md`.

## Lambda-Laplace analytic layer

The Lambda-Laplace layer evaluates lambda trajectories through diffusion, skew drift, entropic drift, heat-trace proxy, and seam/spectral-gap diagnostics. It emits an `AI_LAMBDA_LAPLACE_CERTIFICATE`.

```bash
python ai_trust_enablement/lambda_laplace_operator.py --demo
```

HTTP example:

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

Lambda-Laplace provides analytic seam evidence before Topological Memory makes any topological jump claim. See `docs/LAMBDA_LAPLACE_INTEGRATION.md`.

## Topological Memory topological-memory layer

The Topological Memory Operator layer evaluates a phase trajectory, computes winding-sector movement, and emits an `AI_TOPOLOGICAL_MEMORY_CERTIFICATE` when the trajectory crosses a memory/sector seam.

```bash
python ai_trust_enablement/topological_memory_operator.py --demo
```

HTTP example:

```bash
curl -s http://127.0.0.1:8080/v1/topological-memory \
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

This extends the service from one-answer hallucination detection to temporal recognition-drift detection. See `docs/TOPOLOGICAL_MEMORY_OPERATOR_INTEGRATION.md`.

## Future Arrow forecasting layer

The Future Arrow Operator projects the current recognition/Topological Memory state forward into a probability-coated future cone and emits an `AI_FUTURE_ARROW_CERTIFICATE`.

```bash
python ai_trust_enablement/future_arrow_operator.py --demo
```

HTTP example:

```bash
curl -s http://127.0.0.1:8080/v1/future-arrow \
  -H 'Content-Type: application/json' \
  --data '{
    "entropy_potential": 0.45,
    "statistical_layer": 0.60,
    "delta_t": 2.0,
    "nsl_strength": 0.30,
    "anchor_constraints": ["prime_anchor:recognition"],
    "commit_to_ecl": true
  }'
```

Topological Memory says what crossed. Future Arrow estimates where the recognition trajectory may go next. ECL can seal either actual events or forecast certificates. See `docs/FUTURE_ARROW_INTEGRATION.md`.

## Documentation

- `ai_trust_enablement/README.md` - enablement walkthrough and glossary.
- `docs/DEPLOYMENT.md` - deployment guide.
- `docs/PRODUCTION_CHECKLIST.md` - production readiness checklist.
- `docs/ECL_FINALITY_INTEGRATION.md` - AI certificate to ECL-style finality commit bridge.
- `docs/LAMBDA_LAPLACE_INTEGRATION.md` - Lambda-Laplace analytic diffusion and seam diagnostics.
- `docs/TOPOLOGICAL_MEMORY_OPERATOR_INTEGRATION.md` - Topological Memory Operator winding-sector memory diagnostics.
- `docs/FUTURE_ARROW_INTEGRATION.md` - Future Arrow probability-cone forecasting.

## Status

Deployable v1 for evaluation, gating, audit certificates, regression testing, ECL finality sealing, Lambda-Laplace analytic diagnostics, Topological Memory temporal memory diagnostics, Future Arrow forecasting, and integration into AI applications. It is not a standalone truth oracle and not a substitute for domain validation.
