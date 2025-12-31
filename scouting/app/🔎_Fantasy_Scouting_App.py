import logging

import streamlit as st

from scouting.app.league_handling import get_player_data_with_league_handling
from scouting.app.utils import (
    create_player_identifier,
    format_season,
    get_player_stats_categories,
    get_similar_players,
)
from scouting.app.visualisations import (
    create_barplot,
    create_comparison_plot,
    create_position_filter_ui,
    create_statistics_selector,
    display_player_profile,
    display_player_statistics,
    filter_data,
    get_players_candidates,
    get_single_player_radar,
    plot_best_and_worst_quantiles,
)
from scouting.constants import ROOT_PATH, VALUE_DISPLAY_NAME
from scouting.data_transform.player_stats import load_combined_player_data

logging.basicConfig(level=logging.INFO)

# Load combined data from separate CSV files
try:
    df = load_combined_player_data(ROOT_PATH / "data")
except FileNotFoundError as e:
    st.error(f"Data files not found: {e}")
    st.info(
        "Please run the player stats extraction first to generate the required CSV files."
    )
    st.stop()

# Streamlit app setup
st.set_page_config(page_title="Fantasy Scouting App", layout="wide")
st.title("Fantasy Scouting App")

# Sidebar filters
filtered_df = filter_data(
    df=df, filters_title="Player selection filters", filters_subtitle=""
)

# Player selection
st.write("")
st.markdown("""
### 🔍 Player Scouting Analysis

Dive into a detailed analysis of a single player using our advanced scouting tool. Analyze player profiles across different seasons and competitions.
""")

st.write("")

st.markdown("""
##### 📊 Key Features:
- Analyze players across different seasons
- Get comprehensive scouting reports for each player
- Players are ranked by their market value

##### 🎯 Filter Options:
- Player Position
- League
- Team
- Season

ℹ️ Note: A market value of -1 indicates data not available in our database
""")
filtered_df = filtered_df.sort_values(
    by=[VALUE_DISPLAY_NAME, "season", "player"],
    ascending=[False, False, False],
)

# Get unique players
unique_players = filtered_df[filtered_df["league"] == "Aggregated (All Leagues)"].copy()

unique_players["player_identifier"] = unique_players.apply(
    create_player_identifier, axis=1
)

st.markdown(
    """
    <style>
        .stSelectbox [data-baseweb=select] span{
            max-width: 350px;
            font-size: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Convert DataFrame to list of dictionaries for selectbox
player_options = (
    unique_players[["player_identifier", "player_id"]]
    .drop_duplicates()
    .to_dict("records")
)

selected_player_identifier = st.selectbox(
    "Select a player to analyze ⬇︎",
    player_options,
    format_func=lambda x: x["player_identifier"],
    index=None,
)

if selected_player_identifier is not None:
    player_id = selected_player_identifier["player_id"]
    player_identifier = selected_player_identifier["player_identifier"]

    # Get available seasons for the player
    player_seasons = filtered_df[filtered_df["player_id"] == player_id][
        "season"
    ].unique()

    selected_season: int = st.selectbox(
        "Select season",
        player_seasons,
        format_func=format_season,
        key="single_player_season",
    )

    # Get player data with league handling
    all_player_data, selected_option, player_data = (
        get_player_data_with_league_handling(
            filtered_df,
            player_id,
            selected_season,
            key_suffix="single_player",
        )
    )

    if len(all_player_data) == 0:
        st.stop()

    # Display player profile and radar side by side
    col1, col2 = st.columns([1, 1])

    with col1:
        display_player_profile(st, player_data)

    with col2:
        player_stats_categories = get_player_stats_categories(player_data["pos"])
        radar_categories = list(player_stats_categories["category"].unique())
        radar_fig = get_single_player_radar(player_data, radar_categories)
        st.plotly_chart(radar_fig, use_container_width=True)

    # Get available categories for the player's position
    available_categories = list(player_stats_categories["category"].unique())
    selected_category = st.selectbox(
        "Select a category to view detailed statistics",
        available_categories,
        format_func=lambda x: x.replace("_", " ").title(),
    )

    # Display the statistics for the selected category
    if selected_category is not None:
        display_player_statistics(
            player_data,
            player_stats_categories,
            selected_category,
            key_suffix="_single_player",
        )

    # Add similar players section
    st.markdown("---")
    st.markdown("### Similar Players")
    st.markdown("Use the filters in the sidebar to refine the pool of similar players")

    # Add similar players filters to sidebar
    st.sidebar.markdown("---")
    filtered_players_candidates = filter_data(
        df=df,
        filters_title="Similar players filters",
        filters_subtitle="Refine the pool of similar players: filter by value, age, nation, position, league, team, season.",
    )

    similar_players_candidates = get_players_candidates(filtered_players_candidates)
    similar_players = get_similar_players(
        player_data, similar_players_candidates, top_k=20
    )

    if similar_players is not None:
        st.dataframe(
            similar_players,
            hide_index=True,
        )

    # Add statistics comparison section
    st.markdown("---")
    st.markdown("### Statistics Comparison")
    st.markdown("Compare the selected player with others based on any two statistics.")
    x_stat, y_stat = create_statistics_selector(key_suffix="_single")

    # Add position filter using the dedicated function
    selected_positions = create_position_filter_ui(
        similar_players_candidates,
        default_positions=[player_data["pos"]],
        key_suffix="_single",
    )

    comparison_fig = create_comparison_plot(
        similar_players_candidates,
        x_stat,
        y_stat,
        selected_player=(player_id, player_identifier, selected_season),
        filter_by_position=selected_positions,
    )
    st.plotly_chart(comparison_fig, use_container_width=True)

    # Display barplots and scouting reports
    st.markdown("---")
    st.subheader("Scouting reports")

    # Add toggle for position-based quantiles
    use_position_quantiles = st.toggle(
        "Show position-based quantiles",
        value=True,
        key="quantiles_toggle",
    )

    # Display quantiles in the center
    plot_best_and_worst_quantiles(
        player_data, use_position_quantiles=use_position_quantiles
    )

    # Display barplot below
    create_barplot(
        player_data,
        player_stats_categories,
        st,
        use_position_quantiles=use_position_quantiles,
    )
