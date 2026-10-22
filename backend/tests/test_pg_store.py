"""Postgres round trip; runs only with TEST_DATABASE_URL pointing to a disposable database"""

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app import db
from app.contracts.insights import (
    AgentTrace,
    ChatMessage,
    ChatRole,
    Insight,
    InsightStatus,
    Job,
    JobStatus,
)
from app.contracts.platform import Feedback, Rating
from app.services.repository import PgRepository
from app.services.store import Store

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL is not set")


@pytest.fixture(scope="module")
def migrated():
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", URL)
    command.upgrade(config, "head")
    return URL


@pytest.fixture
async def repo(migrated):
    engine = create_async_engine(db.async_url(migrated))
    async with engine.begin() as conn:
        tables = ", ".join(f"{db.SCHEMA}.{t.name}" for t in db.metadata.sorted_tables)
        await conn.execute(text(f"TRUNCATE {tables}"))
    await engine.dispose()
    repository = PgRepository(migrated)
    yield repository
    await repository.close()


async def test_store_survives_restart(repo):
    now = datetime.now(UTC)
    insight = Insight(
        insight_id="ins-1",
        client_id="c-001",
        event_id="ev-001",
        event_version=2,
        role="cfo",
        status=InsightStatus.READY,
        headline="Ставка",
        trace_id="tr-1",
        created_at=now,
    )
    job = Job(
        job_id="job-1",
        status=JobStatus.DONE,
        client_id="c-001",
        event_id="ev-001",
        role="cfo",
        trace_id="tr-1",
        insight_id="ins-1",
    )
    store = Store(repo)
    store.traces["tr-1"] = AgentTrace(trace_id="tr-1", insight_id="ins-1", total_tokens=42)
    await store.save_insight(insight)
    await store.save_insight(insight.model_copy(update={"headline": "Ставка 14%"}))
    await store.finish_job(job, 1500)
    await store.add_feedback(
        Feedback(
            feedback_id="fb-1",
            insight_id="ins-1",
            rating=Rating.UP,
            user_id="u-demo",
            trace_id="tr-1",
            created_at=now,
        )
    )
    question = ChatMessage(role=ChatRole.USER, content="А если?", created_at=now)
    answer = ChatMessage(role=ChatRole.ASSISTANT, content="Тогда", created_at=now)
    await store.add_chat("u-demo", "ins-1", [question, answer])

    restored = Store(repo)
    await restored.load()
    found = restored.find_insight("c-001", "ev-001", "cfo")
    assert found is not None and found.headline == "Ставка 14%"
    assert restored.traces["tr-1"].total_tokens == 42
    assert restored.job_durations_ms == [1500]
    assert [f.feedback_id for f in restored.feedback] == ["fb-1"]
    assert [m.content for m in restored.chat("u-demo", "ins-1")] == ["А если?", "Тогда"]
