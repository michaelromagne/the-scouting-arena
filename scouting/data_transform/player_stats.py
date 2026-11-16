import logging
from datetime import datetime
from pathlib import Path

import click
import numpy as np
import pandas as pd
import soccerdata as sd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

from scouting.constants import (
    AGGREGATED_LEAGUE_NAME,
    ALL_LEAGUES,
    CURRENT_SEASON,
    MERGE_COLS,
    POSITION_COL,
    POSITION_MAPPING,
    SCOUTING_CATEGORIES,
    SCOUTING_STATISTICS,
    SCRAPING_BASE_CATEGORIES,
    TRANSFERMARKT_IMAGE_COL,
    VALUE_DISPLAY_NAME,
)
from scouting.data_transform.player_name_matching import align_player_names
from scouting.data_transform.quantiles import compute_player_statistics
from scouting.data_transform.transfermarkt import (
    extract_player_values,
    get_club_urls,
)

# Database models not needed - this module only creates CSV files

logger = logging.getLogger(__name__)

DEFAULT_MAX_CONCURRENT = 1
DEFAULT_MIN_MINUTES = 0  # Waiting for fix to put back to 270
DEFAULT_TOP_K = 20


def load_combined_player_data(data_dir: str | Path = "data") -> pd.DataFrame:
    """Load and combine the separate CSV files into a single DataFrame.

    This function provides a bridge for applications that need the combined dataset
    while we transition to database-first architecture.

    Args:
        data_dir (str | Path): Directory containing the CSV files

    Returns:
        pd.DataFrame: Combined player statistics

    Raises:
        FileNotFoundError: If required CSV files are not found
    """
    data_path = Path(data_dir)

    # Load the separate files
    identity_file = data_path / "players_identity.csv"
    metrics_file = data_path / "players_metrics.csv"
    transfermarkt_file = data_path / "players_transfermarkt.csv"

    if not identity_file.exists() or not metrics_file.exists():
        raise FileNotFoundError(
            f"Required CSV files not found in {data_path}. "
            "Run player_stats_extraction() first to generate the separate files."
        )

    # Load identity and metrics data
    identity_df = pd.read_csv(identity_file)
    metrics_df = pd.read_csv(metrics_file)

    # Merge identity and metrics
    key_columns = ["player", "team", "league", "season"]
    combined_df = identity_df.merge(metrics_df, on=key_columns, how="outer")

    # Add transfermarkt data if available
    if transfermarkt_file.exists():
        transfermarkt_df = pd.read_csv(transfermarkt_file)
        combined_df = combined_df.merge(transfermarkt_df, on=key_columns, how="left")

    # Apply position formatting if not already present and position column exists
    if "pos" in combined_df.columns and "pos_display_name" not in combined_df.columns:
        combined_df = format_position_data(combined_df, "pos")

    return combined_df


def extract_category_stats(fbref: sd.FBref, cat: str) -> pd.DataFrame:
    """Extract stats for a single category from FBref.

    Args:
        fbref (sd.FBref): FBref instance
        cat (str): Category to extract

    Returns:
        pd.DataFrame: DataFrame containing the stats for this category
    """
    try:
        players_stats_temp = fbref.read_player_season_stats(stat_type=cat).reset_index()
    except ValueError as e:
        # This error most likely means that there is no data for this league in the season
        if "not enough values to unpack" in str(e):
            logger.error(
                "🚨 Troubleshooting: You probably have selected a league with no data for this season !"
            )
            raise e
        else:
            raise e

    players_stats_temp.columns = [
        "_".join(col) if col[1] != "" else col[0]
        for col in players_stats_temp.columns.values
    ]

    logging.info(
        f"Successfully extracted category: {cat}, Shape: {players_stats_temp.shape}"
    )

    return players_stats_temp.fillna(0, axis=1)


