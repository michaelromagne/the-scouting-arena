"""Add team_seasons and team_metrics tables

Revision ID: add_team_tables
Revises:
Create Date: 2025-12-19

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_team_tables"
down_revision = "c7f4g5h6i7j8"  # Latest revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create team_seasons table
    op.create_table(
        "team_seasons",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("season_id", sa.Integer(), nullable=True),
        sa.Column("league_id", sa.Integer(), nullable=True),
        sa.Column("games_played", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["league_id"], ["leagues.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["season_id"], ["seasons.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "team_id", "season_id", "league_id", name="uq_team_season_league"
        ),
    )

    # Create team_metrics table
    op.create_table(
        "team_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("team_season_id", sa.Integer(), nullable=False),
        sa.Column("metric_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("percentile", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["metric_id"], ["metric_definitions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["team_season_id"], ["team_seasons.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_season_id", "metric_id", name="uq_teamseason_metric"),
    )


def downgrade() -> None:
    op.drop_table("team_metrics")
    op.drop_table("team_seasons")
