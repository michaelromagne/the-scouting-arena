import statistics

import streamlit as st

from scouting.app.utils import COLUMNS_TO_PLOT
from scouting.app.visualisations import (
    filter_and_process_data,
)
from scouting.constants import AGGREGATED_LEAGUE_NAME, ROOT_PATH, SCOUTING_STATISTICS
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
filtered_df = filter_and_process_data(df=df, force_aggregated_league=True)

st.markdown("""
### Find players matching your specific tactical and technical requirements

This tool allows you to identify players based on detailed performance metrics across different aspects of the game.
Select the criteria that matter most for your scouting needs and discover players who excel in those areas.
""")

# Initialize session state for selected criteria if not exists
if "selected_criterias" not in st.session_state:
    st.session_state.selected_criterias = []
if "last_computed_results" not in st.session_state:
    st.session_state.last_computed_results = None
if "last_computed_criterias" not in st.session_state:
    st.session_state.last_computed_criterias = []

# Initialize checkbox states
for category, stat, _ in zip(
    SCOUTING_STATISTICS["category"],
    SCOUTING_STATISTICS["stat"],
    SCOUTING_STATISTICS["definition"],
):
    checkbox_key = f"checkbox_{stat}"
    if checkbox_key not in st.session_state:
        st.session_state[checkbox_key] = stat in st.session_state.selected_criterias

# Add controls at the top
col1, col2 = st.columns([1, 1])
with col1:
    compute_scores = st.button("🔍 Compute Player Scores", type="primary")
with col2:
    if st.button("🔄 Reset Criteria"):
        st.session_state.selected_criterias = []
        st.session_state.last_computed_results = None
        st.session_state.last_computed_criterias = []
        # Reset all checkbox states
        for stat in SCOUTING_STATISTICS["stat"]:
            st.session_state[f"checkbox_{stat}"] = False

top_k = st.number_input(
    "Number of players to display", min_value=1, max_value=100, value=50
)

# Add reverse ranking toggle
show_reverse_ranking = st.checkbox(
    "📉 Show reverse ranking (worst performers)", value=False
)

# Add score filte
# Compute score range from the data
if st.session_state.selected_criterias:
    # Compute scores to get the range
    temp_df = filtered_df.copy()
    temp_df["selected_criteria_score"] = temp_df[
        [f"{col}_scaled" for col in st.session_state.selected_criterias]
    ].apply(
        lambda row: statistics.mean(
            row[f"{stat}_scaled"]
            if not SCOUTING_STATISTICS.loc[
                SCOUTING_STATISTICS["stat"] == stat, "reverse_quantile"
            ].values[0]
            else -row[f"{stat}_scaled"]
            for stat in st.session_state.selected_criterias
        ),
        axis=1,
    )
    score_min = temp_df["selected_criteria_score"].min()
    score_max = temp_df["selected_criteria_score"].max()
else:
    score_min = -10.0
    score_max = 10.0

col1, col2 = st.columns(2)
with col1:
    min_score = st.number_input(
        "Minimum score",
        min_value=score_min,
        max_value=score_max,
        value=score_min,
        step=0.1,
        help="Filter players with score above this value",
    )
with col2:
    max_score = st.number_input(
        "Maximum score",
        min_value=score_min,
        max_value=score_max,
        value=score_max,
        step=0.1,
        help="Filter players with score below this value",
    )

