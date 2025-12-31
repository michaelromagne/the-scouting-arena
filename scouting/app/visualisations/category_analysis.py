"""
Category analysis functionality for the scouting application.

This module contains functions for analyzing and displaying top players
by category, penalty takers, and detailed player statistics.
"""

import pandas as pd
import streamlit as st

from scouting.app.utils import COLUMNS_TO_PLOT, create_player_identifier, format_season
from scouting.constants import SCOUTING_STATISTICS, STATISTIC_THRESHOLDS

from .charts import (
    create_bar_chart,
    create_category_tooltip,
    create_penalty_takers_tooltip,
    get_column_tooltips,
)


def apply_category_thresholds(
    df: pd.DataFrame, category: str, custom_thresholds: dict | None = None
) -> pd.DataFrame:
    """Apply minimum thresholds to filter out players with insufficient activity.

    Args:
        df: DataFrame containing player data
        category: Category name to analyze
        custom_thresholds: Optional custom thresholds to override defaults

    Returns:
        Filtered DataFrame with players meeting minimum thresholds
    """
    category_cols = list(
        SCOUTING_STATISTICS[SCOUTING_STATISTICS["category"] == category]["stat"].values
    )

    # Use custom thresholds if provided, otherwise use defaults
    thresholds_to_use = (
        custom_thresholds if custom_thresholds is not None else STATISTIC_THRESHOLDS
    )

    # Create a mask for players that meet all relevant thresholds
    threshold_mask = pd.Series([True] * len(df), index=df.index)

    for stat in category_cols:
        if stat in thresholds_to_use:
            threshold_value = thresholds_to_use[stat]

            # Check if the statistic exists in the dataframe
            if stat in df.columns:
                # Apply threshold: player must meet or exceed the minimum value
                stat_mask = df[stat] >= threshold_value
                threshold_mask = threshold_mask & stat_mask

    filtered_df = df[threshold_mask].copy()

    if len(filtered_df) == 0:
        st.warning(
            f"No players meet the minimum thresholds for the {category} category. Consider lowering the thresholds."
        )
        return df  # Return original dataframe if no players meet thresholds

    return filtered_df


def display_penalty_takers(df: pd.DataFrame, top_k: int) -> None:
    """Display penalty takers section with visualization and table.

    Args:
        df: DataFrame containing player data with penalty statistics
        top_k: Number of top players to display
    """
    # Calculate penalty conversion rate
    penalty_df = df.sort_values(by="penalty", ascending=False).head(top_k).copy()
    penalty_df["Conversion Rate"] = (
        penalty_df["Standard_PK"] / penalty_df["Standard_PKatt"] * 100
    ).round(1)

    # Create unique identifier for bar chart to prevent stacking
    penalty_df["player_unique"] = (
        penalty_df["player"]
        + " - "
        + penalty_df["team"]
        + " ("
        + penalty_df["season"].apply(format_season)
        + ")"
    )

    # Create tooltip
    penalty_df = create_penalty_takers_tooltip(penalty_df)

    # Create and display bar chart
    fig = create_bar_chart(
        penalty_df,
        x_col="player_unique",  # Use unique identifier instead of just player name
        y_col="penalty",  # Use penalty score for bar height
        color_col="Conversion Rate",  # Use conversion rate for color
        title="Penalty Takers Performance",
        labels={
            "player_unique": "Player - Team (Season)",
            "penalty": "Penalty Score",
            "Conversion Rate": "Conversion Rate (%)",
        },
        hover_data={"hover_text": True},
        custom_data=["hover_text"],
    )
    st.plotly_chart(fig, use_container_width=True)

    # Display the penalty takers table
    penalty_stats = (
        penalty_df[
            COLUMNS_TO_PLOT
            + ["penalty", "Standard_PK", "Standard_PKatt", "Conversion Rate"]
        ]
        .rename(
            columns={
                "Standard_PK": "Scored",
                "Standard_PKatt": "Attempted",
            }
        )
        .reset_index(drop=True)
    )

    # Index starts at 1 for rankings
    penalty_stats.index = penalty_stats.index + 1
    penalty_stats["season"] = penalty_stats["season"].astype(str)

    column_tooltips = get_column_tooltips(penalty_stats)

    # Create a styled DataFrame with tooltips
    styled_df = penalty_stats.style.background_gradient(
        subset=["Conversion Rate"],
        cmap="RdYlGn",
        vmin=0,
        vmax=100,
    )

    st.dataframe(
        styled_df,
        use_container_width=True,
        column_config={
            col: st.column_config.Column(
                help=tooltip,
            )
            for col, tooltip in column_tooltips.items()
        },
    )