def extract_fbref_stats(
    stats_to_extract: list[str],
    leagues: str | list[str],
    seasons: str | list[str],
    no_cache: bool = False,
    timestamp_str: str = datetime.now().strftime("%Y%m%d_%H%M%S"),
) -> pd.DataFrame:
    """Extracts player statistics from FBref.

    Args:
        stats_to_extract (list[str]): List of categories to extract from fbref. See SCOUTING_CATEGORIES for full list.
        leagues (str | list[str]): The league(s) to extract the data from. Example: ["FRA-Ligue 1"]
            If "All", all leagues, big5 and custom leagues in the config file, will be extracted.
        seasons (str | list[str]): The season(s) to extract the data from. Example: ["2223", "2324", "2425"]
        no_cache (bool, optional): Set to True if you want to extract new data and avoid cache.
        timestamp_str (str, optional): Timestamp string for the extraction outputs files

    Returns:
        pd.DataFrame: DataFrame containing player statistics
    """
    if leagues == "All":
        leagues = ALL_LEAGUES
        fbref = sd.FBref(leagues=leagues, seasons=seasons, no_cache=no_cache)
    else:
        fbref = sd.FBref(leagues=leagues, seasons=seasons, no_cache=no_cache)

    logger.info(
        "Extracting FBref statistics sequentially (rate limiting handled by soccerdata)"
    )
    players_stats = extract_category_stats(fbref, stats_to_extract[0])

    for cat in stats_to_extract[1:]:
        df_temp = extract_category_stats(fbref, cat)
        cols_to_use = list(set(df_temp.columns).difference(set(players_stats.columns)))
        players_stats = players_stats.merge(
            df_temp[cols_to_use + MERGE_COLS], on=MERGE_COLS, how="outer"
        ).fillna(0, axis=1)
        players_stats.to_csv(
            f"data/players_fbref_stats_temp_{timestamp_str}.csv", index=False
        )

    return players_stats


def scale_stats(group):
    scaler = StandardScaler()
    return scaler.fit_transform(group.values.reshape(-1, 1))


def normalize_position(position: str) -> str:
    """Normalize compound positions by sorting components alphabetically.

    This ensures that "MF,FW" and "FW,MF" are treated as the same position.
    Single positions remain unchanged.

    Examples:
        >>> normalize_position('FW,MF')
        'FW,MF'
        >>> normalize_position('MF,FW')
        'FW,MF'
        >>> normalize_position('DF,FW')
        'DF,FW'
        >>> normalize_position('FW,DF')
        'DF,FW'
        >>> normalize_position('GK')
        'GK'
        >>> normalize_position('MF,DF,FW')
        'DF,FW,MF'
        >>> normalize_position('')
        ''
        >>> normalize_position(None)

    Args:
        position (str): Original position string

    Returns:
        str: Normalized position string with components sorted alphabetically
    """
    if not isinstance(position, str):
        return position

    if "," not in position:
        return position

    # Split, sort alphabetically, and rejoin
    components = [comp.strip() for comp in position.split(",")]
    normalized_components = sorted(components)
    return ",".join(normalized_components)


def get_position_display_name(position: str | None) -> str:
    """Get the formatted display name for a position.

    Args:
        position (str | None): Position code (e.g., 'GK', 'MF,FW')

    Returns:
        str: Formatted display name (e.g., 'Goalkeeper', 'Winger')
    """
    if not position or not isinstance(position, str):
        return "Unknown"

    # Ensure position is normalized first
    normalized_pos = normalize_position(position.strip())
    return POSITION_MAPPING.get(normalized_pos, normalized_pos)


def format_position_data(
    df: pd.DataFrame, position_column: str = "pos"
) -> pd.DataFrame:
    """Add formatted position display names to a DataFrame.

    This function adds position display names to support frontend display
    and eliminate the need for position formatting in the frontend.

    Args:
        df (pd.DataFrame): DataFrame with position data
        position_column (str): Name of the position column

    Returns:
        pd.DataFrame: DataFrame with added position_display_name column
    """
    if position_column not in df.columns:
        return df

    df = df.copy()

    # Normalize positions (already done in pipeline, but ensure consistency)
    df[position_column] = df[position_column].apply(normalize_position)

    # Add formatted display names
    df[f"{position_column}_display_name"] = df[position_column].apply(
        get_position_display_name
    )

    return df


