"""ETL script for loading player metrics from CSV files into the database."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable, TypeVar

import click
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from scouting.constants import (
    CURRENT_SEASON,
    POSITION_COL,
    TRANSFERMARKT_IMAGE_COL,
    VALUE_DISPLAY_NAME,
)
from scouting.db.models import (
    League,
    MetricDefinition,
    PlayerSeason,
    Season,
    Team,
)
from scouting.db.session import init_db, session_scope

T = TypeVar("T")


def retry_on_timeout(
    func: Callable[..., T], max_retries: int = 3, delay: float = 5.0
) -> Callable[..., T]:
    """Retry a function on timeout errors with exponential backoff."""

    def wrapper(*args, **kwargs) -> T:
        logger = logging.getLogger(__name__)

        # Extract session from args if it's the first argument
        session = None
        if args and hasattr(args[0], "rollback"):
            session = args[0]
        elif "session" in kwargs:
            session = kwargs["session"]

        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = str(e).lower()
                is_retryable = (
                    "timeout" in error_msg
                    or "connection" in error_msg
                    or "server closed" in error_msg
                    or "terminated abnormally" in error_msg
                )

                if is_retryable and attempt < max_retries - 1:
                    wait_time = delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"Attempt {attempt + 1} failed with connection issue: {e}"
                    )
                    logger.info(
                        f"Rolling back transaction and retrying in {wait_time} seconds..."
                    )

                    # Ensure clean transaction state before retry
                    if session:
                        try:
                            session.rollback()
                        except Exception as rollback_error:
                            logger.debug(f"Rollback error (expected): {rollback_error}")

                    time.sleep(wait_time)
                    continue
                raise e
        return func(*args, **kwargs)  # This should never be reached

    return wrapper


def choose_metric_columns(df: pd.DataFrame, identity_cols: list[str]) -> list[str]:
    """Identify metric columns by excluding identity columns."""
    return [col for col in df.columns if col not in identity_cols]


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


def safe_float(value) -> float | None:
    """Convert value to float, return None if not possible."""
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def parse_born_year(born_val) -> int | None:
    """Parse birth year from various formats."""
    if pd.isna(born_val):
        return None
    if isinstance(born_val, (int, float)) and not pd.isna(born_val):
        year = int(born_val)
        # If it's a 4-digit year, use it; otherwise skip
        return year if 1900 <= year <= 2100 else None
    if isinstance(born_val, str):
        try:
            # Handle "2000" format
            if "-" not in born_val:
                year = int(born_val)
                return year if 1900 <= year <= 2100 else None
            # Handle "25-307" (age-days format) - this is not a year
            parts = born_val.split("-")
            if len(parts[0]) == 4:
                year = int(parts[0])
                return year if 1900 <= year <= 2100 else None
        except ValueError:
            pass
    return None


def parse_birth_date(born_val) -> str | None:
    """Parse birth date from born year.

    Since we only have the birth year from FBref, we set the birth date to January 1st.
    Returns ISO date string (YYYY-MM-DD) or None.
    """
    year = parse_born_year(born_val)
    if year is None:
        return None
    # Return January 1st of the birth year
    return f"{year}-01-01"


def bulk_create_metric_definitions(
    session: Session, metric_columns: list[str]
) -> dict[str, int]:
    """Create metric definitions and return code -> id mapping."""
    logger = logging.getLogger(__name__)

    existing = session.query(MetricDefinition).all()
    code_to_id = {m.code: m.id for m in existing}

    new_metrics = []
    for col in metric_columns:
        code = normalize_metric_code(col)
        if code not in code_to_id:
            new_metrics.append(
                MetricDefinition(
                    code=code,
                    name=col,
                    category="Detailed Stats",
                    direction="higher_is_better",
                )
            )

    if new_metrics:
        session.add_all(new_metrics)
        session.flush()
        logger.info(f"Created {len(new_metrics)} new metric definitions")
        # Refresh mapping
        existing = session.query(MetricDefinition).all()
        code_to_id = {m.code: m.id for m in existing}

    return code_to_id


def bulk_upsert_identity_tables(
    session: Session,
    df: pd.DataFrame,
    league_col: str,
    season_col: str,
    team_col: str,
) -> tuple[dict[str, int], dict[str, int], dict[tuple[str, str], int]]:
    """Pre-create all leagues, seasons, and teams. Return mappings."""
    logger = logging.getLogger(__name__)

    # Get unique values
    leagues = df[league_col].dropna().unique().tolist()
    seasons = df[season_col].dropna().unique().tolist()

    # Bulk upsert leagues
    existing_leagues = session.query(League).all()
    league_id_map = {lg.name: lg.id for lg in existing_leagues}

    for league_name in leagues:
        league_name = str(league_name).strip()
        if league_name not in league_id_map:
            new_league = League(name=league_name)
            session.add(new_league)
            session.flush()
            league_id_map[league_name] = new_league.id
            logger.info(f"Created league: {league_name}")

    # Bulk upsert seasons
    existing_seasons = session.query(Season).all()
    season_id_map = {s.label: s.id for s in existing_seasons}

    for season_label in seasons:
        season_label = str(season_label).strip()
        if season_label not in season_id_map:
            new_season = Season(label=season_label)
            session.add(new_season)
            session.flush()
            season_id_map[season_label] = new_season.id
            logger.info(f"Created season: {season_label}")

    # Bulk upsert teams - using raw SQL for performance
    team_league_pairs = (
        df[[team_col, league_col]].dropna().drop_duplicates().values.tolist()
    )

    existing_teams = session.query(Team.id, Team.name, Team.league_id).all()
    team_id_map = {
        (t.name, lg.name): t.id
        for t in existing_teams
        for lg in existing_leagues
        if t.league_id == lg.id
    }

    # Re-query to build proper mapping
    existing_teams_with_league = (
        session.query(Team, League).join(League, Team.league_id == League.id).all()
    )
    team_id_map = {(t.name, lg.name): t.id for t, lg in existing_teams_with_league}

    for team_name, league_name in team_league_pairs:
        team_name = str(team_name).strip()
        league_name = str(league_name).strip()
        key = (team_name, league_name)
        if key not in team_id_map:
            league_id = league_id_map[league_name]
            new_team = Team(name=team_name, league_id=league_id)
            session.add(new_team)
            session.flush()
            team_id_map[key] = new_team.id

    session.commit()
    logger.info(
        f"Pre-created {len(league_id_map)} leagues, {len(season_id_map)} seasons, {len(team_id_map)} team-league combinations"
    )
    return league_id_map, season_id_map, team_id_map


def is_similarities_file(df: pd.DataFrame) -> bool:
    """Check if the DataFrame contains similarities data."""
    similarities_indicators = [
        "similar_player",
        "similarity_score",
        "distance",
        "metric_set_code",
    ]
    return all(col in df.columns for col in similarities_indicators)


def load_similarities_optimized(
    session: Session,
    df: pd.DataFrame,
    league_col: str,
    season_col: str,
    team_col: str,
    player_col: str,
) -> None:
    """Optimized loading of similarities data into player_similarities table."""
    logger = logging.getLogger(__name__)

    from scouting.db.models import MetricSet, PlayerSimilarity

    logger.info(f"Loading {len(df)} similarity records...")

    # Get or create metric set
    metric_set_code = (
        df["metric_set_code"].iloc[0]
        if "metric_set_code" in df.columns
        else "core_per90"
    )
    logger.info("Getting metric set...")
    metric_set = (
        session.query(MetricSet).filter(MetricSet.code == metric_set_code).first()
    )
    if not metric_set:
        logger.info("Creating metric set...")
        metric_set = MetricSet(
            code=metric_set_code,
            name="Core Per-90 Metrics",
            description="Similarity based on core per-90 statistical metrics",
        )
        session.add(metric_set)
        session.flush()
        logger.info(f"Created metric set: {metric_set_code}")

    # Get season
    season_label = (
        df[season_col].iloc[0] if season_col in df.columns else CURRENT_SEASON
    )
    season_label = str(season_label)
    logger.info("Getting season...")
    season = session.query(Season).filter(Season.label == season_label).first()
    if not season:
        logger.error(f"Season {season_label} not found in database")
        return

    # Get (player_name, team_name, league_name) -> player_season_id mapping
    # Using team + league context for disambiguation
    logger.info("Getting player_season mapping...")
    player_seasons = (
        session.query(
            PlayerSeason.id,
            PlayerSeason.player_name,
            Team.name.label("team_name"),
            League.name.label("league_name"),
        )
        .join(Team, PlayerSeason.team_id == Team.id)
        .join(League, PlayerSeason.league_id == League.id)
        .filter(PlayerSeason.season_id == season.id)
        .all()
    )

    # Build mapping: (player_name, team_name, league_name) -> player_season_id
    # Include league to handle players with multiple leagues in same season
    ps_map = {
        (ps.player_name, ps.team_name, ps.league_name): ps.id for ps in player_seasons
    }
    logger.info(f"Loaded {len(ps_map)} player_seasons for similarity mapping")

    # Prepare similarity records
    similarity_records = []
    skipped = 0
    total_rows = len(df)

    logger.info(f"Processing {total_rows} similarity records...")

    for idx, row in df.iterrows():
        if idx % 5000 == 0:
            logger.info(
                f"Processing row {idx + 1}/{total_rows} ({((idx + 1) / total_rows) * 100:.1f}%)"
            )

        player_name = str(row[player_col]).strip()
        similar_player_name = str(row["similar_player"]).strip()
        team_name = str(row[team_col]).strip() if team_col in row else None

        # Extract league from CSV row
        league_name = None
        if league_col in row and not pd.isna(row[league_col]):
            league_name = str(row[league_col]).strip()

        # Support both old and new column names for backward compatibility
        similar_team_name = None
        if "similar_team" in row and not pd.isna(row["similar_team"]):
            similar_team_name = str(row["similar_team"]).strip()
        elif "similar_team_name" in row and not pd.isna(row["similar_team_name"]):
            similar_team_name = str(row["similar_team_name"]).strip()

        # Similar player league (should be same as main player league in most cases)
        similar_league_name = league_name  # Default to same league

        # Skip self-similarities
        if player_name == similar_player_name and team_name == similar_team_name:
            skipped += 1
            continue

        # Look up player_season_ids using (name, team, league) context
        player_season_id = (
            ps_map.get((player_name, team_name, league_name))
            if team_name and league_name
            else None
        )
        similar_player_season_id = (
            ps_map.get((similar_player_name, similar_team_name, similar_league_name))
            if similar_team_name and similar_league_name
            else None
        )

        # REMOVED FALLBACK: The fallback that matched by name only caused homonym issues
        # where players with the same name (e.g., Vitinha from PSG and Vitinha from Genoa)
        # would share similarities. Now we require exact (name, team) matches.

        # Log warnings for missing matches to help debug data issues
        if not player_season_id:
            if idx < 10:  # Only log first 10 to avoid spam
                logger.warning(
                    f"Could not find player_season_id for: '{player_name}' at '{team_name}' in league '{league_name}'"
                )
            skipped += 1
            continue

        if not similar_player_season_id:
            if idx < 10:  # Only log first 10 to avoid spam
                logger.warning(
                    f"Could not find similar_player_season_id for: '{similar_player_name}' at '{similar_team_name}' in league '{similar_league_name}'"
                )
            skipped += 1
            continue

        if player_season_id and similar_player_season_id:
            if player_season_id == similar_player_season_id:
                skipped += 1
                continue

            # Get distance
            if "distance" in row and not pd.isna(row["distance"]):
                distance = float(row["distance"])
            elif "similarity_score" in row and not pd.isna(row["similarity_score"]):
                distance = 1.0 - float(row["similarity_score"])
            else:
                skipped += 1
                continue

            similarity_records.append(
                {
                    "season_id": season.id,
                    "metric_set_id": metric_set.id,
                    "player_season_id": player_season_id,
                    "similar_player_season_id": similar_player_season_id,
                    "distance": distance,
                }
            )
        else:
            skipped += 1

    logger.info(
        f"Finished processing: found {len(similarity_records)} valid pairs, skipped {skipped}"
    )

    if not similarity_records:
        logger.warning("No valid similarity records to save")
        return

    # Deduplicate
    seen_keys: dict[tuple, dict] = {}
    for rec in similarity_records:
        key = (
            rec["season_id"],
            rec["metric_set_id"],
            rec["player_season_id"],
            rec["similar_player_season_id"],
        )
        seen_keys[key] = rec

    similarity_records = list(seen_keys.values())
    logger.info(f"After deduplication: {len(similarity_records)} unique records")

    # Clear existing similarities for this season/metric_set
    session.query(PlayerSimilarity).filter(
        PlayerSimilarity.season_id == season.id,
        PlayerSimilarity.metric_set_id == metric_set.id,
    ).delete()

    # Bulk insert
    batch_size = 2000
    total_batches = (len(similarity_records) + batch_size - 1) // batch_size

    logger.info(f"Bulk inserting {len(similarity_records)} similarities...")

    for i in range(total_batches):
        batch = similarity_records[i * batch_size : (i + 1) * batch_size]
        logger.info(f"Inserting batch {i + 1}/{total_batches} ({len(batch)} records)")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                values_parts = []
                for rec in batch:
                    values_parts.append(
                        f"({rec['season_id']}, {rec['metric_set_id']}, {rec['player_season_id']}, {rec['similar_player_season_id']}, {rec['distance']})"
                    )

                values_clause = ",".join(values_parts)
                session.execute(
                    text(f"""
                        INSERT INTO player_similarities (season_id, metric_set_id, player_season_id, similar_player_season_id, distance)
                        VALUES {values_clause}
                        ON CONFLICT (season_id, metric_set_id, player_season_id, similar_player_season_id)
                        DO UPDATE SET distance = EXCLUDED.distance
                    """)
                )
                session.flush()
                break
            except Exception as e:
                error_msg = str(e).lower()
                is_retryable = "timeout" in error_msg or "connection" in error_msg

                if is_retryable and attempt < max_retries - 1:
                    wait_time = 5 * (2**attempt)
                    logger.warning(f"Batch {i + 1} attempt {attempt + 1} failed: {e}")
                    try:
                        session.rollback()
                    except Exception:
                        pass
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Failed to insert batch after {max_retries} attempts")
                    session.rollback()
                    raise

    session.commit()
    logger.info(f"Successfully loaded {len(similarity_records)} similarity records")


def bulk_insert_player_metrics(session: Session, metrics_data: list[dict]) -> None:
    """Bulk insert player metrics using raw SQL for maximum performance."""
    logger = logging.getLogger(__name__)

    if not metrics_data:
        return

    batch_size = 2000
    total_batches = (len(metrics_data) + batch_size - 1) // batch_size

    logger.info(
        f"Bulk inserting {len(metrics_data)} metrics in {total_batches} batches..."
    )

    for i in range(0, len(metrics_data), batch_size):
        batch = metrics_data[i : i + batch_size]
        batch_num = (i // batch_size) + 1

        logger.info(f"Inserting metrics batch {batch_num}/{total_batches}...")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                values_parts = []
                for m in batch:
                    ps_id = m["player_season_id"]
                    metric_id = m["metric_id"]
                    value = m["value"]
                    percentile = m.get("percentile")
                    percentile_str = "NULL" if percentile is None else str(percentile)
                    values_parts.append(
                        f"({ps_id}, {metric_id}, {value}, {percentile_str})"
                    )

                values_clause = ",".join(values_parts)
                session.execute(
                    text(f"""
                        INSERT INTO player_metrics (player_season_id, metric_id, value, percentile)
                        VALUES {values_clause}
                        ON CONFLICT (player_season_id, metric_id)
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
    logger.info(f"Completed bulk insert of {len(metrics_data)} metrics")


