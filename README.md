# Artificial Intelligence Trust Enablement

This repository contains a deployable AI trust-enablement service for hallucination-residue evaluation, confidence-collapse detection, release control, certificate generation, ECL-style finality, Lambda-Laplace analytic diagnostics, topological-memory / winding-sector diagnostics, and Future Arrow forecasting.

> **Patent status.** This repository is associated with inventor-controlled patent filings and related intellectual-property rights. Publication does not grant any patent license. See [`PATENT_NOTICE.md`](PATENT_NOTICE.md).
>
> **Copyright and license boundary.** This is a public technical inspection and citation release, not an unrestricted open-source grant. All rights are reserved unless a separate written license states otherwise. See [`LICENSE`](LICENSE) and [`COPYRIGHT_NOTICE.md`](COPYRIGHT_NOTICE.md).
>
> **Public release boundary.** This repository is a selected public technical release and does not reproduce the complete private filing, research, hardware, or internal development record. See [`docs/PUBLIC_RELEASE_BOUNDARY.md`](docs/PUBLIC_RELEASE_BOUNDARY.md).

The production-oriented package is in `ai_trust_enablement/`. It provides:

- deterministic AI answer evaluation from context, prompt, and answer,
- concrete state signatures with `phase_value`, `scale_value`, and `seam_memory_value`,
- open-residue classification into `RECOGNITION`, `BOUNDED_RESIDUE`, or `ACTIONABLE_RESIDUE`,
- Lambda-Laplace diffusion, seam, heat-trace, and spectral-gap diagnostics,
- temporal topological-memory diagnostics for winding-sector and memory-transition detection,
- Future Arrow probability-cone forecasting after recognition or memory-transition events,
- machine-readable certificates and JSON schema,
- HTTP API service with health/version/schema/evaluate/batch/release/resolve/lambda-laplace/topological-memory/future-arrow endpoints,
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

The AI Trust stack can seal recognition, repair, release, retrieval-resolution, Lambda-Laplace, topological-memory, or Future Arrow certificates into an append-only ECL-style finality ledger.

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

Lambda-Laplace provides analytic seam evidence before topological-memory diagnostics mark a winding-sector transition. See `docs/LAMBDA_LAPLACE_INTEGRATION.md`.

## Topological-memory / winding-sector layer

The topological-memory layer evaluates a phase trajectory, computes winding-sector movement, and emits an `AI_TOPOLOGICAL_MEMORY_CERTIFICATE` when the trajectory crosses a memory/sector seam.

This extends the service from one-answer hallucination detection to temporal recognition-drift detection. See `docs/TOPOLOGICAL_MEMORY_INTEGRATION.md`.

## Future Arrow forecasting layer

The Future Arrow Operator projects the current recognition or topological-memory state forward into a probability-coated future cone and emits an `AI_FUTURE_ARROW_CERTIFICATE`.

```bash
python ai_trust_enablement/future_arrow_operator.py --demo
```

Future Arrow estimates where the recognition trajectory may go next. ECL can seal either actual events or forecast certificates. See `docs/FUTURE_ARROW_INTEGRATION.md`.

## Documentation

- `ai_trust_enablement/README.md` - enablement walkthrough and glossary.
- `docs/DEPLOYMENT.md` - deployment guide.
- `docs/PRODUCTION_CHECKLIST.md` - production readiness checklist.
- `docs/ECL_FINALITY_INTEGRATION.md` - AI certificate to ECL-style finality commit bridge.
- `docs/LAMBDA_LAPLACE_INTEGRATION.md` - Lambda-Laplace analytic diffusion and seam diagnostics.
- `docs/TOPOLOGICAL_MEMORY_INTEGRATION.md` - topological-memory / winding-sector diagnostics.
- `docs/FUTURE_ARROW_INTEGRATION.md` - Future Arrow probability-cone forecasting.
- `docs/PUBLIC_RELEASE_BOUNDARY.md` - public release scope and exclusions.
- `PATENT_NOTICE.md` - patent-rights notice.
- `COPYRIGHT_NOTICE.md` - copyright ownership and restriction notice.
- `LICENSE` - all-rights-reserved repository license boundary.
- `CITATION.cff` - citation metadata for academic and technical references.

## Status

Deployable v1 for evaluation, gating, audit certificates, regression testing, ECL finality sealing, Lambda-Laplace analytic diagnostics, topological-memory diagnostics, Future Arrow forecasting, and integration into AI applications. It is not a standalone truth oracle and not a substitute for domain validation.

This public release is a technical and citation layer associated with inventor-controlled intellectual-property materials.