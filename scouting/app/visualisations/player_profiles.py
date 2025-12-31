"""
Player profile functionality for the scouting application.

This module contains functions for displaying individual player information,
including player cards and profile displays.
"""

import math

import pandas as pd

from scouting.constants import (
    POSITION_MAPPING,
    TRANSFERMARKT_IMAGE_COL,
    VALUE_DISPLAY_NAME,
)


def display_player_profile(col, player_data: pd.Series):
    """Display a player profile with image and key information.

    Args:
        col: Streamlit column to display the profile in
        player_data: Series containing the player's data
    """
    # Use player image if available, otherwise fall back to FBref image
    if TRANSFERMARKT_IMAGE_COL in player_data and player_data[TRANSFERMARKT_IMAGE_COL]:
        player_image_url = player_data[TRANSFERMARKT_IMAGE_COL]
    else:
        player_image_url = "https://via.placeholder.com/150"

    player_value = round(
        player_data[VALUE_DISPLAY_NAME]
        if not math.isnan(player_data[VALUE_DISPLAY_NAME])
        else 0,
        1,
    )
    col.markdown(
        f"""
        <div style="text-align: center; padding-top: 100px;">
            <img src="{player_image_url}" width="150">
            <br>
            <br><strong>Name:</strong> {player_data["player"]}
            <br><strong>Team:</strong> {player_data["team"]}
            <br><strong>Position:</strong> {POSITION_MAPPING[player_data["pos"]]}
            <br><strong>Value (M€):</strong> <span style='font-size:40px'>{player_value}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
