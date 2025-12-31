"""This module does not send concurrent requests to stay under rate limiting."""

import json
import logging
import os
import random
import time
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

from scouting.constants import (
    TRANSFERMARKT_IMAGE_COL,
    TRANSFERMARKT_TO_FBREF_CLUB_NAME_MAPPING,
    VALUE_DISPLAY_NAME,
    VALUE_FORMAT,
)

# Constants for rate limiting
MIN_DELAY = 5
MAX_DELAY = 10
MAX_RETRIES = 10
TIMEOUT = 60

SEASON_MAPPING_FBREF_TO_TRANSFERMARKT = {
    "2526": 2025,
    "2425": 2024,
}

logger = logging.getLogger(__name__)

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

TRANSFERMARKT_LEAGUE_URLS = {
    "ENG-Premier League": "https://www.transfermarkt.co.uk/premier-league/startseite/wettbewerb/GB1",
    "ESP-La Liga": "https://www.transfermarkt.co.uk/laliga/startseite/wettbewerb/ES1",
    "FRA-Ligue 1": "https://www.transfermarkt.co.uk/ligue-1/startseite/wettbewerb/FR1",
    "GER-Bundesliga": "https://www.transfermarkt.co.uk/bundesliga/startseite/wettbewerb/L1",
    "ITA-Serie A": "https://www.transfermarkt.co.uk/serie-a/startseite/wettbewerb/IT1",
    "Eredivisie": "https://www.transfermarkt.co.uk/eredivisie/startseite/wettbewerb/NL1",
    "Primeira-Liga": "https://www.transfermarkt.co.uk/liga-nos/startseite/wettbewerb/PO1",
    "Sweden": "https://www.transfermarkt.co.uk/allsvenskan/startseite/wettbewerb/SE1",
    "Swiss": "https://www.transfermarkt.co.uk/super-league/startseite/wettbewerb/C1",
    "Belgium": "https://www.transfermarkt.co.uk/jupiler-pro-league/startseite/wettbewerb/BE1",
    "Ligue-2": "https://www.transfermarkt.co.uk/ligue-2/startseite/wettbewerb/FR2",
    "Brasil": "https://www.transfermarkt.co.uk/campeonato-brasileiro-serie-a/startseite/wettbewerb/BRA1",
    "KSA": "https://www.transfermarkt.co.uk/saudi-professional-league/startseite/wettbewerb/SA1",
}

TRANSFERMARKT_CLUB_URLS_FILE = "data/transfermarkt_club_urls.json"


def convert_tf_value_to_float(tf_value: str) -> float:
    """Process transfermarkt value after scraping."""
    try:
        if isinstance(tf_value, float) or isinstance(tf_value, int):
            return tf_value
        if tf_value == "€0":
            return 0.0
        if "k" in tf_value:
            return float(tf_value.split("€")[1].split("k")[0]) / 1000
        if "m" in tf_value:
            return float(tf_value.split("€")[1].split("m")[0])
        return float(tf_value[1:-1])
    except Exception:
        raise ValueError(f"Error for value : {tf_value}")


def fetch_with_retry(url: str, max_retries: int = MAX_RETRIES) -> Optional[str]:
    """Fetch URL with exponential backoff retry logic."""
    for attempt in range(max_retries):
        delay = MIN_DELAY  # Initialize delay at the start of each attempt
        try:
            # Add random delay between attempts
            if attempt > 0:
                delay = MIN_DELAY * (2**attempt) + random.uniform(0, 1)
                delay = min(delay, MAX_DELAY)
                logger.info(
                    f"Retry attempt {attempt + 1}/{max_retries} after {delay:.2f}s delay"
                )
                time.sleep(delay)

            response = requests.get(url, headers=headers, timeout=TIMEOUT)
            if response.status_code == 503:
                logger.warning(f"Rate limited (503) on attempt {attempt + 1}")
                time.sleep(delay * 2)
                continue
            response.raise_for_status()
            return response.text

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise

    return None


