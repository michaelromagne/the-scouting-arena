"""Team statistics extraction and processing module.

This module handles extraction of team-level statistics from FBref,
parallel to player statistics but using read_team_season_stats().
"""

import logging
from datetime import datetime
from pathlib import Path

import click
import pandas as pd
import soccerdata as sd

from scouting.constants import (
    AGGREGATED_LEAGUE_NAME,
    ALL_LEAGUES,
    SCOUTING_STATISTICS,
    SCRAPING_BASE_CATEGORIES,
)
from scouting.data_transform.quantiles import (
    SUM_COLUMNS,
    calculate_category_scores,
    calculate_quantiles,
    calculate_scaled_stats,
)

logger = logging.getLogger(__name__)

# Merge columns for team data
TEAM_MERGE_COLS = ["league", "season", "team"]


def extract_team_category_stats(fbref: sd.FBref, cat: str) -> pd.DataFrame:
    """Extract team stats for a single category from FBref.

    Args:
        fbref (sd.FBref): FBref instance
        cat (str): Category to extract (e.g., 'shooting', 'passing')

    Returns:
        pd.DataFrame: DataFrame containing team stats for this category
    """
    try:
        team_stats_temp = fbref.read_team_season_stats(stat_type=cat).reset_index()
    except ValueError as e:
        if "not enough values to unpack" in str(e):
            logger.error("🚨 No team data for this league/season combination!")
            raise e
        else:
            raise e

    # Flatten multi-level columns
    team_stats_temp.columns = [
        "_".join(col) if col[1] != "" else col[0]
        for col in team_stats_temp.columns.values
    ]

    logger.info(
        f"Successfully extracted team category: {cat}, Shape: {team_stats_temp.shape}"
    )

    return team_stats_temp.fillna(0, axis=1)


def extract_team_stats(
    stats_to_extract: list[str],
    leagues: str | list[str],
    seasons: str | list[str],
    no_cache: bool = False,
    timestamp_str: str = datetime.now().strftime("%Y%m%d_%H%M%S"),
) -> pd.DataFrame:
    """Extract team statistics from FBref.

    Args:
        stats_to_extract (list[str]): List of categories to extract
        leagues (str | list[str]): League(s) to extract from
        seasons (str | list[str]): Season(s) to extract from
        no_cache (bool): Whether to bypass cache
        timestamp_str (str): Timestamp for output files

    Returns:
        pd.DataFrame: DataFrame containing team statistics
    """
    if leagues == "All":
        leagues = ALL_LEAGUES
        fbref = sd.FBref(leagues=leagues, seasons=seasons, no_cache=no_cache)
    else:
        fbref = sd.FBref(leagues=leagues, seasons=seasons, no_cache=no_cache)

    checkpoint_file = f"data/teams_fbref_stats_temp_{timestamp_str}.csv"

    logger.info(
        "Extracting FBref team statistics sequentially (rate limiting handled by soccerdata)"
    )
    team_stats = extract_team_category_stats(fbref, stats_to_extract[0])
    team_stats.to_csv(checkpoint_file, index=False)
    logger.info(
        f"✅ Checkpoint saved after category 1/{len(stats_to_extract)}: {stats_to_extract[0]}"
    )

    for i, cat in enumerate(stats_to_extract[1:], 2):
        logger.info(f"📊 Extracting category {i}/{len(stats_to_extract)}: {cat}")
        df_temp = extract_team_category_stats(fbref, cat)
        cols_to_use = list(set(df_temp.columns).difference(set(team_stats.columns)))
        team_stats = team_stats.merge(
            df_temp[cols_to_use + TEAM_MERGE_COLS], on=TEAM_MERGE_COLS, how="outer"
        ).fillna(0, axis=1)
        team_stats.to_csv(checkpoint_file, index=False)
        logger.info(f"✅ Checkpoint saved after {cat}")

    logger.info(f"🎉 All {len(stats_to_extract)} categories extracted successfully!")
    return team_stats


