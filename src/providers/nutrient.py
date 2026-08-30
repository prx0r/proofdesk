"""Real Nutrient DWS Data Extraction API integration.

API: POST https://api.nutrient.io/extraction/extract
Docs: https://www.nutrient.io/guides/dws-data-extraction/extract/

Requires: NUTRIENT_API_KEY env var (starts with pdf_live_ or pdf_test_)
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx

from ..models.domain import Document, ExtractedFact, _hash, _id


NUTRIENT_BASE_URL = "https://api.nutrient.io"
NUTRIENT_EXTRACT_URL = f"{NUTRIENT_BASE_URL}/extraction/extract"
NUTRIENT_PARSE_URL = f"{NUTRIENT_BASE_URL}/extraction/parse"

# Schema for procurement document extraction
PROCUREMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "vendor_legal_name": {
            "type": "string",
            "description": "Legal name of the vendor/company",
        },
        "requested_spend": {
            "type": "number",
            "description": "Total requested spend amount in USD",
        },
        "quote_total": {
            "type": "number",
            "description": "Total quote amount in USD",
        },
        "platform_price": {
            "type": "number",
            "description": "Platform license price in USD",
        },
        "support_price": {
            "type": "number",
            "description": "Support services price in USD",
        },
        "contract_start_date": {
            "type": "string",
            "description": "Contract start date in ISO format",
        },
        "insurance_expiry_date": {
            "type": "string",
            "description": "Insurance policy expiry date in ISO format",
        },
        "required_coverage_until": {
            "type": "string",
            "description": "Required coverage end date in ISO format",
        },
        "data_retention_days": {
            "type": "number",
            "description": "Data retention period in days",
        },
        "subprocessor_count": {
            "type": "number",
            "description": "Number of subprocessors",
        },
        "encryption_at_rest": {
            "type": "boolean",
            "description": "Whether encryption at rest is enabled",
        },
    },
    "required": ["vendor_legal_name"],
}


class NutrientError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(f"Nutrient API error {status}: {message}")


async def extract_from_document(
    document: Document,
    api_key: str | None = None,
    mode: str = "understand",
    include_citations: bool = True,
) -> list[ExtractedFact]:
    """Call Nutrient DWS /extraction/extract on a document.

    Returns extracted facts with source grounding (page, bbox, confidence).
    """
    api_key = api_key or os.environ.get("NUTRIENT_API_KEY", "")
    if not api_key:
        raise NutrientError(401, "NUTRIENT_API_KEY not set")

    instructions = {
        "schema": PROCUREMENT_SCHEMA,
        "parseConfig": {"mode": mode},
        "options": {"includeCitations": include_citations},
        "instructions": (
            "Extract all procurement-related fields. "
            "For dates, use ISO format (YYYY-MM-DD). "
            "For currency, use numeric values without symbols."
        ),
    }

    from . import trace as vtrace
    t0 = time.time()

    facts = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Upload document bytes — prefer raw_bytes (actual PDF), fall back to raw_text
        if document.raw_bytes:
            file_bytes = document.raw_bytes
        elif document.raw_text:
            file_bytes = document.raw_text.encode("utf-8")
        else:
            file_bytes = b""

        response = await client.post(
            NUTRIENT_EXTRACT_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (document.filename, file_bytes, document.content_type or "application/pdf")},
            data={"instructions": json.dumps(instructions)},
        )

        vtrace.record(
            document.case_id, "Nutrient DWS", f"extract[{document.filename}]",
            "POST", NUTRIENT_EXTRACT_URL,
            request_summary={
                "file": document.filename,
                "bytes": len(file_bytes),
                "schema_fields": list(PROCUREMENT_SCHEMA["properties"].keys()),
                "mode": mode,
                "auth": "Bearer pdf_live_…",
            },
            status=response.status_code,
            response_summary=(response.json().get("output", {}).get("data")
                              if response.status_code == 200 else response.text[:300]),
            duration_ms=(time.time() - t0) * 1000,
        )

        if response.status_code != 200:
            raise NutrientError(response.status_code, response.text)

        result = response.json()
        output = result.get("output", {})
        data = output.get("data", {})
        metadata = output.get("metadata", {})

        # Map schema fields to our fact model
        field_mapping = {
            "vendor_legal_name": "vendor.legal_name",
            "requested_spend": "procurement.requested_spend",
            "quote_total": "quote.total",
            "platform_price": "quote.platform_price",
            "support_price": "quote.support_price",
            "contract_start_date": "procurement.contract_start",
            "insurance_expiry_date": "insurance.expiry_date",
            "required_coverage_until": "procurement.required_coverage_until",
            "data_retention_days": "security.data_retention_days",
            "subprocessor_count": "security.subprocessors",
            "encryption_at_rest": "security.encryption_at_rest",
        }

        for schema_field, fact_field in field_mapping.items():
            value = data.get(schema_field)
            if value is None:
                continue

            # Extract citation metadata
            cite = metadata.get(schema_field, {})
            page = cite.get("pageNumber", 1) if cite else 1
            bbox = cite.get("bbox", {}) if cite else {}
            confidence = cite.get("confidence") if cite and cite.get("confidence") is not None else None

            raw_value = str(value)
            normalized = raw_value

            # Normalize currency
            if isinstance(value, (int, float)) and ("price" in fact_field or "spend" in fact_field or "total" in fact_field):
                normalized = str(value)
                raw_value = f"${value:,.0f}"

            # Normalize boolean
            if isinstance(value, bool):
                normalized = str(value).lower()

            facts.append(ExtractedFact(
                case_id=document.case_id,
                doc_id=document.doc_id,
                field_name=fact_field,
                value_raw=raw_value,
                value_normalized=normalized,
                source_page=page,
                bounding_box=[bbox.get("x", 0), bbox.get("y", 0),
                              bbox.get("x", 0) + bbox.get("width", 0),
                              bbox.get("y", 0) + bbox.get("height", 0)] if bbox else [],
                extractor="nutrient_dws",
                confidence=confidence,
                content_hash=_hash({"field": fact_field, "value": normalized}),
            ))

    return facts


async def parse_document(
    document: Document,
    api_key: str | None = None,
    mode: str = "understand",
    output_format: str = "spatial",
) -> dict:
    """Call Nutrient DWS /extraction/parse for full document structure.

    Returns spatial elements with bounding boxes or Markdown.
    """
    api_key = api_key or os.environ.get("NUTRIENT_API_KEY", "")
    if not api_key:
        raise NutrientError(401, "NUTRIENT_API_KEY not set")

    instructions = {
        "mode": mode,
        "output": {"format": output_format},
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        if document.raw_bytes:
            file_bytes = document.raw_bytes
        elif document.raw_text:
            file_bytes = document.raw_text.encode("utf-8")
        else:
            file_bytes = b""

        response = await client.post(
            NUTRIENT_PARSE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (document.filename, file_bytes, document.content_type or "application/pdf")},
            data={"instructions": json.dumps(instructions)},
        )

        if response.status_code != 200:
            raise NutrientError(response.status_code, response.text)

        return response.json()


def extract_from_document_sync(
    document: Document,
    api_key: str | None = None,
    mode: str = "understand",
    include_citations: bool = True,
) -> list[ExtractedFact]:
    """Synchronous wrapper for extract_from_document."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(
        extract_from_document(document, api_key, mode, include_citations)
    )
