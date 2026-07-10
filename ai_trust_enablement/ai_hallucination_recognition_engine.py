#!/usr/bin/env python3
"""
AI Hallucination Recognition Engine
===================================

A complete, deterministic enablement implementation for an AI hallucination and
confidence-collapse detection embodiment.

The engine compares a current answer signature to a stored reference signature.
The signature has concrete engineering fields:
    phi   = phase/order residue between reference context and answer
    sigma = scale/support residue between reference context and answer
    k     = seam-memory value from unsupported numbers/entities/claim residues

It then computes a testing-footprint-corrected open residue and emits a
machine-readable certificate.

No external knowledge base is required. The stored reference is the input context,
prompt, policy, or task facts supplied to the system.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import time
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)?")
NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
ENTITY_RE = re.compile(r"\b[A-Z][A-Za-z0-9_-]{2,}\b")
SENTENCE_RE = re.compile(r"[^.!?]+[.!?]?")

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to",
    "was", "were", "with", "which", "who", "will", "can", "may", "must", "should",
}

NEGATORS = {"not", "no", "never", "none", "without", "false", "incorrect"}


@dataclass(frozen=True)
class DetectorConfig:
    tokenizer_version: str = "simple-tokenizer-v1"
    recognition_threshold: float = 0.15
    bounded_threshold: float = 0.35
    unsupported_entity_weight: float = 0.25
    unsupported_number_weight: float = 0.30
    phase_weight: float = 0.25
    scale_weight: float = 0.10
    negation_weight: float = 0.10
    max_testing_footprint: float = 0.12
    seam_compensation_limit: float = 0.10
    lambda_v_collapse_threshold: float = 0.05


@dataclass(frozen=True)
class StateSignature:
    signature_hash: str
    token_count: int
    content_token_count: int
    unique_content_token_count: int
    numbers: Tuple[str, ...]
    entities: Tuple[str, ...]
    negator_count: int
    phase_hash: str


@dataclass(frozen=True)
class RecognitionMetrics:
    phase_value: float
    scale_value: float
    seam_memory_value: int
    unsupported_entity_count: int
    unsupported_number_count: int
    unsupported_sentence_count: int
    negation_shift: float
    raw_residue: float
    seam_compensation: float
    testing_footprint: float
    open_residue: float
    classification: str
    technical_action: str


@dataclass(frozen=True)
class EntropyCapacityMetrics:
    entropy: float
    effective_temperature: float
    capacity_v: float
    lambda_v: float
    confidence_collapse: bool


@dataclass(frozen=True)
class RecognitionCertificate:
    version: str
    certificate_type: str
    device: Dict[str, str]
    event: Dict[str, object]
    reference_signature: Dict[str, object]
    current_signature: Dict[str, object]
    recognition_state: Dict[str, object]
    seam_memory: Dict[str, object]
    technical_action: Dict[str, object]
    certificate_hash: str


def canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(obj: object) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def tokenize(text: str) -> List[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text)]


def content_tokens(text: str) -> List[str]:
    return [tok for tok in tokenize(text) if tok not in STOPWORDS]


def extract_numbers(text: str) -> Tuple[str, ...]:
    return tuple(sorted(set(NUMBER_RE.findall(text))))


def extract_entities(text: str) -> Tuple[str, ...]:
    raw = ENTITY_RE.findall(text)
    # Exclude common sentence starters that are often not named entities.
    excluded = {"The", "This", "That", "These", "Those", "When", "Where", "What", "Because"}
    return tuple(sorted(set(x for x in raw if x not in excluded)))


def sentence_list(text: str) -> List[str]:
    return [s.strip() for s in SENTENCE_RE.findall(text) if s.strip()]


def build_signature(text: str) -> StateSignature:
    tokens = tokenize(text)
    c_tokens = content_tokens(text)
    numbers = extract_numbers(text)
    entities = extract_entities(text)
    phase_material = "|".join(c_tokens[:64])
    signature_material = {
        "tokens": c_tokens,
        "numbers": numbers,
        "entities": entities,
        "negators": sum(1 for t in tokens if t in NEGATORS),
    }
    return StateSignature(
        signature_hash=sha256_json(signature_material),
        token_count=len(tokens),
        content_token_count=len(c_tokens),
        unique_content_token_count=len(set(c_tokens)),
        numbers=numbers,
        entities=entities,
        negator_count=sum(1 for t in tokens if t in NEGATORS),
        phase_hash=hashlib.sha256(phase_material.encode("utf-8")).hexdigest(),
    )


def cosine_counter_distance(a_tokens: Sequence[str], b_tokens: Sequence[str]) -> float:
    a = Counter(a_tokens)
    b = Counter(b_tokens)
    if not a and not b:
        return 0.0
    keys = set(a) | set(b)
    dot = sum(a[k] * b[k] for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0.0 or nb == 0.0:
        return 1.0
    return max(0.0, min(1.0, 1.0 - dot / (na * nb)))


def order_phase_distance(reference_tokens: Sequence[str], answer_tokens: Sequence[str]) -> float:
    """Approximate phase/order residue using longest common subsequence length."""
    if not reference_tokens or not answer_tokens:
        return 1.0 if reference_tokens or answer_tokens else 0.0
    # Bounded LCS to keep runtime stable for enablement examples.
    a = list(reference_tokens[:200])
    b = list(answer_tokens[:200])
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b, start=1):
            cur.append(prev[j - 1] + 1 if x == y else max(prev[j], cur[-1]))
        prev = cur
    lcs = prev[-1]
    return 1.0 - lcs / max(1, min(len(a), len(b)))


def unsupported_sentences(reference_text: str, answer_text: str) -> Tuple[int, List[str]]:
    ref_tokens = set(content_tokens(reference_text))
    ref_numbers = set(extract_numbers(reference_text))
    ref_entities = set(extract_entities(reference_text))
    unsupported: List[str] = []
    for sentence in sentence_list(answer_text):
        sent_tokens = set(content_tokens(sentence))
        sent_numbers = set(extract_numbers(sentence))
        sent_entities = set(extract_entities(sentence))
        novel_numbers = sent_numbers - ref_numbers
        novel_entities = sent_entities - ref_entities
        novel_content = [t for t in sent_tokens if t not in ref_tokens]
        if novel_numbers or novel_entities or len(novel_content) >= 5:
            unsupported.append(sentence)
    return len(unsupported), unsupported


def entropy_capacity_from_logits(logits: Sequence[float], temperature: float = 1.0, capacity_floor: float = 1e-6) -> EntropyCapacityMetrics:
    if not logits:
        return EntropyCapacityMetrics(0.0, temperature, capacity_floor, 0.0, True)
    t = max(float(temperature), 1e-6)
    scaled = [x / t for x in logits]
    m = max(scaled)
    exps = [math.exp(x - m) for x in scaled]
    total = sum(exps)
    probs = [x / total for x in exps]
    entropy = -sum(p * math.log(max(p, 1e-12)) for p in probs)
    vocab_size = len(logits)
    capacity_v = max(capacity_floor, math.log(vocab_size + 1.0) / (entropy + 1e-9))
    lambda_v = -entropy * t / capacity_v
    return EntropyCapacityMetrics(
        entropy=entropy,
        effective_temperature=t,
        capacity_v=capacity_v,
        lambda_v=lambda_v,
        confidence_collapse=abs(lambda_v) < 0.05,
    )


class AIHallucinationRecognitionEngine:
    """Concrete state-signature comparison engine for AI answer verification."""

    def __init__(self, config: Optional[DetectorConfig] = None) -> None:
        self.config = config or DetectorConfig()

    def evaluate(
        self,
        reference_text: str,
        prompt_text: str,
        answer_text: str,
        model_id: str = "model-under-test",
        logits: Optional[Sequence[float]] = None,
        event_index: int = 1,
    ) -> RecognitionCertificate:
        reference_material = reference_text + "\n" + prompt_text
        ref_sig = build_signature(reference_material)
        cur_sig = build_signature(answer_text)

        ref_tokens = content_tokens(reference_material)
        ans_tokens = content_tokens(answer_text)
        bag_distance = cosine_counter_distance(ref_tokens, ans_tokens)
        order_distance = order_phase_distance(ref_tokens, ans_tokens)
        phase_value = (bag_distance + order_distance) / 2.0

        scale_value = abs(cur_sig.content_token_count - ref_sig.content_token_count) / max(1, ref_sig.content_token_count)

        ref_entities = set(ref_sig.entities)
        cur_entities = set(cur_sig.entities)
        ref_numbers = set(ref_sig.numbers)
        cur_numbers = set(cur_sig.numbers)
        unsupported_entity_count = len(cur_entities - ref_entities)
        unsupported_number_count = len(cur_numbers - ref_numbers)
        unsupported_sentence_count, unsupported_spans = unsupported_sentences(reference_material, answer_text)
        seam_memory_value = unsupported_entity_count + unsupported_number_count + unsupported_sentence_count

        negation_shift = abs(cur_sig.negator_count - ref_sig.negator_count) / max(1, ref_sig.negator_count + 1)

        unsupported_entity_ratio = unsupported_entity_count / max(1, len(cur_entities))
        unsupported_number_ratio = unsupported_number_count / max(1, len(cur_numbers))

        cfg = self.config
        raw_residue = (
            cfg.phase_weight * phase_value
            + cfg.scale_weight * min(1.0, scale_value)
            + cfg.unsupported_entity_weight * unsupported_entity_ratio
            + cfg.unsupported_number_weight * unsupported_number_ratio
            + cfg.negation_weight * min(1.0, negation_shift)
        )

        # Lawful seam compensation: give limited credit for paraphrase overlap and expected prompt-driven elaboration.
        overlap = 1.0 - bag_distance
        seam_compensation = min(cfg.seam_compensation_limit, max(0.0, 0.05 * overlap))

        # Testing footprint: short or thin references make verification less stable.
        testing_footprint = min(cfg.max_testing_footprint, 1.0 / max(20.0, float(ref_sig.content_token_count)))

        open_residue = max(0.0, raw_residue - seam_compensation - testing_footprint)
        classification, action = self._classify(open_residue, seam_memory_value)

        entropy_metrics = entropy_capacity_from_logits(logits or []) if logits is not None else None
        if entropy_metrics and entropy_metrics.confidence_collapse:
            classification = "ACTIONABLE_RESIDUE"
            action = "DEFER_AND_REGENERATE_WITH_RETRIEVAL"

        metrics = RecognitionMetrics(
            phase_value=phase_value,
            scale_value=scale_value,
            seam_memory_value=seam_memory_value,
            unsupported_entity_count=unsupported_entity_count,
            unsupported_number_count=unsupported_number_count,
            unsupported_sentence_count=unsupported_sentence_count,
            negation_shift=negation_shift,
            raw_residue=raw_residue,
            seam_compensation=seam_compensation,
            testing_footprint=testing_footprint,
            open_residue=open_residue,
            classification=classification,
            technical_action=action,
        )

        payload = {
            "version": "1.0",
            "certificate_type": "AI_RECOGNITION_CERTIFICATE",
            "device": {
                "engine": "AIHallucinationRecognitionEngine",
                "model_id": model_id,
                "tokenizer_version": cfg.tokenizer_version,
            },
            "event": {
                "event_index": event_index,
                "timestamp_unix": int(time.time()),
                "prompt_hash": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
            },
            "reference_signature": asdict(ref_sig),
            "current_signature": asdict(cur_sig),
            "recognition_state": {
                **asdict(metrics),
                "unsupported_spans": unsupported_spans,
                "entropy_capacity": asdict(entropy_metrics) if entropy_metrics else None,
            },
            "seam_memory": {
                "k": seam_memory_value,
                "unsupported_entities": sorted(cur_entities - ref_entities),
                "unsupported_numbers": sorted(cur_numbers - ref_numbers),
            },
            "technical_action": {
                "action": action,
                "classification": classification,
            },
        }
        cert_hash = sha256_json(payload)
        return RecognitionCertificate(certificate_hash=cert_hash, **payload)

    def _classify(self, open_residue: float, seam_memory_value: int) -> Tuple[str, str]:
        cfg = self.config
        if open_residue <= cfg.recognition_threshold and seam_memory_value == 0:
            return "RECOGNITION", "COMMIT_OUTPUT"
        if open_residue <= cfg.bounded_threshold:
            return "BOUNDED_RESIDUE", "FLAG_FOR_REVIEW"
        return "ACTIONABLE_RESIDUE", "DEFER_AND_REGENERATE_WITH_RETRIEVAL"


def demo() -> Dict[str, object]:
    context = (
        "The Eiffel Tower is located in Paris. "
        "It was completed in 1889. "
        "The tower is made of iron."
    )
    prompt = "Answer using only the supplied context: where is the Eiffel Tower, when was it completed, and what material is it made of?"
    grounded_answer = "The Eiffel Tower is located in Paris. It was completed in 1889 and is made of iron."
    hallucinated_answer = "The Eiffel Tower is located in Berlin. It was completed in 1789 and is made of wood."

    engine = AIHallucinationRecognitionEngine()
    grounded = engine.evaluate(context, prompt, grounded_answer, model_id="demo-llm", event_index=1)
    hallucinated = engine.evaluate(context, prompt, hallucinated_answer, model_id="demo-llm", event_index=2)
    return {
        "grounded_certificate": asdict(grounded),
        "hallucinated_certificate": asdict(hallucinated),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="AI hallucination recognition engine")
    parser.add_argument("--context", help="reference context/facts")
    parser.add_argument("--prompt", help="prompt or task instruction")
    parser.add_argument("--answer", help="model answer to evaluate")
    parser.add_argument("--model-id", default="model-under-test")
    parser.add_argument("--out", default="ai_recognition_certificate.json")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    if args.demo:
        result = demo()
    else:
        if not (args.context and args.prompt and args.answer):
            parser.error("--context, --prompt, and --answer are required unless --demo is used")
        engine = AIHallucinationRecognitionEngine()
        result = asdict(engine.evaluate(args.context, args.prompt, args.answer, model_id=args.model_id))

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=True)
    print(json.dumps({"output": args.out, "sha256": sha256_json(result)}, indent=2))


if __name__ == "__main__":
    main()
