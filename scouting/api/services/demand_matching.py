"""Service for matching players to club demands."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from scouting.db.models import (
    ClubDemand,
    DemandMatch,
    League,
    MetricDefinition,
    PlayerMetric,
    PlayerSeason,
    Season,
    Team,
)


def calculate_player_age(player_season: PlayerSeason) -> Optional[int]:
    """Calculate player's current age from birth year or birth date."""
    current_year = datetime.now().year

    if player_season.birth_date:
        age = current_year - player_season.birth_date.year
        # Adjust if birthday hasn't occurred this year
        if datetime.now().month < player_season.birth_date.month or (
            datetime.now().month == player_season.birth_date.month
            and datetime.now().day < player_season.birth_date.day
        ):
            age -= 1
        return age
    elif player_season.born_year:
        return current_year - player_season.born_year
    return None


def calculate_match_score(
    player_season: PlayerSeason,
    demand: ClubDemand,
    metrics: dict[str, float],
) -> float:
    """Calculate a match score (0-1) for a player against a demand.

    The score is based on:
    - Position match (required)
    - Age within range (if specified)
    - Nationality preference (if specified)
    - Budget fit (if specified)
    - Metrics meeting thresholds

    Args:
        player_season: The player to evaluate
        demand: The club demand
        metrics: Dict of metric_code -> value for this player

    Returns:
        Float between 0 and 1 indicating match quality
    """
    score = 0.0
    max_score = 0.0

    # Position match (required - already filtered, so this is always a match)
    score += 1.0
    max_score += 1.0

    # Age fit (weight: 0.5)
    max_score += 0.5
    age = calculate_player_age(player_season)
    if age:
        if demand.age_min and demand.age_max:
            age_range = demand.age_max - demand.age_min
            if age_range > 0:
                # Calculate how centered the player is in the age range
                age_mid = (demand.age_min + demand.age_max) / 2
                deviation = abs(age - age_mid)
                normalized_deviation = deviation / (age_range / 2)
                score += 0.5 * max(0, 1 - normalized_deviation)
            else:
                # Exact age match
                score += 0.5 if age == demand.age_min else 0
        elif demand.age_min:
            score += 0.5 if age >= demand.age_min else 0.25
        elif demand.age_max:
            score += 0.5 if age <= demand.age_max else 0.25
        else:
            score += 0.5  # No age preference

    # Nationality preference (weight: 0.3)
    max_score += 0.3
    if demand.nationality_preferences:
        if player_season.nationality in demand.nationality_preferences:
            score += 0.3
    else:
        score += 0.3  # No nationality preference

    # Budget fit (weight: 0.2)
    max_score += 0.2
    if demand.budget_min or demand.budget_max:
        if player_season.market_value_eur:
            value_eur = int(player_season.market_value_eur)
            within_budget = True
            if demand.budget_min and value_eur < demand.budget_min:
                within_budget = False
            if demand.budget_max and value_eur > demand.budget_max:
                within_budget = False
            score += 0.2 if within_budget else 0
    else:
        score += 0.2  # No budget constraint

    # Metrics requirements (weight: 1.0 per metric)
    if demand.metrics_requirements:
        for metric_code, requirements in demand.metrics_requirements.items():
            max_score += 1.0
            metric_value = metrics.get(metric_code)
            if metric_value is not None:
                meets_min = True
                meets_max = True

                if "min" in requirements:
                    meets_min = metric_value >= requirements["min"]
                if "max" in requirements:
                    meets_max = metric_value <= requirements["max"]

                if meets_min and meets_max:
                    score += 1.0
                elif meets_min or meets_max:
                    score += 0.5

    # Normalize to 0-1 range
    return score / max_score if max_score > 0 else 0.0


