"""FactJudge-derived verification strategies adapted for ProofDesk contract clause extraction.

Based on the factjudge C000-C019 candidates and PLANS.md architecture.
Each strategy is a deterministic check that can be applied to contract clause detection.
"""

from __future__ import annotations

import re
from datetime import date
from difflib import SequenceMatcher


# --- From C000: Token overlap + sequence ratio ---

def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def strategy_token_overlap(ground_truth: str, candidate: str) -> float:
    """C000 baseline: token overlap + sequence ratio."""
    if not ground_truth or not candidate:
        return 0.0
    t, c = set(_tokens(ground_truth)), set(_tokens(candidate))
    overlap = len(t & c) / max(len(t), 1)
    ratio = SequenceMatcher(None, ground_truth.lower(), candidate.lower()).ratio()
    return round(0.6 * overlap + 0.4 * ratio, 4)


# --- From C001: Date normalization ---

MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}
MONTHS.update({m[:3].lower(): i for m, i in [(k.capitalize(), v) for k, v in list(MONTHS.items())]})


def _iso_dates(text: str) -> set:
    found = set()
    for d, m, y in re.findall(r"([A-Z][a-z]+)\s+(\d{1,2}),?\s+(\d{4})", text):
        if m.lower() in MONTHS:
            try:
                found.add(date(int(y), MONTHS[m.lower()], int(d)).isoformat())
            except ValueError:
                pass
    for y, m, d in re.findall(r"(\d{4})-(\d{2})-(\d{2})", text):
        try:
            found.add(date(int(y), int(m), int(d)).isoformat())
        except ValueError:
            pass
    for m, d, y in re.findall(r"(\d{1,2})/(\d{1,2})/(\d{4})", text):
        try:
            found.add(date(int(y), int(m), int(d)).isoformat())
        except ValueError:
            pass
    return found


def strategy_date_consistency(gt_text: str, answer_text: str) -> float:
    """C001: Date format normalization to ISO ordinals."""
    gt_dates = _iso_dates(gt_text)
    ans_dates = _iso_dates(answer_text)
    if not gt_dates:
        return 1.0  # No dates to check
    if not ans_dates:
        return 0.0  # Dates in GT but not in answer
    matches = len(gt_dates & ans_dates)
    return matches / max(len(gt_dates), 1)


# --- From C005: Numeric consistency + negation parity ---

_NUM = re.compile(r"\d+(?:\.\d+)?")
_CUES = [" not ", "n't ", " never ", " no ", "failed to", "did not", "does not",
         "cannot ", "can't ", "won't ", "contrary to", "denied", "without "]


def _numbers(text: str) -> list[float]:
    return [float(x) for x in _NUM.findall(text.replace(",", ""))]


def _near(a: float, b: float) -> bool:
    s = max(abs(a), abs(b), 1.0)
    return abs(a - b) <= max((0.005 if s > 1000 else 0.02) * s, 0.02)


def _negation_count(text: str) -> int:
    x = " " + text.lower() + " "
    return sum(x.count(c) for c in _CUES)


def strategy_numeric_consistency(gt_text: str, answer_text: str) -> float:
    """C005: Numeric consistency with tolerance + negation parity gate."""
    if not gt_text or not answer_text:
        return 0.0

    # Base token overlap
    t, c = set(_tokens(gt_text)), set(_tokens(answer_text))
    base = 0.6 * (len(t & c) / max(len(t), 1)) + 0.4 * SequenceMatcher(
        None, gt_text.lower(), answer_text.lower()).ratio()

    # Numeric check
    gt_nums = _numbers(gt_text)
    if gt_nums:
        num_matches = sum(1 for g in gt_nums if any(_near(g, m) for m in _numbers(answer_text)))
        num_score = num_matches / len(gt_nums)
    else:
        num_score = 1.0

    core = 0.6 * base + 0.4 * (0.5 + 0.5 * num_score)

    # Negation parity gate
    gt_neg = _negation_count(gt_text)
    ans_neg = _negation_count(answer_text)
    mismatch = (gt_neg > 0) != (ans_neg > 0)

    if mismatch:
        return round(core * 0.3, 4)  # Hard penalty

    return round(core, 4)


# --- From C017: Relation-role consistency ---

_PROP = re.compile(r"\b([A-Z][a-zA-Z]+)\b")
_STOP_ENT = {"The", "A", "An", "In", "On", "It", "This", "That", "Its", "Their"}
_VERBS = ["defeated", "beat", "orbits", "acquired", "causes", "founded",
          "wrote", "built", "opened", "located", "formed", "landed",
          "launched", "composed", "divided", "consists", "rose", "reached",
          "capital", "capital of"]


def _extract_roles(text: str) -> dict:
    """Extract PRE-verb and POST-verb entities."""
    words = text.split()
    pre_ents = []
    post_ents = []
    in_post = False

    for w in words:
        if w.lower() in _VERBS or any(v in text.lower() for v in _VERBS):
            in_post = True
        if _PROP.match(w) and w not in _STOP_ENT:
            if in_post:
                post_ents.append(w)
            else:
                pre_ents.append(w)

    return {"pre": set(pre_ents), "post": set(post_ents)}


def strategy_relation_roles(gt_text: str, answer_text: str) -> float:
    """C017: Relation-role consistency — entity position relative to verb."""
    gt_roles = _extract_roles(gt_text)
    ans_roles = _extract_roles(answer_text)

    # Check if entity roles are consistent
    gt_all = gt_roles["pre"] | gt_roles["post"]
    ans_all = ans_roles["pre"] | ans_roles["post"]

    if not gt_all:
        return 1.0

    # Entities in same position (pre/post)
    pre_match = len(gt_roles["pre"] & ans_roles["pre"])
    post_match = len(gt_roles["post"] & ans_roles["post"])
    total = len(gt_all)

    if total == 0:
        return 1.0

    return (pre_match + post_match) / total


# --- Ensemble: combine all strategies ---

def factjudge_ensemble(gt_text: str, answer_text: str) -> float:
    """Combine all factjudge-derived strategies."""
    if not gt_text or not answer_text:
        return 0.0

    s1 = strategy_token_overlap(gt_text, answer_text)
    s2 = strategy_date_consistency(gt_text, answer_text)
    s3 = strategy_numeric_consistency(gt_text, answer_text)
    s4 = strategy_relation_roles(gt_text, answer_text)

    # Weighted combination
    return round(0.30 * s1 + 0.20 * s2 + 0.25 * s3 + 0.25 * s4, 4)
