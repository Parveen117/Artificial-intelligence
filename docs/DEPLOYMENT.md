# Deployment Guide: AI Trust Enablement Service

This guide describes how to run the AI hallucination-recognition engine as a local service, Docker container, or installed Python package.

The service is deployable as a first production-oriented v1. It is not a certified medical, legal, financial, or safety-critical decision system. Use it as a verification, gating, logging, certificate, release-control, Topological Memory temporal-memory, and finality-sealing layer. Humanity keeps trying to skip validation, and somehow the servers keep catching fire.

## 1. Local run

From the repository root:

```bash
python ai_trust_enablement/run_enablement_tests.py
python ai_trust_enablement/server.py
```

Health check:

```bash
curl http://127.0.0.1:8080/healthz
```

Evaluate one answer:

```bash
curl -s http://127.0.0.1:8080/v1/evaluate \
  -H 'Content-Type: application/json' \
  --data @examples/evaluate_request.json
```

Evaluate a Topological Memory temporal-memory trajectory:

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

## 2. Token-protected local service

```bash
export AI_TRUST_API_TOKEN='replace-with-long-random-token'
python ai_trust_enablement/server.py
```

Then call:

```bash
curl -s http://127.0.0.1:8080/v1/evaluate \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $AI_TRUST_API_TOKEN" \
  --data @examples/evaluate_request.json
```

## 3. Docker deployment

```bash
docker build -t ai-trust-enable:latest .
docker run --rm -p 8080:8080 \
  -e AI_TRUST_API_TOKEN='replace-with-long-random-token' \
  ai-trust-enable:latest
```

Or:

```bash
docker compose up --build
```

## 4. Environment variables

| Variable | Default | Meaning |
|---|---:|---|
| `AI_TRUST_HOST` | `0.0.0.0` | HTTP bind host |
| `AI_TRUST_PORT` | `8080` | HTTP bind port |
| `AI_TRUST_API_TOKEN` | empty | Optional bearer token; set this before exposing the service |
| `AI_TRUST_MAX_BODY_BYTES` | `1000000` | Max request size |
| `AI_TRUST_MAX_BATCH_CASES` | `50` | Max cases in `/v1/batch` |
| `AI_TRUST_RATE_LIMIT_PER_MIN` | `120` | Simple per-client request limit |
| `AI_TRUST_MODEL_ID` | `model-under-test` | Default model label in certificates |
| `AI_TRUST_RELEASE_LEDGER_PATH` | empty | Optional release controller evidence ledger path |
| `AI_TRUST_ECL_LEDGER_PATH` | `ai_trust_ecl_finality_ledger.jsonl` | Optional ECL-style finality ledger path |
| `AI_TRUST_DEBUG` | empty | Set `1` only for local debugging |

## 5. API endpoints

### `GET /healthz`

Returns service health.

### `GET /version`

Returns version, engine, schema, and endpoint list.

### `GET /schema`

Returns the JSON schema for AI recognition certificates.

### `POST /v1/evaluate`

Request:

```json
{
  "context": "Supplied reference facts or task context.",
  "prompt": "Prompt sent to the model.",
  "answer": "Model answer to evaluate.",
  "model_id": "model-under-test",
  "event_index": 1,
  "logits": [1.2, 0.4, -0.7]
}
```

Only `context`, `prompt`, and `answer` are required. `logits` are optional and allow confidence-collapse fields to be populated.

Response: an AI recognition certificate with reference signature, current signature, recognition-state metrics, seam memory, technical action, and certificate hash.

### `POST /v1/batch`

Request:

```json
{
  "model_id": "batch-model",
  "cases": [
    {
      "case_id": "case-1",
      "context": "The Eiffel Tower is located in Paris.",
      "prompt": "Answer using only context.",
      "answer": "The Eiffel Tower is located in Berlin."
    }
  ]
}
```

Response: summary counts plus one certificate per case.

### `POST /v1/release`

Evaluates answer safety, repair, retrieval need, and final release action.

### `POST /v1/resolve`

Closes the retrieval loop by checking retrieved evidence against unresolved claims.

### `POST /v1/topological-memory`

Request with raw phase trajectory:

```json
{
  "lambda_p_series": [0.00, 0.15, 0.32, 0.50, 0.74, 1.02, 1.18],
  "skew_intensity_series": [0.0, 0.1, 0.1, 0.2, 0.4, 0.5, 0.5],
  "alpha": 0.25,
  "beta": 0.20,
  "threshold": 0.45,
  "commit_to_ecl": true
}
```

Or with prior AI certificates:

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

Response: an `AI_TOPOLOGICAL_MEMORY_CERTIFICATE`; when `commit_to_ecl` is true, the response also includes an `ecl_finality_commit`.

## 6. Production hardening checklist

Before exposing outside localhost:

- Put the service behind TLS using a reverse proxy or platform load balancer.
- Set `AI_TRUST_API_TOKEN` to a long random secret.
- Set request size and batch limits appropriate to your environment.
- Disable `AI_TRUST_DEBUG`.
- Do not log full prompts or answers unless your privacy policy permits it.
- Persist ECL finality ledgers on durable storage when using `commit_to_ecl`.
- Monitor classification counts, Topological Memory transitions, request latency, error rates, and certificate hashes.
- Keep a dataset of known grounded, unsupported, stable-sector, and transition-sector outputs for regression checks.
- Treat this as a decision-support/gating layer, not as a standalone truth oracle.

## 7. Integration pattern

A practical real-world architecture:

```text
User request
  -> LLM or AI model
  -> AI Trust Enablement Service
  -> recognition / repair / release certificate
  -> optional Topological Memory temporal-memory certificate
  -> optional ECL-style finality commit
  -> application policy gate
  -> commit, flag, defer, retrieve, regenerate, hold, or human review
```

The service does not need to know the model internals. It can work with context, prompt, and answer. If logits are available, the optional confidence-collapse path can also be used. If repeated certificates or phase samples are available, the Topological Memory path can detect temporal recognition-sector transitions.
