"""Drop players table and merge attributes into player_seasons

This migration removes the separate players table and puts all player
identity attributes directly into player_seasons. This simplifies the
schema and avoids the issue where players with the same name (like Vitinha
from PSG vs Vitinha from Genoa) would share the same player record.

Revision ID: c8d4e5f6g7h8
Revises: a5f2e8c1d390
Create Date: 2024-12-18 16:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c8d4e5f6g7h8"
down_revision = "a5f2e8c1d390"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Add new columns to player_seasons
    op.add_column(
        "player_seasons", sa.Column("player_name", sa.String(), nullable=True)
    )
    op.add_column(
        "player_seasons", sa.Column("nationality", sa.String(), nullable=True)
    )
    op.add_column("player_seasons", sa.Column("born_year", sa.Integer(), nullable=True))

    # Step 2: Migrate data from players to player_seasons
    op.execute("""
        UPDATE player_seasons ps
        SET
            player_name = p.name,
            nationality = p.nationality
        FROM players p
        WHERE ps.player_id = p.id
    """)

    # Step 3: Make player_name NOT NULL after data migration
    op.alter_column("player_seasons", "player_name", nullable=False)

    # Step 4: Update player_similarities to reference player_seasons instead of players
    # Add new columns for player_season references
    op.add_column(
        "player_similarities",
        sa.Column("player_season_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "player_similarities",
        sa.Column("similar_player_season_id", sa.Integer(), nullable=True),
    )

    # Step 5: Migrate player_similarities data - map player_id to a player_season_id
    # We pick an arbitrary player_season for each player (the one with max minutes)
    op.execute("""
        UPDATE player_similarities sim
        SET player_season_id = ps.id
        FROM (
            SELECT DISTINCT ON (player_id) id, player_id
            FROM player_seasons
            ORDER BY player_id, minutes DESC NULLS LAST, id
        ) ps
        WHERE sim.player_id = ps.player_id
    """)

    op.execute("""
        UPDATE player_similarities sim
        SET similar_player_season_id = ps.id
        FROM (
            SELECT DISTINCT ON (player_id) id, player_id
            FROM player_seasons
            ORDER BY player_id, minutes DESC NULLS LAST, id
        ) ps
        WHERE sim.similar_player_id = ps.player_id
    """)

    # Step 6: Drop old constraints and columns from player_similarities
    op.drop_constraint("uq_player_similarity", "player_similarities", type_="unique")
    op.drop_constraint("ck_different_players", "player_similarities", type_="check")

    # Drop old foreign keys
    op.drop_constraint(
        "player_similarities_player_id_fkey", "player_similarities", type_="foreignkey"
    )
    op.drop_constraint(
        "player_similarities_similar_player_id_fkey",
        "player_similarities",
        type_="foreignkey",
    )

    # Drop old columns
    op.drop_column("player_similarities", "player_id")
    op.drop_column("player_similarities", "similar_player_id")

    # Make new columns NOT NULL
    op.alter_column("player_similarities", "player_season_id", nullable=False)
    op.alter_column("player_similarities", "similar_player_season_id", nullable=False)

    # Add new foreign keys
    op.create_foreign_key(
        "player_similarities_player_season_id_fkey",
        "player_similarities",
        "player_seasons",
        ["player_season_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "player_similarities_similar_player_season_id_fkey",
        "player_similarities",
        "player_seasons",
        ["similar_player_season_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Add new constraints
    op.create_unique_constraint(
        "uq_player_similarity",
        "player_similarities",
        ["season_id", "metric_set_id", "player_season_id", "similar_player_season_id"],
    )
    op.create_check_constraint(
        "ck_different_players",
        "player_similarities",
        "player_season_id <> similar_player_season_id",
    )

    # Step 7: Drop old constraint and foreign key from player_seasons
    op.drop_constraint("uq_player_team_season_league", "player_seasons", type_="unique")
    op.drop_constraint(
        "player_seasons_player_id_fkey", "player_seasons", type_="foreignkey"
    )
    op.drop_column("player_seasons", "player_id")

    # Create new unique constraint using player_name instead of player_id
    op.create_unique_constraint(
        "uq_player_team_season_league",
        "player_seasons",
        ["player_name", "season_id", "team_id", "league_id"],
    )

    # Step 8: Drop the players table
    op.drop_table("players")


def downgrade() -> None:
    # Recreate players table
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("position_primary", sa.String(), nullable=True),
        sa.Column("foot", sa.String(), nullable=True),
        sa.Column("birthdate", sa.Date(), nullable=True),
        sa.Column("nationality", sa.String(), nullable=True),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_player_name"),
    )

    # Add player_id back to player_seasons
    op.add_column("player_seasons", sa.Column("player_id", sa.Integer(), nullable=True))

    # Recreate players from player_seasons data (deduplicated by name)
    op.execute("""
        INSERT INTO players (name, nationality)
        SELECT DISTINCT ON (player_name) player_name, nationality
        FROM player_seasons
        ORDER BY player_name, id
    """)

    # Link player_seasons back to players
    op.execute("""
        UPDATE player_seasons ps
        SET player_id = p.id
        FROM players p
        WHERE ps.player_name = p.name
    """)

    # Make player_id NOT NULL
    op.alter_column("player_seasons", "player_id", nullable=False)

    # Recreate foreign key
    op.create_foreign_key(
        "player_seasons_player_id_fkey",
        "player_seasons",
        "players",
        ["player_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Drop new unique constraint and create old one
    op.drop_constraint("uq_player_team_season_league", "player_seasons", type_="unique")
    op.create_unique_constraint(
        "uq_player_team_season_league",
        "player_seasons",
        ["player_id", "season_id", "team_id", "league_id"],
    )

    # Drop new columns from player_seasons
    op.drop_column("player_seasons", "player_name")
    op.drop_column("player_seasons", "nationality")
    op.drop_column("player_seasons", "born_year")

    # Revert player_similarities changes
    op.add_column(
        "player_similarities", sa.Column("player_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "player_similarities",
        sa.Column("similar_player_id", sa.Integer(), nullable=True),
    )

    # Map player_season_id back to player_id
    op.execute("""
        UPDATE player_similarities sim
        SET player_id = ps.player_id
        FROM player_seasons ps
        WHERE sim.player_season_id = ps.id
    """)

    op.execute("""
        UPDATE player_similarities sim
        SET similar_player_id = ps.player_id
        FROM player_seasons ps
        WHERE sim.similar_player_season_id = ps.id
    """)

    # Drop new constraints and foreign keys
    op.drop_constraint("uq_player_similarity", "player_similarities", type_="unique")
    op.drop_constraint("ck_different_players", "player_similarities", type_="check")
    op.drop_constraint(
        "player_similarities_player_season_id_fkey",
        "player_similarities",
        type_="foreignkey",
    )
    op.drop_constraint(
        "player_similarities_similar_player_season_id_fkey",
        "player_similarities",
        type_="foreignkey",
    )

    # Drop new columns
    op.drop_column("player_similarities", "player_season_id")
    op.drop_column("player_similarities", "similar_player_season_id")

    # Make old columns NOT NULL and add foreign keys
    op.alter_column("player_similarities", "player_id", nullable=False)
    op.alter_column("player_similarities", "similar_player_id", nullable=False)

    op.create_foreign_key(
        "player_similarities_player_id_fkey",
        "player_similarities",
        "players",
        ["player_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "player_similarities_similar_player_id_fkey",
        "player_similarities",
        "players",
        ["similar_player_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Recreate old constraints
    op.create_unique_constraint(
        "uq_player_similarity",
        "player_similarities",
        ["season_id", "metric_set_id", "player_id", "similar_player_id"],
    )
    op.create_check_constraint(
        "ck_different_players",
        "player_similarities",
        "player_id <> similar_player_id",
    )
