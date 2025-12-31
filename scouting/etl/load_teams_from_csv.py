"""ETL script for loading team metrics from CSV files into the database."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import click
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from scouting.db.models import (
    League,
    MetricDefinition,
    Season,
    Team,
    TeamSeason,
)
from scouting.db.session import init_db, session_scope

logger = logging.getLogger(__name__)


def get_column_name(df: pd.DataFrame, target: str) -> str:
    """Find column name by case-insensitive matching."""
    target_lower = target.lower()
    for col in df.columns:
        if col.lower() == target_lower:
            return col
    raise ValueError(f"Column '{target}' not found in dataframe")


def normalize_metric_code(column_name: str) -> str:
    """Normalize column name to metric code."""
    return column_name.lower().replace(" ", "_").replace("-", "_")


def upsert_team_seasons_bulk(
    session: Session,
    team_seasons: list[dict],
) -> dict[tuple[str, str, str], int]:
    """Bulk upsert team seasons and return mapping of (team, season, league) -> team_season_id.

    Args:
        session: Database session
        team_seasons: List of dicts with team_id, season_id, league_id, games_played

    Returns:
        dict mapping (team_name, season_label, league_name) -> team_season_id
    """
    logger.info(f"  Bulk upserting {len(team_seasons)} team seasons...")

    if not team_seasons:
        logger.warning("  No team seasons to upsert")
        return {}

    # Build VALUES clause for bulk insert
    values_parts = []
    for ts in team_seasons:
        team_id = ts["team_id"]
        season_id = ts["season_id"]
        league_id = ts["league_id"]
        games = ts.get("games_played")
        games_str = "NULL" if games is None else str(games)
        values_parts.append(f"({team_id}, {season_id}, {league_id}, {games_str})")

    values_clause = ",".join(values_parts)
    session.execute(
        text(f"""
            INSERT INTO team_seasons (team_id, season_id, league_id, games_played)
            VALUES {values_clause}
            ON CONFLICT (team_id, season_id, league_id)
            DO UPDATE SET games_played = EXCLUDED.games_played
        """)
    )
    session.commit()

    # Build mapping from (team_name, season_label, league_name) -> team_season_id
    # Query all team_seasons with their related entities in one go
    ts_records = (
        session.query(TeamSeason, Team, Season, League)
        .join(Team, TeamSeason.team_id == Team.id)
        .join(Season, TeamSeason.season_id == Season.id)
        .join(League, TeamSeason.league_id == League.id)
        .all()
    )

    ts_map = {
        (team.name, season.label, league.name): ts.id
        for ts, team, season, league in ts_records
    }

    logger.info(f"✅ Upserted {len(ts_map)} team seasons")
    return ts_map


def bulk_insert_team_metrics(session: Session, metrics_data: list[dict]) -> None:
    """Bulk insert team metrics using raw SQL for maximum performance."""
    if not metrics_data:
        return

    batch_size = 2000
    total_batches = (len(metrics_data) + batch_size - 1) // batch_size

    logger.info(
        f"  Bulk inserting {len(metrics_data)} metrics in {total_batches} batches (batch size: {batch_size})..."
    )

    for i in range(0, len(metrics_data), batch_size):
        batch = metrics_data[i : i + batch_size]
        batch_num = (i // batch_size) + 1
        progress_pct = (batch_num / total_batches) * 100

        logger.info(
            f"  [{batch_num}/{total_batches}] Inserting batch ({progress_pct:.1f}% complete)..."
        )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                values_parts = []
                for m in batch:
                    ts_id = m["team_season_id"]
                    metric_id = m["metric_id"]
                    value = m["value"]
                    percentile = m.get("percentile")
                    percentile_str = "NULL" if percentile is None else str(percentile)
                    values_parts.append(
                        f"({ts_id}, {metric_id}, {value}, {percentile_str})"
                    )

                values_clause = ",".join(values_parts)
                session.execute(
                    text(f"""
                        INSERT INTO team_metrics (team_season_id, metric_id, value, percentile)
                        VALUES {values_clause}
                        ON CONFLICT (team_season_id, metric_id)
                        DO UPDATE SET value = EXCLUDED.value, percentile = EXCLUDED.percentile
                    """)
                )
                session.flush()
                break
            except Exception as e:
                error_msg = str(e).lower()
                is_retryable = "timeout" in error_msg or "connection" in error_msg

                if is_retryable and attempt < max_retries - 1:
                    wait_time = 5 * (2**attempt)
                    logger.warning(
                        f"Metrics batch {batch_num} attempt {attempt + 1} failed: {e}"
                    )
                    try:
                        session.rollback()
                    except Exception:
                        pass
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(
                        f"Failed to insert metrics batch after {max_retries} attempts"
                    )
                    session.rollback()
                    raise

    session.commit()
    logger.info(f"✅ Completed bulk insert of {len(metrics_data)} metrics")


def load_team_data_optimized(
    session: Session,
    df: pd.DataFrame,
    team_col: str,
    league_col: str,
    season_col: str,
    games_col: str | None = None,
):
    """Load team data from DataFrame into database (optimized version).

    Args:
        session: Database session
        df: DataFrame with team data
        team_col: Team column name
        league_col: League column name
        season_col: Season column name
        games_col: Games played column name (optional)
    """
    logger.info("=== Starting Team ETL Process ===")
    total_rows = len(df)
    logger.info(f"Processing {total_rows} rows")

    # Step 1: Bulk upsert leagues
    logger.info("Step 1: Bulk upserting leagues...")
    unique_leagues = df[league_col].dropna().unique().tolist()
    logger.info(f"  Found {len(unique_leagues)} unique leagues")

    # Build VALUES clause for bulk insert
    values_parts = []
    for league_name in unique_leagues:
        escaped_name = str(league_name).replace("'", "''")
        values_parts.append(f"('{escaped_name}')")

    values_clause = ",".join(values_parts)
    session.execute(
        text(f"""
            INSERT INTO leagues (name)
            VALUES {values_clause}
            ON CONFLICT (name) DO NOTHING
        """)
    )
    session.commit()

    # Get all league IDs
    leagues = session.query(League).all()
    league_id_map = {lg.name: lg.id for lg in leagues}
    logger.info(f"✅ Processed {len(league_id_map)} leagues")

    # Step 2: Bulk upsert seasons
    logger.info("Step 2: Bulk upserting seasons...")
    unique_seasons = df[season_col].dropna().unique().tolist()
    logger.info(f"  Found {len(unique_seasons)} unique seasons")

    # Build VALUES clause for bulk insert
    values_parts = []
    for season_label in unique_seasons:
        escaped_label = str(season_label).replace("'", "''")
        values_parts.append(f"('{escaped_label}')")

    values_clause = ",".join(values_parts)
    session.execute(
        text(f"""
            INSERT INTO seasons (label)
            VALUES {values_clause}
            ON CONFLICT (label) DO NOTHING
        """)
    )
    session.commit()

    # Get all season IDs
    seasons = session.query(Season).all()
    season_id_map = {s.label: s.id for s in seasons}
    logger.info(f"✅ Processed {len(season_id_map)} seasons")

    # Step 3: Bulk upsert teams
    logger.info("Step 3: Bulk upserting teams...")

    # Get unique team-league combinations
    team_league_pairs = (
        df[[team_col, league_col]].dropna().drop_duplicates().values.tolist()
    )
    logger.info(f"  Found {len(team_league_pairs)} unique team-league combinations")

    # Build VALUES clause for bulk insert
    values_parts = []
    for team_name, league_name in team_league_pairs:
        escaped_team = str(team_name).replace("'", "''")
        league_id = league_id_map.get(league_name)
        if league_id:
            values_parts.append(f"('{escaped_team}', {league_id})")

    if values_parts:
        values_clause = ",".join(values_parts)
        session.execute(
            text(f"""
                INSERT INTO teams (name, league_id)
                VALUES {values_clause}
                ON CONFLICT (name, league_id) DO NOTHING
            """)
        )
        session.commit()

    # Get all team IDs - join with leagues to build proper mapping
    teams_with_leagues = (
        session.query(Team, League).join(League, Team.league_id == League.id).all()
    )
    team_id_map = {(t.name, lg.name): t.id for t, lg in teams_with_leagues}
    logger.info(f"✅ Processed {len(team_id_map)} team-league combinations")

    # Step 4: Upsert team_seasons
    logger.info("Step 4: Upserting team seasons...")
    team_seasons_data = []

    for _, row in df.iterrows():
        team_name = row[team_col]
        league_name = row[league_col]
        season_label = str(row[season_col])

        league_id = league_id_map.get(league_name)
        season_id = season_id_map.get(season_label)
        team_id = team_id_map.get((team_name, league_name))

        if not all([team_id, season_id, league_id]):
            continue

        games_played = None
        if games_col and games_col in row and not pd.isna(row[games_col]):
            games_played = int(row[games_col])

        team_seasons_data.append(
            {
                "team_id": team_id,
                "season_id": season_id,
                "league_id": league_id,
                "games_played": games_played,
                "team_name": team_name,
                "season_label": season_label,
                "league_name": league_name,
            }
        )

    ts_key_to_id = upsert_team_seasons_bulk(session, team_seasons_data)

    # Step 5: Upsert metric definitions and prepare metrics
    logger.info("Step 5: Processing metrics...")

    identity_cols = [team_col, league_col, season_col]
    if games_col:
        identity_cols.append(games_col)

    metric_columns = [col for col in df.columns if col not in identity_cols]
    logger.info(f"  Found {len(metric_columns)} metric columns")

    # Bulk upsert metric definitions
    values_parts = []
    for col in metric_columns:
        metric_code = normalize_metric_code(col)
        escaped_code = str(metric_code).replace("'", "''")
        escaped_name = str(col).replace("'", "''")
        escaped_desc = f"Team metric: {col}".replace("'", "''")
        # Default direction to 'higher_is_better' for team metrics
        values_parts.append(
            f"('{escaped_code}', '{escaped_name}', 'team', '{escaped_desc}', 'higher_is_better')"
        )

    if values_parts:
        values_clause = ",".join(values_parts)
        session.execute(
            text(f"""
                INSERT INTO metric_definitions (code, name, category, description, direction)
                VALUES {values_clause}
                ON CONFLICT (code) DO NOTHING
            """)
        )
        session.commit()

    # Get all metric IDs
    all_metrics = session.query(MetricDefinition).all()
    metric_id_map = {m.name: m.id for m in all_metrics}
    logger.info(f"✅ Processed {len(metric_columns)} metric definitions")

    # Step 6: Prepare team metrics for bulk insert
    logger.info("Step 6: Preparing team metrics for bulk insert...")
    metrics_dict = {}
    duplicate_count = 0
    processed_rows = 0

    for idx, row in enumerate(df.iterrows(), 1):
        _, row = row
        team_name = row[team_col]
        league_name = row[league_col]
        season_label = str(row[season_col])

        ts_key = (team_name, season_label, league_name)
        team_season_id = ts_key_to_id.get(ts_key)

        if not team_season_id:
            continue

        for col in metric_columns:
            value = row[col]
            if pd.isna(value):
                continue

            metric_id = metric_id_map[col]
            metric_key = (team_season_id, metric_id)

            if metric_key in metrics_dict:
                duplicate_count += 1
                continue

            # Handle percentile columns
            percentile = None
            if col.startswith("quantile_"):
                percentile = float(value)

            metrics_dict[metric_key] = {
                "team_season_id": team_season_id,
                "metric_id": metric_id,
                "value": float(value),
                "percentile": percentile,
            }

        processed_rows += 1
        if processed_rows % 100 == 0:
            logger.info(f"  Prepared metrics for {processed_rows}/{total_rows} rows...")

    all_metrics = list(metrics_dict.values())

    if duplicate_count > 0:
        logger.info(f"  Deduplicated {duplicate_count} duplicate metrics")

    logger.info(f"✅ Prepared {len(all_metrics)} unique team metrics")

    # Step 7: Bulk insert metrics
    logger.info("Step 7: Bulk inserting team metrics...")
    if all_metrics:
        bulk_insert_team_metrics(session, all_metrics)
    else:
        session.commit()
        logger.info("  No metrics to insert")

    logger.info("")
    logger.info("=" * 60)
    logger.info("🎉 TEAM ETL PROCESS COMPLETE")
    logger.info("=" * 60)
    logger.info("📊 Summary:")
    logger.info(f"  • Total rows processed: {total_rows}")
    logger.info(f"  • Leagues: {len(league_id_map)}")
    logger.info(f"  • Seasons: {len(season_id_map)}")
    logger.info(f"  • Teams: {len(team_id_map)}")
    logger.info(f"  • Team seasons: {len(ts_key_to_id)}")
    logger.info(f"  • Metrics inserted: {len(all_metrics)}")
    logger.info("=" * 60)
    logger.info("✅ Team data loading completed successfully!")


@click.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--league-col", default=None, help="League column name override")
@click.option("--season-col", default=None, help="Season column name override")
@click.option("--team-col", default=None, help="Team column name override")
@click.option("--games-col", default=None, help="Games played column name override")
@click.option("--materialize", is_flag=True, help="Create tables if not present")
@click.option("--list-columns", is_flag=True, help="Print detected columns and exit")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def main(
    path: Path,
    league_col: str | None,
    season_col: str | None,
    team_col: str | None,
    games_col: str | None,
    materialize: bool,
    list_columns: bool,
    verbose: bool,
):
    """Load team metrics from CSV files into the database."""

    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    logger = logging.getLogger(__name__)

    logger.info(f"Starting Team ETL process for file: {path}")

    logger.info("Reading input file...")
    if path.suffix.lower() in {".xls", ".xlsx"}:
        df = pd.read_excel(path)
        logger.info(f"Loaded Excel file with {len(df)} rows")
    else:
        df = pd.read_csv(path)
        logger.info(f"Loaded CSV file with {len(df)} rows")

    if list_columns:
        click.echo("Columns detected (in order):")
        for c in df.columns:
            click.echo(c)
        return

    logger.info("Finding required columns...")
    try:
        league_col = league_col or get_column_name(df, "league")
        season_col = season_col or get_column_name(df, "season")
        team_col = team_col or get_column_name(df, "team")
        lower_cols = {c.lower(): c for c in df.columns}
        games_col = (
            games_col or get_column_name(df, "games") if "games" in lower_cols else None
        )
    except ValueError as e:
        logger.error(f"Required column not found: {e}")
        raise click.Abort()

    logger.info(
        f"Using columns: team={team_col}, league={league_col}, season={season_col}"
    )
    if games_col:
        logger.info(f"Games column: {games_col}")

    if materialize:
        logger.info("Initializing database (creating tables if needed)...")
        init_db()

    with session_scope() as session:
        load_team_data_optimized(
            session=session,
            df=df,
            team_col=team_col,
            league_col=league_col,
            season_col=season_col,
            games_col=games_col,
        )


if __name__ == "__main__":
    main()
