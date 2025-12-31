import re

import pandas as pd

# --- New category names (final) ------------------------------------------------
OUTFIELD_CATEGORIES = [
    "Finishing",
    "Passing",
    "Dribbling",
    "Defense",
    "Aerial",
    "Discipline",
]

GOALKEEPER_CATEGORIES = [
    "Reflexes & Saves",
    "Air Dominance",
    "Sweeper Play",
    "Footwork & Distribution",
    "Penalty Specialist",
]

# --- Plain-language definitions (concise, non-FBref) ---------------------------
CATEGORY_DEFINITION = {
    # Outfield
    "Finishing": "Goal threat and shot efficiency — e.g., goals, shots, shots on target, shot quality.",
    "Passing": "Creating chances for teammates through passing — e.g., assists, key passes, dangerous final balls, with a variety and execution of passes to move play — e.g., crosses, switches, through balls, set-piece delivery.",
    "Dribbling": "Dribbling and carrying that advances play — e.g., take-ons, carries, progressive moves, receiving between lines, fouls drawn, penalties won.",
    "Defense": "Ball winning and preventing danger — e.g., tackles, interceptions, blocks, clearances, duel success.",
    "Aerial": "Effectiveness in the air — e.g., aerial duel volume and win rate.",
    "Discipline": "Game management and mistakes — e.g., cards, fouls committed, offsides, penalties conceded, errors, own goals.",
    # Goalkeepers
    "Reflexes & Saves": "Shot-stopping quality and handling — e.g., saves, save rate, goals prevented.",
    "Air Dominance": "Command of high balls and the box — e.g., crosses faced, claims, claim success.",
    "Sweeper Play": "Proactive interventions off the line — e.g., rushes, interceptions of through balls, average sweep distance.",
    "Footwork & Distribution": "Quality of jeu au pied and relance — e.g., short build-up and throws, long kicks/launches, goal-kick profile.",
    "Penalty Specialist": "Reading and stopping penalties — e.g., penalties faced and saved.",
}

# --- Outfield default remap by ORIGINAL FBref 'category' ----------------------
OUTFIELD_REMAP = {
    "shooting": ("Finishing"),
    "passing": ("Passing"),
    "passing_types": ("Passing"),
    "goal_shot_creation": ("Passing"),
    "defense": ("Defense"),
    "possession": ("Dribbling"),
    "misc": None,  # will be handled by STAT-LEVEL overrides below
}

# --- Outfield STAT-LEVEL overrides (apply by regex on 'stat') ------------------
OUTFIELD_OVERRIDES = [
    # Dribbling: dribble-led creation & pressure drawn
    (r"^(SCA|GCA) Types_TO$", "Dribbling"),
    (r"^Performance_Fld$", "Dribbling"),  # fouls drawn
    (r"^Performance_PKwon$", "Dribbling"),  # penalties won
    (r"^Receiving_PrgR$", "Dribbling"),
    # Passing: non-dribble SCA/GCA
    (r"^SCA_.*|^GCA_.*", "Passing"),
    (r"^SCA Types_(PassLive|PassDead|Sh|Def)$", "Passing"),
    (r"^GCA Types_(PassLive|PassDead|Sh|Def)$", "Passing"),
    # Passing: crossing volume from misc
    (r"^Performance_Crs$", "Passing"),
    # Defense: misc defensive actions
    (r"^Performance_Int$|^Performance_TklW$|^Performance_Recov$", "Defense"),
    # Aerial: aerial duels
    (r"^Aerial Duels_.*$", "Aerial"),
    # Discipline: cards, fouls, offsides, pens conceded, OG, errors
    (r"^Performance_(CrdY|CrdR|2CrdY|Fls|Off|PKcon|OG)$|^Err$", "Discipline"),
]

# --- Goalkeeper mapping rules --------------------------------------------------
GK_RULES = [
    # Reflexes & Saves: basic/advanced shot-stopping & goals prevented
    (
        ("keeper", r"^Performance_(Saves|Save%|GA|GA90|SoTA|CS|CS%|W|D|L)$"),
        "Reflexes & Saves",
    ),
    (
        ("keeper_adv", r"^Expected_PSxG(/SoT)?$|^Expected_PSxG\+/-$|^Goals_.*$"),
        "Reflexes & Saves",
    ),
    # Air Dominance: crosses
    (("keeper_adv", r"^Crosses_.*$"), "Air Dominance"),
    # Sweeper Play
    (("keeper_adv", r"^Sweeper_.*$"), "Sweeper Play"),
    # Footwork & Distribution: all GK passing/launching/kicks/throws
    (("keeper_adv", r"^(Passes_|Launched_|Goal Kicks_).*$"), "Footwork & Distribution"),
    # Penalty Specialist
    (("keeper", r"^Penalty Kicks_.*$"), "Penalty Specialist"),
]


# --- Helper: first matching rule wins -----------------------------------------
def _match_any(pattern: str, text: str) -> bool:
    return re.match(pattern, text) is not None


def _classify_outfield(orig_category: str, stat: str) -> str:
    # 1) stat-level overrides (most specific)
    for pat, new_cat in OUTFIELD_OVERRIDES:
        if _match_any(pat, stat):
            return new_cat
    # 2) default by original category
    new_cat = OUTFIELD_REMAP.get(orig_category, None)
    if new_cat:
        return new_cat
    # 3) sensible fallback
    return "Passing"


def _classify_gk(orig_category: str, stat: str) -> str:
    for (cat_pat, stat_pat), new_cat in GK_RULES:
        if re.match(cat_pat, orig_category) and _match_any(stat_pat, stat):
            return new_cat
    # fallback (rare)
    if orig_category in ("keeper", "keeper_adv"):
        return "Reflexes & Saves"
    return "Reflexes & Saves"


def apply_new_categories(df: pd.DataFrame) -> pd.DataFrame:
    """
    Takes a DataFrame with columns: position, category, stat, display_name, definition, reverse_quantile
    Returns the same DataFrame with:
      - 'category' replaced by new scouting categories
      - 'category_definition' added
    """
    out = df.copy()

    # Keep the original category for logic, then overwrite
    orig_cat_col = "__orig_cat__"
    out[orig_cat_col] = out["category"].astype(str).str.strip().str.lower()

    new_categories = []
    for _, row in out.iterrows():
        pos = row.get("position", "")
        orig_cat = row[orig_cat_col]
        stat = row.get("stat", "")

        if pos == "goalkeeper":
            new_cat = _classify_gk(orig_cat, stat)
        else:
            # "both" behaves like outfield for passing stats, etc.
            new_cat = _classify_outfield(orig_cat, stat)

        new_categories.append(new_cat)

    out["category"] = new_categories
    out["category_definition"] = out["category"].map(CATEGORY_DEFINITION)

    # Drop temp column
    out = out.drop(columns=[orig_cat_col])

    # Optionally ensure ordering of columns (keep your original order + new field at end)
    # cols = [c for c in out.columns if c != "category_definition"] + ["category_definition"]
    # out = out[cols]

    return out


# --- Example usage -------------------------------------------------------------
# RECLASSIFIED = apply_new_categories(SCOUTING_STATISTICS)
# RECLASSIFIED.head()
# RECLASSIFIED.to_csv("fbref_stats_reclassified.csv", index=False)