def compute_player_similarities(
    stats_df: pd.DataFrame,
    season: str = str(CURRENT_SEASON),
    top_k: int = DEFAULT_TOP_K,
    min_minutes: int = DEFAULT_MIN_MINUTES,
) -> pd.DataFrame:
    """Compute player similarities using cosine similarity on scaled metrics.

    This function computes similarities for all players within a season using
    standardized metrics. Only players with sufficient minutes played are included.

    Args:
        stats_df (pd.DataFrame): Player statistics dataframe
        season (str): Season to compute similarities for
        top_k (int): Number of top similar players to keep per player
        min_minutes (int): Minimum minutes played to include player

    Returns:
        pd.DataFrame: Similarity pairs with columns [player, similar_player,
                      similarity_score, season, league, similar_team_name, similar_position]
    """
    logger.info(
        f"Computing player similarities for season {season} (top {top_k} per player)"
    )

    # Filter for the target season, aggregated league, and minimum minutes
    season_df = stats_df[
        (stats_df["season"].astype(str) == season)
        & (stats_df["league"] == AGGREGATED_LEAGUE_NAME)
        & (stats_df["90s"] >= min_minutes / 90)
    ].copy()

    if len(season_df) < 2:
        logger.warning(
            f"Not enough players for season {season} with min {min_minutes} minutes"
        )
        return pd.DataFrame()

    logger.info(f"Found {len(season_df)} players for similarity computation")

    # Get metric columns (numerical columns excluding identity and non-metric columns)
    exclude_columns = {
        "player",
        "team",
        "league",
        "season",
        "pos",
        "pos_display_name",
        "minutes",
        "90s",
        "nation",
        "age",
        "born",
        "player_id",
        "value_m_eur",
        "image_url",
    }

    metric_columns = [
        col
        for col in season_df.columns
        if col not in exclude_columns
        and pd.api.types.is_numeric_dtype(season_df[col])
        and not col.startswith("quantile_")  # Exclude quantile columns
        and "_per_90" in col  # Only use per_90 metrics for better comparability
    ]

    if not metric_columns:
        logger.warning("No suitable metric columns found for similarity computation")
        return pd.DataFrame()

    logger.info(
        f"Using {len(metric_columns)} metrics for similarity: {metric_columns[:5]}..."
    )

    # Prepare data for similarity calculation
    metrics_data = season_df[metric_columns].fillna(0)  # Fill NaN with 0

    # Standardize the metrics
    scaler = StandardScaler()
    metrics_scaled = scaler.fit_transform(metrics_data)

    # Calculate cosine similarity matrix
    similarity_matrix = cosine_similarity(metrics_scaled)

    # Create player index mapping for faster lookups
    player_names = season_df["player"].values
    team_names = season_df["team"].values
    positions = season_df["pos"].values

    # Vectorized approach: get top-k similarities for each player
    similarity_records = []

    # For each player, get top-k most similar (excluding self)
    for i in range(len(similarity_matrix)):
        if i % 100 == 0:
            logger.info(
                f"Processing player {i}/{len(similarity_matrix)}: {player_names[i]}"
            )
        # Get similarities for this player, excluding self (set to -1)
        similarities = similarity_matrix[i].copy()
        similarities[i] = -1  # Exclude self-similarity

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        # Filter by similarity threshold and create records
        for idx in top_indices:
            similarity_score = similarities[idx]
            if similarity_score > 0.1:  # Only keep meaningful similarities
                similarity_records.append(
                    {
                        "player": player_names[i],
                        "team": team_names[i],  # Add team for disambiguation
                        "similar_player": player_names[idx],
                        "similar_team": team_names[idx],  # Renamed for consistency
                        "similarity_score": round(float(similarity_score), 4),
                        "season": season,
                        "league": AGGREGATED_LEAGUE_NAME,
                        "similar_position": positions[idx],
                    }
                )

    similarities_df = pd.DataFrame(similarity_records)
    logger.info(f"Generated {len(similarities_df)} similarity pairs")

    return similarities_df


