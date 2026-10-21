"""Shared building blocks of the public contract

Draft v0.1: field names follow the decisions proposed in the ingestion contract doc
(A2 event-centric, D1 ids, D6 provenance, D7 citations, D8 unknown values, D11 versioning)
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "0.1.0"


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False)


class Provenance(StrEnum):
    """Where a statement comes from (D6), drives the colored badges in the UI"""

    SOURCE_FACT = "source_fact"
    BANK_POSITION = "bank_position"
    AI_INFERENCE = "ai_inference"


class CitationKind(StrEnum):
    ARTICLE = "article"
    BANK_DOC = "bank_doc"
    CLIENT_DATA = "client_data"
    USER_INPUT = "user_input"


class Citation(Contract):
    """Link to a primary source (D7); snippets stay short because of copyright (H2)"""

    kind: CitationKind
    source_id: str = Field(description="Article id, bank document chunk id or client feature key")
    title: str
    url: str | None = None
    page: int | None = Field(default=None, description="Page in a bank PDF")
    snippet: str | None = Field(default=None, max_length=400)
    published_at: datetime | None = None


class Claim(Contract):
    """Single statement with its provenance; every block of an insight is a list of claims"""

    text: str
    provenance: Provenance
    citations: list[Citation] = Field(default_factory=list)


class ErrorCode(StrEnum):
    BAD_REQUEST = "bad_request"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    BUDGET_EXHAUSTED = "budget_exhausted"
    UPSTREAM_FAILED = "upstream_failed"
    INTERNAL = "internal"


class ApiError(Contract):
    """Single error shape for every endpoint (E5)"""

    code: ErrorCode
    message: str
    trace_id: str | None = None
    details: dict | None = None


class Page[T](Contract):
    items: list[T]
    next_cursor: str | None = None
