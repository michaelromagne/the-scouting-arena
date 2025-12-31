import streamlit as st

from scouting.app.visualisations import (
    display_category,
    display_penalty_takers,
    filter_and_process_data,
)
from scouting.constants import AGGREGATED_LEAGUE_NAME, ROOT_PATH, SCOUTING_CATEGORIES

# Import at module level
from scouting.data_transform.player_stats import load_combined_player_data

# Load combined data from separate CSV files
try:
    df = load_combined_player_data(ROOT_PATH / "data")
except FileNotFoundError as e:
    st.error(f"Data files not found: {e}")
    st.info(
        "Please run the player stats extraction first to generate the required CSV files."
    )
    st.stop()

# Apply filters and process data
st.session_state["Filters_league"] = [AGGREGATED_LEAGUE_NAME]
filtered_df = filter_and_process_data(df, force_aggregated_league=True)

st.markdown("""
### Discover top performers across different aspects of the game

This tool allows you to analyze player performances across various categories, from penalty specialists to midfield playmakers and defensive leaders.
Use the filters to focus on specific positions, leagues, or seasons.
""")

# Add a section for the number of players to display
top_k = st.number_input(
    "Number of players to display per category",
    min_value=1,
    max_value=100,
    value=50,
    help="Select how many top players to show for each category",
)

# Check if a season filter is applied and filter data accordingly
season_filter = st.session_state.get("Filters_season")
if season_filter:
    filtered_df = filtered_df[filtered_df["season"] == season_filter]

# Performance by Category
st.markdown("#### 📈 Performance by Category")

# Add Penalty Takers to the categories
categories = ["Penalty Takers"] + list(SCOUTING_CATEGORIES)

for category in categories:
    with st.expander(f"**{category}**", expanded=True):
        if category == "Penalty Takers":
            display_penalty_takers(filtered_df, top_k)
        else:
            display_category(filtered_df, category, top_k)
