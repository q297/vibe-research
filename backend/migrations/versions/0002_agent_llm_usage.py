"""LLM usage log of the agent (role 4), source of the shared daily budget

Columns follow the role 4 spec: day, model, tokens, cost, trace id; role 4 owns changes here

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SCHEMA = "agent"


def upgrade() -> None:
    op.create_table(
        "llm_usage",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("day", sa.Date, nullable=False),
        sa.Column("model", sa.Text, nullable=False),
        sa.Column("tokens_in", sa.Integer, nullable=False),
        sa.Column("tokens_out", sa.Integer, nullable=False),
        sa.Column("cost_rub", sa.Numeric(12, 4), nullable=False),
        sa.Column("trace_id", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_llm_usage_day", "llm_usage", ["day"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_table("llm_usage", schema=SCHEMA)