def compute_team_statistics(team_stats_df: pd.DataFrame) -> pd.DataFrame:
    """Compute team statistics including category scores and quantiles.

    Similar to compute_player_statistics but adapted for team data.
    Also creates an aggregated league view combining all leagues.

    Args:
        team_stats_df: Raw team statistics from FBref

    Returns:
        DataFrame with added category scores and quantiles, including aggregated league data
    """
    logger.info("Computing team statistics...")

    # First, aggregate team stats across leagues (e.g., domestic + Champions League)
    team_stats_df = aggregate_team_stats_across_leagues(team_stats_df)

    # Get numerical columns (exclude identity columns)
    exclude_columns = {
        "team",
        "league",
        "season",
        "games",
        "squad",
        "age",
        "pos",
        "players",
        "90s",
        "players_used",
        "url",
    }

    numerical_cols = [
        col
        for col in team_stats_df.columns
        if col not in exclude_columns
        and pd.api.types.is_numeric_dtype(team_stats_df[col])
    ]

    logger.info(f"Found {len(numerical_cols)} numerical columns for processing")

    # Calculate scaled stats by season and league
    logger.info("Calculating scaled statistics...")
    scaled_df = calculate_scaled_stats(
        team_stats_df, numerical_cols, ["season", "league"]
    )
    team_stats_df = team_stats_df.merge(scaled_df, left_index=True, right_index=True)

    # Calculate category scores for each category
    logger.info("Calculating category scores...")
    for category in SCOUTING_STATISTICS["category"].unique():
        team_stats_df[category] = calculate_category_scores(team_stats_df, category)
        logger.info(f"  ✓ Computed {category} scores")

    # Calculate quantiles for category scores by season and league
    logger.info("Calculating quantiles for category scores...")
    category_cols = SCOUTING_STATISTICS["category"].unique().tolist()
    quantiles_category_scores = calculate_quantiles(
        team_stats_df,
        category_cols,
        ["season", "league"],
    )
    quantiles_category_scores = quantiles_category_scores.add_prefix("quantile_")
    team_stats_df = team_stats_df.merge(
        quantiles_category_scores,
        left_index=True,
        right_index=True,
    )

    logger.info("✅ Team statistics computation completed")
    return team_stats_df


