"""Durable storage behind the in-memory Store: memory only, or Postgres write-through"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app import db
from app.contracts.insights import AgentTrace, ChatMessage, Insight, Job
from app.contracts.platform import Feedback


@dataclass
class Snapshot:
    insights: list[Insight] = field(default_factory=list)
    traces: list[AgentTrace] = field(default_factory=list)
    feedback: list[Feedback] = field(default_factory=list)
    chats: dict[str, list[ChatMessage]] = field(default_factory=dict)
    job_durations_ms: list[int] = field(default_factory=list)


class Repository(Protocol):
    async def load(self) -> Snapshot: ...

    async def save_insight(self, insight: Insight) -> None: ...

    async def save_job_run(self, job: Job, trace: AgentTrace, duration_ms: int) -> None: ...

    async def save_feedback(self, item: Feedback) -> None: ...

    async def save_chat(
        self, user_id: str, insight_id: str, messages: list[ChatMessage]
    ) -> None: ...

    async def close(self) -> None: ...


def chat_key(user_id: str, insight_id: str) -> str:
    return f"{user_id}:{insight_id}"


class MemoryRepository:
    """Nothing survives a restart, used by tests and local runs without Postgres"""

    async def load(self) -> Snapshot:
        return Snapshot()

    async def save_insight(self, insight: Insight) -> None:
        pass

    async def save_job_run(self, job: Job, trace: AgentTrace, duration_ms: int) -> None:
        pass

    async def save_feedback(self, item: Feedback) -> None:
        pass

    async def save_chat(self, user_id: str, insight_id: str, messages: list[ChatMessage]) -> None:
        pass

    async def close(self) -> None:
        pass


class PgRepository:
    def __init__(self, url: str) -> None:
        self._engine: AsyncEngine = create_async_engine(db.async_url(url), pool_pre_ping=True)

    async def load(self) -> Snapshot:
        snapshot = Snapshot()
        async with self._engine.connect() as conn:
            rows = await conn.execute(select(db.insights.c.data).order_by(db.insights.c.created_at))
            snapshot.insights = [Insight.model_validate(r.data) for r in rows]
            rows = await conn.execute(select(db.traces.c.data))
            snapshot.traces = [AgentTrace.model_validate(r.data) for r in rows]
            rows = await conn.execute(select(db.feedback.c.data).order_by(db.feedback.c.created_at))
            snapshot.feedback = [Feedback.model_validate(r.data) for r in rows]
            rows = await conn.execute(
                select(
                    db.chat_messages.c.user_id,
                    db.chat_messages.c.insight_id,
                    db.chat_messages.c.data,
                ).order_by(db.chat_messages.c.id)
            )
            for r in rows:
                snapshot.chats.setdefault(chat_key(r.user_id, r.insight_id), []).append(
                    ChatMessage.model_validate(r.data)
                )
            rows = await conn.execute(select(db.job_runs.c.duration_ms))
            snapshot.job_durations_ms = [r.duration_ms for r in rows]
        return snapshot

    async def save_insight(self, insight: Insight) -> None:
        values = {
            "insight_id": insight.insight_id,
            "client_id": insight.client_id,
            "event_id": insight.event_id,
            "event_version": insight.event_version,
            "role": insight.role.value,
            "data": insight.model_dump(mode="json"),
            "created_at": insight.created_at,
        }
        stmt = insert(db.insights).values(values)
        stmt = stmt.on_conflict_do_update(index_elements=["insight_id"], set_=values)
        async with self._engine.begin() as conn:
            await conn.execute(stmt)

    async def save_job_run(self, job: Job, trace: AgentTrace, duration_ms: int) -> None:
        now = datetime.now(UTC)
        trace_values = {
            "trace_id": trace.trace_id,
            "insight_id": trace.insight_id,
            "data": trace.model_dump(mode="json"),
            "updated_at": now,
        }
        trace_stmt = insert(db.traces).values(trace_values)
        trace_stmt = trace_stmt.on_conflict_do_update(
            index_elements=["trace_id"], set_=trace_values
        )
        run_stmt = insert(db.job_runs).values(
            job_id=job.job_id,
            trace_id=job.trace_id,
            client_id=job.client_id,
            event_id=job.event_id,
            role=job.role.value,
            status=job.status.value,
            error_code=job.error_code.value if job.error_code else None,
            duration_ms=duration_ms,
            finished_at=now,
        )
        async with self._engine.begin() as conn:
            await conn.execute(trace_stmt)
            await conn.execute(run_stmt.on_conflict_do_nothing(index_elements=["job_id"]))

    async def save_feedback(self, item: Feedback) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                insert(db.feedback).values(
                    feedback_id=item.feedback_id,
                    insight_id=item.insight_id,
                    user_id=item.user_id,
                    rating=item.rating.value,
                    data=item.model_dump(mode="json"),
                    created_at=item.created_at,
                )
            )

    async def save_chat(self, user_id: str, insight_id: str, messages: list[ChatMessage]) -> None:
        rows = [
            {
                "user_id": user_id,
                "insight_id": insight_id,
                "data": m.model_dump(mode="json"),
                "created_at": m.created_at,
            }
            for m in messages
        ]
        async with self._engine.begin() as conn:
            await conn.execute(insert(db.chat_messages), rows)

    async def close(self) -> None:
        await self._engine.dispose()
