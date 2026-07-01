# Artificial Intelligence Trust Enablement

This repository contains a deployable AI hallucination-recognition, confidence-collapse, release-control, ECL-finality, Monti topological-memory, and Future Arrow forecasting certificate service.

The production-oriented package is in `ai_trust_enablement/`. It provides:

- deterministic AI answer evaluation from context, prompt, and answer,
- concrete state signatures with `phase_value`, `scale_value`, and `seam_memory_value`,
- open-residue classification into `RECOGNITION`, `BOUNDED_RESIDUE`, or `ACTIONABLE_RESIDUE`,
- temporal Monti Operator diagnostics for winding-sector and memory-transition detection,
- Future Arrow probability-cone forecasting after recognition or Monti events,
- machine-readable certificates and JSON schema,
- HTTP API service with health/version/schema/evaluate/batch/release/resolve/monti/future-arrow endpoints,
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

The AI Trust stack can seal recognition, repair, release, retrieval-resolution, Monti, or Future Arrow certificates into an append-only ECL-style finality ledger.

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

## Monti topological-memory layer

The Monti Operator layer evaluates a phase trajectory, computes winding-sector movement, and emits an `AI_TOPOLOGICAL_MEMORY_CERTIFICATE` when the trajectory crosses a memory/sector seam.

```bash
python ai_trust_enablement/monti_operator.py --demo
```

HTTP example:

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

This extends the service from one-answer hallucination detection to temporal recognition-drift detection. See `docs/MONTI_OPERATOR_INTEGRATION.md`.

## Future Arrow forecasting layer

The Future Arrow Operator projects the current recognition/Monti state forward into a probability-coated future cone and emits an `AI_FUTURE_ARROW_CERTIFICATE`.

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

Monti says what crossed. Future Arrow estimates where the recognition trajectory may go next. ECL can seal either actual events or forecast certificates. See `docs/FUTURE_ARROW_INTEGRATION.md`.

## Documentation

- `ai_trust_enablement/README.md` - enablement walkthrough and glossary.
- `docs/DEPLOYMENT.md` - deployment guide.
- `docs/PRODUCTION_CHECKLIST.md` - production readiness checklist.
- `docs/ECL_FINALITY_INTEGRATION.md` - AI certificate to ECL-style finality commit bridge.
- `docs/MONTI_OPERATOR_INTEGRATION.md` - Monti Operator winding-sector memory diagnostics.
- `docs/FUTURE_ARROW_INTEGRATION.md` - Future Arrow probability-cone forecasting.

## Status

Deployable v1 for evaluation, gating, audit certificates, regression testing, ECL finality sealing, Monti temporal memory diagnostics, Future Arrow forecasting, and integration into AI applications. It is not a standalone truth oracle and not a substitute for domain validation.
