"""BFF tables: insights, traces, job runs, feedback, chat

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = "bff"
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "insights",
        sa.Column("insight_id", sa.Text, primary_key=True),
        sa.Column("client_id", sa.Text, nullable=False),
        sa.Column("event_id", sa.Text, nullable=False),
        sa.Column("event_version", sa.Integer, nullable=False),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("data", JSONB, nullable=False),
        sa.Column("created_at", TS, nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_insights_pair", "insights", ["client_id", "event_id", "role"], schema=SCHEMA
    )
    op.create_table(
        "traces",
        sa.Column("trace_id", sa.Text, primary_key=True),
        sa.Column("insight_id", sa.Text, nullable=True),
        sa.Column("data", JSONB, nullable=False),
        sa.Column("updated_at", TS, nullable=False),
        schema=SCHEMA,
    )
    op.create_table(
        "job_runs",
        sa.Column("job_id", sa.Text, primary_key=True),
        sa.Column("trace_id", sa.Text, nullable=False),
        sa.Column("client_id", sa.Text, nullable=False),
        sa.Column("event_id", sa.Text, nullable=False),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("error_code", sa.Text, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=False),
        sa.Column("finished_at", TS, nullable=False),
        schema=SCHEMA,
    )
    op.create_table(
        "feedback",
        sa.Column("feedback_id", sa.Text, primary_key=True),
        sa.Column("insight_id", sa.Text, nullable=False),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("rating", sa.Text, nullable=False),
        sa.Column("data", JSONB, nullable=False),
        sa.Column("created_at", TS, nullable=False),
        schema=SCHEMA,
    )
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("insight_id", sa.Text, nullable=False),
        sa.Column("data", JSONB, nullable=False),
        sa.Column("created_at", TS, nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_chat_messages_thread",
        "chat_messages",
        ["user_id", "insight_id", "id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    for table in ("chat_messages", "feedback", "job_runs", "traces", "insights"):
        op.drop_table(table, schema=SCHEMA)