def aggregate_team_stats_across_leagues(team_stats_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate team statistics across multiple leagues (e.g., domestic + Champions League).

    Similar to player aggregation but for teams. Groups by team and season,
    aggregating stats from different competitions (e.g., La Liga + Champions League).
    Uses the same SUM_COLUMNS logic from quantiles module to determine which stats to sum.

    Args:
        team_stats_df: DataFrame with team statistics

    Returns:
        DataFrame with original data plus aggregated league rows
    """
    logger.info("Aggregating team stats across leagues...")

    group_cols = ["team", "season"]

    # Get all columns that should be aggregated (excluding group columns and league)
    all_cols = [
        col for col in team_stats_df.columns if col not in group_cols + ["league"]
    ]

    # Create aggregation dictionary using the same SUM_COLUMNS logic as player aggregation
    agg_dict = {}
    for col in all_cols:
        if col in SUM_COLUMNS:
            # Sum cumulative stats (goals, shots, passes, etc.)
            agg_dict[col] = "sum"
        elif pd.api.types.is_numeric_dtype(team_stats_df[col]):
            # For other numeric columns (rates, percentages), take first value
            # This is consistent with player aggregation logic
            agg_dict[col] = "first"
        else:
            # For non-numeric columns, take first value
            agg_dict[col] = "first"

    # Aggregate across leagues
    aggregated_df = team_stats_df.groupby(group_cols, as_index=False).agg(agg_dict)
    aggregated_df["league"] = AGGREGATED_LEAGUE_NAME

    logger.info(f"Created {len(aggregated_df)} aggregated league records")

    # Concatenate with original data
    result_df = pd.concat([team_stats_df, aggregated_df], ignore_index=True)

    logger.info(f"Total records after aggregation: {len(result_df)}")
    return result_df


def compute_team_quantiles(team_stats_df: pd.DataFrame) -> pd.DataFrame:
    """Compute percentiles for team stats within each league/season.

    Args:
        team_stats_df (pd.DataFrame): Team statistics dataframe

    Returns:
        pd.DataFrame: Team stats with added percentile columns
    """
    logger.info("Computing team quantiles (percentiles within league/season)...")

    # Get metric columns (exclude identity columns)
    exclude_columns = {
        "team",
        "league",
        "season",
        "games",
        "games_played",
        "90s",
    }

    metric_columns = [
        col
        for col in team_stats_df.columns
        if col not in exclude_columns
        and pd.api.types.is_numeric_dtype(team_stats_df[col])
        and not col.startswith("quantile_")
    ]

    logger.info(f"Computing percentiles for {len(metric_columns)} metrics")

    # Compute percentiles within each league/season group
    for col in metric_columns:
        percentile_col = f"quantile_{col}"
        team_stats_df[percentile_col] = (
            team_stats_df.groupby(["league", "season"])[col]
            .rank(pct=True)
            .mul(100)
            .round(1)
        )

    logger.info("Team quantile computation completed")
    return team_stats_df


@click.command()
@click.option(
    "--seasons",
    default="2526",
    help="Comma-separated list of seasons to extract (e.g. '2223,2324,2425')",
)
@click.option(
    "--leagues",
    default="All",
    help="Comma-separated list of leagues to extract or 'All' for all configured leagues",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Add this flag if you want to extract new data and avoid cache",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True),
    default="data",
    help="Directory to save output files",
)
@click.option(
    "--fbref-checkpoint-file",
    type=click.Path(file_okay=True, dir_okay=False),
    help="Path to checkpoint file for FBref scraping (e.g., data/teams_fbref_stats_temp_*.csv)",
)
def team_stats_extraction(
    seasons: str,
    leagues: str,
    no_cache: bool,
    output_dir: str,
    fbref_checkpoint_file: str | None = None,
):
    """Extract and process team statistics from FBref.

    This function creates separate CSV files for team statistics:
    - teams_identity.csv: Core team info (team, league, season, games_played)
    - teams_metrics.csv: Statistical performance metrics
    """
    target_seasons = seasons.split(",")

    if leagues == "All":
        target_leagues = ALL_LEAGUES
    else:
        target_leagues = leagues.split(",")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load from checkpoint or extract fresh data
    if fbref_checkpoint_file:
        logger.info(f"📂 Loading FBref checkpoint file: {fbref_checkpoint_file}")
        team_stats = pd.read_csv(fbref_checkpoint_file)

        # Extract timestamp from filename (format: YYYYMMDD_HHMMSS)
        # Expected filename pattern: teams_fbref_stats_*_YYYYMMDD_HHMMSS.csv
        filename = fbref_checkpoint_file.split("/")[-1]
        timestamp_str = (
            filename.replace(".csv", "").split("_")[-2]
            + "_"
            + filename.replace(".csv", "").split("_")[-1]
        )
        logger.info(f"⏱️  Using timestamp from checkpoint: {timestamp_str}")
        logger.info(f"✅ Loaded {len(team_stats)} team-season records from checkpoint")
    else:
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

        logger.info(
            f"🔄 Extracting fresh team statistics for leagues: {target_leagues}"
        )
        logger.info(f"📅 Seasons: {target_seasons}")

        # Extract team stats
        team_stats = extract_team_stats(
            stats_to_extract=SCRAPING_BASE_CATEGORIES,
            leagues=target_leagues,
            seasons=target_seasons,
            no_cache=no_cache,
            timestamp_str=timestamp_str,
        ).reset_index(drop=True)

        logger.info(f"✅ Extracted {len(team_stats)} team-season records")

    # Save raw team stats
    raw_output = (
        output_path / f"teams_fbref_stats_raw_{seasons}_{leagues}_{timestamp_str}.csv"
    )
    team_stats.to_csv(raw_output, index=False)
    logger.info(f"Saved raw team stats to {raw_output}")

    # Compute category scores and quantiles
    logger.info("Computing team category scores and quantiles...")
    team_stats = compute_team_statistics(team_stats)

    # Save separate CSV files for modular ETL
    logger.info("Splitting data into separate CSV files for ETL...")

    # 1. Team identity data
    identity_columns = [
        "team",
        "league",
        "season",
        "games",  # or "games_played" depending on FBref column name
    ]
    available_identity_cols = [
        col for col in identity_columns if col in team_stats.columns
    ]

    teams_identity = team_stats[available_identity_cols].copy()
    identity_output = (
        output_path / f"teams_identity_{seasons}_{leagues}_{timestamp_str}.csv"
    )
    teams_identity.to_csv(identity_output, index=False)
    logger.info(f"Saved team identity data to {identity_output}")

    # 2. Team metrics data
    key_columns = ["team", "league", "season"]
    available_key_cols = [col for col in key_columns if col in team_stats.columns]

    # Get category columns and their quantiles (like for players)
    category_cols = SCOUTING_STATISTICS["category"].unique().tolist()
    metric_columns = []

    for category in category_cols:
        if category in team_stats.columns:
            metric_columns.append(category)
        quantile_col = f"quantile_{category}"
        if quantile_col in team_stats.columns:
            metric_columns.append(quantile_col)

    logger.info(
        f"Found {len(metric_columns)} metric columns for teams (categories + quantiles)"
    )

    teams_metrics = team_stats[available_key_cols + metric_columns].copy()
    metrics_output = (
        output_path / f"teams_metrics_{seasons}_{leagues}_{timestamp_str}.csv"
    )
    teams_metrics.to_csv(metrics_output, index=False)
    logger.info(
        f"Saved team metrics data to {metrics_output} ({len(metric_columns)} metrics)"
    )

    logger.info("Team data extraction and processing completed successfully!")
    logger.info("Generated files:")
    logger.info(f"  - Raw team stats: {raw_output}")
    logger.info(f"  - Team identity data: {identity_output}")
    logger.info(f"  - Team metrics data: {metrics_output}")


if __name__ == "__main__":
    team_stats_extraction()
