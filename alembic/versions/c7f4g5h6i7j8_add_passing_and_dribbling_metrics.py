"""Add passing and dribbling combined metrics

Revision ID: c7f4g5h6i7j8
Revises: b6f3g4h5i6j7
Create Date: 2025-12-19 11:00:00.000000

"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "c7f4g5h6i7j8"
down_revision = "b6f3g4h5i6j7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure 'defense' metric definition exists (should come from ETL but ensure it's here)
    op.execute("""
        INSERT INTO metric_definitions (code, name, category, direction, description)
        VALUES ('defense', 'Defense', 'Performance Categories', 'higher_is_better',
                'Ball winning and preventing danger')
        ON CONFLICT (code) DO NOTHING;
    """)

    # Create the new 'passing' metric definition (combination of creative_passing + distribution)
    op.execute("""
        INSERT INTO metric_definitions (code, name, category, direction, description)
        VALUES ('passing', 'Passing', 'Performance Categories', 'higher_is_better',
                'Combined passing ability including creative passing and distribution')
        ON CONFLICT (code) DO NOTHING;
    """)

    # Create the new 'dribbling' metric definition (renamed from percussion)
    op.execute("""
        INSERT INTO metric_definitions (code, name, category, direction, description)
        VALUES ('dribbling', 'Dribbling', 'Performance Categories', 'higher_is_better',
                'Ball carrying and dribbling ability (formerly percussion)')
        ON CONFLICT (code) DO NOTHING;
    """)

    # Populate the 'dribbling' metric values from 'percussion'
    op.execute("""
        INSERT INTO player_metrics (player_season_id, metric_id, value, percentile)
        SELECT
            pm.player_season_id,
            (SELECT id FROM metric_definitions WHERE code = 'dribbling'),
            pm.value,
            pm.percentile
        FROM player_metrics pm
        JOIN metric_definitions md ON pm.metric_id = md.id
        WHERE md.code = 'percussion'
        ON CONFLICT (player_season_id, metric_id) DO UPDATE
        SET value = EXCLUDED.value, percentile = EXCLUDED.percentile;
    """)

    # Populate the 'passing' metric values (average of creative_passing + distribution)
    # Handle cases where only one of the metrics exists
    op.execute("""
        INSERT INTO player_metrics (player_season_id, metric_id, value, percentile)
        SELECT
            COALESCE(cp.player_season_id, dist.player_season_id) as player_season_id,
            (SELECT id FROM metric_definitions WHERE code = 'passing'),
            CASE
                WHEN cp.value IS NOT NULL AND dist.value IS NOT NULL
                THEN (cp.value + dist.value) / 2.0
                WHEN cp.value IS NOT NULL THEN cp.value
                WHEN dist.value IS NOT NULL THEN dist.value
                ELSE 0
            END as value,
            CASE
                WHEN cp.percentile IS NOT NULL AND dist.percentile IS NOT NULL
                THEN (cp.percentile + dist.percentile) / 2.0
                WHEN cp.percentile IS NOT NULL THEN cp.percentile
                WHEN dist.percentile IS NOT NULL THEN dist.percentile
                ELSE NULL
            END as percentile
        FROM
            (SELECT pm.player_season_id, pm.value, pm.percentile
             FROM player_metrics pm
             JOIN metric_definitions md ON pm.metric_id = md.id
             WHERE md.code = 'creative_passing') cp
        FULL OUTER JOIN
            (SELECT pm.player_season_id, pm.value, pm.percentile
             FROM player_metrics pm
             JOIN metric_definitions md ON pm.metric_id = md.id
             WHERE md.code = 'distribution') dist
        ON cp.player_season_id = dist.player_season_id
        WHERE COALESCE(cp.player_season_id, dist.player_season_id) IS NOT NULL
        ON CONFLICT (player_season_id, metric_id) DO UPDATE
        SET value = EXCLUDED.value, percentile = EXCLUDED.percentile;
    """)


def downgrade() -> None:
    # Remove the passing and dribbling metrics
    op.execute("""
        DELETE FROM player_metrics
        WHERE metric_id IN (
            SELECT id FROM metric_definitions WHERE code IN ('passing', 'dribbling')
        );
    """)

    op.execute("""
        DELETE FROM metric_definitions WHERE code IN ('passing', 'dribbling');
    """)
