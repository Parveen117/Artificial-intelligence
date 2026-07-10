#!/usr/bin/env python3
"""
Panini--Nyaya Claim Verification Kernel
=======================================

A no-dependency claim-level verifier for hallucination detection.

Design sources translated into engineering terms:
    Paninian layer  : normalize each generated sentence into a derivation state.
    Nyaya layer     : score each claim through evidence channels (pramanas).
    Pingala layer   : encode the claim support pattern as a binary prastara vector.
    Morphic layer   : compare alternative verification routes and flag route conflict.

This does not pretend to solve open-domain truth. It solves the narrower and useful
problem: given context/prompt/evidence, determine which generated claims are
supported, contradicted, unsupported, or uncertain, and produce a certificate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)?")
NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
ENTITY_RE = re.compile(r"\b[A-Z][A-Za-z0-9_-]{2,}\b")
SENTENCE_RE = re.compile(r"[^.!?]+[.!?]?")

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "in", "into", "is", "it", "its", "of", "on", "or", "that", "the",
    "this", "to", "was", "were", "with", "which", "who", "will", "can", "may",
    "must", "should", "using", "only", "supplied", "context", "answer",
}

NEGATORS = {"not", "no", "never", "none", "without", "false", "incorrect", "cannot"}

RELATION_ALIASES = {
    "located": {"located", "situated", "based", "found"},
    "completed": {"completed", "finished", "built", "constructed"},
    "made": {"made", "composed", "material", "formed"},
    "dose": {"dose", "dosage", "recommended", "take", "used"},
    "converts": {"convert", "converts", "changes", "turns"},
    "causes": {"cause", "causes", "leads", "produces"},
    "prevents": {"prevent", "prevents", "blocks", "inhibits"},
}

PARAPHRASE_MAP = {
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

CLASS_SUPPORTED = "SUPPORTED"
CLASS_CONTRADICTED = "CONTRADICTED"
CLASS_UNSUPPORTED = "UNSUPPORTED"
CLASS_UNCERTAIN = "UNCERTAIN"


@dataclass(frozen=True)
class VerifierConfig:
    direct_support_threshold: float = 0.56
    paraphrase_support_threshold: float = 0.62
    uncertainty_threshold: float = 0.38
    contradiction_similarity_threshold: float = 0.28
    route_conflict_penalty: float = 0.15
    tokenizer_version: str = "panini-nyaya-simple-v1"


@dataclass(frozen=True)
class DerivationState:
    text: str
    normalized: str
    tokens: Tuple[str, ...]
    content_tokens: Tuple[str, ...]
    numbers: Tuple[str, ...]
    entities: Tuple[str, ...]
    relation_tags: Tuple[str, ...]
    marker_set: Tuple[str, ...]
    effect_tags: Tuple[str, ...]
    precedence_key: str
    state_hash: str


@dataclass(frozen=True)
class PramanaResult:
    claim_id: str
    claim_text: str
    best_evidence_id: Optional[str]
    best_evidence_text: Optional[str]
    pratyaksha_direct: float
    anumana_inference: float
    upamana_analogy: float
    shabda_context_authority: float
    normal_form_gap: float
    route_classifications: Dict[str, str]
    route_conflict: bool
    hetvabhasa_tags: Tuple[str, ...]
    classification: str
    confidence: float
    residue: float


@dataclass(frozen=True)
class ClaimVerificationReport:
    version: str
    engine: str
    context_hash: str
    prompt_hash: str
    answer_hash: str
    evidence_count: int
    claim_count: int
    prastara_vector: str
    meru_root: str
    classification_counts: Dict[str, int]
    claim_results: List[Dict[str, Any]]
    report_hash: str


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


def tokens(text: str) -> List[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text)]


def content_tokens(text: str) -> List[str]:
    return [t for t in tokens(text) if t not in STOPWORDS]


def canonical_token(token: str) -> str:
    t = token.lower()
    return PARAPHRASE_MAP.get(t, t)


def canonical_tokens(text: str) -> List[str]:
    return [canonical_token(t) for t in content_tokens(text)]


def extract_numbers(text: str) -> Tuple[str, ...]:
    return tuple(sorted(set(NUMBER_RE.findall(text))))


def extract_entities(text: str) -> Tuple[str, ...]:
    excluded = {"The", "This", "That", "These", "Those", "When", "Where", "What", "Because", "Answer"}
    return tuple(sorted(set(x for x in ENTITY_RE.findall(text) if x not in excluded)))


def sentence_units(text: str) -> List[str]:
    raw = [s.strip() for s in SENTENCE_RE.findall(text) if s.strip()]
    out: List[str] = []
    for s in raw:
        # Split only when a second mini-claim is strongly signaled. This keeps harmless prose intact.
        parts = re.split(r"\b(?:;| and )\b", s)
        if len(parts) > 1 and sum(_has_relation_hint(p) for p in parts) >= 2:
            out.extend(p.strip(" .") + "." for p in parts if p.strip())
        else:
            out.append(s)
    return out


def _has_relation_hint(text: str) -> bool:
    ts = set(tokens(text))
    relation_words = set().union(*RELATION_ALIASES.values()) | {"is", "are", "was", "were", "has", "have"}
    return bool(ts & relation_words)


def relation_tags(text: str) -> Tuple[str, ...]:
    ts = set(tokens(text))
    tags = []
    for tag, aliases in RELATION_ALIASES.items():
        if ts & aliases:
            tags.append(tag)
    if not tags and ts & {"is", "are", "was", "were"}:
        tags.append("identity")
    return tuple(sorted(tags))


def marker_set(text: str) -> Tuple[str, ...]:
    marks = []
    ts = tokens(text)
    if extract_numbers(text):
        marks.append("NUMBER")
    if extract_entities(text):
        marks.append("ENTITY")
    if any(t in NEGATORS for t in ts):
        marks.append("NEGATION")
    if relation_tags(text):
        marks.append("RELATION")
    if len(content_tokens(text)) > 12:
        marks.append("LONG_CLAIM")
    return tuple(sorted(marks))


def effect_tags(text: str) -> Tuple[str, ...]:
    tags = list(relation_tags(text))
    ts = set(tokens(text))
    if ts & {"must", "should", "recommended"}:
        tags.append("normative")
    if ts & {"always", "never", "all", "none"}:
        tags.append("universal")
    return tuple(sorted(set(tags)))


def build_derivation_state(text: str) -> DerivationState:
    c_tokens = tuple(canonical_tokens(text))
    normalized = " ".join(c_tokens)
    state_material = {
        "normalized": normalized,
        "numbers": extract_numbers(text),
        "entities": extract_entities(text),
        "relation_tags": relation_tags(text),
        "markers": marker_set(text),
        "effects": effect_tags(text),
    }
    return DerivationState(
        text=text.strip(),
        normalized=normalized,
        tokens=tuple(tokens(text)),
        content_tokens=tuple(content_tokens(text)),
        numbers=extract_numbers(text),
        entities=extract_entities(text),
        relation_tags=relation_tags(text),
        marker_set=marker_set(text),
        effect_tags=effect_tags(text),
        precedence_key="|".join(relation_tags(text)) or "surface",
        state_hash=sha256_json(state_material),
    )


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa = set(a)
    sb = set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def cosine(a: Sequence[str], b: Sequence[str]) -> float:
    ca = Counter(a)
    cb = Counter(b)
    if not ca and not cb:
        return 1.0
    if not ca or not cb:
        return 0.0
    keys = set(ca) | set(cb)
    dot = sum(ca[k] * cb[k] for k in keys)
    na = math.sqrt(sum(v * v for v in ca.values()))
    nb = math.sqrt(sum(v * v for v in cb.values()))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def edit_distance(a: Sequence[str], b: Sequence[str]) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, start=1):
        cur = [i]
        for j, y in enumerate(b, start=1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (0 if x == y else 1)))
        prev = cur
    return prev[-1]


def normal_form_gap(claim: DerivationState, evidence: DerivationState) -> float:
    surface = edit_distance(claim.content_tokens, evidence.content_tokens) / max(1, max(len(claim.content_tokens), len(evidence.content_tokens)))
    marker = 1.0 - jaccard(claim.marker_set, evidence.marker_set)
    effect = 1.0 - jaccard(claim.effect_tags, evidence.effect_tags)
    precedence = 0.0 if claim.precedence_key == evidence.precedence_key else 1.0
    number = 0.0 if set(claim.numbers).issubset(set(evidence.numbers)) else (1.0 if claim.numbers else 0.0)
    return min(1.0, 0.34 * surface + 0.16 * marker + 0.18 * effect + 0.16 * precedence + 0.16 * number)


def meru_root(bits: str) -> str:
    if not bits:
        return sha256_text("EMPTY_PRASTARA")
    layer = [sha256_text(f"bit:{i}:{b}") for i, b in enumerate(bits)]
    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])
        layer = [sha256_text(layer[i] + layer[i + 1]) for i in range(0, len(layer), 2)]
    return layer[0]


class PaniniNyayaClaimVerifier:
    def __init__(self, config: Optional[VerifierConfig] = None) -> None:
        self.config = config or VerifierConfig()

    def verify(self, context: str, prompt: str, answer: str) -> ClaimVerificationReport:
        evidence_text = context.strip()
        evidence_states = [build_derivation_state(s) for s in sentence_units(evidence_text)]
        claim_states = [build_derivation_state(s) for s in sentence_units(answer)]
        results = [self._verify_one(f"C{i}", claim, evidence_states, prompt) for i, claim in enumerate(claim_states, start=1)]
        vector = "".join("1" if r.classification == CLASS_SUPPORTED else "0" for r in results)
        counts: Dict[str, int] = {}
        for r in results:
            counts[r.classification] = counts.get(r.classification, 0) + 1
        payload = {
            "version": "1.0.0",
            "engine": "PaniniNyayaClaimVerifier",
            "context_hash": sha256_text(context),
            "prompt_hash": sha256_text(prompt),
            "answer_hash": sha256_text(answer),
            "evidence_count": len(evidence_states),
            "claim_count": len(claim_states),
            "prastara_vector": vector,
            "meru_root": meru_root(vector),
            "classification_counts": counts,
            "claim_results": [asdict(r) for r in results],
        }
        return ClaimVerificationReport(report_hash=sha256_json(payload), **payload)

    def _verify_one(self, claim_id: str, claim: DerivationState, evidence_states: List[DerivationState], prompt: str) -> PramanaResult:
        if not evidence_states:
            return self._no_evidence_result(claim_id, claim)
        scored = [(self._score_pair(claim, ev, prompt), ev) for ev in evidence_states]
        scored.sort(key=lambda x: x[0]["total"], reverse=True)
        score, best_ev = scored[0]
        route_classes = self._route_classifications(score)
        route_conflict = len(set(route_classes.values())) > 1
        tags = self._hetvabhasa_tags(claim, best_ev, score, route_conflict)
        classification = self._final_classification(score, route_classes, tags, route_conflict)
        confidence = self._confidence(score, classification, route_conflict)
        residue = 1.0 - confidence if classification == CLASS_SUPPORTED else max(0.0, score["gap"])
        return PramanaResult(
            claim_id=claim_id,
            claim_text=claim.text,
            best_evidence_id=f"E{evidence_states.index(best_ev) + 1}",
            best_evidence_text=best_ev.text,
            pratyaksha_direct=score["direct"],
            anumana_inference=score["inference"],
            upamana_analogy=score["analogy"],
            shabda_context_authority=score["authority"],
            normal_form_gap=score["gap"],
            route_classifications=route_classes,
            route_conflict=route_conflict,
            hetvabhasa_tags=tuple(tags),
            classification=classification,
            confidence=confidence,
            residue=residue,
        )

    def _score_pair(self, claim: DerivationState, evidence: DerivationState, prompt: str) -> Dict[str, float]:
        direct = 0.55 * cosine(claim.content_tokens, evidence.content_tokens) + 0.45 * jaccard(claim.content_tokens, evidence.content_tokens)
        inference = jaccard(claim.relation_tags, evidence.relation_tags)
        analogy = jaccard([canonical_token(t) for t in claim.content_tokens], [canonical_token(t) for t in evidence.content_tokens])
        authority = 1.0 if "context" in prompt.lower() or "supplied" in prompt.lower() else 0.65
        gap = normal_form_gap(claim, evidence)
        number_mismatch = 1.0 if claim.numbers and not set(claim.numbers).issubset(set(evidence.numbers)) else 0.0
        entity_mismatch = self._entity_mismatch(claim, evidence)
        negation_shift = 1.0 if bool(set(claim.tokens) & NEGATORS) != bool(set(evidence.tokens) & NEGATORS) else 0.0
        contradiction = max(number_mismatch, entity_mismatch, negation_shift * (direct > self.config.contradiction_similarity_threshold))
        total = max(direct, 0.55 * inference + 0.45 * analogy) * authority - 0.35 * contradiction - 0.20 * gap
        return {
            "direct": max(0.0, min(1.0, direct)),
            "inference": max(0.0, min(1.0, inference)),
            "analogy": max(0.0, min(1.0, analogy)),
            "authority": authority,
            "gap": max(0.0, min(1.0, gap)),
            "number_mismatch": number_mismatch,
            "entity_mismatch": entity_mismatch,
            "negation_shift": negation_shift,
            "contradiction": max(0.0, min(1.0, contradiction)),
            "total": max(0.0, min(1.0, total)),
        }

    def _entity_mismatch(self, claim: DerivationState, evidence: DerivationState) -> float:
        claim_entities = set(claim.entities)
        evidence_entities = set(evidence.entities)
        if not claim_entities:
            return 0.0
        shared = claim_entities & evidence_entities
        novel = claim_entities - evidence_entities
        # Entity contradiction is strongest when the claim and evidence talk about a similar relation/object class.
        if novel and shared and jaccard(claim.relation_tags, evidence.relation_tags) > 0.0:
            return 1.0
        if novel and cosine(claim.content_tokens, evidence.content_tokens) > 0.42:
            return 0.75
        return 0.0

    def _route_classifications(self, score: Dict[str, float]) -> Dict[str, str]:
        direct_cls = CLASS_SUPPORTED if score["direct"] >= self.config.direct_support_threshold else CLASS_UNSUPPORTED
        inference_cls = CLASS_SUPPORTED if (score["inference"] >= 0.5 and score["analogy"] >= 0.45) else CLASS_UNCERTAIN
        if score["contradiction"] > 0.65:
            guard_cls = CLASS_CONTRADICTED
        elif score["gap"] <= 0.22:
            guard_cls = CLASS_SUPPORTED
        else:
            guard_cls = CLASS_UNSUPPORTED
        return {"pratyaksha": direct_cls, "anumana_upamana": inference_cls, "normal_form_guard": guard_cls}

    def _hetvabhasa_tags(self, claim: DerivationState, evidence: DerivationState, score: Dict[str, float], route_conflict: bool) -> List[str]:
        tags: List[str] = []
        if score["number_mismatch"]:
            tags.append("unsupported_or_contradicted_number")
        if score["entity_mismatch"]:
            tags.append("unsupported_or_contradicted_entity")
        if score["negation_shift"]:
            tags.append("negation_shift")
        if score["direct"] < 0.25 and score["analogy"] < 0.25:
            tags.append("asiddha_no_ground")
        if route_conflict:
            tags.append("route_conflict")
        if set(claim.marker_set) - set(evidence.marker_set):
            tags.append("marker_residue")
        return tags

    def _final_classification(self, score: Dict[str, float], routes: Dict[str, str], tags: List[str], route_conflict: bool) -> str:
        if score["contradiction"] > 0.65:
            return CLASS_CONTRADICTED
        if score["total"] >= self.config.paraphrase_support_threshold and CLASS_CONTRADICTED not in routes.values():
            return CLASS_SUPPORTED
        if score["total"] < self.config.uncertainty_threshold and ("asiddha_no_ground" in tags or score["gap"] > 0.50):
            return CLASS_UNSUPPORTED
        if route_conflict:
            return CLASS_UNCERTAIN
        return CLASS_UNSUPPORTED if score["total"] < self.config.uncertainty_threshold else CLASS_UNCERTAIN

    def _confidence(self, score: Dict[str, float], classification: str, route_conflict: bool) -> float:
        if classification == CLASS_CONTRADICTED:
            base = max(score["contradiction"], 1.0 - score["total"])
        elif classification == CLASS_SUPPORTED:
            base = score["total"]
        elif classification == CLASS_UNSUPPORTED:
            base = 1.0 - score["total"]
        else:
            base = 0.52
        if route_conflict:
            base -= self.config.route_conflict_penalty
        return max(0.0, min(1.0, base))

    def _no_evidence_result(self, claim_id: str, claim: DerivationState) -> PramanaResult:
        return PramanaResult(
            claim_id=claim_id,
            claim_text=claim.text,
            best_evidence_id=None,
            best_evidence_text=None,
            pratyaksha_direct=0.0,
            anumana_inference=0.0,
            upamana_analogy=0.0,
            shabda_context_authority=0.0,
            normal_form_gap=1.0,
            route_classifications={"pratyaksha": CLASS_UNSUPPORTED, "anumana_upamana": CLASS_UNSUPPORTED, "normal_form_guard": CLASS_UNSUPPORTED},
            route_conflict=False,
            hetvabhasa_tags=("no_evidence",),
            classification=CLASS_UNSUPPORTED,
            confidence=1.0,
            residue=1.0,
        )


def demo() -> Dict[str, Any]:
    context = "The Eiffel Tower is located in Paris. It was completed in 1889. The tower is made of iron."
    prompt = "Answer using only the supplied context."
    grounded = "The Eiffel Tower is located in Paris. It was completed in 1889. The tower is made of iron."
    hallucinated = "The Eiffel Tower is located in Berlin. It was completed in 1789. The tower is made of wood."
    verifier = PaniniNyayaClaimVerifier()
    return {"grounded": asdict(verifier.verify(context, prompt, grounded)), "hallucinated": asdict(verifier.verify(context, prompt, hallucinated))}


def main() -> None:
    parser = argparse.ArgumentParser(description="Panini--Nyaya claim-level hallucination verifier")
    parser.add_argument("--context")
    parser.add_argument("--prompt", default="Answer using only the supplied context.")
    parser.add_argument("--answer")
    parser.add_argument("--out", default="panini_nyaya_report.json")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    if args.demo:
        result = demo()
    else:
        if not args.context or not args.answer:
            parser.error("--context and --answer are required unless --demo is used")
        verifier = PaniniNyayaClaimVerifier()
        result = asdict(verifier.verify(args.context, args.prompt, args.answer))
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
    print(json.dumps({"ok": True, "out": args.out, "hash": sha256_json(result)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
