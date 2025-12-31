import logging

import pandas as pd
import streamlit as st
from sklearn.metrics.pairwise import cosine_similarity

from scouting.constants import (
    SCOUTING_STATISTICS,
    VALUE_DISPLAY_NAME,
)

COLUMNS_TO_PLOT = [
    "team",
    "player",
    "season",
    "league",
    "nation",
    "pos",
    "age",
    "90s",
    VALUE_DISPLAY_NAME,
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# @deprecated
# def get_fbref_player_image_url(player_id: str) -> str:
#     """
#     Extracts the player's image URL from his FBref ID.

#     Deprecated: Should use Transfermarkt image instead.

#     Args:
#         player_id (str): The ID of the player in FBref.

#     Returns:
#         str: Direct link to the player's image or a placeholder if not found.
#     """
#     if not player_id:
#         return "https://via.placeholder.com/150"

#     headers = {"User-Agent": "Mozilla/5.0"}
#     # Not bothering with player name, put Random as placeholder

#     player_url = f"https://fbref.com/en/players/{player_id}/Random"
#     response = requests.get(player_url, headers=headers)

#     if response.status_code == 200:
#         tree = html.fromstring(response.content)
#         meta_tag = tree.xpath("//meta[@property='og:image']/@content")

#         if meta_tag and "images/headshots" in meta_tag[0]:
#             return meta_tag[0]
#     logger.warning(
#         f"Reponse code {response.status_code} for player {player_id}", stack_info=True
#     )
#     return "https://via.placeholder.com/150"


def get_player_stats_categories(player_pos: str):
    """Get the statistics categories for the radar chart based on player position."""
    if player_pos == "GK":
        stats_categories = SCOUTING_STATISTICS[
            SCOUTING_STATISTICS["position"].isin(["goalkeeper", "both"])
        ][["category", "stat"]]
    else:
        stats_categories = SCOUTING_STATISTICS[
            SCOUTING_STATISTICS["position"].isin(["field", "both"])
        ][["category", "stat"]]

    return stats_categories


def update_player_selection(player):
    if player in st.session_state.selected_players:
        st.session_state.selected_players.remove(player)
    elif len(st.session_state.selected_players) < 2:
        st.session_state.selected_players.append(player)


def find_most_similar(row_index, df_scaled_stats, top_k=10):
    similarity_matrix = cosine_similarity(df_scaled_stats)
    similarity_scores = pd.Series(similarity_matrix[row_index], name="similarity_score")
    most_similar_index = similarity_scores.argsort()[-top_k - 1 : -1][
        ::-1
    ]  # -2 because the most similar will be the row itself
    return most_similar_index, similarity_scores


def get_similar_players(
    target_player_data: pd.Series,
    df: pd.DataFrame,
    top_k: int = 10,
) -> pd.DataFrame | None:
    """Get the most similar players to the target player based on their statistics."""

    df = df.reset_index(drop=True)

    target_player_in_df = df[
        (df["player"] == target_player_data["player"])
        & (df["season"].astype(int) == int(target_player_data["season"]))
        & (df["team"] == target_player_data["team"])
    ]
    if target_player_in_df.empty:
        target_player_df = pd.DataFrame(
            [target_player_data.values],
            columns=list(target_player_data.index),
            index=[len(df)],
        )
        df = pd.concat([df, target_player_df])
        row_player = len(df) - 1
    else:
        row_player = target_player_in_df.index[0]

    scaled_stats_columns = [
        f"{stat}_scaled" for stat in SCOUTING_STATISTICS["stat"].values
    ]
    most_similar_row_index, similarity_scores = find_most_similar(
        row_index=row_player, df_scaled_stats=df[scaled_stats_columns], top_k=top_k
    )
    most_similar_players_df = pd.concat(
        [
            df[
                [
                    "player",
                    "season",
                    "team",
                    "pos",
                    "nation",
                    "age",
                    VALUE_DISPLAY_NAME,
                ]
            ],
            similarity_scores,
        ],
        axis=1,
    ).iloc[most_similar_row_index]

    # Filter out the same player from different seasons
    most_similar_players_df = most_similar_players_df[
        most_similar_players_df["player"] != target_player_data["player"]
    ]

    most_similar_players_df["similarity_score"] = most_similar_players_df[
        "similarity_score"
    ].round(2)
    most_similar_players_df["season"] = most_similar_players_df["season"].apply(
        format_season
    )

    return most_similar_players_df


def format_season(season: str) -> str:
    """Format season from short format as it is in FBREF (e.g. 2425) to long format (e.g. 2024-2025).

    Args:
        season (str): Season in short format (e.g. 2425)

    Returns:
        str: Season in long format (e.g. 2024-2025)
    """
    if not isinstance(season, str):
        season = str(season)
    return f"20{season[:2]}-20{season[2:]}"


def create_player_identifier(row) -> str:
    """Create a unique player identifier that includes player name and team.

    Args:
        row: DataFrame row containing 'player', and 'team' columns

    Returns:
        str: Player identifier in format "Player Name (Team)"
    """
    player_name = row["player"]
    team = row["team"]

    return f"{player_name} ({team})"
