import unicodedata
from typing import NamedTuple, Sequence

import pandas as pd
from fuzzywuzzy import fuzz, process

# Known name mismatches between Transfermarkt and FBref
# Keys transfermarkt, values fbref
PLAYER_NAME_CORRECTIONS = {
    "Julián Alvarez": "Julián Álvarez",
    "Bremer": "Gleison Bremer",
    "Álex Baena": "Alex Baena",
    "Alejandro Grimaldo": "Álex Grimaldo",
    "Luis Suárez": "Luis Javier Suárez",
    "Samu Aghehowa": "Samu Omorodion",
    "Emmanuel Emegha": "Emanuel Emegha",
}


class FBrefPlayer(NamedTuple):
    """Player info from FBref dataset for matching."""

    name: str
    team: str
    season: str
    player_id: str


def remove_accents(text: str) -> str:
    """Remove accents from text."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def fuzzy_match(
    source_player_name: str,
    source_season: str,
    source_team_name: str,
    target_players: Sequence[FBrefPlayer],
) -> str:
    """Fuzzy match player names from different sources.

    Args:
        source_player_name: Player name from Transfermarkt.
        source_season: Season to match (player may change clubs between seasons).
        source_team_name: Team name from Transfermarkt (mapped to FBref format).
        target_players: FBref players to match against.

    Returns:
        The matched player_id or empty string if no match found.
    """
    # Filter to same team and season, then map normalized name -> player_id
    same_team_players = {
        remove_accents(p.name): p.player_id
        for p in target_players
        if p.team == source_team_name and str(p.season) == str(source_season)
    }

    if not same_team_players:
        return ""

    match = process.extractOne(
        remove_accents(source_player_name),
        list(same_team_players.keys()),
        scorer=fuzz.token_sort_ratio,
    )

    return same_team_players[match[0]] if match and match[1] > 60 else ""


def align_player_names(
    df_transfermarkt: pd.DataFrame, df_fbref: pd.DataFrame
) -> pd.DataFrame:
    """Align player names between Transfermarkt and FBref datasets.

    Args:
        df_transfermarkt: Transfermarkt data with columns [Player, Club, Season, ...]
        df_fbref: FBref data with columns [player, team, season, player_id, ...]

    Returns:
        Transfermarkt data with added fuzzy_fbref_player_id column.
    """
    # Apply known name corrections
    df_transfermarkt = df_transfermarkt.replace({"Player": PLAYER_NAME_CORRECTIONS})

    # Build list of FBref players for matching
    fbref_players = [
        FBrefPlayer(
            name=str(key[0]),
            team=str(key[1]),
            season=str(key[2]),
            player_id=str(key[3]),
        )
        for key in df_fbref.groupby(
            ["player", "team", "season", "player_id"]
        ).groups.keys()
    ]

    # Apply fuzzy matching
    df_transfermarkt["fuzzy_fbref_player_id"] = df_transfermarkt.apply(
        lambda row: fuzzy_match(
            source_player_name=row["Player"],
            source_season=row["Season"],
            source_team_name=row["Club"],
            target_players=fbref_players,
        ),
        axis=1,
    )

    return df_transfermarkt
