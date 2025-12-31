"""
Filtering and data processing functionality for the scouting application.

This module contains the core filtering logic used across the application,
including the FilterState class and related data processing functions.
"""

from typing import Optional, Tuple

import pandas as pd
import streamlit as st
from pydantic import BaseModel

from scouting.app.utils import format_season
from scouting.constants import (
    AGGREGATED_LEAGUE_NAME,
    POSITION_MAPPING,
    VALUE_DISPLAY_NAME,
)


class FilterState(BaseModel):
    position: list[str]
    league: list[str]
    team: list[str]
    season: Optional[int]
    value: Tuple[float, float]
    age: Tuple[float, float]
    nation: list[str]

    @classmethod
    def reset_filters(
        cls,
        df: pd.DataFrame,
        filters_title: str,
    ) -> None:
        """Reset the filter state variables in Streamlit's session state."""
        df_copy = df.copy()
        df_copy["age"] = df_copy["age"].apply(
            lambda x: int(x.split("-")[0]) if isinstance(x, str) else int(x)
        )

        st.session_state[f"{filters_title}_position"] = []
        st.session_state[f"{filters_title}_team"] = []
        st.session_state[f"{filters_title}_nation"] = []

        st.session_state[f"{filters_title}_league"] = []

        st.session_state[f"{filters_title}_season"] = sorted(
            df_copy["season"].unique(), reverse=True
        )[0]

        st.session_state[f"{filters_title}_value"] = (
            int(df_copy[VALUE_DISPLAY_NAME].min()),
            int(df_copy[VALUE_DISPLAY_NAME].max()),
        )

        st.session_state[f"{filters_title}_age"] = (
            int(df_copy["age"].min()),
            int(df_copy["age"].max()),
        )

    @classmethod
    def from_session_state(cls, filters_title: str) -> "FilterState":
        """Create a FilterState instance from Streamlit's session state."""
        return cls(
            position=st.session_state[f"{filters_title}_position"],
            league=st.session_state[f"{filters_title}_league"],
            team=st.session_state[f"{filters_title}_team"],
            season=st.session_state[f"{filters_title}_season"],
            value=st.session_state[f"{filters_title}_value"],
            age=st.session_state[f"{filters_title}_age"],
            nation=st.session_state[f"{filters_title}_nation"],
        )

    @classmethod
    def initialize_missing_session_state(
        cls,
        df: pd.DataFrame,
        filters_title: str,
        force_aggregated_league: bool = False,
    ) -> None:
        """Initialize only missing session state variables."""
        # Create a copy to avoid modifying the original DataFrame
        df_copy = df.copy()

        # Process age column safely
        df_copy["age"] = df_copy["age"].apply(
            lambda x: int(x.split("-")[0]) if isinstance(x, str) else int(x)
        )

        # Initialize only if not exists
        if f"{filters_title}_position" not in st.session_state:
            st.session_state[f"{filters_title}_position"] = []
        if f"{filters_title}_team" not in st.session_state:
            st.session_state[f"{filters_title}_team"] = []
        if f"{filters_title}_nation" not in st.session_state:
            st.session_state[f"{filters_title}_nation"] = []
        if f"{filters_title}_league" not in st.session_state:
            st.session_state[f"{filters_title}_league"] = (
                [AGGREGATED_LEAGUE_NAME] if force_aggregated_league else []
            )
        if f"{filters_title}_season" not in st.session_state:
            st.session_state[f"{filters_title}_season"] = sorted(
                df_copy["season"].unique(), reverse=True
            )[0]
        if f"{filters_title}_value" not in st.session_state:
            st.session_state[f"{filters_title}_value"] = (
                int(df_copy[VALUE_DISPLAY_NAME].min()),
                int(df_copy[VALUE_DISPLAY_NAME].max()),
            )
        if f"{filters_title}_age" not in st.session_state:
            st.session_state[f"{filters_title}_age"] = (
                int(df_copy["age"].min()),
                int(df_copy["age"].max()),
            )


