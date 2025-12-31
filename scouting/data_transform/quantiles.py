import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from scouting.constants import (
    AGGREGATED_LEAGUE_NAME,
    INFO_COLS,
    SCOUTING_STATISTICS,
    VALUE_DISPLAY_NAME,
)

# Columns that should be summed across leagues (cumulative stats)
SUM_COLUMNS = {
    # Basic playing time and identity columns
    "minutes",  # Total minutes played (different from 90s)
    "90s",  # 90-minute periods played
    # Goals and assists
    "Standard_Gls",
    "Standard_Sh",
    "Standard_SoT",
    "Standard_FK",
    "Standard_PK",
    "Standard_PKatt",
    "Expected_xG",
    "Expected_npxG",
    "Expected_G-xG",
    "Expected_np:G-xG",
    "Expected_A-xAG",
    "Ast",
    "Expected_xA",
    "xAG",
    "KP",
    "1/3",  # Passes into final third
    "PPA",
    "CrsPA",
    "PrgP",
    # Passing
    "Total_Cmp",
    "Total_Att",
    "Short_Cmp",
    "Short_Att",
    "Medium_Cmp",
    "Medium_Att",
    "Long_Cmp",
    "Long_Att",
    "Total_PrgDist",
    "Total_TotDist",
    "Corner Kicks_In",
    "Corner Kicks_Str",
    "Corner Kicks_Out",
    "Pass Types_FK",
    "Pass Types_Live",
    "Pass Types_CK",
    "Pass Types_Dead",
    "Pass Types_Sw",
    "Pass Types_Crs",
    "Pass Types_TB",
    "Pass Types_TI",
    "Outcomes_Cmp",
    "Outcomes_Blocks",
    "Outcomes_Off",
    "Att",
    # Goal creation
    "SCA_SCA",
    "GCA_GCA",
    "SCA Types_Fld",
    "SCA Types_TO",
    "SCA Types_Sh",
    "SCA Types_PassLive",
    "SCA Types_PassDead",
    "SCA Types_Def",
    "GCA Types_Fld",
    "GCA Types_TO",
    "GCA Types_Sh",
    "GCA Types_PassLive",
    "GCA Types_PassDead",
    "GCA Types_Def",
    # Defensive actions
    "Tackles_Tkl",
    "Tackles_TklW",
    "Tackles_Att 3rd",
    "Tackles_Def 3rd",
    "Tackles_Mid 3rd",
    "Challenges_Tkl",
    "Challenges_Att",
    "Challenges_Lost",
    "Int",
    "Tkl+Int",
    "Clr",
    "Err",
    "Blocks_Blocks",
    "Blocks_Sh",
    "Blocks_Pass",
    "Vs_Dribbles_Tkl",
    "Vs_Dribbles_Att",
    # Carries and touches
    "Carries_Carries",
    "Carries_TotDist",
    "Carries_PrgDist",
    "Carries_PrgC",
    "Carries_CPA",
    "Carries_Mis",
    "Carries_Dis",
    "Carries_1/3",
    "Touches_Touches",
    "Touches_Live",
    "Touches_Att Pen",
    "Touches_Att 3rd",
    "Touches_Def 3rd",
    "Touches_Def Pen",
    "Touches_Mid 3rd",
    "Take-Ons_Att",
    "Take-Ons_Succ",
    "Take-Ons_Tkld",
    "Receiving_Rec",
    "Receiving_PrgR",
    "Receiving_Targ",
    # Aerial duels
    "Aerial Duels_Won",
    "Aerial Duels_Lost",
    # Performance cards and fouls
    "Performance_CrdY",
    "Performance_CrdR",
    "Performance_2CrdY",
    "Performance_Fls",
    "Performance_Off",
    "Performance_Int",
    "Performance_Crs",
    "Performance_Recov",
    "Performance_Fld",
    "Performance_TklW",
    "Performance_PKwon",
    "Performance_PKcon",
    "Performance_OG",
    # Playing time
    "Playing Time_MP",
    "Playing Time_Min",
    "Playing Time_Starts",
    "Playing Time_90s",
    # Goalkeeper specific
    "Performance_GA",
    "Performance_SoTA",
    "Performance_Saves",
    "Performance_CS",
    "Penalty Kicks_PKatt",
    "Penalty Kicks_PKA",
    "Penalty Kicks_PKm",
    "Penalty Kicks_PKsv",
    "Crosses_Opp",
    "Crosses_Stp",
    "Goals_CK",
    "Goals_FK",
    "Goals_GA",
    "Goals_PKA",
    "Goals_OG",
    "Passes_Att (GK)",
    "Passes_Thr",
    "Goal Kicks_Att",
    "Launched_Att",
    "Launched_Cmp",
    "Sweeper_#OPA",
    "Expected_PSxG",
    "Expected_PSxG/SoT",
    "Expected_PSxG+/-",
    "Performance_W",
    "Performance_D",
    "Performance_L",
}

