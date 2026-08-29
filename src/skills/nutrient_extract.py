"""Nutrient DWS extraction skill with full citation parsing.

Extracts structured fields from documents using Nutrient DWS API.
Returns not just values but full citation metadata: confidence,
match labels, bounding boxes, confidence components.

This is the core skill that the agent brain dispatches to.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

import requests


NUTRIENT_BASE = "https://api.nutrient.io"
EXTRACT_URL = f"{NUTRIENT_BASE}/extraction/extract"
PARSE_URL = f"{NUTRIENT_BASE}/extraction/parse"


# ============================================================
# Citation data model
# ============================================================

@dataclass
class Citation:
    """Full citation metadata for a single extracted field."""
    field: str
    value: Any
    confidence: float | None = None
    match: str | None = None  # id_match, fuzzy_match, not_found, etc.
    page: int | None = None
    bbox: dict | None = None  # {x, y, width, height}
    confidence_components: dict | None = None  # probabilityScore, marginScore, etc.
    recognition_score: float | None = None  # OCR confidence for scans

    @property
    def is_grounded(self) -> bool:
        """True if the value was found in the document (not hallucinated)."""
        return self.match not in ("not_found", None)

    @property
    def is_exact(self) -> bool:
        """True if matched exactly to source text."""
        return self.match in ("id_match", "id_match_multiblock")

    @property
    def needs_review(self) -> bool:
        """True if this field should go to human review."""
        if self.match in ("fuzzy_match", "not_found"):
            return True
        if self.confidence is not None and self.confidence < 0.7:
            return True
        return False

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "value": self.value,
            "confidence": self.confidence,
            "match": self.match,
            "page": self.page,
            "bbox": self.bbox,
            "needs_review": self.needs_review,
        }


# ============================================================
# Extraction result
# ============================================================

@dataclass
class ExtractionResult:
    """Full result from Nutrient extraction including all citations."""
    doc_id: str
    schema_name: str
    extracted: dict  # field -> value
    citations: dict  # field -> Citation
    pages: list[dict] = field(default_factory=list)
    processing_time_ms: float = 0
    credits_used: float = 0
    raw_response: dict = field(default_factory=dict)

    @property
    def fields_needing_review(self) -> list[str]:
        """Fields that should go to human review."""
        return [f for f, c in self.citations.items() if c.needs_review]

    @property
    def fields_auto_approvable(self) -> list[str]:
        """Fields with high confidence and exact match."""
        return [f for f, c in self.citations.items()
                if c.is_exact and c.confidence is not None and c.confidence >= 0.9]

    @property
    def avg_confidence(self) -> float:
        """Average confidence across all cited fields."""
        confs = [c.confidence for c in self.citations.values() if c.confidence is not None]
        return sum(confs) / len(confs) if confs else 0.0

    @property
    def grounding_rate(self) -> float:
        """Fraction of fields that are grounded (not hallucinated)."""
        if not self.citations:
            return 0.0
        grounded = sum(1 for c in self.citations.values() if c.is_grounded)
        return grounded / len(self.citations)

    def summary(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "schema": self.schema_name,
            "fields": len(self.extracted),
            "avg_confidence": round(self.avg_confidence, 3),
            "grounding_rate": round(self.grounding_rate, 3),
            "needs_review": self.fields_needing_review,
            "auto_approvable": self.fields_auto_approvable,
            "credits": self.credits_used,
            "latency_ms": round(self.processing_time_ms, 1),
        }


# ============================================================
# Nutrient extraction skill
# ============================================================

class NutrientExtractSkill:
    """Nutrient DWS extraction with full citation parsing.

    Usage:
        skill = NutrientExtractSkill(api_key="pdf_live_...")
        result = skill.extract(pdf_path, schema, mode="understand")
        print(result.summary())
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("NUTRIENT_API_KEY", "")

    def extract(
        self,
        pdf_path: str,
        schema: dict,
        mode: str = "understand",
        instructions: str = "",
        doc_id: str = "unknown",
        schema_name: str = "default",
    ) -> ExtractionResult:
        """Extract fields from a PDF with full citations.

        Args:
            pdf_path: Path to PDF file
            schema: JSON Schema for extraction
            mode: text/structure/understand/agentic
            instructions: Free-text guidance for extraction model
            doc_id: Document identifier
            schema_name: Schema name for tracking

        Returns:
            ExtractionResult with values, citations, and metadata
        """
        if not self.api_key:
            raise ValueError("NUTRIENT_API_KEY not set")

        start = time.time()

        outer_instructions = {
            "schema": schema,
            "parseConfig": {"mode": mode},
            "instructions": instructions,
            "options": {"includeCitations": True},
        }

        with open(pdf_path, "rb") as f:
            response = requests.post(
                EXTRACT_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": (os.path.basename(pdf_path), f, "application/pdf")},
                data={"instructions": json.dumps(outer_instructions)},
                timeout=60,
            )

        elapsed_ms = (time.time() - start) * 1000

        if response.status_code != 200:
            error = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"errorMessage": response.text}
            raise NutrientAPIError(response.status_code, error)

        result = response.json()
        output = result.get("output", {})
        data = output.get("data", {})
        metadata = output.get("metadata", {})
        pages = output.get("pages", [])
        usage = result.get("usage", {}).get("data_extraction_credits", {})

        # Parse citations
        citations = self._parse_citations(data, metadata)

        return ExtractionResult(
            doc_id=doc_id,
            schema_name=schema_name,
            extracted=data,
            citations=citations,
            pages=pages,
            processing_time_ms=elapsed_ms,
            credits_used=usage.get("cost", 0),
            raw_response=result,
        )

    def _parse_citations(self, data: dict, metadata: dict) -> dict[str, Citation]:
        """Parse Nutrient citation metadata into Citation objects."""
        citations = {}
        self._walk_citations(data, metadata, "", citations)
        return citations

    def _walk_citations(self, data: Any, metadata: Any, path: str, result: dict):
        """Recursively walk data/metadata structures to extract citations."""
        if isinstance(data, dict):
            for key, value in data.items():
                child_path = f"{path}.{key}" if path else key
                child_meta = metadata.get(key, {}) if isinstance(metadata, dict) else {}
                self._walk_citations(value, child_meta, child_path, result)
            return

        if isinstance(data, list):
            for i, value in enumerate(data):
                child_path = f"{path}[{i}]"
                child_meta = metadata[i] if isinstance(metadata, list) and i < len(metadata) else {}
                self._walk_citations(value, child_meta, child_path, result)
            return

        # Leaf node — create Citation
        citation_data = metadata if isinstance(metadata, dict) else {}
        citation = Citation(
            field=path,
            value=data,
            confidence=citation_data.get("confidence"),
            match=citation_data.get("match"),
            page=citation_data.get("pageNumber"),
            bbox=citation_data.get("bbox"),
            confidence_components=citation_data.get("confidenceComponents"),
            recognition_score=citation_data.get("recognitionScore"),
        )
        result[path] = citation


