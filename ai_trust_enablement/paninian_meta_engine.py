#!/usr/bin/env python3
"""
Paninian Meta Engine
====================

A compact on-demand derivation engine for AI trust certificates.

It implements a small, traceable subset of the Paninian rule-index idea:
    rule_id -> canonical tuple -> rendered mathematical/operator form

Canonical tuple:
    (rule_id, name, domain, operator, input, output, condition, scope, priority)

The purpose is practical, not decorative: every claim-level verification result can
carry rule reasons such as designation, negation, elision, exception, optionality,
priority, semantic mapping, or boundary-based object definition.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class RuleMetadata:
    rule_id: str
    name: str
    gloss: str
    domain: str
    archetype: str
    role: str


@dataclass(frozen=True)
class DerivedRule:
    rule_id: str
    name: str
    domain: str
    operator: str
    input: str
    output: str
    condition: str
    scope: str
    priority: str
    archetype: str
    math_form: str
    tags: Tuple[str, ...]
    derivation_hash: str


OPERATOR_ARCHETYPES: Dict[str, Dict[str, str]] = {
    "substitution": {"operator": "rewrite", "template": "f: A -> B if condition(x)"},
    "elision": {"operator": "zero_map", "template": "L(x)=empty for x in marked set"},
    "addition": {"operator": "augmentation", "template": "A -> A + marker_or_affix"},
    "restriction": {"operator": "constraint", "template": "apply only when predicate holds"},
    "generalization": {"operator": "universal_rule", "template": "for all x in domain: predicate(x) -> transform(x)"},
    "exception": {"operator": "override_mask", "template": "if exception matches, protect or override base rule"},
    "designation": {"operator": "type_tag", "template": "type(X):=Y or alias(X,Y)"},
    "boundary": {"operator": "boundary_selector", "template": "select start/end token under scope"},
    "logic": {"operator": "logical_gate", "template": "predicate(x) -> consequence(x)"},
    "choice": {"operator": "optional_branch", "template": "choose {apply rule, skip rule}"},
    "priority": {"operator": "precedence_gate", "template": "resolve conflict by ordered priority"},
    "semantics": {"operator": "meaning_map", "template": "structure -> meaning"},
    "inverse": {"operator": "left_inverse", "template": "base = word - affix"},
    "sum_type": {"operator": "constructor_union", "template": "type = constructor_1 | constructor_2 | ..."},
    "invariant": {"operator": "property_guard", "template": "preserve class property under rule"},
}


SUTRA_INDEX: Dict[str, RuleMetadata] = {
    "1.1.1": RuleMetadata("1.1.1", "vrddhir adaiC", "max-gain vowel map", "phonology", "substitution", "max_gain_vowel_map"),
    "1.1.2": RuleMetadata("1.1.2", "adeng gunah", "mid-gain vowel map", "phonology", "substitution", "mid_gain_vowel_map"),
    "1.1.3": RuleMetadata("1.1.3", "eco yavayavah", "e/o/ai/au replacement before vowel", "phonology", "substitution", "contextual_vowel_rewrite"),
    "1.1.4": RuleMetadata("1.1.4", "aico yan aci", "vowel-to-glide before vowel", "phonology", "substitution", "vowel_glide_rewrite"),
    "1.1.5": RuleMetadata("1.1.5", "hal antyam", "select terminal consonant", "morphology", "boundary", "terminal_boundary_selector"),
    "1.1.6": RuleMetadata("1.1.6", "tasya lopah", "delete marked element", "morphology", "elision", "marker_deletion"),
    "1.1.7": RuleMetadata("1.1.7", "nan", "negation particle", "logic", "logic", "negation_gate"),
    "1.1.8": RuleMetadata("1.1.8", "sup", "noun case suffix set", "morphology", "designation", "case_suffix_set"),
    "1.1.9": RuleMetadata("1.1.9", "tin", "verb ending tensor", "morphology", "designation", "verb_ending_set"),
    "1.1.10": RuleMetadata("1.1.10", "pratyayah", "affix follows base", "morphology", "designation", "affix_composition"),
    "1.1.11": RuleMetadata("1.1.11", "tinsit sarvanamasthane", "conditional slot mapping", "morphology", "substitution", "conditional_slot_mapping"),
    "1.1.12": RuleMetadata("1.1.12", "adyantau takitau", "first and last markers significant", "morphology", "boundary", "first_last_marker_boundary"),
    "1.1.13": RuleMetadata("1.1.13", "upadese aj anunasika it", "non-nasal vowel as marker", "morphology", "restriction", "feature_marker_detection"),
    "1.1.14": RuleMetadata("1.1.14", "hal antyam", "final consonant as marker", "morphology", "boundary", "final_consonant_marker"),
    "1.1.15": RuleMetadata("1.1.15", "tasya lopah", "elide the marker", "morphology", "elision", "marker_erasure_after_recording"),
    "1.1.16": RuleMetadata("1.1.16", "na lopah sakalyasya", "exception protects element from deletion", "logic", "exception", "protected_invariant"),
    "1.1.17": RuleMetadata("1.1.17", "anudattangita atmanepadam", "feature-driven implication", "morphology", "logic", "feature_implication"),
    "1.1.18": RuleMetadata("1.1.18", "svaujasamaut chabhyam", "controlled suffix replacement", "morphology", "substitution", "controlled_replacement"),
    "1.1.19": RuleMetadata("1.1.19", "tin pratyayah", "verb endings are affixes", "morphology", "designation", "type_membership"),
    "1.1.20": RuleMetadata("1.1.20", "suptinantam padam", "word ends in sup or tin", "morphology", "boundary", "word_boundary_definition"),
    "1.1.21": RuleMetadata("1.1.21", "pratipadikam", "base from affix removal", "morphology", "inverse", "base_extraction"),
    "1.1.22": RuleMetadata("1.1.22", "avyayam nistha", "indeclinable by suffix", "morphology", "addition", "derived_invariant_form"),
    "1.1.23": RuleMetadata("1.1.23", "kriyayah karmavat karmopasamyogat", "action inherits object behavior", "semantics", "logic", "relational_inheritance"),
    "1.1.24": RuleMetadata("1.1.24", "pratyayah arthavad dharmanam", "affix conveys meaning", "semantics", "semantics", "structure_to_meaning"),
    "1.1.25": RuleMetadata("1.1.25", "arthavad dharmah pratyayah", "meaningful element is affix", "semantics", "semantics", "meaning_to_structure"),
    "1.1.26": RuleMetadata("1.1.26", "sarvadhatukam apit", "class complement", "morphology", "restriction", "class_complement"),
    "1.1.27": RuleMetadata("1.1.27", "ardhadhatukam", "verbal affix subclass", "morphology", "designation", "subtype_declaration"),
    "1.1.28": RuleMetadata("1.1.28", "krt taddhita samasas ca", "constructor sum types", "morphology", "sum_type", "constructor_union"),
    "1.1.29": RuleMetadata("1.1.29", "pratyayah", "mark constructors as affixes", "morphology", "designation", "constructor_tagging"),
    "1.1.30": RuleMetadata("1.1.30", "sarvadini sarvanamani", "pronoun class list", "morphology", "designation", "class_enumeration"),
    "1.1.31": RuleMetadata("1.1.31", "pratyayasya", "restrict rule to affix domain", "morphology", "restriction", "affix_scope"),
    "1.1.32": RuleMetadata("1.1.32", "samjna", "technical designation or alias", "meta", "designation", "alias_declaration"),
    "1.1.33": RuleMetadata("1.1.33", "pratyayalaksanam", "affix class property", "morphology", "invariant", "affix_property_invariant"),
    "1.1.34": RuleMetadata("1.1.34", "vibhasa", "optional branch", "meta", "choice", "optional_rule_branch"),
    "1.1.35": RuleMetadata("1.1.35", "anitya", "non-obligatory priority", "meta", "priority", "non_obligatory_precedence"),
}


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def derive(rule_id: str) -> DerivedRule:
    if rule_id not in SUTRA_INDEX:
        raise KeyError(f"unknown_rule_id:{rule_id}")
    meta = SUTRA_INDEX[rule_id]
    arch = OPERATOR_ARCHETYPES[meta.archetype]
    rule = _derive_tuple(meta, arch)
    material = asdict(rule)
    material.pop("derivation_hash")
    return DerivedRule(derivation_hash=sha256_json(material), **material)


def _derive_tuple(meta: RuleMetadata, arch: Dict[str, str]) -> DerivedRule:
    operator = arch["operator"]
    input_set, output_set, condition, scope, priority = _infer_io_condition_scope_priority(meta)
    math_form = _render_math(meta, operator, input_set, output_set, condition, scope, priority)
    tags = tuple(sorted({meta.domain, meta.archetype, meta.role, operator, priority}))
    return DerivedRule(
        rule_id=meta.rule_id,
        name=meta.name,
        domain=meta.domain,
        operator=operator,
        input=input_set,
        output=output_set,
        condition=condition,
        scope=scope,
        priority=priority,
        archetype=meta.archetype,
        math_form=math_form,
        tags=tags,
        derivation_hash="",
    )


def _infer_io_condition_scope_priority(meta: RuleMetadata) -> Tuple[str, str, str, str, str]:
    rid = meta.rule_id
    defaults = ("symbolic_state", "normalized_state", "true", "local", "nitya")
    table = {
        "1.1.3": ("{e,o,ai,au}", "{y,v,ay,av}", "next_token_is_vowel", "base_right_boundary", "nitya"),
        "1.1.6": ("it_marker", "empty", "is_marked(x)", "affix", "nitya"),
        "1.1.7": ("claim", "negated_claim", "has_negation_particle", "logic", "nitya"),
        "1.1.13": ("vowel", "it_marker", "non_nasal_vowel_in_instruction", "marker_detection", "nitya"),
        "1.1.15": ("recorded_marker", "empty", "marker_already_recorded", "surface_rendering", "nitya"),
        "1.1.16": ("protected_element", "protected_element", "exception_matches", "rule_mask", "exception"),
        "1.1.17": ("feature_bundle", "voice_assignment", "has_marker_and_pitch", "feature_gate", "nitya"),
        "1.1.18": ("suffix_set", "replacement_set", "plural_suffix_context", "suffix", "nitya"),
        "1.1.20": ("token_sequence", "word_object", "ends_with_sup_or_tin", "word_boundary", "nitya"),
        "1.1.21": ("word_object", "base_object", "remove_affix", "inverse_morphology", "nitya"),
        "1.1.23": ("action_relation", "object_inheritance", "action_connected_to_object", "semantic_relation", "nitya"),
        "1.1.24": ("structure", "meaning", "affix_has_semantic_value", "semantics", "nitya"),
        "1.1.25": ("meaning", "structure", "element_has_meaning", "semantics", "nitya"),
        "1.1.32": ("term", "technical_alias", "designation_declared", "meta", "nitya"),
        "1.1.34": ("rule", "{apply,skip}", "optional_context", "global", "optional"),
        "1.1.35": ("rule", "priority_adjusted_rule", "non_obligatory_context", "global", "anitya"),
    }
    return table.get(rid, defaults)


def _render_math(meta: RuleMetadata, operator: str, input_set: str, output_set: str, condition: str, scope: str, priority: str) -> str:
    if meta.archetype == "designation":
        return f"type_or_alias({input_set}) := {output_set} when {condition}; scope={scope}; priority={priority}"
    if meta.archetype == "elision":
        return f"L({input_set}) = {output_set} when {condition}; scope={scope}; priority={priority}"
    if meta.archetype == "substitution":
        return f"R: {input_set} -> {output_set} when {condition}; scope={scope}; priority={priority}"
    if meta.archetype == "exception":
        return f"protect({input_set}) -> {output_set} when {condition}; masks base rewrite"
    if meta.archetype == "choice":
        return f"choose({input_set}) = {output_set}; branch retained in trace"
    if meta.archetype == "priority":
        return f"P({input_set}) -> {output_set}; conflict order={priority}"
    if meta.archetype == "semantics":
        return f"Sem({input_set}) -> {output_set} when {condition}; bidirectional semantic guard"
    if meta.archetype == "inverse":
        return f"Inv({input_set}) -> {output_set} when {condition}"
    return f"O_{operator}: {input_set} -> {output_set} when {condition}; scope={scope}; priority={priority}"


def derive_many(rule_ids: Sequence[str]) -> List[DerivedRule]:
    return [derive(rule_id) for rule_id in rule_ids]


def rule_trace_for_markers(markers: Iterable[str], effect_tags: Iterable[str] = (), has_route_conflict: bool = False) -> List[DerivedRule]:
    marker_set = {m.upper() for m in markers}
    effects = {e.lower() for e in effect_tags}
    rule_ids: List[str] = []
    if "ENTITY" in marker_set:
        rule_ids.append("1.1.32")
    if "NUMBER" in marker_set:
        rule_ids.append("1.1.20")
    if "NEGATION" in marker_set:
        rule_ids.append("1.1.7")
    if "RELATION" in marker_set or effects:
        rule_ids.extend(["1.1.23", "1.1.24"])
    if "LONG_CLAIM" in marker_set:
        rule_ids.append("1.1.31")
    if has_route_conflict:
        rule_ids.extend(["1.1.34", "1.1.35"])
    # Always record marker erasure as a certificate hygiene step.
    rule_ids.append("1.1.15")
    deduped: List[str] = []
    for rid in rule_ids:
        if rid not in deduped:
            deduped.append(rid)
    return derive_many(deduped)


def compact_trace(markers: Iterable[str], effect_tags: Iterable[str] = (), has_route_conflict: bool = False) -> List[Dict[str, Any]]:
    return [asdict(rule) for rule in rule_trace_for_markers(markers, effect_tags, has_route_conflict)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Paninian on-demand meta derivation engine")
    parser.add_argument("--rule", action="append", help="rule id such as 1.1.6; may be repeated")
    parser.add_argument("--markers", default="", help="comma separated marker list, e.g. NUMBER,ENTITY,RELATION")
    parser.add_argument("--effects", default="", help="comma separated effect tag list")
    parser.add_argument("--route-conflict", action="store_true")
    args = parser.parse_args()
    if args.rule:
        output = [asdict(rule) for rule in derive_many(args.rule)]
    else:
        markers = [x.strip() for x in args.markers.split(",") if x.strip()]
        effects = [x.strip() for x in args.effects.split(",") if x.strip()]
        output = compact_trace(markers, effects, args.route_conflict)
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
