"""Core data models for ProofDesk — evidence-gated document execution."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


def _id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def _hash(data: Any) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()[:16]}"


# --- Enums ---

class FactStatus(str, Enum):
    EXTRACTED = "EXTRACTED"
    CONFIRMED = "CONFIRMED"
    DISPUTED = "DISPUTED"
    RESOLVED = "RESOLVED"


class AssertionResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class ExceptionSeverity(str, Enum):
    BLOCKER = "BLOCKER"
    WARNING = "WARNING"
    INFO = "INFO"


class ResolutionDecision(str, Enum):
    ACCEPT = "ACCEPT"
    CONDITIONAL_ACCEPT = "CONDITIONAL_ACCEPT"
    REJECT = "REJECT"
    CORRECTED = "CORRECTED"


class CaseState(str, Enum):
    RECEIVED = "RECEIVED"
    INGESTED = "INGESTED"
    EXTRACTED = "EXTRACTED"
    RECONCILED = "RECONCILED"
    CHECKED = "CHECKED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    RESOLVED = "RESOLVED"
    APPROVABLE = "APPROVABLE"
    APPROVED = "APPROVED"
    GENERATED = "GENERATED"
    PREPARED = "PREPARED"
    SIGNATURE_AUTHORIZED = "SIGNATURE_AUTHORIZED"
    SIGNATURE_REQUESTED = "SIGNATURE_REQUESTED"
    SIGNED = "SIGNED"
    ARCHIVED = "ARCHIVED"


FORBIDDEN_TRANSITIONS = {
    (CaseState.REVIEW_REQUIRED, CaseState.GENERATED),
    (CaseState.CHECKED, CaseState.SIGNATURE_REQUESTED),
    (CaseState.GENERATED, CaseState.SIGNATURE_REQUESTED),
}


# --- Core Models ---

@dataclass
class Document:
    doc_id: str = field(default_factory=lambda: _id("doc_"))
    case_id: str = ""
    filename: str = ""
    content_type: str = ""
    content_hash: str = ""
    raw_text: str = ""
    raw_bytes: bytes = b""  # Actual PDF/image bytes for Nutrient API
    metadata: dict = field(default_factory=dict)


@dataclass
class ExtractedFact:
    fact_id: str = field(default_factory=lambda: _id("fact_"))
    case_id: str = ""
    doc_id: str = ""
    field_name: str = ""
    value_raw: str = ""
    value_normalized: str = ""
    source_page: int = 0
    bounding_box: list[float] = field(default_factory=list)
    extractor: str = "nutrient_dws"
    confidence: float = 0.0
    content_hash: str = ""
    status: FactStatus = FactStatus.EXTRACTED
    metadata: dict = field(default_factory=dict)

    def to_public(self) -> dict:
        return {
            "fact_id": self.fact_id,
            "field": self.field_name,
            "value_raw": self.value_raw,
            "value_normalized": self.value_normalized,
            "doc_id": self.doc_id,
            "page": self.source_page,
            "confidence": self.confidence,
            "status": self.status.value,
        }


@dataclass
class Assertion:
    assertion_id: str = field(default_factory=lambda: _id("assert_"))
    case_id: str = ""
    predicate: str = ""
    inputs: list[str] = field(default_factory=list)
    result: AssertionResult = AssertionResult.UNKNOWN
    method: str = "deterministic"
    rule_version: str = ""
    detail: str = ""
    severity: ExceptionSeverity = ExceptionSeverity.BLOCKER

    def to_dict(self) -> dict:
        return {
            "assertion_id": self.assertion_id,
            "predicate": self.predicate,
            "result": self.result.value,
            "method": self.method,
            "rule_version": self.rule_version,
            "detail": self.detail,
            "severity": self.severity.value,
        }


@dataclass
class Resolution:
    resolution_id: str = field(default_factory=lambda: _id("res_"))
    assertion_id: str = ""
    decision: ResolutionDecision = ResolutionDecision.ACCEPT
    reason: str = ""
    actor_id: str = "user_demo"
    evidence_refs: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class StructuredRecord:
    record_id: str = field(default_factory=lambda: _id("rec_"))
    case_id: str = ""
    revision: int = 1
    facts: list[dict] = field(default_factory=list)
    assertions: list[dict] = field(default_factory=list)
    resolutions: list[dict] = field(default_factory=list)
    content_hash: str = ""
    approved_by: str | None = None
    approved_at: float | None = None

    def compute_hash(self) -> str:
        data = {
            "facts": self.facts,
            "assertions": self.assertions,
            "resolutions": self.resolutions,
            "revision": self.revision,
        }
        self.content_hash = _hash(data)
        return self.content_hash


@dataclass
class GeneratedArtifact:
    artifact_id: str = field(default_factory=lambda: _id("art_"))
    case_id: str = ""
    record_id: str = ""
    record_hash: str = ""
    template_id: str = ""
    template_version: str = ""
    output_path: str = ""
    content_hash: str = ""
    provider_job_id: str = ""
    generated_at: float = field(default_factory=time.time)


@dataclass
class SignatureRequest:
    request_id: str = field(default_factory=lambda: _id("sig_"))
    case_id: str = ""
    artifact_id: str = ""
    artifact_hash: str = ""
    approval_id: str = ""
    signer: str = ""
    status: str = "PENDING"
    foxit_request_id: str = ""
    signed_at: float | None = None


@dataclass
class AuditEvent:
    event_id: str = field(default_factory=lambda: _id("evt_"))
    case_id: str = ""
    event_type: str = ""
    actor: str = "system"
    from_state: str = ""
    to_state: str = ""
    detail: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    content_hash: str = ""

    def compute_hash(self, prev_hash: str = "") -> str:
        data = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "detail": self.detail,
            "prev_hash": prev_hash,
        }
        self.content_hash = _hash(data)
        return self.content_hash


@dataclass
class Case:
    case_id: str = field(default_factory=lambda: _id("case_"))
    prompt: str = ""
    state: CaseState = CaseState.RECEIVED
    documents: list[Document] = field(default_factory=list)
    facts: list[ExtractedFact] = field(default_factory=list)
    assertions: list[Assertion] = field(default_factory=list)
    resolutions: list[Resolution] = field(default_factory=list)
    structured_record: StructuredRecord | None = None
    generated_artifact: GeneratedArtifact | None = None
    signature_request: SignatureRequest | None = None
    audit_events: list[AuditEvent] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @property
    def blocking_exceptions(self) -> int:
        return sum(
            1 for a in self.assertions
            if a.result == AssertionResult.FAIL and a.severity == ExceptionSeverity.BLOCKER
        )

    @property
    def unresolved_blockers(self) -> int:
        return sum(
            1 for a in self.assertions
            if a.result == AssertionResult.FAIL
            and a.severity == ExceptionSeverity.BLOCKER
            and not any(
                r.assertion_id == a.assertion_id
                for r in self.resolutions
                if r.decision in (ResolutionDecision.ACCEPT, ResolutionDecision.CONDITIONAL_ACCEPT)
            )
        )

    @property
    def human_approval(self) -> Resolution | None:
        for r in reversed(self.resolutions):
            if r.decision in (ResolutionDecision.ACCEPT, ResolutionDecision.CONDITIONAL_ACCEPT):
                return r
        return None