if compute_scores or st.session_state.last_computed_results is not None:
    if st.session_state.selected_criterias:
        # Add a loading spinner while computing the scores
        with st.spinner("Analyzing player performances..."):
            filtered_df["selected_criteria_score"] = filtered_df[
                [f"{col}_scaled" for col in st.session_state.selected_criterias]
            ].apply(
                lambda row: statistics.mean(
                    row[f"{stat}_scaled"]
                    if not SCOUTING_STATISTICS.loc[
                        SCOUTING_STATISTICS["stat"] == stat, "reverse_quantile"
                    ].values[0]
                    else -row[f"{stat}_scaled"]
                    for stat in st.session_state.selected_criterias
                ),
                axis=1,
            )

            # Store the computed results
            season_filter = st.session_state.get("Filters_season")

            if season_filter:
                filtered_by_season = filtered_df[filtered_df["season"] == season_filter]
                # Apply score filter
                score_filtered = filtered_by_season[
                    (filtered_by_season["selected_criteria_score"] >= min_score)
                    & (filtered_by_season["selected_criteria_score"] <= max_score)
                ]
                st.session_state.last_computed_results = (
                    score_filtered.sort_values(
                        by="selected_criteria_score", ascending=show_reverse_ranking
                    )
                    .head(top_k)[
                        COLUMNS_TO_PLOT
                        + ["selected_criteria_score"]
                        + st.session_state.selected_criterias
                    ]
                    .reset_index(drop=True)
                )
            else:
                # Apply score filter
                score_filtered = filtered_df[
                    (filtered_df["selected_criteria_score"] >= min_score)
                    & (filtered_df["selected_criteria_score"] <= max_score)
                ]
                st.session_state.last_computed_results = (
                    score_filtered.sort_values(
                        by="selected_criteria_score", ascending=show_reverse_ranking
                    )
                    .head(top_k)[
                        COLUMNS_TO_PLOT
                        + ["selected_criteria_score"]
                        + st.session_state.selected_criterias
                    ]
                    .reset_index(drop=True)
                )

            st.session_state.last_computed_criterias = (
                st.session_state.selected_criterias.copy()
            )
            st.session_state.last_computed_results["season"] = (
                st.session_state.last_computed_results["season"].astype(str)
            )

    if st.session_state.last_computed_results is not None:
        st.markdown("### 📊 Selected Performance Metrics")
        st.markdown(
            "\n".join(
                f"- **{SCOUTING_STATISTICS[SCOUTING_STATISTICS['stat'] == criteria]['display_name'].values[0]}** : {SCOUTING_STATISTICS[SCOUTING_STATISTICS['stat'] == criteria]['definition'].values[0]}"
                for criteria in st.session_state.last_computed_criterias
            )
        )
        st.markdown("---")

        if show_reverse_ranking:
            st.markdown(f"### 📉 Worst {top_k} Players Matching Your Criteria")
        else:
            st.markdown(f"### 🏆 Top {top_k} Players Matching Your Criteria")

        # Format the dataframe for better display
        display_df = st.session_state.last_computed_results.copy()
        display_df["selected_criteria_score"] = display_df[
            "selected_criteria_score"
        ].round(2)

        # Rename selected criteria columns to their display names
        for criteria in st.session_state.selected_criterias:
            display_name = SCOUTING_STATISTICS[SCOUTING_STATISTICS["stat"] == criteria][
                "display_name"
            ].values[0]
            display_df = display_df.rename(columns={criteria: display_name})

        # Add color coding for the score
        score_values = display_df["selected_criteria_score"]
        if show_reverse_ranking:
            # For worst performers, use the actual min/max of the data
            vmin = score_values.min()
            vmax = score_values.max()
        else:
            # For top performers, use 0 to max
            vmin = 0
            vmax = score_values.max()

        st.dataframe(
            display_df.style.background_gradient(
                subset=["selected_criteria_score"],
                cmap="RdYlGn",
                vmin=vmin,
                vmax=vmax,
            ),
            use_container_width=True,
        )

st.markdown("---")
st.markdown("### 📋 Performance Criteria Selection")

# Group criteria by category
criteria_by_category: dict[str, list[tuple[str, str]]] = {}
for category, stat, display_name in zip(
    SCOUTING_STATISTICS["category"],
    SCOUTING_STATISTICS["stat"],
    SCOUTING_STATISTICS["display_name"],
):
    if category not in criteria_by_category:
        criteria_by_category[category] = []
    criteria_by_category[category].append((stat, display_name))

# Create checkboxes for each category in collapsible sections
selected_criterias = []
for category, criteria_list in criteria_by_category.items():
    with st.expander(f"**{category}**", expanded=False):
        for stat, display_name in criteria_list:
            checkbox_key = f"checkbox_{stat}"

            if st.checkbox(
                f"{display_name}",
                value=st.session_state[checkbox_key],
                key=checkbox_key,
            ):
                selected_criterias.append(stat)
            else:
                if stat in selected_criterias:
                    selected_criterias.remove(stat)

# Update session state with new selections
st.session_state.selected_criterias = selected_criterias