def save_player_similarities_to_csv(
    similarities_df: pd.DataFrame,
    output_path: Path,
    season: str = "2425",
    metric_set_code: str = "core_per90",
    timestamp_str: str = datetime.now().strftime("%Y%m%d_%H%M%S"),
) -> Path | None:
    """Save player similarities to CSV file.

    Args:
        similarities_df (pd.DataFrame): Similarities dataframe with team column already set
        output_path (Path): Directory to save the CSV file
        season (str): Season label
        metric_set_code (str): Metric set code identifier
        timestamp_str (str): Timestamp string for the extraction outputs files

    Returns:
        Path | None: Path to the saved CSV file, or None if no data to save
    """
    if similarities_df.empty:
        logger.info("No similarities to save to CSV")
        return None

    logger.info(f"Saving {len(similarities_df)} similarity pairs to CSV")

    # Add metadata columns for database loading
    similarities_df = similarities_df.copy()
    similarities_df["season"] = season
    similarities_df["metric_set_code"] = metric_set_code

    # Convert similarity_score to distance for database compatibility
    similarities_df["distance"] = 1.0 - similarities_df["similarity_score"]

    # Note: team column is already set correctly in compute_player_similarities
    # with the actual team from the dataframe, which handles homonyms correctly.
    # We should NOT overwrite it with a simple name mapping as that breaks homonyms.

    # Reorder columns for clarity
    column_order = [
        "player",
        "team",  # Player's team for disambiguation
        "similar_player",
        "similar_team",  # Similar player's team for disambiguation
        "similarity_score",
        "distance",
        "season",
        "metric_set_code",
        "league",
        "similar_position",
    ]

    # Only include columns that exist
    available_columns = [col for col in column_order if col in similarities_df.columns]
    similarities_df = similarities_df[available_columns]

    # Save to CSV
    similarities_output = (
        output_path / f"player_similarities_{season}_{timestamp_str}.csv"
    )
    similarities_df.to_csv(similarities_output, index=False)
    logger.info(f"Saved similarities to {similarities_output}")

    return similarities_output


def get_quantiles(row):
    return row.transform(
        lambda x: (
            round(x.rank(pct=True) * 100)
            if not SCOUTING_STATISTICS.loc[
                SCOUTING_STATISTICS["stat"] == row.name, "reverse_quantile"
            ].values[0]  # type: ignore
            else round((1 - x.rank(pct=True)) * 100)
        )
    )


def merge_fbref_transfermarkt_data(
    players_stats: pd.DataFrame,
    df_transfermarkt: pd.DataFrame,
) -> pd.DataFrame:
    """Merge FBref stats with Transfermarkt values and images.

    Args:
        players_stats (pd.DataFrame): FBref player statistics
        df_transfermarkt (pd.DataFrame): Transfermarkt player values and images

    Returns:
        pd.DataFrame: Merged dataset with player stats, values, and images
    """
    # Get the highest value and corresponding image for each player from Transfermarkt
    # First, get the row with the highest value for each player
    df_transfermarkt_max = (
        df_transfermarkt.loc[
            df_transfermarkt.groupby("fuzzy_fbref_player_id")[
                VALUE_DISPLAY_NAME
            ].idxmax()
        ]
        if not df_transfermarkt.empty
        else pd.DataFrame()
    )

    # Merge with Transfermarkt values and images
    merge_columns = [VALUE_DISPLAY_NAME, "fuzzy_fbref_player_id"]
    if TRANSFERMARKT_IMAGE_COL in df_transfermarkt_max.columns:
        merge_columns.append(TRANSFERMARKT_IMAGE_COL)

    stats_with_tfmkt_value = players_stats.merge(
        df_transfermarkt_max[merge_columns],
        left_on=["player_id"],
        right_on=["fuzzy_fbref_player_id"],
        how="left",
    )
    stats_with_tfmkt_value[VALUE_DISPLAY_NAME] = stats_with_tfmkt_value[
        VALUE_DISPLAY_NAME
    ].fillna(-1)

    # Drop the fuzzy_fbref_player_id column
    stats_with_tfmkt_value = stats_with_tfmkt_value.drop(
        columns=["fuzzy_fbref_player_id"]
    )

    return stats_with_tfmkt_value