def find_matching_players(
    db: Session,
    demand: ClubDemand,
    season: Optional[str] = None,
    limit: int = 50,
) -> list[tuple[PlayerSeason, float, dict[str, float]]]:
    """Find players matching a club demand.

    Returns list of (player_season, match_score, metrics_dict) tuples.
    """
    # Use specified season or demand's default
    target_season = season or demand.default_season

    # Base query with all required joins
    query = (
        db.query(PlayerSeason)
        .join(Season, PlayerSeason.season_id == Season.id)
        .outerjoin(Team, PlayerSeason.team_id == Team.id)
        .outerjoin(League, PlayerSeason.league_id == League.id)
    )

    # Filter by season
    query = query.filter(Season.label == target_season)

    # Filter by position (required)
    query = query.filter(PlayerSeason.position.in_(demand.position))

    # Filter by minimum minutes played (270 as per design)
    query = query.filter((PlayerSeason.minutes != None) & (PlayerSeason.minutes >= 270))

    # Filter by age range if specified
    if demand.age_min or demand.age_max:
        current_year = datetime.now().year

        if demand.age_min:
            max_birth_year = current_year - demand.age_min
            query = query.filter(
                or_(
                    PlayerSeason.born_year <= max_birth_year,
                    and_(
                        PlayerSeason.birth_date != None,
                        PlayerSeason.birth_date <= datetime(max_birth_year, 12, 31),
                    ),
                )
            )

        if demand.age_max:
            min_birth_year = current_year - demand.age_max - 1
            query = query.filter(
                or_(
                    PlayerSeason.born_year >= min_birth_year,
                    and_(
                        PlayerSeason.birth_date != None,
                        PlayerSeason.birth_date >= datetime(min_birth_year, 1, 1),
                    ),
                )
            )

    # Filter by nationality preferences if specified
    if demand.nationality_preferences:
        query = query.filter(
            PlayerSeason.nationality.in_(demand.nationality_preferences)
        )

    # Get candidate players
    candidates = query.all()

    # Get metric requirements for filtering
    metric_filters = {}
    if demand.metrics_requirements:
        for metric_code in demand.metrics_requirements.keys():
            metric_def = (
                db.query(MetricDefinition)
                .filter(MetricDefinition.code == metric_code)
                .first()
            )
            if metric_def:
                metric_filters[metric_code] = metric_def.id

    # Build results with match scores
    results = []
    for player_season in candidates:
        # Fetch player's metrics
        player_metrics_query = (
            db.query(PlayerMetric, MetricDefinition.code)
            .join(MetricDefinition, PlayerMetric.metric_id == MetricDefinition.id)
            .filter(PlayerMetric.player_season_id == player_season.id)
        )

        # Filter to only required metrics if specified
        if metric_filters:
            player_metrics_query = player_metrics_query.filter(
                MetricDefinition.code.in_(list(metric_filters.keys()))
            )

        player_metrics_rows = player_metrics_query.all()
        metrics_dict = {code: pm.value for pm, code in player_metrics_rows}

        # Apply hard metric thresholds
        if demand.metrics_requirements:
            meets_all_thresholds = True
            for metric_code, requirements in demand.metrics_requirements.items():
                metric_value = metrics_dict.get(metric_code)
                if metric_value is None:
                    meets_all_thresholds = False
                    break

                if "min" in requirements and metric_value < requirements["min"]:
                    meets_all_thresholds = False
                    break
                if "max" in requirements and metric_value > requirements["max"]:
                    meets_all_thresholds = False
                    break

            if not meets_all_thresholds:
                continue

        # Calculate match score
        match_score = calculate_match_score(player_season, demand, metrics_dict)
        results.append((player_season, match_score, metrics_dict))

    # Sort by match score descending and limit
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:limit]


def create_demand_matches(
    db: Session,
    demand_id: int,
    player_seasons_with_scores: list[tuple[PlayerSeason, float, dict[str, float]]],
) -> list[DemandMatch]:
    """Create DemandMatch records for matched players.

    Args:
        db: Database session
        demand_id: ID of the demand
        player_seasons_with_scores: List of (player_season, match_score, metrics) tuples

    Returns:
        List of created DemandMatch objects
    """
    now = datetime.now()
    matches = []

    for player_season, match_score, _ in player_seasons_with_scores:
        # Check if match already exists
        existing = (
            db.query(DemandMatch)
            .filter(
                DemandMatch.demand_id == demand_id,
                DemandMatch.player_season_id == player_season.id,
            )
            .first()
        )

        if existing:
            # Update existing match score if different
            if existing.match_score != match_score:
                existing.match_score = match_score
                existing.status_updated_date = now
            matches.append(existing)
        else:
            # Create new match
            match = DemandMatch(
                demand_id=demand_id,
                player_season_id=player_season.id,
                match_score=match_score,
                status="suggested",
                added_date=now,
                status_updated_date=now,
            )
            db.add(match)
            matches.append(match)

    db.commit()
    return matches
