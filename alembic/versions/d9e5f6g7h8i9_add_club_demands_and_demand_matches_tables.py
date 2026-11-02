"""Add club_demands and demand_matches tables

Revision ID: d9e5f6g7h8i9
Revises: c8d4e5f6g7h8
Create Date: 2026-01-27 20:30:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "d9e5f6g7h8i9"
down_revision = "c8d4e5f6g7h8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create club_demands table
    op.create_table(
        "club_demands",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("club_name", sa.String(), nullable=False),
        sa.Column("club_contact_name", sa.String(), nullable=True),
        sa.Column("club_contact_email", sa.String(), nullable=True),
        sa.Column("created_date", sa.DateTime(), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(), nullable=False, server_default="medium"),
        sa.Column("position", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("age_min", sa.Integer(), nullable=True),
        sa.Column("age_max", sa.Integer(), nullable=True),
        sa.Column(
            "nationality_preferences", postgresql.ARRAY(sa.String()), nullable=True
        ),
        sa.Column("budget_min", sa.Integer(), nullable=True),
        sa.Column("budget_max", sa.Integer(), nullable=True),
        sa.Column(
            "metrics_requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("playing_style_notes", sa.Text(), nullable=True),
        sa.Column("default_season", sa.String(), nullable=False),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('open', 'closed')",
            name="ck_club_demand_status",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'medium', 'high')",
            name="ck_club_demand_priority",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create demand_matches table
    op.create_table(
        "demand_matches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("demand_id", sa.Integer(), nullable=False),
        sa.Column("player_season_id", sa.Integer(), nullable=False),
        sa.Column("match_score", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="suggested"),
        sa.Column("added_date", sa.DateTime(), nullable=False),
        sa.Column("status_updated_date", sa.DateTime(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('suggested', 'proposed', 'interested', 'rejected', 'signed')",
            name="ck_demand_match_status",
        ),
        sa.ForeignKeyConstraint(
            ["demand_id"],
            ["club_demands.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["player_season_id"],
            ["player_seasons.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("demand_id", "player_season_id", name="uq_demand_player"),
    )

    # Create indexes for better query performance
    op.create_index("ix_club_demands_status", "club_demands", ["status"], unique=False)
    op.create_index(
        "ix_club_demands_deadline", "club_demands", ["deadline"], unique=False
    )
    op.create_index(
        "ix_demand_matches_demand_id", "demand_matches", ["demand_id"], unique=False
    )
    op.create_index(
        "ix_demand_matches_status", "demand_matches", ["status"], unique=False
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_demand_matches_status", table_name="demand_matches")
    op.drop_index("ix_demand_matches_demand_id", table_name="demand_matches")
    op.drop_index("ix_club_demands_deadline", table_name="club_demands")
    op.drop_index("ix_club_demands_status", table_name="club_demands")

    # Drop tables
    op.drop_table("demand_matches")
    op.drop_table("club_demands")
