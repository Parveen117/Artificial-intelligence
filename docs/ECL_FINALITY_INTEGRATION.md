# ECL Finality Integration

This document describes the first integrated bridge between the AI Trust Enablement stack and the ECL/IEL finality idea.

The goal is simple:

```text
AI answer
  -> recognition / repair / release certificate
  -> certificate hash
  -> ECL-style external transition proposal
  -> append-only finality commit
  -> chained proof record
```

## Why this matters

The AI Trust Enablement service already evaluates model output and emits machine-readable certificates. The ECL/IEL architecture supplies the irreversible proof body. This bridge connects those two halves without forcing the AI service to import a separate private repository at runtime.

In practical terms, an AI answer is no longer only evaluated. Its evaluation can be sealed as a finality commit.

## Added module

`ai_trust_enablement/ecl_commit_adapter.py`

The adapter accepts any certificate-like dictionary, including:

- recognition certificates from `AIHallucinationRecognitionEngine`
- repair certificates from `ClaimRepairEngine`
- release certificates from `ReleaseController`
- retrieval-resolution certificates from `RetrievalResolutionEngine`

It extracts or computes:

- `certificate_hash`
- `payload_hash`
- `classification`
- `action`
- `prev_state_hash`
- `proposed_state_hash`
- `proposal_hash`
- `effect_units`
- `entropy_delta`
- `commit_hash`

The ledger is append-only JSONL. By default it writes to:

```text
ai_trust_ecl_finality_ledger.jsonl
```

Override the path with:

```bash
export AI_TRUST_ECL_LEDGER_PATH=/secure/path/ai_trust_ecl_finality_ledger.jsonl
```

## Python usage

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

adapter = ECLCommitAdapter("./ai_trust_ecl_finality_ledger.jsonl")
commit = adapter.commit_certificate(certificate, source_type="AI_RECOGNITION_CERTIFICATE")
print(commit.to_dict())
print(adapter.verify())
```

## Verification

Run:

```bash
python ai_trust_enablement/run_enablement_tests.py
```

The test suite now includes `test_ecl_finality_commit_adapter`, which confirms:

- certificate hash is carried forward
- proposal hash is generated
- commit hash is generated
- entropy delta is strictly positive
- second commit points to the first commit hash
- ledger verification passes

## Relation to ECL/IEL

This bridge is intentionally conservative. It does not claim to replace the separate ECL repo. It implements a local ECL-style finality record inside the AI repo so the AI stack can demonstrate the full proof path immediately.

A later hard integration can replace the local JSONL append operation with the external ECL repo's `submit_external_transition(...)` function. The interface is already shaped for that migration: certificate hash, previous state hash, proposed state hash, effect units, proposal hash, and finality verdict.

## Patent / enablement value

This gives a concrete device-level chain:

```text
model output
  -> recognition operator
  -> recognition certificate
  -> release / repair controller
  -> finality adapter
  -> append-only ECL-style proof ledger
```

That matters because it converts abstract AI trust language into a repeatable machine process with hashes, transitions, audit records, and verification.
