"""SerpApi integration — external fact verification layer.

Uses SerpApi to search the web and verify extracted claims against
real-world sources. This adds a web-verification step that can
confirm or contradict facts before routing to human review.

API: https://serpapi.com/
Requires: SERPAPI_KEY env var
"""

from __future__ import annotations

import os
from typing import Any

import httpx

SERPAPI_BASE_URL = "https://serpapi.com/search.json"


class SerpApiError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(f"SerpApi error {status}: {message}")


async def search_claims(
    claims: list[str],
    api_key: str | None = None,
    num_results: int = 3,
) -> list[dict]:
    """Search the web for each claim and return verification evidence.

    For each claim, returns:
    - search results with titles, snippets, and URLs
    - a confidence score based on result consistency
    - whether the claim appears supported or contradicted
    """
    api_key = api_key or os.environ.get("SERPAPI_KEY", "")
    if not api_key:
        return [{"claim": c, "status": "no_api_key", "results": []} for c in claims]

    results = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for claim in claims:
            try:
                response = await client.get(
                    SERPAPI_BASE_URL,
                    params={
                        "q": claim,
                        "api_key": api_key,
                        "num": num_results,
                        "engine": "google",
                    },
                )

                if response.status_code != 200:
                    results.append({
                        "claim": claim,
                        "status": "error",
                        "error": f"HTTP {response.status_code}",
                        "results": [],
                    })
                    continue

                data = response.json()
                organic = data.get("organic_results", [])

                # Analyze results for support/contradiction
                claim_words = set(claim.lower().split())
                supported = 0
                contradicted = 0
                relevant_results = []

                for r in organic[:num_results]:
                    title = r.get("title", "").lower()
                    snippet = r.get("snippet", "").lower()
                    combined = f"{title} {snippet}"

                    # Simple word overlap scoring
                    overlap = len(claim_words & set(combined.split()))
                    relevance = overlap / max(len(claim_words), 1)

                    # Check for contradiction signals
                    negation_words = {"not", "no", "never", "false", "incorrect", "denied", "refuted", "contradicts"}
                    has_negation = any(w in combined for w in negation_words)

                    if relevance > 0.3:
                        if has_negation:
                            contradicted += 1
                        else:
                            supported += 1
                        relevant_results.append({
                            "title": r.get("title", ""),
                            "snippet": r.get("snippet", ""),
                            "url": r.get("link", ""),
                            "relevance": round(relevance, 2),
                            "has_negation": has_negation,
                        })

                # Determine verification status
                total = supported + contradicted
                if total == 0:
                    status = "unclear"
                    confidence = 0.0
                elif contradicted > supported:
                    status = "contradicted"
                    confidence = contradicted / total
                elif supported > 0:
                    status = "supported"
                    confidence = supported / total
                else:
                    status = "unclear"
                    confidence = 0.0

                results.append({
                    "claim": claim,
                    "status": status,
                    "confidence": round(confidence, 2),
                    "supported_count": supported,
                    "contradicted_count": contradicted,
                    "results": relevant_results,
                })

            except Exception as e:
                results.append({
                    "claim": claim,
                    "status": "error",
                    "error": str(e),
                    "results": [],
                })

    return results


async def verify_entity(
    entity_name: str,
    entity_type: str = "company",
    api_key: str | None = None,
) -> dict:
    """Verify an entity exists and get basic info from web search.

    entity_type: "company", "person", "product", "location"
    """
    queries = {
        "company": f'"{entity_name}" company official site',
        "person": f'"{entity_name}" biography',
        "product": f'"{entity_name}" product specifications',
        "location": f'"{entity_name}" location address',
    }

    query = queries.get(entity_type, f'"{entity_name}"')
    results = await search_claims([query], api_key=api_key, num_results=3)

    if results and results[0]["status"] != "error":
        return {
            "entity": entity_name,
            "type": entity_type,
            "verified": len(results[0].get("results", [])) > 0,
            "sources": [r["url"] for r in results[0].get("results", [])],
            "confidence": results[0].get("confidence", 0),
        }

    return {
        "entity": entity_name,
        "type": entity_type,
        "verified": False,
        "sources": [],
        "confidence": 0,
    }


async def cross_reference_values(
    values: list[dict],
    api_key: str | None = None,
) -> list[dict]:
    """Cross-reference extracted values against web sources.

    Each value dict should have:
    - field: the field name
    - value: the extracted value
    - context: optional context for search
    """
    results = []
    for v in values:
        query = f"{v.get('context', '')} {v['value']}".strip()
        search_results = await search_claims([query], api_key=api_key, num_results=2)

        results.append({
            "field": v["field"],
            "value": v["value"],
            "web_verification": search_results[0] if search_results else None,
        })

    return results


def sync_search_claims(claims: list[str], api_key: str | None = None) -> list[dict]:
    """Synchronous wrapper for search_claims."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(search_claims(claims, api_key))
