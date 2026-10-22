"""In-process interfaces the BFF expects from roles 2, 3 and 4 (A1)

Real modules implement these protocols and get wired in app/services/registry.py
"""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Protocol

from app.contracts.clients import ClientProfile, ClientSummary, FeedItem
from app.contracts.events import Event, NewsIngestRequest
from app.contracts.insights import BankPosition, ChatMessage, Insight, TraceStep, UserRole
from app.contracts.taxonomy import SensitivityTag


class BudgetExhausted(Exception):
    """Raised by the agent's LLM gateway when the shared daily budget is spent"""


class NewsPort(Protocol):
    """Role 2: events and bank knowledge base"""

    async def list_events(
        self, *, since: datetime | None = None, tags: list[SensitivityTag] | None = None
    ) -> list[Event]: ...

    async def get_event(self, event_id: str) -> Event | None: ...

    async def ingest_text(self, request: NewsIngestRequest, *, trace_id: str) -> Event: ...

    async def bank_positions(self, topics: list[str]) -> list[BankPosition]: ...


class ProfilePort(Protocol):
    """Role 3: client profiles and personalized ranking"""

    async def list_clients(self) -> list[ClientSummary]: ...

    async def get_profile(self, client_id: str) -> ClientProfile | None: ...

    async def rank(self, profile: ClientProfile, events: list[Event]) -> list[FeedItem]: ...


class AgentPort(Protocol):
    """Role 4: insight agent, yields trace steps as they happen and the insight last

    Failures come as a step with status=error and an Insight with status=failed,
    only BudgetExhausted is raised
    """

    def run(
        self, *, profile: ClientProfile, event: Event, role: UserRole, trace_id: str
    ) -> AsyncIterator[TraceStep | Insight]: ...

    async def chat(
        self, *, insight: Insight, history: list[ChatMessage], message: str, trace_id: str
    ) -> ChatMessage: ...
