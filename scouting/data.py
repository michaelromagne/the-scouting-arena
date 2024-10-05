import soccerdata as sd
import pandas as pd
import socceraction.spadl as spadl

from scouting.constants import (
    CARDS_AND_SUBSTITUTIONS_COLS,
    GAME_ID_COL,
    WHOSCORED_RAW_EVENTS_COLS,
    WHOSCORED_SCHEDULE_COLS,
)
import logging

logger = logging.getLogger(__name__)


def get_cards_and_substitutions(whoscored: sd.WhoScored, game_id: int):
    """Get cards and substitutions for a game in Whoscored."""
    raw_events = whoscored.read_events(match_id=game_id, force_cache=True)
    processed_events = (
        raw_events[raw_events["type"].isin(CARDS_AND_SUBSTITUTIONS_COLS)][
            WHOSCORED_RAW_EVENTS_COLS
        ]
        .reset_index(drop=True)
        .replace({"FirstHalf": 1, "SecondHalf": 2})
        .rename(columns={"period": "period_id", "type": "type_name"})
        .assign(
            time_seconds=lambda x: x["minute"]
            - (45 * (x["period_id"] - 1) * 60 + x["second"])
        )
    )
    return processed_events


def get_game_data(
    league: str,
    season: str,
    game_id: int,
):
    """Get events data for a given game.

    Args:
        league (str): League of the game.
        season (str): Season of the game.
        game_id (int): The ID of the game.
            It can be found in the URL of the game page in Whoscored.

    Returns:
        pd.DataFrame: The events data of the game.

    >>> get_game_data("EUR-Champions League", 2024, 1866220) # Salzbourg - Brest
    """
    whoscored = sd.WhoScored(leagues=league, seasons=season)
    logger.info("Reading schedule...")
    schedule = whoscored.read_schedule(force_cache=True)
    game_info = schedule[schedule[GAME_ID_COL] == game_id]

    logger.info("Cards and substitutions events...")
    cards_and_substitutions = get_cards_and_substitutions(whoscored, game_id)

    logger.info("SPADL events...")
    spadl_events = spadl.add_names(
        whoscored.read_events(match_id=game_id, force_cache=True, output_fmt="spadl")
    )
    spadl_events_with_home_away = spadl_events.merge(
        game_info[WHOSCORED_SCHEDULE_COLS],
        on=GAME_ID_COL,
    )
    cards_and_subs = cards_and_substitutions.merge(
        schedule[WHOSCORED_SCHEDULE_COLS],
        on=GAME_ID_COL,
    )

    complete_game_data = pd.concat([spadl_events_with_home_away, cards_and_subs])
    logger.info("Success !")

    return complete_game_data