def get_club_urls(
    leagues_to_extract: list[str],
    seasons: list[str],
    club_urls_json_file: str | None = None,
    timestamp_str: str | None = None,
) -> dict[str, str]:
    """Extract club URLs from Transfermarkt league pages.

    This function does not send concurrent requests to stay under rate limiting.

    Args:
        leagues_to_extract (list[str]): A list of leagues to extract club URLs from
        seasons (list[str]): The seasons to extract club URLs from
        club_urls_file (str | None): Path to checkpoint file for Transfermarkt club urls json file
        timestamp_str (str | None): Timestamp string for the checkpoint file

    Returns:
        dict[str, str]: A dictionary mapping club names + seasons to their Transfermarkt URLs
    """
    club_urls = {}

    if club_urls_json_file and os.path.exists(club_urls_json_file):
        with open(club_urls_json_file, "r") as f:
            club_urls = json.load(f)
        logger.info(f"Loaded {len(club_urls)} club URLs from {club_urls_json_file}")
        return club_urls

    else:
        if not club_urls_json_file:
            club_urls_json_file = f"data/transfermarkt_club_urls_{timestamp_str}.json"
        logger.info(f"Creating new club urls json file {club_urls_json_file}")

    for selected_league in leagues_to_extract:
        if selected_league in [
            "Champions League",
            "Conference League",
            "Europa League",
        ]:
            logger.info(
                "Skipping Champions League as it is not a league in Transfermarkt"
            )
            continue

        logger.info(f"Getting {selected_league} club URLs...")

        # Add season filter in the league URL
        for season in seasons:
            enriched_league_url_with_season = f"{TRANSFERMARKT_LEAGUE_URLS[selected_league]}/plus/?saison_id={SEASON_MAPPING_FBREF_TO_TRANSFERMARKT[season]}"
            content = fetch_with_retry(enriched_league_url_with_season)

            if not content:
                logger.error(
                    f"Failed to fetch {selected_league} page after all retries"
                )
                continue

            page_soup = BeautifulSoup(content, "html.parser")
            league_club_urls = {}

            # Find the table containing club information
            table = page_soup.find("table", {"class": "items"})
            if not table:
                logger.error(f"Could not find club table for {selected_league}")
                continue

            # Find all club rows
            club_rows = table.find_all("tr", {"class": ["odd", "even"]})
            for row in club_rows:
                try:
                    # Find the club name and URL in the first column
                    club_cell = row.find("td", {"class": "hauptlink no-border-links"})
                    if not club_cell:
                        continue

                    club_link = club_cell.find("a")
                    if not club_link:
                        continue

                    club_name = club_link["title"].strip()
                    club_url = f"https://www.transfermarkt.co.uk{club_link['href']}"
                    league_club_urls[(club_name, season)] = club_url
                except Exception as e:
                    logger.error(f"Error processing club row in {selected_league}: {e}")
                    continue

            logger.info(f"Found {len(league_club_urls)} clubs in {selected_league}")

            club_urls.update(
                {
                    "_".join(club_name_season_tuple): club_url
                    for club_name_season_tuple, club_url in league_club_urls.items()
                }
            )

            # Add delay between leagues to avoid rate limiting
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    with open(club_urls_json_file, "w") as f:
        json.dump(club_urls, f)

    logger.info(f"Done! Found {len(club_urls)} club URLs")
    return club_urls


