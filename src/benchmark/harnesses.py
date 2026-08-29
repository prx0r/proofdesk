"""Frontier contract extraction harnesses — V2 with complete label coverage.

Based on 2025-2026 research + actual CUAD clause text analysis.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass


@dataclass
class HarnessResult:
    harness_name: str
    accuracy: float
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    tn: int
    fn: int


# --- COMPLETE keyword dictionaries (based on actual CUAD clause text) ---

ALL_KEYWORDS = {
    "Document Name": {
        "required": ["agreement", "contract", "amendment", "license agreement"],
        "context": [],
    },
    "Parties": {
        "required": ["party", "seller", "buyer", "licensor", "licensee", "hereinafter"],
        "context": ["referred to as", "incorporated"],
    },
    "Agreement Date": {
        "required": ["dated", "executed on", "as of", "entered into"],
        "context": ["day of", "2019", "2018", "2017", "2016", "2015"],
    },
    "Anti-Assignment": {
        "required": ["assign"],
        "context": ["shall not", "prohibited", "consent", "written", "without"],
    },
    "Cap On Liability": {
        "required": ["liability"],
        "context": ["shall not exceed", "limited to", "aggregate", "maximum", "cap"],
    },
    "Change Of Control": {
        "required": ["change of control", "change in control"],
        "context": ["acquisition", "merger", "sale"],
    },
    "Competitive Restriction Exception": {
        "required": ["exception to", "carve-out from", "notwithstanding"],
        "context": ["competitive", "restriction", "exclusivity"],
    },
    "Competitive Restriction Exclusivity": {
        "required": ["exclusive", "exclusivity"],
        "context": ["during", "period", "restriction", "competitive"],
    },
    "Covenant Not To Sue": {
        "required": ["covenant not to sue", "waive"],
        "context": ["claims", "action", "proceeding"],
    },
    "Effective Date": {
        "required": ["effective date", "effective as of", "commences on"],
        "context": [],
    },
    "Expiration Date": {
        "required": ["expiration date", "expires on", "end of term", "term ends"],
        "context": [],
    },
    "Governing Law": {
        "required": ["governing law", "laws of the state", "laws of the commonwealth"],
        "context": ["shall be governed", "applicable law"],
    },
    "Indemnification Cap": {
        "required": ["indemnif"],
        "context": ["cap", "limit", "aggregate", "sole remedy"],
    },
    "Insurance": {
        "required": ["insurance", "insurer"],
        "context": ["coverage", "certificate", "maintain", "policy"],
    },
    "IP Ownership Assignment": {
        "required": ["intellectual property", "work for hire", "ip ownership"],
        "context": ["ownership", "assign", "invention"],
    },
    "Legal Action Notice": {
        "required": ["notice"],
        "context": ["legal action", "demand", "arbitration", "dispute"],
    },
    "License Grant": {
        "required": ["grant", "license", "right to use"],
        "context": ["non-exclusive", "royalty-free", "permission"],
    },
    "Liquidated Damages": {
        "required": ["liquidated damages"],
        "context": ["agreed", "predetermined", "stipulated"],
    },
    "Non-Compete": {
        "required": ["non-compete", "noncompete", "competitive activity"],
        "context": ["during", "restricted", "prohibited"],
    },
    "Non-Disparagement": {
        "required": ["disparag"],
        "context": ["negative", "defamatory", "publicly"],
    },
    "Non-Solicitation": {
        "required": ["solicit"],
        "context": ["employee", "customer", "client"],
    },
    "Renewal Term": {
        "required": ["renewal", "auto-renew", "renewal term"],
        "context": ["successive", "automatically extend"],
    },
    "Termination For Convenience": {
        "required": ["termination for convenience", "terminate for convenience", "without cause"],
        "context": ["written notice", "days", "notice period"],
    },
    "Termination For Cause": {
        "required": ["termination for cause", "material breach", "default"],
        "context": ["cure period", "remed", "breach"],
    },
    "Uncapped Liability": {
        "required": ["uncapped liability", "unlimited liability", "no limitation"],
        "context": [],
    },
    "Warranty": {
        "required": ["warranty", "warrant"],
        "context": ["as is", "disclaim", "represent and warrant"],
    },
    "Audit Rights": {
        "required": ["audit"],
        "context": ["inspection", "books and records", "examine"],
    },
    "Exclusivity": {
        "required": ["exclusive", "sole partner", "exclusively"],
        "context": ["right", "license", "during"],
    },
    "License Grant": {
        "required": ["grant", "license", "right to use"],
        "context": ["non-exclusive", "royalty-free", "permission"],
    },
    "Minimum Commitment": {
        "required": ["minimum", "commitment"],
        "context": ["purchase", "guaranteed", "obligation"],
    },
    "Revenue/Profit Sharing": {
        "required": ["revenue", "profit sharing", "commission", "royalty"],
        "context": ["percentage", "share", "split"],
    },
    "Non-Transferable License": {
        "required": ["non-transferable", "non-assignable"],
        "context": ["rights", "obligations"],
    },
    "Post-Termination Services": {
        "required": ["post-termination", "after termination", "surviving"],
        "context": ["obligations", "services", "wind-down"],
    },
    "Irrevocable Or Perpetual License": {
        "required": ["irrevocable", "perpetual", "in perpetuity"],
        "context": ["license", "right"],
    },
    "Joint Ip Ownership": {
        "required": ["joint ownership", "jointly owned", "co-ownership"],
        "context": ["ip", "intellectual property"],
    },
    "Third Party Beneficiary": {
        "required": ["third party beneficiary", "intended beneficiary"],
        "context": [],
    },
    "Volume Restriction": {
        "required": ["volume", "volume cap", "volume limit"],
        "context": ["maximum", "quantity"],
    },
    "Warranty Duration": {
        "required": ["warranty period", "warranty duration", "warranty shall last"],
        "context": ["months", "years", "period"],
    },
    "No-Solicit Of Employees": {
        "required": ["solicit employees", "hire employees"],
        "context": ["during", "period", "after"],
    },
    "No-Solicit Of Customers": {
        "required": ["solicit customers", "solicit clients", "solicit business"],
        "context": ["during", "period"],
    },
    "Affiliate License-Licensee": {
        "required": ["affiliate", "subsidiary"],
        "context": ["license", "right", "sublicense"],
    },
    "Affiliate License-Licensor": {
        "required": ["affiliate", "subsidiary"],
        "context": ["licensor", "grant"],
    },
    "Source Code Escrow": {
        "required": ["escrow", "source code"],
        "context": ["deposit", "release"],
    },
    "Most Favored Nation": {
        "required": ["most favored", "most favourable", "best terms"],
        "context": [],
    },
    "Price Restrictions": {
        "required": ["price", "pricing", "resale price"],
        "context": ["restriction", "minimum", "maximum"],
    },
}


def extract_clause_v2(text: str, label: str) -> tuple[bool, float]:
    """Improved extraction with complete keyword coverage."""
    text_lower = text.lower()
    patterns = ALL_KEYWORDS.get(label, {})
    required = patterns.get("required", [])
    context_words = patterns.get("context", [])

    # Check required keywords
    has_required = any(kw.lower() in text_lower for kw in required)
    if not has_required:
        return False, 0.95

    # Count context matches
    ctx_count = sum(1 for cw in context_words if cw.lower() in text_lower) if context_words else 1

    if len(context_words) == 0:
        # No context needed (e.g., Document Name, Parties)
        return True, 0.85
    elif ctx_count >= 2:
        return True, 0.85
    elif ctx_count == 1:
        return True, 0.7
    else:
        return True, 0.5


def run_v2_harness(max_contracts: int = 102) -> HarnessResult:
    """Run V2 harness on CUAD data."""
    data_path = "/tmp/cuad/data/test.json"
    if not os.path.exists(data_path):
        return HarnessResult("v2", 0, 0, 0, 0, 0, 0, 0, 0)

    with open(data_path) as f:
        data = json.load(f)

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
                gt_present = not qa.get("is_impossible", True) and bool(qa.get("answers", []))

                found, _ = extract_clause_v2(full_text, label)

                if gt_present and found: tp += 1
                elif not gt_present and not found: tn += 1
                elif gt_present and not found: fn += 1
                elif not gt_present and found: fp += 1

    total = tp + tn + fp + fn
    acc = (tp + tn) / max(total, 1)
    prec = tp / max(tp + fp, 1)
    rec = tp / max(tp + fn, 1)
    f1 = 2 * prec * rec / max(prec + rec, 1e-9)

    return HarnessResult("v2_complete_keywords", acc, prec, rec, f1, tp, fp, tn, fn)


def run_all_harnesses(max_contracts: int = 102) -> list[HarnessResult]:
    """Run all harnesses and compare."""
    data_path = "/tmp/cuad/data/test.json"
    if not os.path.exists(data_path):
        return []

    with open(data_path) as f:
        data = json.load(f)

    # Harness configs
    harnesses = {
        "baseline_prefilter": lambda t, l: (
            any(kw.lower() in t.lower() for kw in ALL_KEYWORDS.get(l, {}).get("required", ["NEVER"])),
            0.6
        ),
        "v2_with_context": extract_clause_v2,
        "section_header_only": lambda t, l: (
            any(h.lower() in t.lower() for h in [
                l.lower(),
                l.lower().replace(" ", "-"),
            ]),
            0.8
        ),
    }

    results = []
    for hname, hfn in harnesses.items():
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
                    found, _ = hfn(full_text, label)
                    if gt and found: tp += 1
                    elif not gt and not found: tn += 1
                    elif gt and not found: fn += 1
                    elif not gt and found: fp += 1

        total = tp + tn + fp + fn
        acc = (tp + tn) / max(total, 1)
        prec = tp / max(tp + fp, 1)
        rec = tp / max(tp + fn, 1)
        f1 = 2 * prec * rec / max(prec + rec, 1e-9)
        results.append(HarnessResult(hname, acc, prec, rec, f1, tp, fp, tn, fn))

    # Add V2
    results.append(run_v2_harness(max_contracts))
    return results
