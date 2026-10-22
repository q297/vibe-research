"""Insight, agent trace and chat produced by the agent (role 4)"""

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from app.contracts.common import SCHEMA_VERSION, Citation, Claim, Contract, ErrorCode, Provenance


class UserRole(StrEnum):
    CEO = "ceo"
    CFO = "cfo"
    ACCOUNTANT = "accountant"
    TREASURER = "treasurer"


class InsightStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    READY = "ready"
    FAILED = "failed"
    STALE = "stale"


class Direction(StrEnum):
    UP = "up"
    DOWN = "down"
    FLAT = "flat"
    UNKNOWN = "unknown"


class Level(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BankPosition(Contract):
    """Alfa-Bank analytics view (D12); value may be absent for qualitative views"""

    position_id: str
    topic: str
    indicator: str | None = None
    value: float | None = None
    range_low: float | None = None
    range_high: float | None = None
    unit: str | None = None
    horizon: str | None = None
    direction: Direction = Direction.UNKNOWN
    statement: str
    citation: Citation


class ImpactItem(Contract):
    claim: Claim
    severity: Level = Level.MEDIUM
    horizon: str | None = None


class Action(Contract):
    text: str
    provenance: Provenance = Provenance.AI_INFERENCE
    priority: Level = Level.MEDIUM
    product_hint: str | None = Field(default=None, description="Bank product, if relevant")
    is_promo: bool = Field(
        default=False, description="Native bank offer, the UI marks it apart from AI conclusions"
    )


class Insight(Contract):
    schema_version: str = SCHEMA_VERSION
    insight_id: str
    client_id: str
    event_id: str
    event_version: int
    role: UserRole
    status: InsightStatus
    headline: str
    what_happened: list[Claim] = Field(default_factory=list)
    why_it_matters: list[Claim] = Field(default_factory=list)
    risks: list[ImpactItem] = Field(default_factory=list)
    opportunities: list[ImpactItem] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)
    bank_positions: list[BankPosition] = Field(default_factory=list)
    sources: list[Citation] = Field(default_factory=list)
    client_features_used: list[str] = Field(default_factory=list)
    data_gaps: list[str] = Field(
        default_factory=list, description="What the agent could not find or verify"
    )
    scenarios: list[Claim] = Field(
        default_factory=list, description="Factors to watch and questions for further analysis"
    )
    relevance: float | None = Field(default=None, ge=0, le=1)
    confidence: Level | None = None
    critic_passed: bool | None = None
    critic_notes: list[str] = Field(
        default_factory=list, description="What the critic found and what was fixed"
    )
    trace_id: str
    created_at: datetime


class StepKind(StrEnum):
    PLAN = "plan"
    TOOL_CALL = "tool_call"
    DRAFT = "draft"
    CRITIC = "critic"
    RETRY = "retry"
    FINAL = "final"


class StepStatus(StrEnum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


class TraceStep(Contract):
    index: int
    kind: StepKind
    title: str
    detail: str | None = None
    tool: str | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    model: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    duration_ms: int | None = None
    status: StepStatus = StepStatus.OK
    started_at: datetime
    retry_of: int | None = Field(default=None, description="Index of the step being redone")
    cost_rub: float | None = None
    cache_hit: bool = False


class AgentTrace(Contract):
    trace_id: str
    insight_id: str | None = None
    steps: list[TraceStep] = Field(default_factory=list)
    total_tokens: int = 0
    total_cost_rub: float = 0
    retries: int = 0


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class Job(Contract):
    job_id: str
    status: JobStatus
    client_id: str
    event_id: str
    role: UserRole
    trace_id: str
    insight_id: str | None = None
    error: str | None = None
    error_code: ErrorCode | None = None


class RunInsightRequest(Contract):
    role: UserRole | None = Field(default=None, description="Defaults to the current user role")
    force: bool = Field(default=False, description="Ignore cache and recompute")


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(Contract):
    role: ChatRole
    content: str
    provenance: Provenance | None = None
    citations: list[Citation] = Field(default_factory=list)
    created_at: datetime


class ChatRequest(Contract):
    message: str = Field(min_length=1, max_length=2_000)


class ChatResponse(Contract):
    messages: list[ChatMessage]
    trace_id: str
