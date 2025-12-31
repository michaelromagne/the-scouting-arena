import pandas as pd
from requests import get

MPG_LEAGUES_PLAYERS_URL = {
    "ligue_1": "https://api.mpg.football/api/data/championship-players-pool/1?season=2024",
    "premier_league": "https://api.mpg.football/api/data/championship-players-pool/2?season=2024",
    "liga": "https://api.mpg.football/api/data/championship-players-pool/3?season=2024",
    "serie_a": "https://api.mpg.football/api/data/championship-players-pool/5?season=2024",
    "bundesliga": "https://api.mpg.football/api/data/championship-players-pool/6?season=2024",
}
MPG_CLUBS_URL = "https://api.mpg.football/api/data/championship-clubs"


def get_mpg_quotations() -> pd.DataFrame:
    mpg_players = []
    for url in MPG_LEAGUES_PLAYERS_URL.values():
        new_players = get(url).json()["poolPlayers"]
        mpg_players += new_players

    player_data = []

    for player in mpg_players:
        average_rating = player["stats"].get("averageRating", 5)
        average_rating_trend = (
            player["stats"].get("nearestMatches", {}).get("averageRatingTrend", 0)
        )

        if player["firstName"] is None:
            player["firstName"] = ""
        player_data.append(
            {
                "player_name": player["firstName"] + " " + player["lastName"],
                "season": "2425",  # To match season in fbref
                "club_id": player["clubId"],
                "quotation": player["quotation"],
                "average_rating": average_rating,
                "average_rating_trend": average_rating_trend,
            }
        )

    return pd.DataFrame(player_data)


def get_mpg_clubs() -> pd.DataFrame:
    mpg_clubs = get(MPG_CLUBS_URL).json()

    clubs_dict = mpg_clubs["championshipClubs"]

    team_id_names_mapping = pd.DataFrame.from_dict(
        {key: value["name"]["fr-FR"] for key, value in clubs_dict.items()},
        orient="index",
        columns=["team_name"],
    )
    team_id_names_mapping.replace(
        {
            "team_name": {
                "OM": "Marseille",
                "OL": "Lyon",
                "Paris": "Paris S-G",
                "Havre AC": "Le Havre",
                "AS Saint-Étienne": "Saint-Étienne",
                "Angers SCO": "Angers",
                "RC Lens": "Lens",
                "FC Nantes": "Nantes",
                "AJ Auxerre": "Auxerre",
                "OGC Nice": "Nice",
                "Toulouse FC": "Toulouse",
            }
        },
        inplace=True,
    )
    return team_id_names_mapping
