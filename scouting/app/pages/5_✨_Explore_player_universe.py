import streamlit as st

from scouting.app.visualisations import filter_data, plot_tsne_player
from scouting.constants import ROOT_PATH
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

numerical_col_per_90 = [col for col in df.columns if "per_90" in col]


st.set_page_config(page_title="FantasyScouting App", layout="wide")
st.title("Explore player universe")

st.write("Only players with value > 5M€.")
st.write("Bigger points correspond to players with higher market value.")
st.write(
    "Data points that are close to each other mean that players are similar in terms of statistics."
)

filtered_df = filter_data(df=df, force_aggregated_league=True)

plot_tsne_player(filtered_df, numerical_col_per_90)
