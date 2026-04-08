"""Initial AML schema

Revision ID: 001
Revises:
Create Date: 2026-04-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Projects
    op.create_table(
        "projects",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("config", sa.JSON(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Modules
    op.create_table(
        "modules",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("project_id", sa.String(50), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("module_type", sa.String(50), nullable=False),
        sa.Column("config", sa.JSON(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Episodes
    op.create_table(
        "episodes",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("module_id", sa.String(100), sa.ForeignKey("modules.id"), nullable=False),
        sa.Column("action", sa.String(200), nullable=False),
        sa.Column("input_data", sa.JSON(), nullable=False),
        sa.Column("output_data", sa.JSON(), nullable=False),
        sa.Column("input_embedding", Vector(1536)),
        sa.Column("metadata", sa.JSON(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_episodes_module", "episodes", ["module_id", sa.text("created_at DESC")])

    # Feedback
    op.create_table(
        "feedback",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("episode_id", sa.UUID(), sa.ForeignKey("episodes.id"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("feedback_type", sa.String(50), nullable=False),
        sa.Column("source", sa.String(200)),
        sa.Column("details", sa.JSON(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_feedback_episode", "feedback", ["episode_id"])

    # Rules
    op.create_table(
        "rules",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("module_id", sa.String(100), sa.ForeignKey("modules.id"), nullable=False),
        sa.Column("scope", sa.String(20), server_default="module"),
        sa.Column("rule_text", sa.Text(), nullable=False),
        sa.Column("rule_structured", sa.JSON()),
        sa.Column("rule_embedding", Vector(1536)),
        sa.Column("confidence", sa.Float(), server_default="0.5"),
        sa.Column("evidence_count", sa.Integer(), server_default="0"),
        sa.Column("tags", sa.ARRAY(sa.String(50)), server_default="{}"),
        sa.Column("active", sa.Boolean(), server_default="true"),
        sa.Column("parent_rule_id", sa.UUID(), sa.ForeignKey("rules.id")),
        sa.Column("source_project", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_confirmed_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "idx_rules_module_active", "rules", ["module_id"],
        postgresql_where=sa.text("active = true"),
    )
    op.create_index(
        "idx_rules_scope", "rules", ["scope"],
        postgresql_where=sa.text("active = true"),
    )

    # Extraction runs
    op.create_table(
        "extraction_runs",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("module_id", sa.String(100)),
        sa.Column("episodes_analyzed", sa.Integer(), server_default="0"),
        sa.Column("rules_created", sa.Integer(), server_default="0"),
        sa.Column("rules_updated", sa.Integer(), server_default="0"),
        sa.Column("rules_deactivated", sa.Integer(), server_default="0"),
        sa.Column("llm_model", sa.String(100)),
        sa.Column("llm_tokens_used", sa.Integer(), server_default="0"),
        sa.Column("duration_ms", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("extraction_runs")
    op.drop_table("rules")
    op.drop_table("feedback")
    op.drop_table("episodes")
    op.drop_table("modules")
    op.drop_table("projects")
    op.execute("DROP EXTENSION IF EXISTS vector")
