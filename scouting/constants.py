"""Constants for the scouting package."""

from pathlib import Path

import pandas as pd

ROOT_PATH = Path(__file__).parent.parent

CURRENT_SEASON = 2526
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

# NODES
MIN_NODE_SIZE = 5
MAX_NODE_SIZE = 35

MAX_PLAYER_COUNT = 88
MIN_PLAYER_COUNT = 1

MAX_PLAYER_VALUE = 0.36
MIN_PLAYER_VALUE = 0.01

# FONT
FONT_SIZE = 8
FONT_COLOR = "black"

# EDGES ARROW
MIN_EDGE_WIDTH = 0.5
MAX_EDGE_WIDTH = 5

HEAD_LENGTH = 0.3
HEAD_WIDTH = 0.12

MAX_PAIR_COUNT = 16
MIN_PAIR_COUNT = 1

MIN_PAIR_VALUE = 0.01
MAX_PAIR_VALUE = 0.085

MIN_PASSES = 4

MIN_ALPHA = 0.6  # Transparency
MAX_ALPHA = 1  # Transparency

AGGREGATED_LEAGUE_NAME = "Aggregated (All Leagues)"

# Big 5 European domestic leagues
BIG_5_LEAGUES = [
    "ENG-Premier League",
    "ESP-La Liga",
    "GER-Bundesliga",
    "ITA-Serie A",
    "FRA-Ligue 1",
]
BIG_5_FILTER_NAME = "Big 5 European Leagues"

SCRAPING_BASE_CATEGORIES = [
    "shooting",
    "passing",
    "passing_types",
    "goal_shot_creation",
    "defense",
    "possession",
    "playing_time",
    "misc",
    "keeper",
    "keeper_adv",
]

SCOUTING_STATISTICS = pd.read_csv(Path(__file__).parent / "statistics.csv")

# FBREF constants
SCOUTING_CATEGORIES = SCOUTING_STATISTICS["category"].unique()

# Player value column display configuration
VALUE_DISPLAY_NAME = "Value (M€)"
VALUE_FORMAT = "{:.1f}"

# Position mapping for better display
POSITION_MAPPING = {
    "GK": "Goalkeeper",
    "DF": "Defender",
    "MF": "Midfielder",
    "FW": "Forward",
    "DF,MF": "Defender/Midfielder",
    "FW,MF": "Winger",
    "DF,FW": "Full-Back",
}

POSITION_COL = "pos"

# Position colors for consistent styling across the application
POSITION_COLORS = {
    "GK": "#FF6B35",  # Orange for goalkeepers
    "DF": "#2563EB",  # Blue for defenders
    "MF": "#00E673",  # Green (accent) for midfielders
    "FW": "#DC2626",  # Red for forwards
    "DF,MF": "#06B6D4",  # Cyan for defender/midfielders
    "MF,DF": "#06B6D4",  # Cyan for midfielder/defenders
    "FW,MF": "#8B5CF6",  # Purple for forward/midfielders (wingers)
    "MF,FW": "#8B5CF6",  # Purple for midfielder/forwards (wingers)
    "DF,FW": "#F59E0B",  # Amber for defender/forwards (full-backs)
    "Unknown": "#9CA3AF",  # Gray for unknown positions
}

# Position emojis for visual representation
POSITION_EMOJIS = {
    "GK": "🥅",
    "DF": "🛡️",
    "MF": "⚡",
    "FW": "⚽",
    "DF,MF": "🔄",
    "MF,DF": "🔄",
    "FW,MF": "🌟",
    "MF,FW": "🌟",
    "DF,FW": "🚀",
    "Unknown": "👤",
}


MERGE_COLS = [
    "league",
    "season",
    "team",
    "player",
    "player_id",
    "nation",
    POSITION_COL,
    "age",
    "born",
]

TRANSFERMARKT_IMAGE_COL = "Transfermarkt_image"


INFO_COLS = [
    "league",
    "season",
    "team",
    "player",
    "nation",
    "player_id",
    POSITION_COL,
    "age",
    "born",
    "90s",
    VALUE_DISPLAY_NAME,
    TRANSFERMARKT_IMAGE_COL,
]


