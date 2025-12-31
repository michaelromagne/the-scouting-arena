import streamlit as st

from scouting.app.visualisations import (
    create_comparison_plot,
    create_position_filter_ui,
    create_statistics_selector,
    filter_data,
)
from scouting.constants import POSITION_MAPPING, ROOT_PATH
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

st.title("📊 Statistics comparison")
st.write("Compare players based on any two statistics to find standout performers.")

# Sidebar filters
filtered_df = filter_data(df=df, force_aggregated_league=True)

# Convert age to integer
filtered_df["age"] = filtered_df["age"].apply(
    lambda x: int(x.split("-")[0]) if isinstance(x, str) else int(x)
)

# Format positions
filtered_df["formatted_pos"] = filtered_df["pos"].apply(lambda x: POSITION_MAPPING[x])

# Create statistics selectors and get selected stats
x_stat, y_stat = create_statistics_selector(key_suffix="_stats_comparison")

# Add position filter using the dedicated function
selected_positions = create_position_filter_ui(filtered_df, key_suffix="_stats")

# Create and display comparison plot
comparison_fig = create_comparison_plot(
    filtered_df, x_stat, y_stat, filter_by_position=selected_positions
)
st.plotly_chart(comparison_fig, use_container_width=True)

# Add explanation of the visualization
st.markdown("""
### How to Use This Visualization
1. Use the sidebar to filter players by position, league, team, and season
2. Select two statistics to compare from the dropdowns above
3. Each point represents a player:
   - Colors indicate player positions
   - Hover over points to see detailed player information
4. Look for players who excel in both metrics (top-right of the plot)
5. Use this to:
   - Find undervalued players who perform well
   - Compare players in similar positions
   - Identify standout performers in specific metrics
""")