# Columns that should take the first value (rates, percentages, averages)
FIRST_COLUMNS = {
    # Player value (should be first, not sum)
    VALUE_DISPLAY_NAME,
}


@dataclass
class CompetitionStats:
    """Class to hold statistics for a specific competition."""

    name: str
    df: pd.DataFrame
    scaled_stats: pd.DataFrame
    per_90_stats: pd.DataFrame
    quantiles_pos: pd.DataFrame
    quantiles_season: pd.DataFrame
    category_scores: pd.DataFrame

    def get_stats(self, stat_type: str) -> pd.DataFrame:
        """Get specific type of statistics.

        Args:
            stat_type: One of ['raw', 'scaled', 'per_90', 'quantiles_pos', 'quantiles_season', 'category_scores']
        """
        if stat_type == "raw":
            return self.df
        elif stat_type == "scaled":
            return self.scaled_stats
        elif stat_type == "per_90":
            return self.per_90_stats
        elif stat_type == "quantiles_pos":
            return self.quantiles_pos
        elif stat_type == "quantiles_season":
            return self.quantiles_season
        elif stat_type == "category_scores":
            return self.category_scores
        else:
            raise ValueError(f"Unknown stat_type: {stat_type}")


class PlayerStatsManager:
    """Class to manage player statistics across different competitions."""

    def __init__(self):
        self.competitions: dict[str, CompetitionStats] = {}

    def add_competition(self, name: str, df: pd.DataFrame) -> None:
        """Add a new competition's statistics.

        Args:
            name: Competition name (e.g., 'La Liga', 'Champions League')
            df: DataFrame containing the competition's statistics
        """
        # Process the statistics for this competition
        processed_df = compute_player_statistics(df)

        # Create CompetitionStats object
        competition_stats = CompetitionStats(
            name=name,
            df=df,
            scaled_stats=processed_df.filter(regex="_scaled$"),
            per_90_stats=processed_df.filter(regex="_per_90$"),
            quantiles_pos=processed_df.filter(regex="^quantile_pos_"),
            quantiles_season=processed_df.filter(regex="^quantile_season_"),
            category_scores=processed_df[
                list(SCOUTING_STATISTICS["category"].unique())
            ],
        )

        self.competitions[name] = competition_stats

    def get_combined_stats(self, stat_type: str) -> pd.DataFrame:
        """Get combined statistics across all competitions.

        Args:
            stat_type: Type of statistics to combine
        """
        return pd.concat(
            [stats.get_stats(stat_type) for stats in self.competitions.values()]
        )

    def get_competition_stats(self, competition: str, stat_type: str) -> pd.DataFrame:
        """Get statistics for a specific competition.

        Args:
            competition: Competition name
            stat_type: Type of statistics to get
        """
        if competition not in self.competitions:
            raise ValueError(f"Unknown competition: {competition}")
        return self.competitions[competition].get_stats(stat_type)


def get_position_groups(pos: str) -> list[str]:
    """Split a position string into individual positions.

    Args:
        pos (str): Position string (e.g., "MF,FW" or "DF")

    Returns:
        List[str]: List of individual positions
    """
    return pos.split(",") if "," in pos else [pos]


