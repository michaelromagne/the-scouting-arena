"""
General chart and plot components for the scouting application.

This module contains reusable chart components, tooltip functions,
and specialized visualizations like t-SNE plots.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE

from scouting.app.utils import format_season
from scouting.constants import (
    POSITION_MAPPING,
    SCOUTING_STATISTICS,
    VALUE_DISPLAY_NAME,
)


@st.cache_data(show_spinner=False)
def tse_fit_transform(stats_with_tfmkt_value, per_90_columns):
    """Fit and transform data using t-SNE for dimensionality reduction."""
    tsne = TSNE(n_components=2, perplexity=30, random_state=42)
    return tsne.fit_transform(stats_with_tfmkt_value[per_90_columns].fillna(0))


def plot_tsne_player(stats_with_tfmkt_value: pd.DataFrame, per_90_columns: list[str]):
    """Create a t-SNE visualization of football players.

    Args:
        stats_with_tfmkt_value: DataFrame containing player statistics and market values
        per_90_columns: list of per-90 statistics columns to use for clustering
    """
    with st.spinner("Computing player positions in figure..."):
        x_embedded = tse_fit_transform(stats_with_tfmkt_value, per_90_columns)
        kmeans = KMeans(10)
        stats_with_tfmkt_value["cluster"] = kmeans.fit(x_embedded).labels_

    df_vis = pd.DataFrame(
        {
            "x": x_embedded[:, 0],
            "y": x_embedded[:, 1],
            "Player Name": stats_with_tfmkt_value["player"],
            "Season": stats_with_tfmkt_value["season"].apply(format_season),
            "Position": stats_with_tfmkt_value["pos"].apply(
                lambda x: POSITION_MAPPING[x]
            ),
            "Cluster": stats_with_tfmkt_value["cluster"].astype(str),
            VALUE_DISPLAY_NAME: stats_with_tfmkt_value[VALUE_DISPLAY_NAME].fillna(0),
        }
    )

    special_players = ["Kylian Mbappé", "Lionel Messi", "Neymar"]
    df_vis["Size"] = (
        df_vis[VALUE_DISPLAY_NAME] / df_vis[VALUE_DISPLAY_NAME].max() * 10
    ).clip(lower=1)  # Scale between 0-10
    df_vis["Size"] = df_vis.apply(
        lambda x: 10 if x["Player Name"] in special_players else x["Size"], axis=1
    )
    df_vis["Symbol"] = df_vis["Player Name"].apply(
        lambda x: "star" if x in special_players else "circle"
    )

    fig = px.scatter(
        df_vis,
        x="x",
        y="y",
        color="Cluster",
        size="Size",
        symbol="Symbol",
        hover_data=[
            "Player Name",
            "Position",
            "Season",
            VALUE_DISPLAY_NAME,
        ],
        title="t-SNE Visualization of Football Players",
        template="plotly_dark",
    )

    fig.update_layout(
        height=800,
    )

    st.plotly_chart(fig, use_container_width=True)


def create_penalty_takers_tooltip(df: pd.DataFrame) -> pd.DataFrame:
    """Create tooltip text for penalty takers visualization.

    Args:
        df: DataFrame containing penalty takers data

    Returns:
        DataFrame with added hover_text column
    """
    df["hover_text"] = (
        "Player: "
        + df["player"].astype(str)
        + "<br>"
        + "Team: "
        + df["team"].astype(str)
        + "<br>"
        + f"{VALUE_DISPLAY_NAME}: "
        + df[VALUE_DISPLAY_NAME].astype(str)
        + "<br>"
        + "Position: "
        + df["pos"].apply(lambda x: POSITION_MAPPING[x]).astype(str)
        + "<br>"
        + "Age: "
        + df["age"].astype(str)
        + "<br>"
        + "League: "
        + df["league"].astype(str)
        + "<br>"
        + "Season: "
        + df["season"].apply(format_season).astype(str)
        + "<br>"
        + "Penalties Scored: "
        + df["Standard_PK"].astype(str)
        + "<br>"
        + "Penalties Attempted: "
        + df["Standard_PKatt"].astype(str)
        + "<br>"
        + "Conversion Rate: "
        + df["Conversion Rate"].astype(str)
        + "%"
    )
    return df


def create_category_tooltip(
    df: pd.DataFrame, category: str, category_cols: list[str]
) -> pd.DataFrame:
    """Create tooltip text for category visualization.

    Args:
        df: DataFrame containing category data
        category: Category name
        category_cols: list of category-specific columns

    Returns:
        DataFrame with added hover_text column
    """
    df["hover_text"] = (
        "Player: "
        + df["player"].astype(str)
        + "<br>"
        + "Team: "
        + df["team"].astype(str)
        + "<br>"
        + f"{VALUE_DISPLAY_NAME}: "
        + df[VALUE_DISPLAY_NAME].astype(str)
        + "<br>"
        + "Position: "
        + df["pos"].apply(lambda x: POSITION_MAPPING[x]).astype(str)
        + "<br>"
        + "Age: "
        + df["age"].astype(str)
        + "<br>"
        + "League: "
        + df["league"].astype(str)
        + "<br>"
        + "Season: "
        + df["season"].apply(format_season).astype(str)
        + "<br>"
        + category
        + ": "
        + df[category].round(2).astype(str)
        + "<br>"
    )

    # Add category-specific stats to hover text
    for stat in category_cols:
        # Get display name for the statistic
        if stat in SCOUTING_STATISTICS["stat"].values:
            display_name = SCOUTING_STATISTICS[SCOUTING_STATISTICS["stat"] == stat][
                "display_name"
            ].values[0]
            df["hover_text"] += (
                display_name + ": " + df[stat].round(2).astype(str) + "<br>"
            )
        else:
            df["hover_text"] += stat + ": " + df[stat].round(2).astype(str) + "<br>"
    return df


def create_bar_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    color_col: str,
    title: str,
    labels: dict,
    hover_data: dict,
    custom_data: list[str],
) -> go.Figure:
    """Create a bar chart with custom tooltips.

    Args:
        df: DataFrame containing the data
        x_col: Column name for x-axis
        y_col: Column name for y-axis
        color_col: Column name for color mapping
        title: Chart title
        labels: Dictionary of axis labels
        hover_data: Dictionary of hover data
        custom_data: list of custom data columns

    Returns:
        Plotly figure object
    """
    fig = px.bar(
        df,
        x=x_col,
        y=y_col,
        color=color_col,
        color_continuous_scale="RdYlGn",
        title=title,
        labels=labels,
        hover_data=hover_data,
        custom_data=custom_data,
    )
    fig.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
    fig.update_layout(
        xaxis_tickangle=45,
        xaxis=dict(
            tickmode="array",
            ticktext=df[x_col],
            tickvals=df[x_col],
            tickfont=dict(size=10),
        ),
        margin=dict(l=10, r=10, t=30, b=100),  # Increase bottom margin for labels
    )
    return fig


def get_column_tooltips(df: pd.DataFrame) -> dict:
    """Create tooltips for DataFrame columns based on SCOUTING_STATISTICS.

    Args:
        df: DataFrame to create tooltips for

    Returns:
        Dictionary mapping column names to tooltip text
    """
    tooltips = {}
    for column in df.columns:
        # Check if the column is in SCOUTING_STATISTICS
        if column in SCOUTING_STATISTICS["stat"].values:
            display_name = SCOUTING_STATISTICS[SCOUTING_STATISTICS["stat"] == column][
                "display_name"
            ].values[0]
            definition = SCOUTING_STATISTICS[SCOUTING_STATISTICS["stat"] == column][
                "definition"
            ].values[0]
            tooltips[column] = f"{display_name}: {definition}"
        # Special cases for penalty takers
        elif column == "Scored":
            tooltips[column] = "Penalties Scored: Number of penalties scored"
        elif column == "Attempted":
            tooltips[column] = "Penalties Attempted: Number of penalties attempted"
        elif column == "Conversion Rate":
            tooltips[column] = (
                "Conversion Rate: Percentage of penalties scored (Scored/Attempted * 100)"
            )
    return tooltips
