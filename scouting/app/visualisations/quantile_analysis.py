"""
Quantile analysis functionality for the scouting application.

This module contains functions for analyzing player statistics in terms of
percentiles, both position-based and season-based comparisons.
"""

import plotly.graph_objects as go
import streamlit as st

from scouting.constants import SCOUTING_STATISTICS


def _display_quantiles(
    player_data,
    quantile_columns,
    quantile_prefix,
    title_prefix,
    stat_display_mapping,
    stat_category_mapping,
):
    """Helper function to display top and worst quantiles.

    Args:
        player_data: Series containing the player's data
        quantile_columns: List of quantile column names
        quantile_prefix: Prefix to remove from quantile column names
        title_prefix: Prefix for the section titles
        stat_display_mapping: Mapping of stat names to display names
        stat_category_mapping: Mapping of stat names to categories
    """
    # Display top quantiles
    st.markdown(
        f"<h4 style='text-align: center; background-color: #6cc46c;'>Top {title_prefix} Quantiles</h4>",
        unsafe_allow_html=True,
    )
    top_quantiles = player_data[quantile_columns].astype(int).nlargest(5)
    st.markdown("<ul>", unsafe_allow_html=True)
    for stat, quantile_value in top_quantiles.items():
        base_stat = stat.replace(quantile_prefix, "").replace("_per_90", "")
        display_name = stat_display_mapping[base_stat]
        category = stat_category_mapping[base_stat]
        st.markdown(
            f"""
            <li><strong>{display_name}</strong>: {quantile_value}%, actual value: {player_data[base_stat]} [{category}]</li>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</ul>", unsafe_allow_html=True)

    # Display worst quantiles
    st.markdown(
        f"<h4 style='text-align: center; background-color: #d16464;'>Worst {title_prefix} Quantiles</h4>",
        unsafe_allow_html=True,
    )
    worst_quantiles = player_data[quantile_columns].astype(int).nsmallest(5)
    st.markdown("<ul>", unsafe_allow_html=True)
    for stat, quantile_value in worst_quantiles.items():
        base_stat = stat.replace(quantile_prefix, "").replace("_per_90", "")
        display_name = stat_display_mapping[base_stat]
        category = stat_category_mapping[base_stat]
        st.markdown(
            f"""
            <li><strong>{display_name}</strong>: {quantile_value}%, actual value: {player_data[base_stat]} [{category}]</li>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</ul>", unsafe_allow_html=True)


def plot_best_and_worst_quantiles(player_data, use_position_quantiles=True):
    """Display best and worst quantile stats for a player.

    Args:
        player_data: Series containing the player's data with quantile columns
    """
    stat_display_mapping = {
        stat: display_name
        for _, (stat, display_name) in SCOUTING_STATISTICS[
            ["stat", "display_name"]
        ].iterrows()
    }
    stat_category_mapping = {
        stat: category
        for _, (stat, category) in SCOUTING_STATISTICS[["stat", "category"]].iterrows()
    }
    player_info = player_data.index.to_list()

    if use_position_quantiles:
        # Get both position-based and season-based quantile columns
        quantile_pos_columns = [col for col in player_info if "quantile_pos_" in col]
        quantile_season_columns = [
            col for col in player_info if "quantile_season_" in col
        ]

        # Create tabs for position-based and season-based quantiles
        tab1, tab2 = st.tabs(["Position-based Quantiles", "Season-based Quantiles"])

        with tab1:
            _display_quantiles(
                player_data,
                quantile_pos_columns,
                "quantile_pos_",
                "Position-based",
                stat_display_mapping,
                stat_category_mapping,
            )

        with tab2:
            _display_quantiles(
                player_data,
                quantile_season_columns,
                "quantile_season_",
                "Season-based",
                stat_display_mapping,
                stat_category_mapping,
            )
    else:
        # Only show season-based quantiles
        quantile_season_columns = [
            col for col in player_info if "quantile_season_" in col
        ]

        _display_quantiles(
            player_data,
            quantile_season_columns,
            "quantile_season_",
            "Season-based",
            stat_display_mapping,
            stat_category_mapping,
        )


def create_barplot(
    player_data,
    stats_categories,
    streamlit_col,
    use_position_quantiles=True,
):
    """Create bar plots showing quantile performance by category.

    Args:
        player_data: Series containing the player's data
        stats_categories: DataFrame containing categories and their statistics
        streamlit_col: Streamlit column to display the plots in
    """
    figures = []

    quantile_prefix = "quantile_pos_" if use_position_quantiles else "quantile_season_"

    for category in stats_categories["category"].unique():
        category_stats = stats_categories[stats_categories["category"] == category][
            "stat"
        ].unique()
        # Filter out per 90 stats because they are computed separately
        category_stats = [stat for stat in category_stats if "90" not in stat]
        quantile_values = [
            player_data[f"{quantile_prefix}{stat}_per_90"] for stat in category_stats
        ]
        quantile_labels = []
        for stat in category_stats:
            # Get the display name from SCOUTING_STATISTICS
            display_name = SCOUTING_STATISTICS[SCOUTING_STATISTICS["stat"] == stat][
                "display_name"
            ].values[0]
            quantile_labels.append(display_name)

        colors = [
            "#d16464" if quantile < 50 else "#fcc556" if quantile < 80 else "#6cc46c"
            for quantile in quantile_values
        ]

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=quantile_values[::-1],
                y=quantile_labels[::-1],
                orientation="h",
                marker=dict(color=colors[::-1]),
                text=[f"{int(quantile)}" for quantile in quantile_values[::-1]],
                textposition="inside",
                insidetextanchor="end",
                textfont=dict(color="white"),
                textangle=0,
                hovertext=[
                    f"{SCOUTING_STATISTICS[SCOUTING_STATISTICS['stat'] == stat]['display_name'].values[0]}: {SCOUTING_STATISTICS[SCOUTING_STATISTICS['stat'] == stat]['definition'].values[0]}<br>Actual value: {player_data[stat]}<br>Per 90s value: {round(player_data[f'{stat}_per_90'], 2)}<br>Quantile: {int(quantile)}"
                    for stat, quantile in zip(
                        category_stats[::-1], quantile_values[::-1]
                    )
                ],
                hoverinfo="text",
            )
        )

        fig.update_layout(
            title=dict(
                text=f"{category.capitalize()}",
                x=0.5,
                xanchor="center",
                yanchor="top",
                font=dict(size=14, color="black", family="Arial"),
            ),
            xaxis_title="Quantile",
            yaxis_title="",
            xaxis=dict(range=[0, 100]),
            height=500,
            margin=dict(l=10, r=10, t=60, b=30),
        )

        figures.append((category, fig))

    for category, fig in figures:
        streamlit_col.plotly_chart(fig, use_container_width=False)