def calculate_scaled_stats(
    df: pd.DataFrame,
    numerical_cols: list[str],
    group_by: list[str] | None = None,
) -> pd.DataFrame:
    """Calculate scaled statistics for numerical columns.

    For player data (with 'pos' column):
    - Goalkeeper-specific stats are scaled only among goalkeepers
    - Field player stats are scaled only among field players
    - Stats applicable to both are scaled across all players

    For team data (without 'pos' column):
    - All stats are scaled across all teams in each group

    Args:
        df (pd.DataFrame): Input DataFrame
        numerical_cols (List[str]): List of numerical columns to scale
        group_by (Optional[List[str]]): Columns to group by before scaling

    Returns:
        pd.DataFrame: DataFrame with scaled statistics
    """
    if group_by is None:
        group_by = ["season"]

    # Check if position-based scaling is applicable
    has_position_column = "pos" in df.columns

    scaled_df = pd.DataFrame(index=df.index)

    # If no position column, treat all columns the same (team data)
    if not has_position_column:
        logging.info("DataFrame does not have position column")
        for group_values, group_df in df.groupby(group_by):
            if len(group_df) > 0:
                scaled_values = (
                    MinMaxScaler((0, 10))
                    .fit_transform(group_df[numerical_cols].values)
                    .round(2)
                )
                scaled_group = pd.DataFrame(
                    scaled_values,
                    columns=[col + "_scaled" for col in numerical_cols],
                    index=group_df.index,
                )
                for col in scaled_group.columns:
                    scaled_df.loc[scaled_group.index, col] = scaled_group[col]
        return scaled_df

    # Position-based scaling for player data
    # Separate columns by position requirement
    goalkeeper_cols = []
    field_cols = []
    both_cols = []

    for col in numerical_cols:
        base_col = col.replace("_per_90", "")
        if base_col in SCOUTING_STATISTICS["stat"].values:
            position_type = SCOUTING_STATISTICS.loc[
                SCOUTING_STATISTICS["stat"] == base_col, "position"
            ].values[0]
            if position_type == "goalkeeper":
                goalkeeper_cols.append(col)
            elif position_type == "field":
                field_cols.append(col)
            else:  # "both"
                both_cols.append(col)
        else:
            # If not in SCOUTING_STATISTICS, treat as applicable to both
            both_cols.append(col)

    # Process each group separately
    for group_values, group_df in df.groupby(group_by):
        # Scale goalkeeper-specific stats (only among goalkeepers)
        if goalkeeper_cols:
            gk_mask = group_df["pos"] == "GK"
            gk_df = group_df[gk_mask]

            if len(gk_df) > 0:
                scaled_values = (
                    MinMaxScaler((0, 10))
                    .fit_transform(gk_df[goalkeeper_cols].values)
                    .round(2)
                )
                scaled_group = pd.DataFrame(
                    scaled_values,
                    columns=[col + "_scaled" for col in goalkeeper_cols],
                    index=gk_df.index,
                )
                for col in scaled_group.columns:
                    scaled_df.loc[scaled_group.index, col] = scaled_group[col]

        # Scale field player stats (only among field players)
        if field_cols:
            field_mask = group_df["pos"] != "GK"
            field_df = group_df[field_mask]

            if len(field_df) > 0:
                scaled_values = (
                    MinMaxScaler((0, 10))
                    .fit_transform(field_df[field_cols].values)
                    .round(2)
                )
                scaled_group = pd.DataFrame(
                    scaled_values,
                    columns=[col + "_scaled" for col in field_cols],
                    index=field_df.index,
                )
                for col in scaled_group.columns:
                    scaled_df.loc[scaled_group.index, col] = scaled_group[col]

        # Scale stats applicable to both (across all players)
        if both_cols:
            scaled_values = (
                MinMaxScaler((0, 10)).fit_transform(group_df[both_cols].values).round(2)
            )
            scaled_group = pd.DataFrame(
                scaled_values,
                columns=[col + "_scaled" for col in both_cols],
                index=group_df.index,
            )
            for col in scaled_group.columns:
                scaled_df.loc[scaled_group.index, col] = scaled_group[col]

    return scaled_df