def bulk_upsert_player_seasons(
    session: Session,
    df: pd.DataFrame,
    league_col: str,
    season_col: str,
    team_col: str,
    player_col: str,
    pos_col: str | None,
    minutes_col: str | None,
    ninety_col: str | None,
    nation_col: str | None,
    born_col: str | None,
    league_id_map: dict[str, int],
    season_id_map: dict[str, int],
    team_id_map: dict[tuple[str, str], int],
) -> dict[tuple[str, int, int, int], int]:
    """Bulk create player_seasons, return mapping to player_season_id.

    The unique key is (player_name, season_id, team_id, league_id).
    """
    logger = logging.getLogger(__name__)

    # Get optional columns
    df_lower_cols = {c.lower(): c for c in df.columns}
    img_col = (
        get_column_name(df, TRANSFERMARKT_IMAGE_COL)
        if TRANSFERMARKT_IMAGE_COL.lower() in df_lower_cols
        else None
    )
    value_col = (
        get_column_name(df, VALUE_DISPLAY_NAME)
        if VALUE_DISPLAY_NAME.lower() in df_lower_cols
        else None
    )

    # Prepare player_seasons data - keyed by (player_name, season_id, team_id, league_id)
    player_season_records = []
    player_season_key_to_data = {}

    for _, row in df.iterrows():
        player_name = str(row[player_col]).strip()
        league_name = str(row[league_col]).strip()
        season_label = str(row[season_col]).strip()
        team_name = str(row[team_col]).strip()

        season_id = season_id_map[season_label]
        team_id = team_id_map[(team_name, league_name)]
        league_id = league_id_map[league_name]

        # Parse nationality
        nationality = None
        if nation_col and not pd.isna(row.get(nation_col)):
            nationality = str(row[nation_col]).strip()

        # Parse born_year
        born_year = parse_born_year(row.get(born_col)) if born_col else None

        # Parse birth_date (YYYY-MM-DD format)
        birth_date = parse_birth_date(row.get(born_col)) if born_col else None

        # Calculate minutes
        minutes_val: int | None = None
        if ninety_col and ninety_col in df.columns:
            n90 = safe_float(row[ninety_col]) or 0
            minutes_val = int(round(n90 * 90))
        elif minutes_col and minutes_col in df.columns:
            minutes_val = int(safe_float(row[minutes_col]) or 0)

        # Position
        position_val = None
        if pos_col and pos_col in df.columns:
            position_val = str(row[pos_col]) if not pd.isna(row[pos_col]) else None

        # Market value
        market_value_eur = None
        if value_col and not pd.isna(row.get(value_col)):
            market_value_eur = safe_float(row[value_col])

        # Image URL
        image_url_val = None
        if img_col and not pd.isna(row.get(img_col)):
            image_url_val = str(row[img_col]).strip()

        ps_key = (player_name, season_id, team_id, league_id)
        if ps_key not in player_season_key_to_data:
            player_season_records.append(
                {
                    "player_name": player_name,
                    "season_id": season_id,
                    "team_id": team_id,
                    "league_id": league_id,
                    "nationality": nationality,
                    "born_year": born_year,
                    "birth_date": birth_date,
                    "minutes": minutes_val,
                    "position": position_val,
                    "market_value_eur": market_value_eur,
                    "image_url": image_url_val,
                }
            )
            player_season_key_to_data[ps_key] = len(player_season_records) - 1

    # Bulk upsert player_seasons
    if player_season_records:
        batch_size = 500
        total_batches = (len(player_season_records) + batch_size - 1) // batch_size
        logger.info(
            f"Bulk upserting {len(player_season_records)} player seasons in {total_batches} batches..."
        )

        for i in range(0, len(player_season_records), batch_size):
            batch = player_season_records[i : i + batch_size]
            batch_num = (i // batch_size) + 1
            logger.info(
                f"Upserting batch {batch_num}/{total_batches} ({len(batch)} player seasons)..."
            )

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    values_parts = []
                    for rec in batch:
                        player_name = rec["player_name"].replace("'", "''")
                        season_id = rec["season_id"]
                        team_id = rec["team_id"]
                        league_id = rec["league_id"]
                        nationality = (
                            f"'{rec['nationality'].replace(chr(39), chr(39) + chr(39))}'"
                            if rec["nationality"]
                            else "NULL"
                        )
                        born_year = (
                            str(rec["born_year"]) if rec["born_year"] else "NULL"
                        )
                        birth_date = (
                            f"'{rec['birth_date']}'" if rec["birth_date"] else "NULL"
                        )
                        minutes = (
                            "NULL" if rec["minutes"] is None else str(rec["minutes"])
                        )
                        position = (
                            f"'{rec['position'].replace(chr(39), chr(39) + chr(39))}'"
                            if rec["position"]
                            else "NULL"
                        )
                        market_value = (
                            "NULL"
                            if rec["market_value_eur"] is None
                            else str(rec["market_value_eur"])
                        )
                        image_url = (
                            f"'{rec['image_url'].replace(chr(39), chr(39) + chr(39))}'"
                            if rec["image_url"]
                            else "NULL"
                        )
                        values_parts.append(
                            f"('{player_name}', {season_id}, {team_id}, {league_id}, {nationality}, {born_year}, {birth_date}, {minutes}, {position}, {market_value}, {image_url})"
                        )

                    values_clause = ",".join(values_parts)
                    session.execute(
                        text(f"""
                            INSERT INTO player_seasons (player_name, season_id, team_id, league_id, nationality, born_year, birth_date, minutes, position, market_value_eur, image_url)
                            VALUES {values_clause}
                            ON CONFLICT (player_name, season_id, team_id, league_id) DO UPDATE SET
                                nationality = COALESCE(EXCLUDED.nationality, player_seasons.nationality),
                                born_year = COALESCE(EXCLUDED.born_year, player_seasons.born_year),
                                birth_date = COALESCE(EXCLUDED.birth_date, player_seasons.birth_date),
                                minutes = COALESCE(EXCLUDED.minutes, player_seasons.minutes),
                                position = COALESCE(EXCLUDED.position, player_seasons.position),
                                market_value_eur = COALESCE(EXCLUDED.market_value_eur, player_seasons.market_value_eur),
                                image_url = COALESCE(EXCLUDED.image_url, player_seasons.image_url)
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
                            f"Batch {batch_num} attempt {attempt + 1} failed: {e}"
                        )
                        try:
                            session.rollback()
                        except Exception:
                            pass
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(
                            f"Failed to upsert player seasons batch after {max_retries} attempts"
                        )
                        session.rollback()
                        raise

    session.commit()
    logger.info("Successfully committed all player_seasons insertions")

    # Get player_season mapping
    player_seasons = session.query(
        PlayerSeason.id,
        PlayerSeason.player_name,
        PlayerSeason.season_id,
        PlayerSeason.team_id,
        PlayerSeason.league_id,
    ).all()
    ps_key_to_id = {
        (ps.player_name, ps.season_id, ps.team_id, ps.league_id): ps.id
        for ps in player_seasons
    }

    logger.info(f"Created/found {len(ps_key_to_id)} player seasons")
    return ps_key_to_id


def load_frame_optimized(
    session: Session,
    df: pd.DataFrame,
    league_col: str,
    season_col: str,
    team_col: str,
    player_col: str,
    pos_col: str | None,
    minutes_col: str | None,
    ninety_col: str | None,
    nation_col: str | None,
    age_col: str | None,
    born_col: str | None,
) -> None:
    """Load player metrics data with fully optimized bulk operations."""
    logger = logging.getLogger(__name__)

    # Check if this is a similarities file
    if is_similarities_file(df):
        logger.info(
            "Detected similarities file - loading into player_similarities table"
        )
        load_similarities_optimized(
            session, df, league_col, season_col, team_col, player_col
        )
        return

    # Build identity columns list for metric detection
    identity_cols = [league_col, season_col, team_col, player_col]
    if pos_col:
        identity_cols.append(pos_col)
    if minutes_col:
        identity_cols.append(minutes_col)
    if ninety_col:
        identity_cols.append(ninety_col)
    if nation_col:
        identity_cols.append(nation_col)
    if age_col:
        identity_cols.append(age_col)
    if born_col:
        identity_cols.append(born_col)

    metrics = choose_metric_columns(df, identity_cols)
    total_rows = len(df)

    logger.info(f"Processing {total_rows} rows with {len(metrics)} metric columns")

    # Step 1: Bulk create metric definitions
    logger.info("Creating metric definitions...")
    metric_id_map = bulk_create_metric_definitions(session, metrics)

    # Step 2: Bulk create identity tables
    logger.info("Creating identity tables...")
    league_id_map, season_id_map, team_id_map = bulk_upsert_identity_tables(
        session, df, league_col, season_col, team_col
    )

    # Step 3: Bulk create player_seasons (no separate Player table anymore)
    logger.info("Creating player seasons...")
    ps_key_to_id = bulk_upsert_player_seasons(
        session,
        df,
        league_col,
        season_col,
        team_col,
        player_col,
        pos_col,
        minutes_col,
        ninety_col,
        nation_col,
        born_col,
        league_id_map,
        season_id_map,
        team_id_map,
    )

    # Step 4: Bulk create all metrics
    logger.info("Preparing metrics for bulk insert...")
    metrics_dict = {}  # (player_season_id, metric_id) -> metric_data
    duplicate_count = 0

    for row_idx, row in df.iterrows():
        player_name = str(row[player_col]).strip()
        league_name = str(row[league_col]).strip()
        season_label = str(row[season_col]).strip()
        team_name = str(row[team_col]).strip()

        season_id = season_id_map[season_label]
        team_id = team_id_map[(team_name, league_name)]
        league_id = league_id_map[league_name]
        ps_key = (player_name, season_id, team_id, league_id)
        player_season_id = ps_key_to_id.get(ps_key)

        if not player_season_id:
            logger.warning(f"No player_season found for {player_name}")
            continue

        # Process all metrics for this row
        for col in metrics:
            value = safe_float(row[col])
            if value is None:
                continue

            code = normalize_metric_code(col)
            metric_id = metric_id_map.get(code)
            if not metric_id:
                continue

            metric_key = (player_season_id, metric_id)
            if metric_key in metrics_dict:
                duplicate_count += 1

            metrics_dict[metric_key] = {
                "player_season_id": player_season_id,
                "metric_id": metric_id,
                "value": value,
                "percentile": None,
            }

    all_metrics = list(metrics_dict.values())

    if duplicate_count > 0:
        logger.info(f"Deduplicated {duplicate_count} duplicate metrics")

    # Step 5: Bulk insert metrics
    if all_metrics:
        logger.info(f"Bulk inserting {len(all_metrics)} unique metrics...")
        bulk_insert_player_metrics(session, all_metrics)
    else:
        session.commit()

    logger.info("=== ETL Process Complete ===")
    logger.info(f"Successfully processed {total_rows} rows")
    logger.info(f"Created/found {len(league_id_map)} leagues")
    logger.info(f"Created/found {len(season_id_map)} seasons")
    logger.info(f"Created/found {len(team_id_map)} team-league combinations")
    logger.info(f"Created/found {len(ps_key_to_id)} player seasons")
    logger.info(f"Inserted {len(all_metrics)} metrics")
    logger.info("Data loading completed successfully!")


@click.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--league-col", default=None, help="League column name override")
@click.option("--season-col", default=None, help="Season column name override")
@click.option("--team-col", default=None, help="Team column name override")
@click.option("--player-col", default=None, help="Player column name override")
@click.option("--pos-col", default=None, help="Position column name override")
@click.option(
    "--minutes-col",
    default=None,
    help="Minutes column name override (fallback if 90s missing)",
)
@click.option("--materialize", is_flag=True, help="Create tables if not present")
@click.option("--list-columns", is_flag=True, help="Print detected columns and exit")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def main(
    path: Path,
    league_col: str | None,
    season_col: str | None,
    team_col: str | None,
    player_col: str | None,
    pos_col: str | None,
    minutes_col: str | None,
    materialize: bool,
    list_columns: bool,
    verbose: bool,
):
    """Load player metrics from CSV/Excel files into the database."""

    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    logger = logging.getLogger(__name__)

    logger.info(f"Starting ETL process for file: {path}")

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
        player_col = player_col or get_column_name(df, "player")
        lower_cols = {c.lower(): c for c in df.columns}
        pos_col = (
            pos_col or get_column_name(df, POSITION_COL)
            if POSITION_COL in lower_cols or "position" in lower_cols
            else None
        )
        minutes_col = (
            minutes_col or get_column_name(df, "minutes")
            if "minutes" in lower_cols
            else None
        )
        ninety_col = get_column_name(df, "90s") if "90s" in lower_cols else None
        nation_col = get_column_name(df, "nation") if "nation" in lower_cols else None
        age_col = get_column_name(df, "age") if "age" in lower_cols else None
        born_col = get_column_name(df, "born") if "born" in lower_cols else None

    except ValueError as e:
        logger.error(f"Column mapping error: {e}")
        raise

    logger.info("Column mapping:")
    logger.info(f"  League: {league_col}")
    logger.info(f"  Season: {season_col}")
    logger.info(f"  Team: {team_col}")
    logger.info(f"  Player: {player_col}")
    if pos_col:
        logger.info(f"  Position: {pos_col}")
    if minutes_col:
        logger.info(f"  Minutes: {minutes_col}")
    if ninety_col:
        logger.info(f"  90s played: {ninety_col}")
    if nation_col:
        logger.info(f"  Nation: {nation_col}")
    if age_col:
        logger.info(f"  Age: {age_col}")
    if born_col:
        logger.info(f"  Born: {born_col}")

    if materialize:
        logger.info("Initializing database tables...")
        init_db()

    logger.info("Starting data loading process...")
    try:
        with session_scope() as session:
            load_frame_optimized(
                session,
                df,
                league_col,
                season_col,
                team_col,
                player_col,
                pos_col,
                minutes_col,
                ninety_col,
                nation_col,
                age_col,
                born_col,
            )
    except Exception as e:
        logger.error(f"ETL process failed: {e}")
        raise


if __name__ == "__main__":
    main()
