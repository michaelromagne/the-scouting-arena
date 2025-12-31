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
    display_similarity_score,
    filter_data,
    get_players_candidates,
    plot_best_and_worst_quantiles,
    plot_two_players_radar_comparison,
)
from scouting.constants import ROOT_PATH, VALUE_DISPLAY_NAME
from scouting.data_transform.player_stats import load_combined_player_data

# Page setup
st.set_page_config(page_title="Player Comparison", layout="wide")
st.title("Player Comparison")
st.write("")
st.markdown("""
### 🔍 Player Comparison & Scouting Analysis

Dive into a detailed comparison of two players using our advanced analysis tool. It allows you to analyze player profiles across different seasons and competitions.
""")

st.write("")

st.markdown("""
##### 📊 Key Features:
- Compare players using a sophisticated similarity score (-1 to 1 scale, 1 being the most similar) based on player statistics
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

# Load and filter data
try:
    df = load_combined_player_data(ROOT_PATH / "data")
except FileNotFoundError as e:
    st.error(f"Data files not found: {e}")
    st.info(
        "Please run the player stats extraction first to generate the required CSV files."
    )
    st.stop()
filtered_df = filter_data(
    df=df,
    filters_title="Player selection filters",
    filters_subtitle="",
)

filtered_df = filtered_df.sort_values(
    by=[VALUE_DISPLAY_NAME, "season", "player"],
    ascending=[False, False, False],
)

# Get unique players with their most recent season
unique_players = filtered_df[filtered_df["league"] == "Aggregated (All Leagues)"].copy()

unique_players["player_identifier"] = unique_players.apply(
    create_player_identifier, axis=1
)

st.markdown(
    """
    <style>
        .stMultiSelect [data-baseweb=select] span{
            max-width: 250px;
            font-size: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Convert DataFrame to list of dictionaries for multiselect
player_options = (
    unique_players[["player_identifier", "player_id"]]
    .drop_duplicates()
    .to_dict("records")
)

selected_players: list[dict] = st.multiselect(
    "Select 2 players to compare ⬇︎",
    player_options,
    max_selections=2,
    format_func=lambda x: x["player_identifier"],
)

# Extract player IDs and identifiers
if len(selected_players) == 2:
    selected_player_1, selected_player_2 = selected_players

    # Extract player ID and identifier
    player_1_id = selected_player_1["player_id"]
    player_1_identifier = selected_player_1["player_identifier"]
    player_2_id = selected_player_2["player_id"]
    player_2_identifier = selected_player_2["player_identifier"]

    # Get available seasons for each player
    player_1_seasons = filtered_df[filtered_df["player_id"] == player_1_id][
        "season"
    ].unique()
    player_2_seasons = filtered_df[filtered_df["player_id"] == player_2_id][
        "season"
    ].unique()

    # Create columns for player profiles and season selection
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Player 1")
        selected_season_1: int = st.selectbox(
            "Select season",
            player_1_seasons,
            format_func=format_season,
            key="player1_season",
        )

        # Get player data with league handling
        all_player_data_1, selected_option_1, player_data_1 = (
            get_player_data_with_league_handling(
                filtered_df,
                player_1_id,
                selected_season_1,
                key_suffix="player1",
            )
        )

        if len(all_player_data_1) == 0:
            st.error(
                f"No data found for {player_1_identifier} for season {selected_season_1}"
            )
            st.stop()

        display_player_profile(col1, player_data_1)

    with col2:
        st.markdown("### Player 2")
        selected_season_2: int = st.selectbox(
            "Select season",
            player_2_seasons,
            format_func=format_season,
            key="player2_season",
        )

        # Get player data with league handling
        all_player_data_2, selected_option_2, player_data_2 = (
            get_player_data_with_league_handling(
                filtered_df,
                player_2_id,
                selected_season_2,
                key_suffix="player2",
            )
        )

        if len(all_player_data_2) == 0:
            st.error(
                f"No data found for {player_2_identifier} for season {selected_season_2}"
            )
            st.stop()

        display_player_profile(col2, player_data_2)
else:
    st.warning("Please select exactly two players.")
    st.stop()

# Display similarity score
display_similarity_score(player_data_1, player_data_2)

player_1_stats_categories = get_player_stats_categories(player_data_1["pos"])
player_2_stats_categories = get_player_stats_categories(player_data_2["pos"])

if not player_1_stats_categories.equals(player_2_stats_categories):
    st.warning("Players do not have the same statistics categories.")
    st.stop()

# Radar Chart
plot_two_players_radar_comparison(
    list(player_1_stats_categories["category"].unique()), player_data_1, player_data_2
)

# Display player statistics for selected category
st.markdown("---")
st.markdown("### Player Statistics Comparison")

# Get available categories for the players' position
available_categories = list(player_1_stats_categories["category"].unique())
selected_category = st.selectbox(
    "Select a category to view detailed statistics",
    available_categories,
    format_func=lambda x: x.replace("_", " ").title(),
)

# Display the statistics for the selected category
if selected_category is not None:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"#### {player_data_1['player']}")
        display_player_statistics(
            player_data_1,
            player_1_stats_categories,
            selected_category,
            key_suffix="_player1",
        )

    with col2:
        st.markdown(f"#### {player_data_2['player']}")
        display_player_statistics(
            player_data_2,
            player_2_stats_categories,
            selected_category,
            key_suffix="_player2",
        )

# Similar players
similar_players_col1, similar_players_col2 = st.columns(2)

st.sidebar.markdown("---")
filtered_players_candidates = filter_data(
    df,
    "Similar players filters",
    "Refine the pool of similar players: filter by value, age, nation, position, league, team, season.",
)

similar_players_candidates = get_players_candidates(filtered_players_candidates)

similar_players_1 = get_similar_players(
    player_data_1, similar_players_candidates, top_k=20
)
similar_players_2 = get_similar_players(
    player_data_2, similar_players_candidates, top_k=20
)

with similar_players_col1:
    st.subheader(
        f"Similar players to {player_data_1['player']}, season {format_season(player_data_1['season'])}"
    )
    st.markdown("Use 'Similar players filters' on the left for more precise search")
    if similar_players_1 is not None:
        st.dataframe(
            similar_players_1,
            hide_index=True,
        )

with similar_players_col2:
    st.subheader(
        f"Similar players to {player_data_2['player']}, season {format_season(player_data_2['season'])}"
    )
    st.markdown("Use 'Similar players filters' on the left for more precise search")
    if similar_players_2 is not None:
        st.dataframe(
            similar_players_2,
            hide_index=True,
        )

# Add statistics comparison section
st.markdown("---")
st.markdown("### Statistics Comparison")
st.markdown("Compare the selected players with others based on any two statistics.")
x_stat, y_stat = create_statistics_selector(key_suffix="_comparison")

# Add position filter using the dedicated function
selected_positions = create_position_filter_ui(
    similar_players_candidates,
    default_positions=[player_data_1["pos"]],
    key_suffix="_comparison",
)

comparison_fig = create_comparison_plot(
    similar_players_candidates,
    x_stat,
    y_stat,
    selected_player=(player_1_id, player_1_identifier, selected_season_1),
    selected_player2=(player_2_id, player_2_identifier, selected_season_2),
    filter_by_position=selected_positions,
)
st.plotly_chart(comparison_fig, use_container_width=True)

# Display barplots
st.markdown("---")
st.subheader("Scouting reports")

# Add toggle for position-based quantiles
use_position_quantiles = st.toggle(
    "Show position-based quantiles",
    value=True,
    key="quantiles_toggle",
)

scouting_report_col1a, scouting_report_col2a = st.columns(2)
with scouting_report_col1a:
    plot_best_and_worst_quantiles(
        player_data_1,
        use_position_quantiles=use_position_quantiles,
    )

with scouting_report_col2a:
    plot_best_and_worst_quantiles(
        player_data_2,
        use_position_quantiles=use_position_quantiles,
    )

scouting_report_col1b, scouting_report_col2b = st.columns(2)
create_barplot(
    player_data_1,
    player_1_stats_categories,
    scouting_report_col1b,
    use_position_quantiles=use_position_quantiles,
)
create_barplot(
    player_data_2,
    player_1_stats_categories,
    scouting_report_col2b,
    use_position_quantiles=use_position_quantiles,
)
