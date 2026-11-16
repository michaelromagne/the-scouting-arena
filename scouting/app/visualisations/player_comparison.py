"""
Player comparison functionality for the scouting application.

This module contains comprehensive player comparison tools including:
- Radar charts for single and dual player analysis
- Scatter plot comparisons for statistics analysis
- Similarity scoring and analysis
- Statistics selection and display UI components
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.metrics.pairwise import cosine_similarity

from scouting.app.utils import format_season
from scouting.constants import (
    AGGREGATED_LEAGUE_NAME,
    POSITION_MAPPING,
    SCOUTING_STATISTICS,
    VALUE_DISPLAY_NAME,
)


def get_available_statistics() -> list[tuple[str, str, str]]:
    """Get list of available statistics with their definitions and display names for selection."""
    available_stats = []
    for _, row in SCOUTING_STATISTICS.iterrows():
        if pd.notna(row["stat"]):
            stat_name = row["stat"]
            category = row["category"]
            definition = row["definition"]
            display_name = row["display_name"]
            available_stats.append(
                (f"{category} - {stat_name}", definition, display_name)
            )
    return available_stats


def get_stat_definition(stat_name: str) -> str:
    """Get the definition of a statistic from SCOUTING_STATISTICS."""
    return SCOUTING_STATISTICS[SCOUTING_STATISTICS["stat"] == stat_name][
        "definition"
    ].values[0]


def create_statistics_selector(key_suffix: str = "") -> tuple[str, str]:
    """Create two columns with statistics selectors and return selected stats.

    Args:
        key_suffix: Optional suffix to make keys unique in Streamlit components

    Returns:
        Tuple of (x_stat, y_stat) selected statistics
    """
    col1, col2 = st.columns(2)
    available_stats = get_available_statistics()

    with col1:
        x_stat = st.selectbox(
            "Select X-axis statistic",
            options=[stat[0] for stat in available_stats],
            index=1,
            key=f"x_stat_main{key_suffix}",
            format_func=lambda x: (
                f"[{x.split(' - ')[0]}] {next((stat[2] for stat in available_stats if stat[0] == x), '')}"
            ),
        )
    with col2:
        y_stat = st.selectbox(
            "Select Y-axis statistic",
            options=[stat[0] for stat in available_stats],
            index=0,
            key=f"y_stat_main{key_suffix}",
            format_func=lambda x: (
                f"[{x.split(' - ')[0]}] {next((stat[2] for stat in available_stats if stat[0] == x), '')}"
            ),
        )

    return x_stat, y_stat


def create_comparison_plot(
    df: pd.DataFrame,
    x_stat: str,
    y_stat: str,
    selected_player: tuple[str, str, int] | None = None,
    selected_player2: tuple[str, str, int] | None = None,
    filter_by_position: str | list[str] | None = None,
) -> go.Figure:
    """Create a scatter plot comparing players based on selected statistics.

    Args:
        df: DataFrame containing player statistics
        x_stat: Statistic for x-axis in format "category - stat_name"
        y_stat: Statistic for y-axis in format "category - stat_name"
        selected_player: Tuple of (player_id, player_identifier, season) to highlight, or None
        selected_player2: Tuple of (player_id, player_identifier, season) to highlight as second player, or None
        filter_by_position: Position(s) to filter by (e.g., "FW", ["FW", "MF"], or None for all positions)

    Returns:
        Plotly figure object for the scatter plot
    """
    x_stat_name = x_stat.split(" - ")[1]
    y_stat_name = y_stat.split(" - ")[1]

    # Add information about aggregated league data
    st.markdown("""
    **📊 Visualization Note:** This plot shows one point per player using aggregated statistics across all leagues.
    For players with aggregated data available, that data is used. For others, their primary league data is shown.
    """)

    # Format season in the DataFrame
    df = df.copy()
    df["formatted_season"] = df["season"].apply(format_season)
    df["formatted_pos"] = df["pos"].apply(lambda x: POSITION_MAPPING[x])
    # Only show aggregated league data to have unique points per player
    df = df[df["league"] == AGGREGATED_LEAGUE_NAME]

    # Filter by position if specified
    if filter_by_position:
        if isinstance(filter_by_position, str):
            df = df[df["pos"] == filter_by_position]
            position_filter_text = f" (Filtered by {filter_by_position})"
        else:  # list of positions
            df = df[df["pos"].isin(filter_by_position)]
            position_filter_text = f" (Filtered by {', '.join(filter_by_position)})"
    else:
        position_filter_text = ""

    # Get display names for the statistics
    x_display_name = SCOUTING_STATISTICS[SCOUTING_STATISTICS["stat"] == x_stat_name][
        "display_name"
    ].values[0]
    y_display_name = SCOUTING_STATISTICS[SCOUTING_STATISTICS["stat"] == y_stat_name][
        "display_name"
    ].values[0]

    # Create base scatter plot
    fig = px.scatter(
        df,
        x=x_stat_name,
        y=y_stat_name,
        color="formatted_pos",
        hover_data={
            "player": True,
            "team": True,
            "formatted_season": True,
            "age": True,
            "90s": True,
            VALUE_DISPLAY_NAME: True,
            "pos": True,
            "league": True,
        },
        title=f"Player Comparison: {y_display_name} vs {x_display_name}{position_filter_text}",
        labels={
            x_stat_name: x_display_name,
            y_stat_name: y_display_name,
            "formatted_pos": "Position",
            VALUE_DISPLAY_NAME: VALUE_DISPLAY_NAME,
            "formatted_season": "Season",
            "league": "League",
        },
    )

    # Highlight selected players if provided
    for player_data in [selected_player, selected_player2]:
        if player_data is not None:
            player_id, player_identifier, season = player_data
            selected_player_data = df[
                (df["player_id"] == player_id) & (df["season"] == season)
            ]

            if not selected_player_data.empty:
                fig.add_trace(
                    px.scatter(
                        selected_player_data,
                        x=x_stat_name,
                        y=y_stat_name,
                        color_discrete_sequence=["red"],
                        hover_data={
                            "player": True,
                            "team": True,
                            "formatted_season": True,
                            "age": True,
                            "90s": True,
                            VALUE_DISPLAY_NAME: True,
                            "pos": True,
                            "league": True,
                        },
                    ).data[0]
                )

                # Update marker size and style for the selected player
                fig.data[-1].marker.size = 20
                fig.data[-1].marker.symbol = "star"
                fig.data[-1].marker.color = "orange"
                fig.data[-1].marker.line.width = 2
                fig.data[-1].marker.line.color = "black"
                fig.data[-1].marker.opacity = 1.0
                fig.data[-1].name = f"{player_identifier} (Selected)"

    return fig


def get_single_player_radar(
    player_stats: pd.Series,
    categories: list[str],
) -> go.Figure:
    """Create a radar plot for a single player's stats.

    Args:
        player_stats: Series containing the player's statistics
        categories: List of categories to plot on the radar

    Returns:
        Plotly figure object for the radar chart
    """
    fig = go.Figure()

    score_list = [category for category in categories]

    player_stats_list = list(player_stats[score_list].values)
    fig.add_trace(
        go.Scatterpolar(
            r=player_stats_list,
            theta=score_list,
            fill="toself",
        )
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[min(player_stats_list) - 1, max(player_stats_list) + 1],
            )
        ),
        showlegend=False,
    )
    return fig


def plot_two_players_radar_comparison(
    categories: list[str],
    player_a_stats: pd.Series,
    player_b_stats: pd.Series,
):
    """Create a radar plot comparing two players' stats.

    Args:
        categories: List of categories to plot on the radar
        player_a_stats: First player's statistics
        player_b_stats: Second player's statistics
    """
    fig = go.Figure()

    # Convert all values to string for legend name
    player_a_stats.season = player_a_stats.season.astype(str)
    player_b_stats.season = player_b_stats.season.astype(str)

    player_a_scores = list(player_a_stats[categories].values)
    player_b_scores = list(player_b_stats[categories].values)
    fig.add_trace(
        go.Scatterpolar(
            r=player_a_scores,
            theta=categories,
            fill="toself",
            name=f"{player_a_stats['player']} - {player_a_stats['team']} ({format_season(player_a_stats['season'])})",
            line_color="#4d8ef7",
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=player_b_scores,
            theta=categories,
            fill="toself",
            name=f"{player_b_stats['player']} - {player_b_stats['team']} ({format_season(player_b_stats['season'])})",
            line_color="#ed5a5d",
        )
    )

    fig.update_layout(
        title=dict(
            text="Player Comparison",
            x=0.5,
            xanchor="center",
            yanchor="top",
            font=dict(size=18, color="black", family="Arial"),
            pad=dict(b=40, t=40),
        ),
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[
                    min(min(player_a_scores), min(player_b_scores)) - 1,
                    max(max(player_a_scores), max(player_b_scores)) + 1,
                ],
            )
        ),
        showlegend=True,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.8),
    )
    st.plotly_chart(fig, use_container_width=True)
    return fig


def display_similarity_score(
    player_data_1: pd.Series, player_data_2: pd.Series
) -> None:
    """Display the similarity score between two players in a prominent way.

    Args:
        player_data_1: First player's data
        player_data_2: Second player's data
    """
    # Convert to numpy arrays for cosine similarity calculation
    player_1_scaled = player_data_1[
        [f"{stat}_scaled" for stat in SCOUTING_STATISTICS["stat"].values]
    ].to_numpy()
    player_2_scaled = player_data_2[
        [f"{stat}_scaled" for stat in SCOUTING_STATISTICS["stat"].values]
    ].to_numpy()

    similarity_score = cosine_similarity(
        player_1_scaled.reshape(1, -1),
        player_2_scaled.reshape(1, -1),
    )[0][0]

    st.markdown(
        f"""
    <div style='text-align: center; margin: 20px;'>
        <h2>Similarity Score: {similarity_score:.2f}</h2>
    </div>
    """,
        unsafe_allow_html=True,
    )
