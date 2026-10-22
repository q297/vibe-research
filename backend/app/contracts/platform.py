"""Auth, feedback, metrics and health owned by the BFF (role 5)"""

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from app.contracts.common import Contract
from app.contracts.insights import UserRole


class LoginRequest(Contract):
    username: str = Field(max_length=100)
    password: str = Field(max_length=200)


class Token(Contract):
    access_token: str
    token_type: str = "bearer"


class Me(Contract):
    user_id: str
    display_name: str
    role: UserRole
    client_ids: list[str]
    is_demo_admin: bool = False


class Rating(StrEnum):
    UP = "up"
    DOWN = "down"


class FeedbackRequest(Contract):
    insight_id: str
    rating: Rating
    reason: str | None = Field(default=None, max_length=100)
    comment: str | None = Field(default=None, max_length=2_000)


class Feedback(FeedbackRequest):
    feedback_id: str
    user_id: str
    trace_id: str | None = None
    created_at: datetime


class Metrics(Contract):
    insights_total: int
    feedback_up: int
    feedback_down: int
    self_corrections: int
    avg_tokens_per_insight: float | None = None
    avg_latency_ms: float | None = None


class Budget(Contract):
    tokens_used_today: int
    tokens_limit_today: int | None = None
    cost_rub_today: float | None = None
    exhausted: bool = False


class WarmupRequest(Contract):
    """Precompute insights for demo clients so the live demo spends no budget"""

    client_ids: list[str] | None = Field(default=None, description="All accessible if empty")
    top: int = Field(default=5, ge=1, le=20, description="Top events of each client feed")
    roles: list[UserRole] | None = Field(default=None, description="The user role if empty")
    force: bool = Field(default=False, description="Recompute even fresh cached insights")


class WarmupStatus(Contract):
    running: bool = False
    total: int = 0
    computed: int = 0
    skipped: int = 0
    failed: int = 0
    current: str | None = Field(default=None, description="client_id:event_id:role")
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class Health(Contract):
    status: str
    mock_mode: bool
    offline_mode: bool
    version: str