def scrape_club(club_name: str, club_url: str, season: str) -> pd.DataFrame:
    """Scrape a single club's player values and images."""
    try:
        logger.info(f"Scraping {club_name} players...")
        content = fetch_with_retry(club_url)

        if not content:
            logger.error(f"Failed to fetch content for {club_name} after all retries")
            return pd.DataFrame()

        page_soup = BeautifulSoup(content, "html.parser")

        # Scrape player names and values
        players_list = [
            x.text.strip() for x in page_soup.find_all("td", {"class": "hauptlink"})
        ][::2]
        values = page_soup.find_all("td", {"class": "rechts hauptlink"})
        values_list = [v.text for v in values]

        # Scrape player images
        images_list = []
        player_cells = page_soup.find_all("td", {"class": "posrela"})
        for cell in player_cells:
            img_tag = cell.find("img", {"class": "bilderrahmen-fixed lazy lazy"})
            if img_tag and img_tag.get("data-src"):
                image_url = img_tag["data-src"]
            else:
                image_url = ""
            images_list.append(image_url)

        if not players_list or not values_list:
            logger.error(f"No player data found for {club_name}")
            return pd.DataFrame()

        df_temp = pd.DataFrame(
            {
                "Club": [TRANSFERMARKT_TO_FBREF_CLUB_NAME_MAPPING[club_name]]
                * len(values_list),
                "Player": players_list[: len(values_list)],
                VALUE_DISPLAY_NAME: values_list,
                TRANSFERMARKT_IMAGE_COL: images_list[: len(values_list)],
                "Season": season,
            }
        )

        df_temp[VALUE_DISPLAY_NAME] = (
            df_temp[VALUE_DISPLAY_NAME]
            .astype(str)
            .str.replace("-", "€0")
            .apply(convert_tf_value_to_float)
            .apply(lambda x: VALUE_FORMAT.format(x))
        )

        logger.info(f"Successfully scraped {len(df_temp)} players from {club_name}")
        return df_temp

    except KeyError as e:
        logger.error(f"Missing mapping for team {club_name}: {e}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"An unexpected error occurred for team {club_name}: {e}")
        return pd.DataFrame()


def extract_player_values(
    club_urls: dict[str, str],
    timestamp_str: str,
    seasons: list[str],
    checkpoint_file: str | None = None,
) -> pd.DataFrame:
    """Extract player values from Transfermarkt club pages

    Args:
        club_urls (dict[tuple[str, str], str]): A dictionary mapping club names + seasons to their Transfermarkt URLs
        timestamp_str (str): Timestamp string for the checkpoint file
        seasons (list[str]): Seasons to extract player values
        checkpoint_file (str | None): Path to checkpoint file for Transfermarkt scraping

    Returns:
        pd.DataFrame: A DataFrame containing player values from Transfermarkt
    """
    try:
        if checkpoint_file:
            df_transfermarkt = pd.read_csv(checkpoint_file)
            logger.info(
                f"Loaded {len(df_transfermarkt)} players from {df_transfermarkt['Club'].nunique()} clubs from checkpoint file {checkpoint_file}"
            )
        else:
            # Use first season to create checkpoint file
            checkpoint_file = (
                f"data/transfermarkt_checkpoint_{seasons[0]}_{timestamp_str}.csv"
            )
            df_transfermarkt = pd.DataFrame()
            logger.info(f"Creating new checkpoint file {checkpoint_file}")
    except Exception:
        df_transfermarkt = pd.DataFrame()

    for season in seasons:
        clubs_to_scrape = {}

        existing_clubs = (
            list(
                set(
                    df_transfermarkt[
                        df_transfermarkt["Season"].astype(int) == int(season)
                    ]["Club"].tolist()
                )
            )
            if "Club" in df_transfermarkt.columns and len(df_transfermarkt) > 0
            else []
        )

        logger.info(f"{len(existing_clubs)} existing clubs: {existing_clubs}")

        for club_name_season_key, url in club_urls.items():
            # Split club_name_season_key properly - season is always last element after underscore
            parts = club_name_season_key.rsplit("_", 1)
            if len(parts) != 2:
                logger.error(
                    f"Invalid club_name_season_key format: {club_name_season_key}"
                )
                continue

            club_name, club_season = parts

            # Only process clubs for the current season
            if club_season != season:
                continue

            try:
                fbref_club_name = TRANSFERMARKT_TO_FBREF_CLUB_NAME_MAPPING[club_name]
            except KeyError:
                logger.error(f"Missing mapping for team {club_name}")
                continue

            if fbref_club_name not in existing_clubs:
                logger.info(
                    f"New club name: {fbref_club_name}, existing clubs: {existing_clubs}"
                )
                clubs_to_scrape[(club_name, club_season)] = url
            else:
                logger.info(
                    f"Skipping {club_name} ({fbref_club_name}) for season {season} - already scraped"
                )

        logger.info(
            f"Scraping {len(clubs_to_scrape)} clubs for season {season}: {clubs_to_scrape.keys()}"
        )

        if not clubs_to_scrape:
            logger.info(f"All clubs already scraped for season {season}.")
            continue

        for (club_name, club_season), club_url in clubs_to_scrape.items():
            # Add delay between requests to avoid rate limiting
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

            df_temp = scrape_club(club_name, club_url, club_season)
            if not df_temp.empty:
                df_transfermarkt = pd.concat(
                    [df_transfermarkt, df_temp], ignore_index=True
                )
                if checkpoint_file:
                    logger.info(
                        f"Saving {len(df_transfermarkt)} players (club: {club_name}, season: {club_season}) to checkpoint file {checkpoint_file}"
                    )
                    df_transfermarkt.to_csv(checkpoint_file, index=False)

    return df_transfermarkt