def calculate_per_90_stats(
    df: pd.DataFrame,
    numerical_cols: list[str],
) -> pd.DataFrame:
    """Calculate per 90 statistics for numerical columns.

    Args:
        df (pd.DataFrame): Input DataFrame
        numerical_cols (List[str]): List of numerical columns to convert to per 90

    Returns:
        pd.DataFrame: DataFrame with per 90 statistics. Average statistics (like Standard_Dist)
        are excluded from per_90 conversion as they represent rates rather than cumulative values.
    """
    per_90_df = df.copy()[numerical_cols + ["90s"]]

    # Columns that should not be converted to per_90 (averages, rates, percentages)
    exclude_from_per_90 = {
        "Standard_Dist",  # Average Shot Distance
        "Passes_AvgLen",  # Average Pass Length
        "Goal Kicks_AvgLen",  # Average Goal Kick Length
        "Sweeper_AvgDist",  # Average Sweeper Distance
        "Standard_G/Sh",  # Goals per Shot
        "Standard_G/SoT",  # Goals per Shot on Target
        "Expected_npxG/Sh",  # Non-Penalty xG per Shot
        "Expected_PSxG/SoT",  # Expected Post-Shot xG per Shot on Target
    }

    # Convert to per 90, excluding percentage columns and average columns
    per_90_df[numerical_cols] = per_90_df[numerical_cols].apply(
        lambda x: x.div(per_90_df["90s"].replace(0, np.nan))
        if "%" not in x.name and x.name not in exclude_from_per_90
        else x
    )
    per_90_df.columns = per_90_df.columns.str.replace("_per_90", "", regex=False)
    per_90_df.columns = [
        col + "_per_90" if col in numerical_cols else col for col in per_90_df.columns
    ]

    return per_90_df


def calculate_quantiles(
    df: pd.DataFrame,
    numerical_cols: list[str],
    group_by: list[str] | None = None,
) -> pd.DataFrame:
    """Calculate quantiles for numerical columns.

    For player data (with 'pos' column):
    - Goalkeeper-specific stats: quantiles calculated only against other goalkeepers
    - Field player stats: quantiles calculated only against field players
    - Stats applicable to both: quantiles calculated across all players

    For team data (without 'pos' column):
    - All stats: quantiles calculated across all teams in each group

    Args:
        df (pd.DataFrame): Input DataFrame
        numerical_cols (List[str]): List of numerical columns to calculate quantiles for
        group_by (Optional[List[str]]): Columns to group by before calculating quantiles

    Returns:
        pd.DataFrame: DataFrame with quantile statistics
    """
    if group_by is None:
        group_by = ["season"]

    # Check if position-based quantile calculation is applicable
    has_position_column = "pos" in df.columns

    quantile_df = pd.DataFrame(index=df.index)

    # If no position column, treat all columns the same (team data)
    if not has_position_column:
        logging.info("DataFrame does not have position column")
        for _, group_df in df.groupby(group_by):
            if len(group_df) > 0:
                quantiles = (
                    group_df[numerical_cols]
                    .apply(lambda col: col.rank(pct=True).fillna(0) * 100)
                    .round()
                    .astype(int)
                )

                # Apply reverse quantiles if applicable
                for col in numerical_cols:
                    base_col = col.replace("_per_90", "")
                    if base_col in SCOUTING_STATISTICS["stat"].values:
                        is_reverse = SCOUTING_STATISTICS.loc[
                            SCOUTING_STATISTICS["stat"] == base_col, "reverse_quantile"
                        ].values[0]
                        if is_reverse:
                            quantiles[col] = 100 - quantiles[col]

                quantile_df.loc[quantiles.index, numerical_cols] = quantiles
        return quantile_df

    # Position-based quantile calculation for player data
    # Separate columns by position requirement
    goalkeeper_cols = []
    field_cols = []
    both_cols = []

    for col in numerical_cols:
        base_col = col.replace("_per_90", "")
        if base_col in SCOUTING_STATISTICS["stat"].values:
            position_type = SCOUTING_STATISTICS.loc[
                SCOUTING_STATISTICS["stat"] == base_col, "position"
            ].values[0]
            if position_type == "goalkeeper":
                goalkeeper_cols.append(col)
            elif position_type == "field":
                field_cols.append(col)
            else:  # "both"
                both_cols.append(col)
        else:
            # If not in SCOUTING_STATISTICS, treat as applicable to both
            both_cols.append(col)

    # Process each group separately
    for group_values, group_df in df.groupby(group_by):
        group_indices = group_df.index

        # Calculate quantiles for goalkeeper-specific stats (only among goalkeepers)
        if goalkeeper_cols:
            gk_mask = group_df["pos"] == "GK"
            gk_df = group_df[gk_mask]

            if len(gk_df) > 0:
                gk_quantiles = (
                    gk_df[goalkeeper_cols]
                    .apply(lambda col: col.rank(pct=True).fillna(0) * 100)
                    .round()
                    .astype(int)
                )

                # Apply reverse quantiles
                for col in goalkeeper_cols:
                    base_col = col.replace("_per_90", "")
                    if base_col in SCOUTING_STATISTICS["stat"].values:
                        is_reverse = SCOUTING_STATISTICS.loc[
                            SCOUTING_STATISTICS["stat"] == base_col, "reverse_quantile"
                        ].values[0]
                        if is_reverse:
                            gk_quantiles[col] = 100 - gk_quantiles[col]

                quantile_df.loc[gk_quantiles.index, goalkeeper_cols] = gk_quantiles

        # Calculate quantiles for field player stats (only among field players)
        if field_cols:
            field_mask = group_df["pos"] != "GK"
            field_df = group_df[field_mask]

            if len(field_df) > 0:
                field_quantiles = (
                    field_df[field_cols]
                    .apply(lambda col: col.rank(pct=True).fillna(0) * 100)
                    .round()
                    .astype(int)
                )

                # Apply reverse quantiles
                for col in field_cols:
                    base_col = col.replace("_per_90", "")
                    if base_col in SCOUTING_STATISTICS["stat"].values:
                        is_reverse = SCOUTING_STATISTICS.loc[
                            SCOUTING_STATISTICS["stat"] == base_col, "reverse_quantile"
                        ].values[0]
                        if is_reverse:
                            field_quantiles[col] = 100 - field_quantiles[col]

                quantile_df.loc[field_quantiles.index, field_cols] = field_quantiles

        # Calculate quantiles for stats applicable to both (across all players)
        if both_cols:
            both_quantiles = (
                group_df[both_cols]
                .apply(lambda col: col.rank(pct=True).fillna(0) * 100)
                .round()
                .astype(int)
            )

            # Apply reverse quantiles
            for col in both_cols:
                base_col = col.replace("_per_90", "")
                if base_col in SCOUTING_STATISTICS["stat"].values:
                    is_reverse = SCOUTING_STATISTICS.loc[
                        SCOUTING_STATISTICS["stat"] == base_col, "reverse_quantile"
                    ].values[0]
                    if is_reverse:
                        both_quantiles[col] = 100 - both_quantiles[col]

            quantile_df.loc[both_quantiles.index, both_cols] = both_quantiles

    return quantile_df


