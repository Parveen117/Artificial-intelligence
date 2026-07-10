# AI Trust Enablement Walkthrough

This folder provides a deterministic implementation for evaluating generated answers against supplied context, classifying recognition residue, and producing machine-readable certificates and release-control actions.

## Files

- `ai_hallucination_recognition_engine.py` - complete deterministic implementation.
- `certificate_schema_v1.json` - machine-readable JSON schema for the recognition certificate.
- `sample_cases.jsonl` - deterministic grounded, hallucinated, dosage-error, and bounded-paraphrase cases.
- `batch_evaluator.py` - evaluates JSONL cases and writes certificate JSONL plus a summary.
- `run_enablement_tests.py` - no-dependency assertion tests for the implementation.

## Engineering definitions

| Term | Meaning in this implementation |
|---|---|
| domain state | the reference context, prompt, and model answer being evaluated |
| stored reference signature | deterministic signature built from supplied context and prompt |
| current state signature | deterministic signature built from the model answer |
| recognition operator | comparison between reference signature and current answer signature |
| phase value, `phi` | token-order and content-distribution residue |
| scale value, `sigma` | relative support, length, and coverage residue |
| seam-memory value, `k` | count of unsupported entities, numbers, and unsupported answer spans |
| lawful transport | allowed paraphrase or elaboration accounted for by limited seam compensation |
| testing footprint | uncertainty allowance caused by short reference context and tokenizer limits |
| open residue | raw residue after seam compensation and testing-footprint subtraction |
| certificate | JSON record containing signatures, residue fields, classification, action, and hash |

## Step-by-step example

Input context:

```text
The Eiffel Tower is located in Paris. It was completed in 1889. The tower is made of iron.
```

Prompt:

```text
Answer using only the supplied context: where is the Eiffel Tower, when was it completed, and what material is it made of?
```

Grounded answer:

```text
The Eiffel Tower is located in Paris. It was completed in 1889 and is made of iron.
```

Hallucinated answer:

```text
The Eiffel Tower is located in Berlin. It was completed in 1789 and is made of wood.
```

The engine performs these steps:

1. Build a stored reference signature from context plus prompt.
2. Build a current state signature from the answer.
3. Compare the current state signature with the reference signature.
4. Compute `phase_value`, `scale_value`, and `seam_memory_value`.
5. Detect unsupported entities, unsupported numbers, and unsupported answer spans.
6. Compute raw residue.
7. Subtract limited seam compensation and testing footprint.
8. Compute open residue.
9. Classify the result as `RECOGNITION`, `BOUNDED_RESIDUE`, or `ACTIONABLE_RESIDUE`.
10. Generate a machine-readable certificate with a deterministic certificate hash and recommended action.

## Run

```bash
python ai_trust_enablement/ai_hallucination_recognition_engine.py --demo --out demo_certificate.json
```

Run a custom example:

```bash
python ai_trust_enablement/ai_hallucination_recognition_engine.py \
  --context "The drug label says the dose is 5 mg once daily." \
  --prompt "Answer using only the supplied context." \
  --answer "The dose is 50 mg twice daily." \
  --model-id demo-model \
  --out certificate.json
```

Run the deterministic sample suite:

```bash
python ai_trust_enablement/batch_evaluator.py \
  --input ai_trust_enablement/sample_cases.jsonl \
  --output ai_trust_enablement/batch_certificates.jsonl \
  --summary ai_trust_enablement/batch_summary.json
```

Run the no-dependency tests:

```bash
python ai_trust_enablement/run_enablement_tests.py
```

## Runtime output

Each evaluation produces a structured certificate containing the reference and current signatures, residue measurements, detected unsupported content, classification, recommended action, and deterministic hash. Applications can use the resulting action to commit, flag, defer, retrieve additional context, repair, or regenerate an answer.

This implementation is an evaluation and control layer, not a standalone truth oracle. Its thresholds and behavior should be validated for the intended domain before production use.