"""Constants for the scouting package."""

LEAGUES = ["FRA-Ligue 1", "EUR-Champions League"]

WHOSCORED_SCHEDULE_COLS = [
    "game_id",
    "home_team_id",
    "home_team",
    "away_team_id",
    "away_team",
    "home_score",
    "away_score",
    "date",
]

WHOSCORED_RAW_EVENTS_COLS = [
    "game_id",
    "team_id",
    "team",
    "player_id",
    "player",
    "period",
    "minute",
    "second",
    "type",
    "card_type",
]

CARDS_AND_SUBSTITUTIONS_COLS = ("Card", "SubstitutionOn", "SubstitutionOff")

GAME_ID_COL = "game_id"