def calculate_category_scores(
    df: pd.DataFrame,
    category: str,
) -> pd.Series:
    """Calculate category scores based on scaled statistics.

    For player data (with 'pos' column):
    - Goalkeeper categories: only goalkeepers receive scores (field players get NaN)
    - Field player categories: only field players receive scores (goalkeepers get NaN)

    For team data (without 'pos' column):
    - All teams receive scores regardless of category type

    Args:
        df (pd.DataFrame): Input DataFrame with scaled statistics
        category (str): Category to calculate score for

    Returns:
        pd.Series: Category scores
    """
    # Standard category calculation
    category_stats = SCOUTING_STATISTICS[SCOUTING_STATISTICS["category"] == category]
    category_cols = list(category_stats["stat"].values)
    scaled_category_cols = [col + "_scaled" for col in category_cols]

    # Check if this is a goalkeeper or field player category
    position_types = category_stats["position"].unique()
    is_goalkeeper_category = "goalkeeper" in position_types and len(position_types) == 1
    is_field_category = "field" in position_types and len(position_types) == 1

    def calculate_score(row: pd.Series) -> float:
        # Skip calculation if position doesn't match category type
        if "pos" in row.index:
            is_gk = row["pos"] == "GK"
            if is_goalkeeper_category and not is_gk:
                return np.nan
            if is_field_category and is_gk:
                return np.nan

        scores = []
        for _, stat_row in category_stats.iterrows():
            stat = stat_row["stat"]
            stat_scaled_col = f"{stat}_scaled"
            if stat_scaled_col in row.index and not pd.isna(row[stat_scaled_col]):
                is_reverse = stat_row["reverse_quantile"]
                score = (
                    row[stat_scaled_col] if not is_reverse else -row[stat_scaled_col]
                )
                scores.append(score)
        return float(np.mean(scores) if scores else np.nan)

    # Need to include 'pos' column in the apply
    cols_to_use = (
        scaled_category_cols + ["pos"] if "pos" in df.columns else scaled_category_cols
    )
    return df[cols_to_use].apply(calculate_score, axis=1)