def display_category(df: pd.DataFrame, category: str, top_k: int) -> None:
    """Display category section with visualization and table.

    Args:
        df: DataFrame containing player data
        category: Category name to analyze
        top_k: Number of top players to display
    """

    filtered_df = apply_category_thresholds(df, category)

    category_cols = list(
        SCOUTING_STATISTICS[SCOUTING_STATISTICS["category"] == category]["stat"].values
    )

    best_stats = (
        filtered_df.sort_values(by=category, ascending=False)
        .head(top_k)
        .drop(columns=["player_id", "born"])[
            COLUMNS_TO_PLOT + [category] + category_cols
        ]
        .reset_index(drop=True)
    )

    # Replace stat column names with display names
    stat_to_display = dict(
        zip(SCOUTING_STATISTICS["stat"], SCOUTING_STATISTICS["display_name"])
    )

    best_stats = best_stats.rename(columns=stat_to_display)

    # Create unique identifier for bar chart to prevent stacking
    best_stats["player_unique"] = best_stats.apply(create_player_identifier, axis=1)

    # Index starts at 1 for rankings
    best_stats.index = best_stats.index + 1
    best_stats["season"] = best_stats["season"].astype(str)

    # Get the renamed category columns for tooltip creation, if not available, use the original column name
    renamed_category_cols = [stat_to_display.get(col, col) for col in category_cols]
    best_stats = create_category_tooltip(best_stats, category, renamed_category_cols)

    fig = create_bar_chart(
        best_stats,
        x_col="player_unique",  # Use unique identifier instead of just player name
        y_col=category,
        color_col=category,
        title=f"Top {category} Performers",
        labels={"player_unique": "Player - Team (Season)", category: category},
        hover_data={"hover_text": True},
        custom_data=["hover_text"],
    )
    st.plotly_chart(fig, use_container_width=True)

    column_tooltips = get_column_tooltips(best_stats)

    # Create a styled DataFrame with tooltips
    styled_df = best_stats.style.background_gradient(
        subset=[category],
        cmap="RdYlGn",
        vmin=best_stats[category].min(),
        vmax=best_stats[category].max(),
    )

    st.dataframe(
        styled_df,
        use_container_width=True,
        column_config={
            col: st.column_config.Column(
                help=tooltip,
            )
            for col, tooltip in column_tooltips.items()
        },
    )


def display_player_statistics(
    player_data: pd.Series,
    player_stats_categories: pd.DataFrame,
    selected_category: str,
    key_suffix: str = "",
) -> None:
    """Display detailed statistics for a player in a specific category.

    Args:
        player_data: Series containing the player's statistics
        player_stats_categories: DataFrame containing the categories and their statistics
        selected_category: The selected category to display statistics for
        key_suffix: Optional suffix to make keys unique in Streamlit components
    """
    # Get statistics for the selected category
    category_stats = player_stats_categories[
        player_stats_categories["category"] == selected_category
    ]["stat"].unique()

    # Add toggle for position-based quantiles
    use_position_quantiles = st.toggle(
        "Show position-based quantiles",
        value=True,
        key=f"quantiles_toggle_3{key_suffix}",
    )
    quantile_prefix = "quantile_pos_" if use_position_quantiles else "quantile_season_"

    # Create a dataframe with the statistics and their descriptions
    stats_data = []
    for stat in category_stats:
        if "90" in stat:
            # Skip per 90 stats because they are computed separately
            continue
        stat_value = player_data[stat]
        stat_per_90 = player_data[f"{stat}_per_90"]
        stat_quantile = player_data[f"{quantile_prefix}{stat}_per_90"]
        stat_definition = SCOUTING_STATISTICS[SCOUTING_STATISTICS["stat"] == stat][
            "definition"
        ].values[0]

        # Get the display name from SCOUTING_STATISTICS
        display_name = SCOUTING_STATISTICS[SCOUTING_STATISTICS["stat"] == stat][
            "display_name"
        ].values[0]

        stats_data.append(
            {
                "Statistic": display_name,
                "Value": stat_value,
                "Per 90": round(stat_per_90, 2),
                "Percentile": int(stat_quantile),
                "Description": stat_definition,
            }
        )

    stats_df = pd.DataFrame(stats_data)

    # Display the dataframe with tooltips
    st.dataframe(
        stats_df,
        use_container_width=True,
        column_config={
            "Statistic": st.column_config.TextColumn(
                "Statistic", help="The name of the statistic"
            ),
            "Value": st.column_config.NumberColumn(
                "Value", help="The raw value of the statistic", format="%.2f"
            ),
            "Per 90": st.column_config.NumberColumn(
                "Per 90", help="The value per 90 minutes played", format="%.2f"
            ),
            "Percentile": st.column_config.NumberColumn(
                "Percentile",
                help="The percentile rank of the player for this statistic",
                format="%d",
            ),
            "Description": st.column_config.TextColumn(
                "Description",
                help="Detailed description of what the statistic measures",
            ),
        },
    )