class NutrientAPIError(Exception):
    def __init__(self, status: int, error: dict):
        self.status = status
        self.error = error
        super().__init__(f"Nutrient API {status}: {error.get('errorMessage', 'unknown')}")


# ============================================================
# Parse skill (full document structure)
# ============================================================

class NutrientParseSkill:
    """Nutrient DWS parse — full document structure."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("NUTRIENT_API_KEY", "")

    def parse(
        self,
        pdf_path: str,
        mode: str = "understand",
        output_format: str = "spatial",
    ) -> dict:
        """Parse document into spatial elements."""
        if not self.api_key:
            raise ValueError("NUTRIENT_API_KEY not set")

        instructions = {"mode": mode, "output": {"format": output_format}}

        with open(pdf_path, "rb") as f:
            response = requests.post(
                PARSE_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": (os.path.basename(pdf_path), f, "application/pdf")},
                data={"instructions": json.dumps(instructions)},
                timeout=60,
            )

        if response.status_code != 200:
            raise NutrientAPIError(response.status_code, response.json())

        return response.json()


# ============================================================
# OCR skill
# ============================================================

class NutrientOCRSkill:
    """Nutrient DWS OCR — make scans searchable."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("NUTRIENT_API_KEY", "")

    def ocr(self, pdf_path: str, language: str = "english") -> dict:
        """OCR a scanned PDF and return searchable PDF."""
        if not self.api_key:
            raise ValueError("NUTRIENT_API_KEY not set")

        with open(pdf_path, "rb") as f:
            response = requests.post(
                f"{NUTRIENT_BASE}/processor/ocr",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": (os.path.basename(pdf_path), f, "application/pdf")},
                data={"data": json.dumps({"language": language})},
                timeout=120,
            )

        if response.status_code != 200:
            raise NutrientAPIError(response.status_code, response.json())

        return response.content  # Returns PDF bytes


# ============================================================
# Redact skill
# ============================================================

class NutrientRedactSkill:
    """Nutrient DWS redaction — remove PII."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("NUTRIENT_API_KEY", "")

    def redact_text(self, pdf_path: str, patterns: list[str]) -> bytes:
        """Redact text patterns from a PDF."""
        if not self.api_key:
            raise ValueError("NUTRIENT_API_KEY not set")

        all_redactions = []
        for pattern in patterns:
            all_redactions.append({
                "strategy": "text",
                "strategyOptions": {"text": pattern, "caseSensitive": False},
                "redactionState": "apply",
            })

        with open(pdf_path, "rb") as f:
            response = requests.post(
                f"{NUTRIENT_BASE}/processor/redact",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": (os.path.basename(pdf_path), f, "application/pdf")},
                data={"data": json.dumps(all_redactions[0])},  # one at a time
                timeout=120,
            )

        if response.status_code != 200:
            raise NutrientAPIError(response.status_code, response.json())

        return response.content  # Returns redacted PDF bytes


# ============================================================
# Generate PDF skill
# ============================================================

class NutrientGenerateSkill:
    """Nutrient DWS PDF generation from HTML."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("NUTRIENT_API_KEY", "")

    def generate_from_html(self, html_path: str) -> bytes:
        """Generate PDF from HTML file."""
        if not self.api_key:
            raise ValueError("NUTRIENT_API_KEY not set")

        with open(html_path, "rb") as f:
            response = requests.post(
                f"{NUTRIENT_BASE}/processor/generate_pdf",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"html": (os.path.basename(html_path), f, "text/html")},
                timeout=120,
            )

        if response.status_code != 200:
            raise NutrientAPIError(response.status_code, response.json())

        return response.content  # Returns PDF bytes

    def generate_from_string(self, html: str) -> bytes:
        """Generate PDF from HTML string."""
        if not self.api_key:
            raise ValueError("NUTRIENT_API_KEY not set")

        response = requests.post(
            f"{NUTRIENT_BASE}/processor/generate_pdf",
            headers={"Authorization": f"Bearer {self.api_key}"},
            files={"html": ("doc.html", html.encode(), "text/html")},
            timeout=120,
        )

        if response.status_code != 200:
            raise NutrientAPIError(response.status_code, response.json())

        return response.content
