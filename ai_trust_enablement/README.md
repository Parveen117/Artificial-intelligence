# AI Trust Enablement Walkthrough

This folder provides a concrete enablement implementation for AI hallucination and confidence-collapse detection. It is intended to answer the practical question a patent examiner or engineer will ask, because apparently “recognition geometry” alone does not solder itself into a working system.

## Files

- `ai_hallucination_recognition_engine.py` - complete deterministic implementation.
- `certificate_schema_v1.json` - machine-readable JSON schema for the recognition certificate.
- `sample_cases.jsonl` - deterministic grounded, hallucinated, dosage-error, and bounded-paraphrase cases.
- `batch_evaluator.py` - evaluates JSONL cases and writes certificate JSONL plus a summary.
- `run_enablement_tests.py` - no-dependency assertion tests for the implementation.

## Concrete engineering definitions

| Draft term | Engineering meaning in this implementation |
|---|---|
| domain state | the reference context, prompt, and model answer being evaluated |
| stored reference signature | deterministic signature built from supplied context and prompt |
| current state signature | deterministic signature built from the model answer |
| recognition operator | comparison between reference signature and current answer signature |
| phase value, `phi` | token-order and content-distribution residue |
| scale value, `sigma` | relative support/length/coverage residue |
| seam-memory value, `k` | count of unsupported entities, numbers, and unsupported answer spans |
| lawful transport | allowed paraphrase/elaboration accounted for by limited seam compensation |
| testing footprint | uncertainty allowance caused by short/thin reference context and tokenizer limits |
| open residue | raw residue after seam compensation and testing footprint subtraction |
| certificate | JSON record containing signatures, residue fields, classification, action, and hash |

## Step-by-step AI hallucination example

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
9. Classify as `RECOGNITION`, `BOUNDED_RESIDUE`, or `ACTIONABLE_RESIDUE`.
10. Generate a machine-readable certificate with a certificate hash.

## Run

```bash
python ai_trust_enablement/ai_hallucination_recognition_engine.py --demo --out demo_certificate.json
```

Or run a custom example:

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

## Why this improves enablement and definiteness

This is not merely a broad claim saying “apply a recognition operator.” The recognition operator is concretely implemented as a state-signature comparison. The signature includes phase/order residue, scale/support residue, and seam-memory residue. The output is a certificate containing concrete fields and a deterministic hash.

A narrower claim can now say:

> applying a recognition operator that compares a current state signature to a stored reference signature, wherein the current state signature comprises at least one of a phase value, a scale value, and a seam-memory value.

That is far more definite than the earlier abstract wording. Tiny miracle, really.

## Subject-matter eligibility hook

The implementation is tied to a practical computer task: detecting unreliable generated output from a model answer, producing a machine-readable certificate, and triggering a technical action such as commit, flag, defer, or regenerate. The output is not a mental judgment; it is a structured runtime record and control signal.

## Prosecution-useful anchors

This folder now supports three things the provisional needs badly:

1. A working implementation, not just equations.
2. A step-by-step AI hallucination walkthrough from input to certificate.
3. A concrete glossary that maps invented terms into engineering fields.

The strongest bridge into claim language is the state signature: `phase_value`, `scale_value`, and `seam_memory_value`. The strongest bridge into eligibility is the generated certificate plus technical action.
