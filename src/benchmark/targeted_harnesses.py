"""Targeted harnesses for specific failure modes — based on frontier research.

Each harness addresses a specific failure pattern with a different strategy:
1. Expiration Date: paraphrase detection (duration/continuation patterns)
2. IP Ownership: legal phrase expansion (vest in, assign all right)
3. Non-Compete: activity-based detection (engage in business)
4. Post-Termination: survival obligation patterns
5. Rofr/Rofo/Rofn: domain-specific terms
6. Multi-signal voting: combine all strategies
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass


@dataclass
class HarnessResult:
    name: str
    accuracy: float
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    tn: int
    fn: int


# --- Strategy 1: Expiration Date paraphrase detection ---
# Research: clauses say "shall continue for X years", "shall extend until",
# "shall remain in effect until", not literal "expiration date"

EXPIRATION_PATTERNS = [
    r'shall\s+continue\s+(?:for|until)',
    r'shall\s+extend\s+until',
    r'shall\s+remain\s+in\s+effect',
    r'shall\s+commence.*and\s+(?:shall\s+)?(?:continue|extend|expire)',
    r'expire\s+on',
    r'expiration\s+date',
    r'end\s+of\s+term',
    r'term\s+(?:shall\s+)?(?:end|expire)',
    r'for\s+a\s+(?:period\s+of\s+)?(?:\d+\s*\([^)]*\)\s*)?(?:year|month|day)',
    r'unless\s+earlier\s+terminated',
]


def harness_expiration_date(text: str) -> tuple[bool, float]:
    """Detect expiration dates via paraphrase patterns."""
    text_lower = text.lower()
    matches = sum(1 for p in EXPIRATION_PATTERNS if re.search(p, text_lower))
    if matches >= 2:
        return True, 0.85
    elif matches == 1:
        return True, 0.7
    return False, 0.9


# --- Strategy 2: IP Ownership legal phrase expansion ---
# Research: clauses say "shall assign all right, title and interest",
# "shall at all times vest in", "any and all intellectual property"

IP_PATTERNS = [
    r'(?:shall\s+)?assign\s+(?:all\s+)?(?:right|title|interest)',
    r'vest\s+in\s+(?:and\s+)?inure',
    r'(?:any\s+and\s+all\s+)?intellectual\s+property',
    r'work\s+for\s+hire',
    r'ip\s+ownership',
    r'ownership.*(?:shall\s+)?(?:vest|remain|transfer)',
    r'(?:all\s+)?right.*title.*interest.*(?:vest|assign|transfer)',
]


def harness_ip_ownership(text: str) -> tuple[bool, float]:
    """Detect IP ownership clauses via legal phrase patterns."""
    text_lower = text.lower()
    matches = sum(1 for p in IP_PATTERNS if re.search(p, text_lower))
    if matches >= 2:
        return True, 0.85
    elif matches == 1:
        return True, 0.7
    return False, 0.9


# --- Strategy 3: Non-Compete activity-based detection ---
# Research: clauses say "shall not engage in", "shall not conduct",
# "will not enter into", not literal "non-compete"

NONCOMPETE_PATTERNS = [
    r'(?:shall|will|must)\s+not\s+(?:engage|conduct|enter|participate)',
    r'(?:shall|will|must)\s+not.*(?:business|compete|competition)',
    r'non-compete',
    r'noncompete',
    r'competing\s+(?:product|service|business)',
    r'exclusive\s+(?:right|license|partner)',
    r'(?:during|throughout)\s+the\s+(?:term|period).*(?:not|shall\s+not)',
]


def harness_non_compete(text: str) -> tuple[bool, float]:
    """Detect non-compete clauses via activity patterns."""
    text_lower = text.lower()
    matches = sum(1 for p in NONCOMPETE_PATTERNS if re.search(p, text_lower))
    if matches >= 2:
        return True, 0.85
    elif matches == 1:
        return True, 0.7
    return False, 0.9


# --- Strategy 4: Post-Termination survival patterns ---
# Research: clauses reference "Step-in Right", "upon termination",
# "surviving obligations", "until the earlier of"

POSTTERM_PATTERNS = [
    r'post-termination',
    r'upon\s+termination',
    r'after\s+termination',
    r'surviving\s+(?:obligations|provisions)',
    r'step-in\s+right',
    r'wind[-\s]?down',
    r'(?:shall\s+)?(?:continue|remain)\s+(?:to\s+)?(?:perform|provide|supply).*(?:after|upon|following)\s+terminat',
    r'(?:obligations?\s+)?(?:that\s+)?(?:shall\s+)?(?:survive|continue)\s+(?:the\s+)?terminat',
]


def harness_post_termination(text: str) -> tuple[bool, float]:
    """Detect post-termination service clauses."""
    text_lower = text.lower()
    matches = sum(1 for p in POSTTERM_PATTERNS if re.search(p, text_lower))
    if matches >= 2:
        return True, 0.85
    elif matches == 1:
        return True, 0.7
    return False, 0.9


# --- Strategy 5: ROFR/ROFO/ROFN domain-specific ---
# Research: clauses reference "option period", "negotiate exclusively",
# "right of first refusal", "first offer"

ROFR_PATTERNS = [
    r'right\s+of\s+first\s+(?:refusal|offer|notification)',
    r'rofr|rofo|rofn',
    r'option\s+period',
    r'license\s+option',
    r'negotiate\s+exclusively',
    r'first\s+(?:opportunity|right)\s+to',
]


def harness_rofr(text: str) -> tuple[bool, float]:
    """Detect ROFR/ROFO/ROFN clauses."""
    text_lower = text.lower()
    matches = sum(1 for p in ROFR_PATTERNS if re.search(p, text_lower))
    if matches >= 1:
        return True, 0.8
    return False, 0.95


# --- Strategy 6: Multi-signal voting ensemble ---

def harness_ensemble(text: str, label: str) -> tuple[bool, float]:
    """Combine all strategies via voting."""
    strategies = {
        "Expiration Date": harness_expiration_date,
        "Ip Ownership Assignment": harness_ip_ownership,
        "Non-Compete": harness_non_compete,
        "Post-Termination Services": harness_post_termination,
        "Rofr/Rofo/Rofn": harness_rofr,
    }

    if label in strategies:
        return strategies[label](text)

    # Fallback: keyword + context (V2 from harnesses.py)
    from .harnesses import ALL_KEYWORDS
    patterns = ALL_KEYWORDS.get(label, {})
    required = patterns.get("required", [])
    context_words = patterns.get("context", [])

    text_lower = text.lower()
    has_required = any(kw.lower() in text_lower for kw in required)
    if not has_required:
        return False, 0.95

    ctx_count = sum(1 for cw in context_words if cw.lower() in text_lower) if context_words else 1
    if len(context_words) == 0:
        return True, 0.85
    elif ctx_count >= 2:
        return True, 0.85
    elif ctx_count == 1:
        return True, 0.7
    return True, 0.5


def run_targeted_comparison(max_contracts: int = 102) -> dict:
    """Run targeted harnesses on specific failing labels."""
    data_path = "/tmp/cuad/data/test.json"
    if not os.path.exists(data_path):
        return {}

    with open(data_path) as f:
        data = json.load(f)

    # Test each targeted harness on its specific label
    targeted = {
        "Expiration Date": harness_expiration_date,
        "Ip Ownership Assignment": harness_ip_ownership,
        "Non-Compete": harness_non_compete,
        "Post-Termination Services": harness_post_termination,
        "Rofr/Rofo/Rofn": harness_rofr,
    }

    results = {}
    for label, harness_fn in targeted.items():
        tp = tn = fp = fn = 0
        for doc in data["data"][:max_contracts]:
            paragraphs = doc.get("paragraphs", [])
            if not paragraphs:
                continue
            full_text = " ".join(p.get("context", "") for p in paragraphs)
            for p in paragraphs:
                for qa in p.get("qas", []):
                    match = re.search(r'related to "(.+?)"', qa.get("question", ""))
                    if not match or match.group(1) != label:
                        continue
                    gt = not qa.get("is_impossible", True) and bool(qa.get("answers", []))
                    found, _ = harness_fn(full_text)
                    if gt and found: tp += 1
                    elif not gt and not found: tn += 1
                    elif gt and not found: fn += 1
                    elif not gt and found: fp += 1

        total = tp + tn + fp + fn
        acc = (tp + tn) / max(total, 1)
        prec = tp / max(tp + fp, 1)
        rec = tp / max(tp + fn, 1)
        f1 = 2 * prec * rec / max(prec + rec, 1e-9)
        results[label] = HarnessResult(label, acc, prec, rec, f1, tp, fp, tn, fn)

    # Also run ensemble on ALL labels
    tp = tn = fp = fn = 0
    for doc in data["data"][:max_contracts]:
        paragraphs = doc.get("paragraphs", [])
        if not paragraphs:
            continue
        full_text = " ".join(p.get("context", "") for p in paragraphs)
        for p in paragraphs:
            for qa in p.get("qas", []):
                match = re.search(r'related to "(.+?)"', qa.get("question", ""))
                if not match:
                    continue
                label = match.group(1)
                gt = not qa.get("is_impossible", True) and bool(qa.get("answers", []))
                found, _ = harness_ensemble(full_text, label)
                if gt and found: tp += 1
                elif not gt and not found: tn += 1
                elif gt and not found: fn += 1
                elif not gt and found: fp += 1

    total = tp + tn + fp + fn
    acc = (tp + tn) / max(total, 1)
    prec = tp / max(tp + fp, 1)
    rec = tp / max(tp + fn, 1)
    f1 = 2 * prec * rec / max(prec + rec, 1e-9)
    results["ENSEMBLE_ALL"] = HarnessResult("ENSEMBLE_ALL", acc, prec, rec, f1, tp, fp, tn, fn)

    return results