MIN_GAMES = 2
# Leagues are the ones available in FBREF through soccerdata
# https://soccerdata.readthedocs.io/en/latest/howto/custom-leagues.html
# 🚨 Brasil is not advised as league calendars are not aligned with other leagues (results are biased)
ALL_LEAGUES = [
    # "Argentina",
    "Belgium",
    "Big 5 European Leagues Combined",
    # "Canada",
    "Champions League",
    "Conference League",
    "Europa League",
    "Eredivisie",
    # "Greece",
    "KSA",
    # "MLS",
    "Primeira-Liga",
    "Sweden",
    "Swiss",
    # "Turkey",
    "Ligue-2",
]

CUSTOM_LEAGUE_DICT_SOCCERDATA = {
    "Champions League": {"FBref": "UEFA Champions League"},
    "Conference League": {"FBref": "UEFA Conference League"},
    "Europa League": {"FBref": "UEFA Europa League"},
    "Eredivisie": {"FBref": "Eredivisie"},
    "KSA": {"FBref": "Saudi Pro League"},
    "Primeira-Liga": {"FBref": "Primeira Liga"},
    "Sweden": {"FBref": "Allsvenskan"},
    "Swiss": {"FBref": "Swiss Super League"},
    "Ligue-2": {"FBref": "Ligue 2"},
    "Brasil": {"FBref": "Campeonato Brasileiro Série A"},
    "Argentina": {"FBref": "Liga Profesional de Fútbol Argentina"},
    "Canada": {"FBref": "Canadian Premier League"},
    "Belgium": {"FBref": "Belgian Pro League"},
}

