#!/usr/bin/env python3
"""
Claim Frame Kernel
==================

Semantic frame closure layer for the AI Trust Enablement system.

Design hints used:
    Vedic/Paninian: normalize text into claim frames and record markers before surface erasure.
    Nyaya: evaluate claims by direct evidence, inference, analogy, and source route.
    IEL: hash every frame and report deterministically for replay/audit.
    ECL: compute closure residue after lawful compensation rather than only raw similarity.
    Atomic-model grammar: treat a claim like a relation/bond between entities with attributes.

The kernel is intentionally no-dependency. It is not a universal semantic parser. It is a practical
field-level verifier for context-grounded AI answers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from .paninian_meta_engine import compact_trace
except ImportError:
    from paninian_meta_engine import compact_trace

TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)?")
NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
ENTITY_RE = re.compile(r"\b[A-Z][A-Za-z0-9_-]{2,}\b")
SENTENCE_RE = re.compile(r"[^.!?]+[.!?]?")

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "in", "into", "is", "it", "its", "of", "on", "or", "that", "the",
    "this", "to", "was", "were", "with", "which", "who", "will", "can", "may",
    "must", "should", "using", "only", "supplied", "context", "answer", "what",
    "where", "when", "why", "how", "does", "do", "did", "also",
}
NEGATORS = {"not", "no", "never", "none", "without", "false", "incorrect", "cannot", "can't", "doesn't", "didn't"}
MODAL_WORDS = {"must", "should", "may", "can", "could", "would", "recommended", "required", "optional"}
SOURCE_WORDS = {"according", "says", "states", "reported", "source", "label", "context", "evidence"}

RELATION_ALIASES: Dict[str, Tuple[str, ...]] = {
    "located_in": ("located", "situated", "based", "found", "in"),
    "completed_in": ("completed", "finished", "built", "constructed"),
    "made_of": ("made", "composed", "formed", "material"),
    "dose_is": ("dose", "dosage", "recommended", "take", "used"),
    "converts_to": ("convert", "converts", "changes", "turns"),
    "causes": ("cause", "causes", "leads", "produces"),
    "prevents": ("prevent", "prevents", "blocks", "inhibits"),
    "has_property": ("has", "have", "contains", "contain", "includes", "include", "stores", "store", "borrow"),
    "equals": ("is", "are", "was", "were", "means", "equals"),
}

STRICT_OBJECT_RELATIONS = {"located_in", "completed_in", "made_of", "dose_is", "converts_to"}

CANONICAL_TERMS = {
    "dc": "direct_current",
    "direct": "direct_current",
    "current": "current",
    "ac": "alternating_current",
    "alternating": "alternating_current",
    "electricity": "electrical_energy",
    "electrical": "electrical_energy",
    "energy": "electrical_energy",
    "mg": "milligram",
    "milligrams": "milligram",
    "daily": "per_day",
    "once": "one_time",
    "twice": "two_times",
}

SUPPORTED_EXACT = "SUPPORTED_EXACT"
SUPPORTED_PARAPHRASE = "SUPPORTED_PARAPHRASE"
SUPPORTED_INFERRED = "SUPPORTED_INFERRED"
CONTRADICTED_ENTITY = "CONTRADICTED_ENTITY"
CONTRADICTED_NUMBER = "CONTRADICTED_NUMBER"
CONTRADICTED_NEGATION = "CONTRADICTED_NEGATION"
UNSUPPORTED_RELATION = "UNSUPPORTED_RELATION"
UNSUPPORTED_SOURCE = "UNSUPPORTED_SOURCE"
UNCERTAIN_ROUTE_CONFLICT = "UNCERTAIN_ROUTE_CONFLICT"
UNSUPPORTED_NO_EVIDENCE = "UNSUPPORTED_NO_EVIDENCE"


@dataclass(frozen=True)
class ClaimFrame:
    frame_id: str
    text: str
    subject: str
    relation: str
    object: str
    quantity: Tuple[str, ...]
    time: Tuple[str, ...]
    location: Tuple[str, ...]
    modality: Tuple[str, ...]
    negation: bool
    source: Tuple[str, ...]
    qualifiers: Tuple[str, ...]
    markers: Tuple[str, ...]
    paninian_trace: Tuple[Dict[str, Any], ...]
    frame_hash: str


@dataclass(frozen=True)
class FieldComparison:
    field: str
    claim_value: Any
    evidence_value: Any
    status: str
    score: float


@dataclass(frozen=True)
class FrameMatch:
    claim_frame_id: str
    evidence_frame_id: Optional[str]
    classification: str
    confidence: float
    residue: float
    route_scores: Dict[str, float]
    field_comparisons: Tuple[FieldComparison, ...]
    reason_tags: Tuple[str, ...]
    match_hash: str


@dataclass(frozen=True)
class FrameClosureReport:
    version: str
    engine: str
    context_hash: str
    prompt_hash: str
    answer_hash: str
    evidence_frame_count: int
    claim_frame_count: int
    closure_counts: Dict[str, int]
    open_residue: float
    claim_frames: Tuple[Dict[str, Any], ...]
    evidence_frames: Tuple[Dict[str, Any], ...]
    matches: Tuple[Dict[str, Any], ...]
    report_hash: str


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def tokenize(text: str) -> List[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text)]


def canonical_token(token: str) -> str:
    return CANONICAL_TERMS.get(token.lower(), token.lower())


def content_tokens(text: str) -> List[str]:
    return [canonical_token(t) for t in tokenize(text) if t not in STOPWORDS]


def sentence_units(text: str) -> List[str]:
    raw = [s.strip() for s in SENTENCE_RE.findall(text) if s.strip()]
    units: List[str] = []
    for s in raw:
        parts = re.split(r"\b(?:;| and )\b", s)
        if len(parts) > 1 and sum(_has_relation_hint(p) for p in parts) >= 2:
            units.extend(p.strip(" .") + "." for p in parts if p.strip())
        else:
            units.append(s)
    return units


def _has_relation_hint(text: str) -> bool:
    ts = set(tokenize(text))
    rel_words = set().union(*[set(v) for v in RELATION_ALIASES.values()])
    return bool(ts & rel_words)


def extract_entities(text: str) -> Tuple[str, ...]:
    excluded = {"The", "This", "That", "These", "Those", "When", "Where", "What", "Because", "Answer"}
    return tuple(sorted(set(x for x in ENTITY_RE.findall(text) if x not in excluded)))


def extract_numbers(text: str) -> Tuple[str, ...]:
    return tuple(sorted(set(NUMBER_RE.findall(text))))


def detect_relation(text: str) -> str:
    ts = set(tokenize(text))
    best = "equals"
    best_hits = 0
    for relation, aliases in RELATION_ALIASES.items():
        hits = len(ts & set(aliases))
        if hits > best_hits:
            best = relation
            best_hits = hits
    return best


def extract_time(text: str) -> Tuple[str, ...]:
    out: List[str] = []
    for n in extract_numbers(text):
        if len(n.split(".")[0]) == 4:
            out.append(n)
    for t in tokenize(text):
        if t in {"daily", "weekly", "monthly", "yearly", "today", "tomorrow", "yesterday"}:
            out.append(canonical_token(t))
    return tuple(sorted(set(out)))


def extract_modality(text: str) -> Tuple[str, ...]:
    return tuple(sorted(set(t for t in tokenize(text) if t in MODAL_WORDS)))


def extract_source(text: str) -> Tuple[str, ...]:
    return tuple(sorted(set(t for t in tokenize(text) if t in SOURCE_WORDS)))


def extract_location(text: str, relation: str, entities: Sequence[str]) -> Tuple[str, ...]:
    if relation == "located_in":
        if len(entities) >= 2:
            return (entities[-1],)
        for m in re.finditer(r"\bin\s+([A-Z][A-Za-z0-9_-]+)", text):
            return (m.group(1),)
    return tuple()


def extract_conversion_object(text: str) -> str:
    """Extract the target object in conversion claims such as 'converts X into Y'."""
    lower = text.lower()
    match = re.search(r"\b(?:into|to)\s+([^.;,]+)", text, flags=re.IGNORECASE)
    if not match:
        return ""
    rhs = match.group(1).strip(" .")
    raw_tokens = set(tokenize(rhs))
    if raw_tokens & {"electrical", "electricity", "electric"}:
        return "electrical_energy"
    if "sound" in raw_tokens:
        return "sound_energy"
    if "heat" in raw_tokens or "thermal" in raw_tokens:
        return "heat_energy"
    if "light" in raw_tokens:
        return "light_energy"
    if "mechanical" in raw_tokens:
        return "mechanical_energy"
    if "chemical" in raw_tokens:
        return "chemical_energy"
    c_tokens = content_tokens(rhs)
    if len(c_tokens) >= 2:
        return "_".join(c_tokens[-2:])
    return c_tokens[-1] if c_tokens else ""


def split_subject_object(text: str, relation: str, entities: Sequence[str], numbers: Sequence[str]) -> Tuple[str, str]:
    c_tokens = content_tokens(text)
    subject = entities[0] if entities else (c_tokens[0] if c_tokens else "")
    obj = ""
    if relation == "located_in" and len(entities) >= 2:
        obj = entities[-1]
    elif relation in {"completed_in", "dose_is"} and numbers:
        obj = numbers[0]
    elif relation == "made_of":
        lower = text.lower()
        if " of " in lower:
            rhs = text.split(" of ", 1)[1]
            rhs_tokens = content_tokens(rhs)
            obj = rhs_tokens[0] if rhs_tokens else ""
        elif c_tokens:
            obj = c_tokens[-1]
    elif relation == "converts_to" and c_tokens:
        obj = extract_conversion_object(text) or c_tokens[-1]
    elif relation == "has_property" and c_tokens:
        obj = c_tokens[-1]
    elif c_tokens:
        obj = c_tokens[-1]
    return subject, obj


def marker_set(text: str, relation: str) -> Tuple[str, ...]:
    marks: List[str] = []
    if extract_entities(text):
        marks.append("ENTITY")
    if extract_numbers(text):
        marks.append("NUMBER")
    if any(t in NEGATORS for t in tokenize(text)):
        marks.append("NEGATION")
    if relation:
        marks.append("RELATION")
    if extract_source(text):
        marks.append("SOURCE")
    if extract_modality(text):
        marks.append("MODALITY")
    if len(content_tokens(text)) > 12:
        marks.append("LONG_CLAIM")
    return tuple(sorted(set(marks)))


def build_frame(text: str, frame_id: str) -> ClaimFrame:
    relation = detect_relation(text)
    entities = extract_entities(text)
    numbers = extract_numbers(text)
    subject, obj = split_subject_object(text, relation, entities, numbers)
    markers = marker_set(text, relation)
    effect_tags = tuple(t for t in [relation] if t)
    trace = tuple(compact_trace(markers, effect_tags, False))
    payload = {
        "frame_id": frame_id,
        "text": text.strip(),
        "subject": subject,
        "relation": relation,
        "object": obj,
        "quantity": numbers,
        "time": extract_time(text),
        "location": extract_location(text, relation, entities),
        "modality": extract_modality(text),
        "negation": any(t in NEGATORS for t in tokenize(text)),
        "source": extract_source(text),
        "qualifiers": tuple(sorted(set(content_tokens(text)) - {canonical_token(subject), canonical_token(obj)})),
        "markers": markers,
        "paninian_trace": trace,
    }
    return ClaimFrame(frame_hash=sha256_json(payload), **payload)


def frames_from_text(text: str, prefix: str) -> List[ClaimFrame]:
    return [build_frame(unit, f"{prefix}{i}") for i, unit in enumerate(sentence_units(text), start=1)]


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa = {canonical_token(str(x)) for x in a if str(x)}
    sb = {canonical_token(str(x)) for x in b if str(x)}
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def token_similarity(a: str, b: str) -> float:
    return jaccard(content_tokens(a), content_tokens(b))


def compare_field(field: str, claim_value: Any, evidence_value: Any) -> FieldComparison:
    if isinstance(claim_value, tuple):
        claim_set = set(claim_value)
        evidence_set = set(evidence_value or ())
        if not claim_set:
            return FieldComparison(field, claim_value, evidence_value, "not_claimed", 1.0)
        if claim_set.issubset(evidence_set):
            return FieldComparison(field, claim_value, evidence_value, "match", 1.0)
        if claim_set & evidence_set:
            return FieldComparison(field, claim_value, evidence_value, "partial", 0.55)
        return FieldComparison(field, claim_value, evidence_value, "mismatch", 0.0)
    if isinstance(claim_value, bool):
        ok = claim_value == evidence_value
        return FieldComparison(field, claim_value, evidence_value, "match" if ok else "mismatch", 1.0 if ok else 0.0)
    c = canonical_token(str(claim_value))
    e = canonical_token(str(evidence_value))
    if not c:
        return FieldComparison(field, claim_value, evidence_value, "not_claimed", 1.0)
    if c == e:
        return FieldComparison(field, claim_value, evidence_value, "match", 1.0)
    sim = token_similarity(str(claim_value), str(evidence_value))
    if sim >= 0.5:
        return FieldComparison(field, claim_value, evidence_value, "paraphrase", sim)
    return FieldComparison(field, claim_value, evidence_value, "mismatch", sim)


class ClaimFrameKernel:
    def __init__(self) -> None:
        pass

    def verify(self, context: str, prompt: str, answer: str) -> FrameClosureReport:
        evidence_frames = frames_from_text(context, "E")
        claim_frames = frames_from_text(answer, "C")
        matches = [self._match_claim(claim, evidence_frames) for claim in claim_frames]
        counts: Dict[str, int] = {}
        residues: List[float] = []
        for match in matches:
            counts[match.classification] = counts.get(match.classification, 0) + 1
            residues.append(match.residue)
        open_residue = sum(residues) / len(residues) if residues else 0.0
        payload = {
            "version": "1.0.1",
            "engine": "ClaimFrameKernel",
            "context_hash": sha256_text(context),
            "prompt_hash": sha256_text(prompt),
            "answer_hash": sha256_text(answer),
            "evidence_frame_count": len(evidence_frames),
            "claim_frame_count": len(claim_frames),
            "closure_counts": counts,
            "open_residue": open_residue,
            "claim_frames": tuple(asdict(f) for f in claim_frames),
            "evidence_frames": tuple(asdict(f) for f in evidence_frames),
            "matches": tuple(asdict(m) for m in matches),
        }
        return FrameClosureReport(report_hash=sha256_json(payload), **payload)

    def _match_claim(self, claim: ClaimFrame, evidence_frames: Sequence[ClaimFrame]) -> FrameMatch:
        if not evidence_frames:
            return self._make_match(claim, None, UNSUPPORTED_NO_EVIDENCE, 1.0, {}, (), ("no_evidence",))
        scored = [(self._route_scores(claim, ev), ev) for ev in evidence_frames]
        scored.sort(key=lambda pair: pair[0]["total"], reverse=True)
        best_scores, best_ev = scored[0]
        comparisons = self._field_comparisons(claim, best_ev)
        classification, reason_tags = self._classify(comparisons, best_scores)
        residue = self._residue(classification, comparisons, best_scores)
        confidence = max(0.0, min(1.0, 1.0 - residue if classification.startswith("SUPPORTED") else max(best_scores.get("contradiction", 0.0), residue)))
        return self._make_match(claim, best_ev, classification, residue, best_scores, comparisons, tuple(reason_tags), confidence)

    def _route_scores(self, claim: ClaimFrame, ev: ClaimFrame) -> Dict[str, float]:
        direct = token_similarity(claim.text, ev.text)
        frame = 0.24 * compare_field("subject", claim.subject, ev.subject).score
        frame += 0.24 * compare_field("relation", claim.relation, ev.relation).score
        frame += 0.20 * compare_field("object", claim.object, ev.object).score
        frame += 0.16 * compare_field("quantity", claim.quantity, ev.quantity).score
        frame += 0.08 * compare_field("time", claim.time, ev.time).score
        frame += 0.08 * compare_field("negation", claim.negation, ev.negation).score
        analogy = jaccard(claim.qualifiers, ev.qualifiers)
        contradiction, entity_contradiction = self._contradiction_scores(claim, ev, direct)
        total = max(0.0, min(1.0, 0.35 * direct + 0.45 * frame + 0.20 * analogy - 0.35 * contradiction))
        return {
            "direct": direct,
            "frame": frame,
            "analogy": analogy,
            "contradiction": contradiction,
            "entity_contradiction": entity_contradiction,
            "total": total,
        }

    def _field_comparisons(self, claim: ClaimFrame, ev: ClaimFrame) -> Tuple[FieldComparison, ...]:
        fields = ["subject", "relation", "object", "quantity", "time", "location", "modality", "negation", "source"]
        return tuple(compare_field(field, getattr(claim, field), getattr(ev, field)) for field in fields)

    def _contradiction_scores(self, claim: ClaimFrame, ev: ClaimFrame, direct: float) -> Tuple[float, float]:
        score = 0.0
        entity_score = 0.0
        relation_matches = claim.relation == ev.relation
        subject_matches = bool(claim.subject and ev.subject and canonical_token(claim.subject) == canonical_token(ev.subject))
        object_mismatch = bool(claim.object and ev.object and canonical_token(claim.object) != canonical_token(ev.object))
        subject_mismatch = bool(claim.subject and ev.subject and canonical_token(claim.subject) != canonical_token(ev.subject))
        if claim.quantity and not set(claim.quantity).issubset(set(ev.quantity)):
            score = max(score, 1.0)
        if claim.negation != ev.negation:
            score = max(score, 0.95)
        if relation_matches and subject_mismatch and direct >= 0.42:
            entity_score = max(entity_score, 0.70)
        if relation_matches and object_mismatch:
            if claim.relation in STRICT_OBJECT_RELATIONS:
                entity_score = max(entity_score, 0.95)
            elif subject_matches and direct >= 0.55:
                entity_score = max(entity_score, 0.65)
        score = max(score, entity_score)
        return score, entity_score

    def _classify(self, comparisons: Sequence[FieldComparison], scores: Dict[str, float]) -> Tuple[str, List[str]]:
        by_field = {c.field: c for c in comparisons}
        if by_field["quantity"].status == "mismatch" and by_field["quantity"].claim_value:
            return CONTRADICTED_NUMBER, ["quantity_mismatch"]
        if by_field["negation"].status == "mismatch":
            return CONTRADICTED_NEGATION, ["negation_mismatch"]
        if scores.get("entity_contradiction", 0.0) >= 0.70:
            return CONTRADICTED_ENTITY, ["strict_entity_or_object_mismatch"]
        if scores["total"] >= 0.82 and scores["contradiction"] == 0.0:
            return SUPPORTED_EXACT, ["field_closure"]
        if scores["total"] >= 0.62 and scores["contradiction"] < 0.3:
            return SUPPORTED_PARAPHRASE, ["bounded_paraphrase"]
        if by_field["relation"].status == "match" and scores["analogy"] >= 0.35 and scores["contradiction"] < 0.3:
            return SUPPORTED_INFERRED, ["relation_plus_analogy"]
        if by_field["relation"].status == "mismatch":
            return UNSUPPORTED_RELATION, ["relation_not_grounded"]
        if by_field["source"].status == "mismatch" and by_field["source"].claim_value:
            return UNSUPPORTED_SOURCE, ["source_not_grounded"]
        return UNCERTAIN_ROUTE_CONFLICT, ["insufficient_route_closure"]

    def _residue(self, classification: str, comparisons: Sequence[FieldComparison], scores: Dict[str, float]) -> float:
        if classification.startswith("SUPPORTED"):
            return max(0.0, 1.0 - scores["total"])
        if classification.startswith("CONTRADICTED"):
            return max(0.75, scores["contradiction"])
        return max(0.45, 1.0 - scores["total"])

    def _make_match(
        self,
        claim: ClaimFrame,
        ev: Optional[ClaimFrame],
        classification: str,
        residue: float,
        scores: Dict[str, float],
        comparisons: Sequence[FieldComparison],
        reason_tags: Sequence[str],
        confidence: Optional[float] = None,
    ) -> FrameMatch:
        payload = {
            "claim_frame_id": claim.frame_id,
            "evidence_frame_id": ev.frame_id if ev else None,
            "classification": classification,
            "confidence": confidence if confidence is not None else max(0.0, 1.0 - residue),
            "residue": residue,
            "route_scores": scores,
            "field_comparisons": tuple(asdict(c) for c in comparisons),
            "reason_tags": tuple(reason_tags),
        }
        return FrameMatch(match_hash=sha256_json(payload), **payload)


def demo() -> Dict[str, Any]:
    context = "The Eiffel Tower is located in Paris. It was completed in 1889. The tower is made of iron."
    prompt = "Answer using only the supplied context."
    answer = "The Eiffel Tower is located in Berlin. It was completed in 1789. The tower is made of wood."
    return asdict(ClaimFrameKernel().verify(context, prompt, answer))


def main() -> None:
    parser = argparse.ArgumentParser(description="Claim frame semantic closure verifier")
    parser.add_argument("--context")
    parser.add_argument("--prompt", default="Answer using only the supplied context.")
    parser.add_argument("--answer")
    parser.add_argument("--out", default="claim_frame_report.json")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    if args.demo:
        result = demo()
    else:
        if not args.context or not args.answer:
            parser.error("--context and --answer are required unless --demo is used")
        result = asdict(ClaimFrameKernel().verify(args.context, args.prompt, args.answer))
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
    print(json.dumps({"ok": True, "out": args.out, "hash": sha256_json(result)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