def team_matches(row_team: str, selected_team: list[str]) -> bool:
    """Create a boolean mask that matches if any selected team is in the team column
    This handles both individual teams and combined teams like "Napoli FC & Paris S-G"
    """
    if " & " in row_team:
        # For combined teams, check if any selected team matches any individual team
        individual_teams = [t.strip() for t in row_team.split(" & ")]
        return any(selected in individual_teams for selected in selected_team)
    else:
        # For individual teams, check if it's in the selected teams
        return row_team in selected_team


def filter_data(
    df: pd.DataFrame,
    filters_title="Filters",
    filters_subtitle="",
    force_aggregated_league: bool = False,
) -> pd.DataFrame:
    """Apply filters to the dataframe based on user selections."""
    st.sidebar.header(filters_title)
    if filters_subtitle:
        st.sidebar.markdown(filters_subtitle)

    # Add reset button with styling
    st.sidebar.markdown(
        """
        <style>
            div[data-testid="stButton"] button {
                width: 100%;
                background-color: #ff4b4b;
                color: white;
                border: none;
                padding: 0.5rem 1rem;
                border-radius: 0.25rem;
                font-weight: bold;
            }
            div[data-testid="stButton"] button:hover {
                background-color: #ff3333;
                color: white !important;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    if st.sidebar.button("🔄 Reset Filters", key=f"{filters_title}_reset_button"):
        FilterState.reset_filters(
            df,
            filters_title,
        )
        st.rerun()

    # Initialize session state for each page only if not already exists
    FilterState.initialize_missing_session_state(
        df, filters_title, force_aggregated_league=force_aggregated_league
    )

    # Start with the full dataframe
    filtered_df: pd.DataFrame = df.copy()

    # Get unique single positions for the filter
    single_positions = sorted(
        set(p for pos in filtered_df["pos"].unique() for p in pos.split(","))
    )
    position_display = {pos: POSITION_MAPPING[pos] for pos in single_positions}

    # Position filter
    selected_position: list[str] = st.sidebar.multiselect(
        "Position",
        single_positions,
        format_func=lambda x: position_display[x],
        key=f"{filters_title}_position",
    )
    if selected_position:
        # Create a boolean mask for position filtering
        position_mask = filtered_df["pos"].apply(
            lambda x: any(p in selected_position for p in x.split(","))
        )
        filtered_df = pd.DataFrame(filtered_df[position_mask]).copy()

    # Season filter - options based on current filtered_df
    available_seasons = sorted(filtered_df["season"].unique(), reverse=True)

    selected_season = st.sidebar.selectbox(
        "Season",
        available_seasons,
        index=len(available_seasons) - 1,
        format_func=format_season,
        key=f"{filters_title}_season",
    )
    if selected_season:
        filtered_df = pd.DataFrame(
            filtered_df[filtered_df["season"] == selected_season]
        ).copy()

    # League filter - options based on current filtered_df (including season)
    available_leagues = sorted(filtered_df["league"].unique())

    selected_league: list[str] = st.sidebar.multiselect(
        "League",
        available_leagues,
        key=f"{filters_title}_league",
    )
    if selected_league:
        filtered_df = pd.DataFrame(
            filtered_df[filtered_df["league"].isin(selected_league)]
        ).copy()

    # Team filter - options based on current filtered_df (including season and league)
    # Get all individual team names (split combined teams like "Napoli FC & Paris S-G")
    all_individual_teams = set()
    for team in filtered_df["team"].unique():
        if " & " in team:
            # Split combined team names
            individual_teams = [t.strip() for t in team.split(" & ")]
            all_individual_teams.update(individual_teams)
        else:
            all_individual_teams.add(team)

    available_teams = sorted(all_individual_teams)
    selected_team: list[str] = st.sidebar.multiselect(
        "Team", available_teams, key=f"{filters_title}_team"
    )
    if selected_team:
        team_mask = filtered_df["team"].apply(lambda x: team_matches(x, selected_team))
        filtered_df = pd.DataFrame(filtered_df[team_mask]).copy()

    return filtered_df


def get_players_candidates(
    full_df: pd.DataFrame, filters_title="Filters"
) -> pd.DataFrame:
    """Get candidate players based on value, age, and nation filters."""
    full_df = process_dataframe(full_df)

    FilterState.initialize_missing_session_state(full_df, filters_title)

    # Slider for filtering similar players by value
    similar_players_pool: pd.DataFrame = full_df.copy()
    value_filter = st.sidebar.slider(
        "Filter by value",
        min_value=int(full_df[VALUE_DISPLAY_NAME].min()),
        max_value=int(full_df[VALUE_DISPLAY_NAME].max()),
        key=f"{filters_title}_value",
    )
    # Handle both tuple and single value cases
    if isinstance(value_filter, (list, tuple)):
        min_val, max_val = value_filter
    else:
        min_val = max_val = value_filter

    similar_players_pool = pd.DataFrame(
        similar_players_pool[
            (similar_players_pool[VALUE_DISPLAY_NAME] >= min_val)
            & (similar_players_pool[VALUE_DISPLAY_NAME] <= max_val)
        ]
    ).copy()

    # Slider for filtering similar players by age
    age_filter = st.sidebar.slider(
        "Filter by age",
        min_value=int(full_df["age"].min()),
        max_value=int(full_df["age"].max()),
        key=f"{filters_title}_age",
    )

    # Handle both tuple and single value cases for age filter
    if isinstance(age_filter, (list, tuple)):
        min_age, max_age = age_filter
    else:
        min_age = max_age = age_filter

    similar_players_pool = pd.DataFrame(
        similar_players_pool[
            (similar_players_pool["age"] >= min_age)
            & (similar_players_pool["age"] <= max_age)
        ]
    ).copy()

    # Multiselect for filtering similar players by nation
    nation_filter: list[str] = st.sidebar.multiselect(
        "Filter by nation",
        similar_players_pool["nation"].unique(),
        key=f"{filters_title}_nation",
    )
    if nation_filter:
        similar_players_pool = pd.DataFrame(
            similar_players_pool[similar_players_pool["nation"].isin(nation_filter)]
        ).copy()

    # Filter on aggregated league to deduplicate players in similar players pool
    similar_players_pool = pd.DataFrame(
        similar_players_pool[similar_players_pool["league"] == AGGREGATED_LEAGUE_NAME]
    ).copy()

    return similar_players_pool


def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Process dataframe to ensure age column is properly formatted."""
    df = df.copy()
    df["age"] = df["age"].apply(
        lambda x: int(x.split("-")[0]) if isinstance(x, str) else int(x)
    )
    return df


def create_position_filter_ui(
    df: pd.DataFrame,
    default_positions: list[str] | None = None,
    key_suffix: str = "",
    help_text: str = "Choose which positions to include in the comparison",
) -> list[str] | None:
    """Create a position filter UI with toggle and multiselect.

    Args:
        df: DataFrame containing player data
        default_positions: List of positions to default to (e.g., current player's position)
        key_suffix: Suffix for unique keys in Streamlit components
        help_text: Help text for the multiselect component

    Returns:
        List of selected positions or None if filtering is disabled
    """
    col1, col2 = st.columns([1, 3])

    with col1:
        filter_by_position = st.toggle(
            "Filter by position",
            value=False,
            key=f"filter_by_position{key_suffix}",
            help="Filter the comparison to show only players in specific positions",
        )

    with col2:
        if filter_by_position:
            # Get all available positions from the data
            available_positions = sorted(df["pos"].unique())

            # Set default positions if provided and they exist in available positions
            if default_positions:
                default_selected = [
                    pos for pos in default_positions if pos in available_positions
                ]
            else:
                default_selected = []

            selected_positions = st.multiselect(
                "Select positions to filter by:",
                available_positions,
                default=default_selected,
                format_func=lambda x: POSITION_MAPPING[x],
                key=f"position_filter{key_suffix}",
                help=help_text,
            )
        else:
            selected_positions = None

    return selected_positions


def filter_and_process_data(
    df: pd.DataFrame,
    filters_title: str = "Filters",
    force_aggregated_league: bool = False,
) -> pd.DataFrame:
    """Apply filters and process the dataframe."""
    # Process age column first
    df = process_dataframe(df)

    # Apply filters
    filtered_df = filter_data(
        df=df,
        filters_title=filters_title,
        force_aggregated_league=force_aggregated_league,
    )
    filtered_df = get_players_candidates(filtered_df, filters_title=filters_title)

    return filtered_df
