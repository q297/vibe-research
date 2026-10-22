"""Tables of the BFF schema; migrations in migrations/ must mirror them"""

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Identity,
    Index,
    Integer,
    MetaData,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB

SCHEMA = "bff"

metadata = MetaData(schema=SCHEMA)

# Documents are stored as JSONB in contract shape, key columns are copied out for lookups
insights = Table(
    "insights",
    metadata,
    Column("insight_id", Text, primary_key=True),
    Column("client_id", Text, nullable=False),
    Column("event_id", Text, nullable=False),
    Column("event_version", Integer, nullable=False),
    Column("role", Text, nullable=False),
    Column("data", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Index("ix_insights_pair", "client_id", "event_id", "role"),
)

traces = Table(
    "traces",
    metadata,
    Column("trace_id", Text, primary_key=True),
    Column("insight_id", Text, nullable=True),
    Column("data", JSONB, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

job_runs = Table(
    "job_runs",
    metadata,
    Column("job_id", Text, primary_key=True),
    Column("trace_id", Text, nullable=False),
    Column("client_id", Text, nullable=False),
    Column("event_id", Text, nullable=False),
    Column("role", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("error_code", Text, nullable=True),
    Column("duration_ms", Integer, nullable=False),
    Column("finished_at", DateTime(timezone=True), nullable=False),
)

feedback = Table(
    "feedback",
    metadata,
    Column("feedback_id", Text, primary_key=True),
    Column("insight_id", Text, nullable=False),
    Column("user_id", Text, nullable=False),
    Column("rating", Text, nullable=False),
    Column("data", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

chat_messages = Table(
    "chat_messages",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("user_id", Text, nullable=False),
    Column("insight_id", Text, nullable=False),
    Column("data", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Index("ix_chat_messages_thread", "user_id", "insight_id", "id"),
)


def async_url(url: str) -> str:
    """Compose passes a plain postgresql:// URL, SQLAlchemy needs the asyncpg driver"""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url.removeprefix(prefix)
    return url
