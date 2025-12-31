import pandas as pd
import streamlit as st

from scouting.constants import AGGREGATED_LEAGUE_NAME


def get_player_leagues_data(
    df: pd.DataFrame, player_id: str, season: int
) -> pd.DataFrame:
    """
    Get all league data for a specific player in a specific season.

    Args:
        df: Full dataframe with player data
        player_id: FBREF ID of the player
        season: Season to filter by

    Returns:
        DataFrame with all league data for the player
    """
    player_data = df[(df["player_id"] == player_id) & (df["season"] == season)].copy()
    return player_data


def create_league_selector(
    player_data: pd.DataFrame,
    default_selection: str = "aggregated",
    key: str = "league_selector",
) -> tuple[str, pd.Series]:
    """
    Create a league selector for players with multiple leagues.

    Args:
        player_data: DataFrame with player data from multiple leagues
        default_selection: Default selection ('aggregated', 'first', or specific league name)
        key: Unique key for the Streamlit selectbox to avoid duplicate key errors

    Returns:
        Tuple of (selected_option, selected_data)
    """
    if len(player_data) == 1:
        return "single_league", player_data.iloc[0]

    # Get available leagues
    available_leagues = player_data["league"].tolist()

    # Create options for selector
    options = [AGGREGATED_LEAGUE_NAME] + [
        league for league in available_leagues if league != AGGREGATED_LEAGUE_NAME
    ]

    # Set default index
    if default_selection == "aggregated":
        default_index = 0
    elif default_selection == "first":
        default_index = 1
    else:
        default_index = (
            options.index(default_selection) if default_selection in options else 0
        )

    selected_option = st.radio(
        "Select league data to display:",
        options,
        index=default_index,
        help="Choose between aggregated statistics across all leagues or individual league data",
        key=key,
    )

    if selected_option == AGGREGATED_LEAGUE_NAME:
        aggregated_data = player_data[player_data["league"] == AGGREGATED_LEAGUE_NAME]
        if len(aggregated_data) > 0:
            selected_data = aggregated_data.iloc[0]
        else:
            # Fallback to first available league if no aggregated data
            selected_data = player_data.iloc[0]
    else:
        selected_data = player_data[player_data["league"] == selected_option].iloc[0]

    return selected_option, selected_data


def display_league_comparison(player_data: pd.DataFrame) -> None:
    """
    Display a comparison table of player statistics across different leagues.

    Args:
        player_data: DataFrame with player data from multiple leagues
    """
    if len(player_data) <= 1:
        return

    st.markdown("### 📊 League Comparison")
    st.markdown("Compare the player's performance across different competitions:")

    # Select key statistics to display based on position
    position = player_data.iloc[0]["pos"]

    if "FW" in position or "MF" in position:
        # Forward/Midfielder stats
        key_stats = [
            "league",
            "90s",
            "Standard_Gls",
            "Standard_Sh",
            "Standard_SoT",
            "Standard_SoT%",
            "Standard_G/Sh",
            "Expected_xG",
            "Expected_xA",
            "Ast",
            "KP",
            "PPA",
            "Total_Cmp",
            "Total_Att",
            "Total_Cmp%",
            "Carries_PrgC",
            "Carries_CPA",
            "Receiving_Rec%",
        ]
    elif "DF" in position:
        # Defender stats
        key_stats = [
            "league",
            "90s",
            "Tackles_Tkl",
            "Tackles_TklW",
            "Vs_Dribbles_Tkl",
            "Vs_Dribbles_Tkl%",
            "Blocks_Blocks",
            "Int",
            "Clr",
            "Aerial_Duels_Won%",
            "Total_Cmp",
            "Total_Att",
            "Total_Cmp%",
            "Carries_PrgC",
            "Ast",
        ]
    elif "GK" in position:
        # Goalkeeper stats
        key_stats = [
            "league",
            "90s",
            "Saves_Saves",
            "Saves_Save%",
            "Saves_PSxG",
            "Saves_PSxG/SoT",
            "Saves_PSxG+/-",
            "Launched_Cmp%",
            "Passes_Att (GK)",
            "Crosses_Stp%",
            "Sweeper_#OPA",
            "Sweeper_AvgDist",
        ]
    else:
        # Default stats
        key_stats = [
            "league",
            "90s",
            "Standard_Gls",
            "Standard_Sh",
            "Standard_SoT",
            "Standard_SoT%",
            "Standard_G/Sh",
            "Expected_xG",
            "Expected_xA",
            "Ast",
            "Total_Cmp",
            "Total_Att",
            "Total_Cmp%",
        ]

    # Filter available stats
    available_stats = [stat for stat in key_stats if stat in player_data.columns]

    # Create comparison dataframe
    comparison_df = player_data[available_stats].copy()

    # Format the dataframe for display
    if "90s" in comparison_df.columns:
        comparison_df["90s"] = comparison_df["90s"].round(1)

    # Round numeric columns
    numeric_cols = comparison_df.select_dtypes(include=["number"]).columns
    for col in numeric_cols:
        if col != "90s":  # Already rounded
            comparison_df[col] = comparison_df[col].round(2)

    # Display the comparison table with better styling
    st.dataframe(
        comparison_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "league": st.column_config.TextColumn(
                "League", width="medium", help="Competition name"
            ),
            "90s": st.column_config.NumberColumn(
                "90s", format="%.1f", help="Number of 90-minute periods played"
            ),
        },
    )


def get_player_data_with_league_handling(
    df: pd.DataFrame,
    player_id: str,
    season: int,
    key_suffix: str = "",
) -> tuple[pd.DataFrame, str, pd.Series]:
    """
    Get player data with proper league handling and return the selected data.
    If multiple leagues are available, allows user to select between them.

    Args:
        df: Full dataframe with player data
        player_name: Name of the player
        player_team: Team of the player
        season: Season to filter by
        key_suffix: Suffix to add to the league selector key to make it unique

    Returns:
        Tuple of (all_player_data, selected_option, selected_data)
    """
    player_data = get_player_leagues_data(df, player_id, season)

    if len(player_data) == 0:
        st.error(f"No data found for {player_id} for season {season}")
        return pd.DataFrame(), "", pd.Series()

    # If only one league available, use it directly
    if len(player_data) == 1:
        selected_data = player_data.iloc[0]
        selected_option = selected_data["league"]
        return player_data, selected_option, selected_data

    # If multiple leagues available, use the league selector with unique key
    unique_key = f"league_selector_{key_suffix}" if key_suffix else "league_selector"
    selected_option, selected_data = create_league_selector(player_data, key=unique_key)

    return player_data, selected_option, selected_data