def compute_player_statistics(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Process player statistics to add scaled stats, per 90 stats, and quantiles.

    Args:
        df (pd.DataFrame): Input DataFrame with player statistics

    Returns:
        pd.DataFrame: Processed DataFrame with additional statistics
    """
    # First, aggregate player stats across leagues
    df = aggregate_player_stats_across_leagues(df)

    # Get numerical columns
    numerical_cols = df.drop(INFO_COLS, axis=1).columns.tolist()

    # Calculate scaled stats by season and position
    scaled_df = calculate_scaled_stats(df, numerical_cols, ["season"])
    df = df.merge(scaled_df, left_index=True, right_index=True)

    # Calculate per 90 stats. Filter out columns that already have "90" in the name.
    per_90_cols = [col for col in numerical_cols if "90" not in col]
    per_90_df = calculate_per_90_stats(df, per_90_cols)
    # Merge with suffixes to identify duplicates
    df = df.merge(
        per_90_df,
        left_index=True,
        right_index=True,
        suffixes=("", "_duplicate_90_merge"),
    )
    # Drop any duplicate columns that might have been created
    df = df.loc[:, ~df.columns.duplicated()]

    # Calculate scaled per 90 stats by season and position
    per_90_cols = [col + "_per_90" for col in per_90_cols]
    scaled_per_90_df = calculate_scaled_stats(df, per_90_cols, ["season"])
    df_with_scaled_per_90 = df.merge(
        scaled_per_90_df,
        left_index=True,
        right_index=True,
        suffixes=("", "_duplicate_scaled_90_merge"),
    )
    df_with_scaled_per_90 = df_with_scaled_per_90.loc[
        :, ~df_with_scaled_per_90.columns.duplicated()
    ]

    # Calculate quantiles by season and position
    quantile_df_pos = calculate_quantiles(
        df_with_scaled_per_90, per_90_cols, ["season", "pos"]
    )
    quantile_df_pos = quantile_df_pos.add_prefix("quantile_pos_")
    df_with_quantiles_pos = df_with_scaled_per_90.merge(
        quantile_df_pos,
        left_index=True,
        right_index=True,
        suffixes=("", "_duplicate_quantile_pos_merge"),
    )
    df_with_quantiles_pos = df_with_quantiles_pos.loc[
        :, ~df_with_quantiles_pos.columns.duplicated()
    ]

    # Calculate quantiles by season only
    quantile_df_season = calculate_quantiles(
        df_with_quantiles_pos, per_90_cols, ["season"]
    )
    quantile_df_season = quantile_df_season.add_prefix("quantile_season_")
    df_with_quantiles_season = df_with_quantiles_pos.merge(
        quantile_df_season,
        left_index=True,
        right_index=True,
        suffixes=("", "_duplicate_quantile_season_merge"),
    )
    df_with_quantiles_season = df_with_quantiles_season.loc[
        :, ~df_with_quantiles_season.columns.duplicated()
    ]

    # Calculate quantiles by season and league
    quantile_df_league = calculate_quantiles(
        df_with_quantiles_season, per_90_cols, ["season", "league"]
    )
    quantile_df_league = quantile_df_league.add_prefix("quantile_league_")
    df_with_quantiles_league = df_with_quantiles_season.merge(
        quantile_df_league,
        left_index=True,
        right_index=True,
        suffixes=("", "_duplicate_quantile_league_merge"),
    )
    df_with_quantiles_league = df_with_quantiles_league.loc[
        :, ~df_with_quantiles_league.columns.duplicated()
    ]

    # Calculate category scores
    for category in SCOUTING_STATISTICS["category"].unique():
        df_with_quantiles_league[category] = calculate_category_scores(
            df_with_quantiles_league, category
        )

    # Compute quantiles for category scores
    quantiles_category_scores = calculate_quantiles(
        df_with_quantiles_league,
        SCOUTING_STATISTICS["category"].unique().tolist(),
        ["season"],
    )
    quantiles_category_scores = quantiles_category_scores.add_prefix(
        "quantile_category_scores_"
    )
    df_with_quantiles_category_scores = df_with_quantiles_league.merge(
        quantiles_category_scores,
        left_index=True,
        right_index=True,
        suffixes=("", "_duplicate_quantile_category_scores_merge"),
    )
    df_with_quantiles_category_scores = df_with_quantiles_category_scores.loc[
        :, ~df_with_quantiles_category_scores.columns.duplicated()
    ]

    return df_with_quantiles_category_scores


def _recalculate_derived_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recalculate percentage and per-90 statistics based on aggregated totals.

    Args:
        df: DataFrame with aggregated statistics

    Returns:
        DataFrame with recalculated derived statistics
    """
    # Only process aggregated rows
    aggregated_rows = df[df["league"] == AGGREGATED_LEAGUE_NAME].copy()

    if len(aggregated_rows) == 0:
        return df

    # Recalculate per 90 stats
    per_90_mappings = {
        "Standard_Sh/90": "Standard_Sh",
        "Standard_SoT/90": "Standard_SoT",
        "Ast/90": "Ast",
        "Expected_xA/90": "Expected_xA",
        "KP/90": "KP",
        "PPA/90": "PPA",
        "CrsPA/90": "CrsPA",
        "PrgP/90": "PrgP",
        "Carries_PrgC/90": "Carries_PrgC",
        "Carries_CPA/90": "Carries_CPA",
        "Carries_Mis/90": "Carries_Mis",
        "Carries_Dis/90": "Carries_Dis",
        "Receiving_PrgR/90": "Receiving_PrgR",
        "Tackles_Tkl/90": "Tackles_Tkl",
        "Tackles_TklW/90": "Tackles_TklW",
        "Vs_Dribbles_Tkl/90": "Vs_Dribbles_Tkl",
        "Vs_Dribbles_Att/90": "Vs_Dribbles_Att",
        "Blocks_Blocks/90": "Blocks_Blocks",
        "Blocks_Sh/90": "Blocks_Sh",
        "Blocks_Pass/90": "Blocks_Pass",
        "Int/90": "Int",
        "Tkl+Int/90": "Tkl+Int",
        "Clr/90": "Clr",
        "Err/90": "Err",
        "Aerial_Duels_Won/90": "Aerial_Duels_Won",
        "Aerial_Duels_Lost/90": "Aerial_Duels_Lost",
        "Performance_GA90": "Performance_GA",
        "SCA_SCA90": "SCA_SCA",
        "GCA_GCA90": "GCA_GCA",
    }

    for per_90_col, base_col in per_90_mappings.items():
        if (
            per_90_col in aggregated_rows.columns
            and base_col in aggregated_rows.columns
        ):
            mask = aggregated_rows["90s"] > 0
            aggregated_rows.loc[mask, per_90_col] = (
                aggregated_rows.loc[mask, base_col] / aggregated_rows.loc[mask, "90s"]
            )

    # Recalculate percentage and ratio stats
    percentage_mappings = {
        "Standard_SoT%": ("Standard_SoT", "Standard_Sh"),
        "Total_Cmp%": ("Total_Cmp", "Total_Att"),
        "Short_Cmp%": ("Short_Cmp", "Short_Att"),
        "Medium_Cmp%": ("Medium_Cmp", "Medium_Att"),
        "Long_Cmp%": ("Long_Cmp", "Long_Att"),
        "Receiving_Rec%": ("Receiving_Rec", "Receiving_Targ"),
        "Vs_Dribbles_Tkl%": ("Vs_Dribbles_Tkl", "Vs_Dribbles_Att"),
        "Aerial_Duels_Won%": (
            "Aerial_Duels_Won",
            "Aerial_Duels_Won + Aerial_Duels_Lost",
        ),
        "Challenges_Tkl%": ("Challenges_Tkl", "Challenges_Att"),
        "Take-Ons_Succ%": ("Take-Ons_Succ", "Take-Ons_Att"),
        "Take-Ons_Tkld%": ("Take-Ons_Tkld", "Take-Ons_Att"),
        "Performance_CS%": ("Performance_CS", "Playing Time_MP"),
        "Performance_Save%": ("Performance_Saves", "Performance_SoTA"),
        "Penalty Kicks_Save%": ("Penalty Kicks_PKsv", "Penalty Kicks_PKA"),
        "Crosses_Stp%": ("Crosses_Stp", "Crosses_Opp"),
    }

    ratio_mappings = {
        "Standard_G/Sh": ("Standard_Gls", "Standard_Sh"),
        "Standard_G/SoT": ("Standard_Gls", "Standard_SoT"),
        "Expected_npxG/Sh": ("Expected_npxG", "Standard_Sh"),
    }

    # Combine all mappings and process with appropriate factor
    all_mappings = {**percentage_mappings, **ratio_mappings}

    for col, (numerator_col, denominator_col) in all_mappings.items():
        if col in aggregated_rows.columns:
            # Determine if this is a percentage (ends with %) or ratio
            factor = 100 if col.endswith("%") else 1

            if " + " in denominator_col:
                denominator_cols = denominator_col.split(" + ")
                denominator = aggregated_rows[denominator_cols].sum(axis=1)
            else:
                denominator = aggregated_rows.get(denominator_col, 0)

            # Handle both scalar and Series denominators
            if isinstance(denominator, (int, float)):
                mask = denominator > 0
                if mask:
                    aggregated_rows[col] = (
                        aggregated_rows[numerator_col] / denominator
                    ) * factor
                else:
                    aggregated_rows[col] = 0
            else:
                # denominator is a Series
                mask = denominator > 0
                aggregated_rows.loc[mask, col] = (
                    aggregated_rows.loc[mask, numerator_col]
                    / aggregated_rows.loc[mask, denominator_col]
                ) * factor
                aggregated_rows.loc[~mask, col] = 0

    # Update the original dataframe with recalculated values
    df.loc[df["league"] == AGGREGATED_LEAGUE_NAME, aggregated_rows.columns] = (
        aggregated_rows
    )

    return df


def _merge_across_positions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge player statistics across multiple positions for the same player-season-team-league combination.

    Replaces multiple rows with a single merged row.
    This is important to merge data for players that play in multiple positions within the same league.

    Args:
        df: DataFrame with player statistics that may have multiple rows per player-season-team

    Returns:
        DataFrame with merged rows (no additional rows)
    """
    group_cols = [
        "player_id",
        "team",
        "season",
        "league",
    ]

    # Get all columns that should be aggregated (excluding group columns and position)
    all_cols = [col for col in df.columns if col not in group_cols and col != "pos"]

    agg_dict = {}
    for col in all_cols:
        if col in SUM_COLUMNS:
            agg_dict[col] = "sum"
        else:
            agg_dict[col] = "first"

    # Use the first position for the merged rows
    agg_dict["pos"] = "first"

    merged_df = df.groupby(group_cols, as_index=False).agg(agg_dict)

    merged_df = _recalculate_derived_stats(merged_df)

    return merged_df


def _aggregate_across_leagues(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate player statistics across multiple leagues for the same player-season-position combination.

    Useful to aggregate stats for players who play Champions League or changed league during the season.

    Args:
        df: DataFrame with player statistics that may have multiple rows per player-season-team-position

    Returns:
        DataFrame with aggregated statistics and additional "Aggregated (All Leagues)" rows
    """
    group_cols = [
        "player",
        "season",
        "player_id",
    ]

    # Get all columns that should be aggregated (excluding group columns, league, and team)
    all_cols = [col for col in df.columns if col not in group_cols and col != "team"]

    # Create aggregation dictionary using the predefined mappings
    agg_dict = {}

    for col in all_cols:
        if col in SUM_COLUMNS:
            agg_dict[col] = "sum"
        else:
            agg_dict[col] = "first"

    # Use the first position for the aggregated rows
    agg_dict["pos"] = "first"

    aggregated_df = df.groupby(group_cols, as_index=False).agg(agg_dict)

    # Handle team column separately: combine team names if player changed clubs
    team_combinations = (
        df.groupby(group_cols)["team"]
        .apply(
            lambda teams: " & ".join(sorted(teams.unique()))
            if len(teams.unique()) > 1
            else teams.iloc[0]
        )
        .reset_index()
    )

    # Merge the team combinations back to the aggregated dataframe
    aggregated_df = aggregated_df.merge(team_combinations, on=group_cols, how="left")

    aggregated_df["league"] = AGGREGATED_LEAGUE_NAME
    aggregated_df = _recalculate_derived_stats(aggregated_df)

    # Concatenate the aggregated df with the original df
    return pd.concat([df, aggregated_df], ignore_index=True)


def aggregate_player_stats_across_leagues(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate player statistics across multiple leagues and positions for the same player-season-team-league combination.
    First merges positions for same player-season-team-league, then aggregates across leagues to have aggregated stats.

    Args:
        df: DataFrame with player statistics that may have multiple rows per player-season-team

    Returns:
        DataFrame with merged rows and additional "Aggregated (All Leagues)" rows
    """
    df_positions_merged = _merge_across_positions(df)
    df_league_aggregated = _aggregate_across_leagues(df_positions_merged)
    return df_league_aggregated