@click.command()
@click.option(
    "--seasons",
    default="2425",
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
    "--min-games",
    type=float,
    default=3.0,
    help="Minimum number of 90s (games) played to include a player in the dataset",
)
@click.option(
    "--fbref-checkpoint-file",
    type=click.Path(file_okay=True, dir_okay=False),
    help="Path to checkpoint file for FBref scraping",
)
@click.option(
    "--transfermarkt-checkpoint-file",
    type=click.Path(file_okay=True, dir_okay=False),
    help="Path to checkpoint file for Transfermarkt scraping",
)
@click.option(
    "--transfermarkt-club-urls-file",
    type=click.Path(file_okay=True, dir_okay=False),
    help="Path to checkpoint file for Transfermarkt club urls json file",
)
def player_stats_extraction(
    seasons: str,
    leagues: str,
    no_cache: bool,
    output_dir: str,
    min_games: float,
    fbref_checkpoint_file: str | None = None,
    transfermarkt_checkpoint_file: str | None = None,
    transfermarkt_club_urls_file: str | None = None,
):
    """Extract and process player statistics from FBref and Transfermarkt.

    This function creates separate CSV files to support modular ETL:
    - players_identity.csv: Core player info (name, team, league, season, position, etc.)
    - players_metrics.csv: Statistical performance metrics (includes basic identity keys)
    - players_transfermarkt.csv: Market values and images (if available)

    Load BOTH identity and metrics files for complete data coverage.
    """
    target_seasons = seasons.split(",")

    if leagues == "All":
        target_leagues = ALL_LEAGUES
    else:
        target_leagues = leagues.split(",")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if fbref_checkpoint_file:
        players_stats = pd.read_csv(fbref_checkpoint_file)
        # Extract timestamp from filename (format: YYYYMMDD_HHMMSS)
        # Expected filename pattern: players_fbref_stats_raw_*_YYYYMMDD_HHMMSS.csv
        filename = fbref_checkpoint_file.split("/")[-1]
        # Get the last 19 characters before .csv (YYYYMMDD_HHMMSS = 15 chars)
        timestamp_str = (
            filename.replace(".csv", "").split("_")[-2]
            + "_"
            + filename.replace(".csv", "").split("_")[-1]
        )
        logger.info(
            f"Loaded FBref checkpoint file: {fbref_checkpoint_file} with timestamp {timestamp_str}"
        )
        leagues_already_extracted = players_stats["league"].unique().tolist()
    else:
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        leagues_already_extracted = []
        players_stats = pd.DataFrame()

    logger.info(f"Leagues already extracted: {leagues_already_extracted}")

    # Handle "Big 5 European Leagues Combined" specially - it's actually 5 separate leagues
    # We need to check which of the Big 5 are already extracted and only extract missing ones
    big5_component_leagues = [
        "ENG-Premier League",
        "ESP-La Liga",
        "GER-Bundesliga",
        "ITA-Serie A",
        "FRA-Ligue 1",
    ]

    # Expand Big 5 into component leagues if present in target
    expanded_target_leagues = []
    for league in target_leagues:
        if league == "Big 5 European Leagues Combined":
            expanded_target_leagues.extend(big5_component_leagues)
        else:
            expanded_target_leagues.append(league)

    # Remove duplicates while preserving order
    expanded_target_leagues = list(dict.fromkeys(expanded_target_leagues))

    logger.info(f"Target leagues (after Big 5 expansion): {expanded_target_leagues}")
    leagues_to_extract = list(
        set(expanded_target_leagues) - set(leagues_already_extracted)
    )

    if leagues_to_extract:
        logger.info(
            f"Extracting FBref statistics for {len(leagues_to_extract)} new leagues: {leagues_to_extract}..."
        )

        # If we're extracting all Big 5 component leagues, use the combined league for efficiency
        if set(big5_component_leagues).issubset(set(leagues_to_extract)):
            logger.info(
                "All Big 5 leagues needed - using 'Big 5 European Leagues Combined' for efficiency"
            )
            # Remove individual Big 5 leagues and add the combined one
            leagues_for_extraction = [
                league
                for league in leagues_to_extract
                if league not in big5_component_leagues
            ]
            leagues_for_extraction.append("Big 5 European Leagues Combined")
        else:
            leagues_for_extraction = leagues_to_extract

        logger.info(f"Actually extracting from: {leagues_for_extraction}")
        new_players_stats = extract_fbref_stats(
            stats_to_extract=SCRAPING_BASE_CATEGORIES,
            leagues=leagues_for_extraction,
            seasons=target_seasons,
            no_cache=no_cache,
            timestamp_str=timestamp_str,
        ).reset_index(drop=True)

        # Normalize positions right after extraction if position column exists
        if POSITION_COL in new_players_stats.columns:
            logger.info("Normalizing positions in FBref data...")
            new_players_stats[POSITION_COL] = new_players_stats[POSITION_COL].apply(
                normalize_position
            )
            logger.info("FBref position normalization completed")

        players_stats = pd.concat([players_stats, new_players_stats])

        logger.info(f"Filtering players with at least {min_games} games played...")
        players_stats = players_stats[players_stats["90s"] >= min_games].reset_index(
            drop=True
        )
        logger.info(f"After filtering: {len(players_stats)} players remaining")

        fbref_output = (
            output_path
            / f"players_fbref_stats_raw_{seasons}_{leagues}_{timestamp_str}.csv"
        )
        players_stats.to_csv(fbref_output, index=False)
        logger.info(f"Saved raw FBref stats to {fbref_output}")

    logger.info("Extracting Transfermarkt values...")
    club_urls = get_club_urls(
        players_stats["league"].unique().tolist(),
        target_seasons,
        transfermarkt_club_urls_file,
        timestamp_str,
    )
    df_transfermarkt = extract_player_values(
        club_urls,
        timestamp_str,
        target_seasons,
        transfermarkt_checkpoint_file,
    )

    df_transfermarkt = align_player_names(df_transfermarkt, players_stats)

    logger.info("Merging FBref and Transfermarkt data...")
    stats_with_tfmkt_value = merge_fbref_transfermarkt_data(
        players_stats, df_transfermarkt
    )

    logger.info("Processing statistics...")
    stats_with_tfmkt_value = compute_player_statistics(stats_with_tfmkt_value)

    # Apply comprehensive position formatting
    logger.info("Applying position formatting...")
    stats_with_tfmkt_value = format_position_data(stats_with_tfmkt_value, POSITION_COL)
    logger.info("Position formatting completed")

    # Save separate CSV files for modular ETL
    logger.info("Splitting data into separate CSV files for ETL...")

    # 1. Player identity data (core information needed for database entities)
    identity_columns = [
        "player",
        "team",
        "league",
        "season",
        "pos",
        "pos_display_name",  # Formatted position name
        "minutes",
        "90s",
        "nation",
        "age",
        "born",
    ]
    # Only include columns that actually exist in the dataframe
    available_identity_cols = [
        col for col in identity_columns if col in stats_with_tfmkt_value.columns
    ]

    players_identity = stats_with_tfmkt_value[available_identity_cols].copy()
    identity_output = (
        output_path / f"players_identity_{seasons}_{leagues}_{timestamp_str}.csv"
    )
    players_identity.to_csv(identity_output, index=False)
    logger.info(f"Saved identity data to {identity_output}")

    # 2. Player metrics data (statistical performance metrics)
    key_columns = ["player", "team", "league", "season"]
    available_key_cols = [
        col for col in key_columns if col in stats_with_tfmkt_value.columns
    ]

    # If the column contains a category, it is a metric
    metric_columns = [
        col
        for category in SCOUTING_CATEGORIES
        for col in stats_with_tfmkt_value.columns
        if col == category or col == f"quantile_category_scores_{category}"
    ]

    metrics_df = stats_with_tfmkt_value[available_key_cols + metric_columns].copy()
    metrics_output = (
        output_path / f"players_metrics_{seasons}_{leagues}_{timestamp_str}.csv"
    )
    metrics_df.to_csv(metrics_output, index=False)
    logger.info(
        f"Saved metrics data to {metrics_output} ({len(metric_columns)} metrics)"
    )

    # 3. Transfermarkt data (market values and images)
    transfermarkt_columns = ["player", "team", "league", "season"]  # Keys for joining
    if VALUE_DISPLAY_NAME in stats_with_tfmkt_value.columns:
        transfermarkt_columns.append(VALUE_DISPLAY_NAME)
    if TRANSFERMARKT_IMAGE_COL in stats_with_tfmkt_value.columns:
        transfermarkt_columns.append(TRANSFERMARKT_IMAGE_COL)

    # Only save transfermarkt data if we have value or image data
    has_transfermarkt_data = any(
        col in stats_with_tfmkt_value.columns
        for col in [VALUE_DISPLAY_NAME, TRANSFERMARKT_IMAGE_COL]
    )
    if has_transfermarkt_data:
        available_tfmkt_cols = [
            col
            for col in transfermarkt_columns
            if col in stats_with_tfmkt_value.columns
        ]
        transfermarkt_df = stats_with_tfmkt_value[available_tfmkt_cols].copy()
        # Only include rows where we have actual transfermarkt data (not -1 fillna values)
        if VALUE_DISPLAY_NAME in transfermarkt_df.columns:
            transfermarkt_df = transfermarkt_df[
                transfermarkt_df[VALUE_DISPLAY_NAME] != -1
            ]
        transfermarkt_output = (
            output_path
            / f"players_transfermarkt_{seasons}_{leagues}_{timestamp_str}.csv"
        )
        transfermarkt_df.to_csv(transfermarkt_output, index=False)
        logger.info(f"Saved Transfermarkt data to {transfermarkt_output}")

    # 4. Compute and save player similarities for each season
    logger.info("Computing player similarities...")
    seasons_to_process = target_seasons
    similarity_files = []

    for season in seasons_to_process:
        similarities_df = compute_player_similarities(
            stats_df=stats_with_tfmkt_value,
            season=str(season),
            top_k=DEFAULT_TOP_K,
            min_minutes=270,
        )
        if not similarities_df.empty:
            # Save to CSV file (team column is already correctly set in similarities_df)
            similarity_file = save_player_similarities_to_csv(
                similarities_df=similarities_df,
                output_path=output_path,
                season=season,
                metric_set_code="core_per90",
                timestamp_str=timestamp_str,
            )
            if similarity_file:
                similarity_files.append(similarity_file)
            logger.info(
                f"Computed and saved similarities for season {season}: {len(similarities_df)} pairs"
            )

    logger.info("Data extraction and processing completed successfully!")
    logger.info("Generated files:")
    logger.info(f"  - Identity data: {identity_output}")
    logger.info(f"  - Metrics data: {metrics_output}")
    if has_transfermarkt_data:
        logger.info(f"  - Transfermarkt data: {transfermarkt_output}")
    for sim_file in similarity_files:
        logger.info(f"  - Similarities data: {sim_file}")
    logger.info("Load BOTH identity and metrics files for complete data coverage.")


if __name__ == "__main__":
    player_stats_extraction()