TRANSFERMARKT_TO_FBREF_CLUB_NAME_MAPPING = {
    # Ligue 1
    "AJ Auxerre": "Auxerre",
    "AS Monaco": "Monaco",
    "AS Saint-Étienne": "Saint-Étienne",
    "Angers SCO": "Angers",
    "FC Nantes": "Nantes",
    "FC Toulouse": "Toulouse",
    "LOSC Lille": "Lille",
    "Le Havre AC": "Le Havre",
    "Montpellier HSC": "Montpellier",
    "OGC Nice": "Nice",
    "Olympique Lyon": "Lyon",
    "Olympique Marseille": "Marseille",
    "Paris Saint-Germain": "Paris S-G",
    "RC Lens": "Lens",
    "RC Strasbourg Alsace": "Strasbourg",
    "Stade Brestois 29": "Brest",
    "Stade Reims": "Reims",
    "Stade Rennais FC": "Rennes",
    # Belgian Pro League
    "Club Brugge KV": "Club Brugge",
    "RSC Anderlecht": "Anderlecht",
    "KRC Genk": "Genk",
    "KAA Gent": "Gent",
    "Union Saint-Gilloise": "Union SG",
    "Standard Liège": "Standard Liège",
    "Royal Antwerp FC": "Antwerp",
    "KVC Westerlo": "Westerlo",
    "Cercle Brugge": "Cercle Brugge",
    "Oud-Heverlee Leuven": "OH Leuven",
    "Sint-Truidense VV": "Sint-Truiden",
    "R Charleroi SC": "Charleroi",
    "KV Mechelen": "Mechelen",
    "KV Kortrijk": "Kortrijk",
    "FCV Dender EH": "Dender",
    "Beerschot VA": "Beerschot",
    "RWD Molenbeek": "RWD Molenbeek",
    "Royal Charleroi SC": "Charleroi",
    "Zulte Waregem": "Zulte Waregem",
    "RAAL La Louvière": "La Louvière",
    # English Premier League
    "Manchester City": "Manchester City",
    "Arsenal FC": "Arsenal",
    "Liverpool FC": "Liverpool",
    "Chelsea FC": "Chelsea",
    "Tottenham Hotspur": "Tottenham",
    "Manchester United": "Manchester Utd",
    "Aston Villa": "Aston Villa",
    "Newcastle United": "Newcastle Utd",
    "Brighton & Hove Albion": "Brighton",
    "West Ham United": "West Ham",
    "Crystal Palace": "Crystal Palace",
    "Brentford FC": "Brentford",
    "Nottingham Forest": "Nott'ham Forest",
    "Wolverhampton Wanderers": "Wolves",
    "AFC Bournemouth": "Bournemouth",
    "Everton FC": "Everton",
    "Fulham FC": "Fulham",
    "Leicester City": "Leicester City",
    "Southampton FC": "Southampton",
    "Ipswich Town": "Ipswich Town",
    "Burnley FC": "Burnley",
    "Luton Town": "Luton Town",
    "Sheffield United": "Sheffield Utd",
    "Leeds United": "Leeds United",
    "Sunderland AFC": "Sunderland",
    # La Liga
    "Real Madrid": "Real Madrid",
    "FC Barcelona": "Barcelona",
    "Atlético de Madrid": "Atlético Madrid",
    "Real Sociedad": "Real Sociedad",
    "Athletic Bilbao": "Athletic Club",
    "Valencia CF": "Valencia",
    "Villarreal CF": "Villarreal",
    "Girona FC": "Girona",
    "Real Betis Balompié": "Betis",
    "Sevilla FC": "Sevilla",
    "UD Las Palmas": "Las Palmas",
    "CA Osasuna": "Osasuna",
    "Celta de Vigo": "Celta Vigo",
    "RCD Mallorca": "Mallorca",
    "Deportivo Alavés": "Alavés",
    "Getafe CF": "Getafe",
    "RCD Espanyol Barcelona": "Espanyol",
    "Rayo Vallecano": "Rayo Vallecano",
    "CD Leganés": "Leganés",
    "Real Valladolid CF": "Valladolid",
    "Almería": "Almería",
    "Cádiz": "Cádiz",
    "Elche": "Elche",
    "Granada": "Granada",
    "Levante UD": "Levante",
    "Elche CF": "Elche",
    "Real Oviedo": "Oviedo",
    # Eredivisie
    "PSV Eindhoven": "PSV Eindhoven",
    "Feyenoord Rotterdam": "Feyenoord",
    "Ajax Amsterdam": "Ajax",
    "AZ Alkmaar": "AZ Alkmaar",
    "Twente Enschede FC": "Twente",
    "FC Utrecht": "Utrecht",
    "SC Heerenveen": "Heerenveen",
    "NEC Nijmegen": "NEC Nijmegen",
    "Sparta Rotterdam": "Sparta R'dam",
    "Fortuna Sittard": "Fortuna Sittard",
    "PEC Zwolle": "Zwolle",
    "FC Groningen": "Groningen",
    "NAC Breda": "NAC Breda",
    "Go Ahead Eagles": "Go Ahead Eag",
    "Heracles Almelo": "Heracles Almelo",
    "Willem II Tilburg": "Willem II",
    "Almere City FC": "Almere City",
    "RKC Waalwijk": "RKC Waalwijk",
    "Cambuur": "Cambuur",
    "Emmen": "Emmen",
    "Excelsior": "Excelsior",
    "Vitesse": "Vitesse",
    "Volendam": "Volendam",
    "Excelsior Rotterdam": "Excelsior",
    "FC Volendam": "Volendam",
    "SC Telstar": "Telstar",
    # Bundesliga
    "Bayern Munich": "Bayern Munich",
    "Bayer 04 Leverkusen": "Leverkusen",
    "RB Leipzig": "RB Leipzig",
    "Borussia Dortmund": "Dortmund",
    "VfB Stuttgart": "Stuttgart",
    "Eintracht Frankfurt": "Eint Frankfurt",
    "VfL Wolfsburg": "Wolfsburg",
    "SC Freiburg": "Freiburg",
    "TSG 1899 Hoffenheim": "Hoffenheim",
    "Borussia Mönchengladbach": "Gladbach",
    "SV Werder Bremen": "Werder Bremen",
    "1.FC Union Berlin": "Union Berlin",
    "1.FSV Mainz 05": "Mainz 05",
    "FC Augsburg": "Augsburg",
    "1.FC Heidenheim 1846": "Heidenheim",
    "VfL Bochum": "Bochum",
    "FC St. Pauli": "St. Pauli",
    "Holstein Kiel": "Holstein Kiel",
    "Darmstadt 98": "Darmstadt 98",
    "Schalke 04": "Schalke 04",
    "Köln": "Köln",
    "Hertha BSC": "Hertha BSC",
    "Hamburger SV": "Hamburger SV",
    "1.FC Köln": "Köln",
    # Serie A
    "Inter Milan": "Inter",
    "Juventus FC": "Juventus",
    "AC Milan": "Milan",
    "Atalanta BC": "Atalanta",
    "SSC Napoli": "Napoli",
    "AS Roma": "Roma",
    "SS Lazio": "Lazio",
    "ACF Fiorentina": "Fiorentina",
    "Bologna FC 1909": "Bologna",
    "Torino FC": "Torino",
    "Parma Calcio 1913": "Parma",
    "Genoa CFC": "Genoa",
    "Udinese Calcio": "Udinese",
    "Como 1907": "Como",
    "AC Monza": "Monza",
    "FC Empoli": "Empoli",
    "Hellas Verona": "Hellas Verona",
    "Cagliari Calcio": "Cagliari",
    "US Lecce": "Lecce",
    "Venezia FC": "Venezia",
    "Cremonese": "Cremonese",
    "Salernitana": "Salernitana",
    "Sampdoria": "Sampdoria",
    "US Sassuolo": "Sassuolo",
    "Spezia": "Spezia",
    "Frosinone": "Frosinone",
    "Pisa Sporting Club": "Pisa",
    "US Cremonese": "Cremonese",
    # Primeira Liga
    "Sporting CP": "Sporting CP",
    "SL Benfica": "Benfica",
    "FC Porto": "Porto",
    "SC Braga": "Braga",
    "Vitória Guimarães SC": "Vitória",
    "FC Famalicão": "Famalicão",
    "Rio Ave FC": "Rio Ave",
    "FC Arouca": "Arouca",
    "GD Estoril Praia": "Estoril",
    "Gil Vicente FC": "Gil Vicente FC",
    "Moreirense FC": "Moreirense",
    "CD Santa Clara": "Santa Clara",
    "SC Farense": "Farense",
    "Avs Futebol": "AVS Futebol",
    "Casa Pia AC": "Casa Pia",
    "Boavista FC": "Boavista",
    "CD Nacional": "Nacional",
    "CF Estrela Amadora": "Estrela",
    "Paços": "Paços",
    "Portimonense": "Portimonense",
    "FC Alverca": "Alverca",
    "CD Tondela": "Tondela",
    # Sweden - Allsvenskan
    "AIK": "AIK Stockholm",
    "Degerfors IF": "Degerfors",
    "Djurgårdens IF": "Djurgården",
    "IF Elfsborg": "Elfsborg",
    "IFK Göteborg": "Göteborg",
    "Hammarby IF": "Hammarby",
    "Helsingborgs IF": "Helsingborg",
    "BK Häcken": "Häcken",
    "Kalmar FF": "Kalmar",
    "Malmö FF": "Malmö",
    "Mjällby AIF": "Mjällby",
    "IFK Norrköping": "Norrköping",
    "IK Sirius": "Sirius",
    "GIF Sundsvall": "Sundsvall",
    "Varbergs BoIS": "Varberg",
    "IFK Värnamo": "Värnamo",
    "IF Brommapojkarna": "Brommapojkarna",
    "Halmstads BK": "Halmstad",
    "GAIS": "GAIS",
    "Västerås SK": "Västerås",
    "Östers IF": "Östers",
    # Switzerland - Super League
    "FC Basel 1893": "Basel",
    "BSC Young Boys": "Young Boys",
    "FC Lugano": "Lugano",
    "FC Lausanne-Sport": "Lausanne-Sport",
    "FC St. Gallen 1879": "St. Gallen",
    "Servette FC": "Servette FC",
    "FC Luzern": "Luzern",
    "FC Zürich": "Zürich",
    "FC Sion": "Sion",
    "Grasshopper Club Zurich": "Grasshopper",
    "Yverdon Sport FC": "Yverdon-Sport",
    "FC Winterthur": "FC Winterthur",
    "FC Stade Lausanne-Ouchy": "FC Stade Lausanne-Ouchy",
    # France - Ligue 2 (2024–25 Season)
    "AC Ajaccio": "Ajaccio",
    "Amiens SC": "Amiens",
    "FC Annecy": "Annecy",
    "SC Bastia": "Bastia",
    "SM Caen": "Caen",
    "Clermont Foot 63": "Clermont",
    "USL Dunkerque": "Dunkerque",
    "Grenoble Foot 38": "Grenoble",
    "EA Guingamp": "Guingamp",
    "Stade Lavallois": "Laval",
    "FC Lorient": "Lorient",
    "FC Martigues": "Martigues",
    "FC Metz": "Metz",
    "Paris FC": "Paris FC",
    "Pau FC": "Pau",
    "Red Star FC": "Red Star",
    "Rodez AF": "Rodez",
    "ESTAC Troyes": "Troyes",
    "AS Nancy-Lorraine": "Nancy",
    "Le Mans FC": "Le Mans",
    "US Boulogne": "Boulogne",
    # Brazilian teams
    "CR Flamengo": "Flamengo",
    "Sociedade Esportiva Palmeiras": "Palmeiras",
    "Botafogo de Futebol e Regatas": "Botafogo",
    "Sport Club Corinthians Paulista": "Corinthians",
    "Cruzeiro Esporte Clube": "Cruzeiro",
    "Clube Atlético Mineiro": "Atlético Mineiro",
    "Clube de Regatas Vasco da Gama": "Vasco da Gama",
    "Esporte Clube Bahia": "Bahia",
    "Sport Club Internacional": "Internacional",
    "Grêmio Foot-Ball Porto Alegrense": "Grêmio",
    "Red Bull Bragantino": "Red Bull Bragantino",
    "São Paulo Futebol Clube": "São Paulo",
    "Fluminense Football Club": "Fluminense",
    "Santos FC": "Santos",
    "Fortaleza Esporte Clube": "Fortaleza",
    "Sport Club do Recife": "Sport Recife",
    "Esporte Clube Vitória": "Vitória",
    "Ceará Sporting Club": "Ceará",
    "Esporte Clube Juventude": "Juventude",
    "Mirassol Futebol Clube (SP)": "Mirassol",
    # Saudi teams
    "Al-Hilal SFC": "Al-Hilal",
    "Al-Nassr FC": "Al-Nassr",
    "Al-Ahli SFC": "Al-Ahli",
    "Al-Qadsiah FC": "Al-Qadsiah",
    "Al-Ittihad Club": "Al-Ittihad",
    "NEOM SC": "NEOM",
    "Al-Shabab FC": "Al-Shabab",
    "Al-Ettifaq FC": "Al-Ettifaq",
    "Al-Taawoun FC": "Al-Taawoun",
    "Al-Fateh SC": "Al-Fateh",
    "Al-Fayha FC": "Al-Fayha",
    "Al-Khaleej FC": "Al-Khaleej",
    "Damac FC": "Damac",
    "Al-Kholood Club": "Al-Kholood",
    "Al-Riyadh SC": "Al-Riyadh",
    "Al-Najma SC": "Al-Najma",
    "Al-Hazem SC": "Al-Hazem",
    "Al-Okhdood Club": "Al-Okhdood",
}

# Threshold values to avoid edge cases where players with minimal activity appear as top performers
# These thresholds are applied per 90 minutes where applicable
STATISTIC_THRESHOLDS = {
    # Shooting thresholds
    "Standard_Sh/90": 0.5,  # Minimum shots per 90 minutes
    "Standard_SoT/90": 0.2,  # Minimum shots on target per 90 minutes
}
