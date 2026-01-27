"""API router for club demands and demand matching."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, func
from sqlalchemy.orm import Session, joinedload

from scouting.api.services.demand_matching import (
    create_demand_matches,
    find_matching_players,
)
from scouting.db.models import (
    ClubDemand,
    DemandMatch,
    League,
    PlayerSeason,
    Season,
    Team,
)


def get_db():
    """Yield a database session for request lifetime."""
    from scouting.db.session import get_session_factory

    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()


router = APIRouter(prefix="/demands", tags=["demands"])


# Pydantic models for request/response


class ClubDemandCreate(BaseModel):
    club_name: str
    club_contact_name: Optional[str] = None
    club_contact_email: Optional[str] = None
    deadline: Optional[str] = None  # ISO date string
    priority: str = "medium"
    position: list[str]
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    nationality_preferences: Optional[list[str]] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    metrics_requirements: Optional[dict] = None
    playing_style_notes: Optional[str] = None
    default_season: str
    internal_notes: Optional[str] = None


class ClubDemandUpdate(BaseModel):
    club_name: Optional[str] = None
    club_contact_name: Optional[str] = None
    club_contact_email: Optional[str] = None
    deadline: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    position: Optional[list[str]] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    nationality_preferences: Optional[list[str]] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    metrics_requirements: Optional[dict] = None
    playing_style_notes: Optional[str] = None
    default_season: Optional[str] = None
    internal_notes: Optional[str] = None


class MatchCounts(BaseModel):
    suggested: int = 0
    proposed: int = 0
    interested: int = 0
    rejected: int = 0
    signed: int = 0


class DemandSummary(BaseModel):
    id: int
    club_name: str
    position: list[str]
    status: str
    priority: str
    deadline: Optional[str]
    created_date: str
    match_counts: MatchCounts


class DemandDetail(BaseModel):
    id: int
    club_name: str
    club_contact_name: Optional[str]
    club_contact_email: Optional[str]
    created_date: str
    deadline: Optional[str]
    status: str
    priority: str
    position: list[str]
    age_min: Optional[int]
    age_max: Optional[int]
    nationality_preferences: Optional[list[str]]
    budget_min: Optional[int]
    budget_max: Optional[int]
    metrics_requirements: Optional[dict]
    playing_style_notes: Optional[str]
    default_season: str
    internal_notes: Optional[str]
    match_counts: MatchCounts


class PlayerInfo(BaseModel):
    id: int
    name: str
    team: Optional[str]
    league: Optional[str]
    season: Optional[str]
    position: Optional[str]
    age: Optional[int]
    nationality: Optional[str]
    image_url: Optional[str]
    market_value: Optional[float]
    key_metrics: dict[str, float]


class DemandMatchResponse(BaseModel):
    id: int
    demand_id: int
    player_season_id: int
    match_score: float
    status: str
    added_date: str
    status_updated_date: str
    notes: Optional[str]
    player: PlayerInfo


class DemandMatchUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class MatchRequest(BaseModel):
    season: Optional[str] = None
    limit: int = 50


# Helper functions


def get_match_counts(db: Session, demand_id: int) -> MatchCounts:
    """Get counts of matches by status for a demand."""
    counts = (
        db.query(DemandMatch.status, func.count(DemandMatch.id))
        .filter(DemandMatch.demand_id == demand_id)
        .group_by(DemandMatch.status)
        .all()
    )

    match_counts = MatchCounts()
    for status, count in counts:
        setattr(match_counts, status, count)

    return match_counts


def demand_to_summary(demand: ClubDemand, db: Session) -> DemandSummary:
    """Convert ClubDemand to DemandSummary."""
    return DemandSummary(
        id=demand.id,
        club_name=demand.club_name,
        position=demand.position,
        status=demand.status,
        priority=demand.priority,
        deadline=demand.deadline.isoformat() if demand.deadline else None,
        created_date=demand.created_date.isoformat(),
        match_counts=get_match_counts(db, demand.id),
    )


def demand_to_detail(demand: ClubDemand, db: Session) -> DemandDetail:
    """Convert ClubDemand to DemandDetail."""
    return DemandDetail(
        id=demand.id,
        club_name=demand.club_name,
        club_contact_name=demand.club_contact_name,
        club_contact_email=demand.club_contact_email,
        created_date=demand.created_date.isoformat(),
        deadline=demand.deadline.isoformat() if demand.deadline else None,
        status=demand.status,
        priority=demand.priority,
        position=demand.position,
        age_min=demand.age_min,
        age_max=demand.age_max,
        nationality_preferences=demand.nationality_preferences,
        budget_min=demand.budget_min,
        budget_max=demand.budget_max,
        metrics_requirements=demand.metrics_requirements,
        playing_style_notes=demand.playing_style_notes,
        default_season=demand.default_season,
        internal_notes=demand.internal_notes,
        match_counts=get_match_counts(db, demand.id),
    )


def calculate_player_age(player_season: PlayerSeason) -> Optional[int]:
    """Calculate player's current age."""
    current_year = datetime.now().year
    if player_season.birth_date:
        age = current_year - player_season.birth_date.year
        if datetime.now().month < player_season.birth_date.month or (
            datetime.now().month == player_season.birth_date.month
            and datetime.now().day < player_season.birth_date.day
        ):
            age -= 1
        return age
    elif player_season.born_year:
        return current_year - player_season.born_year
    return None


def match_to_response(
    match: DemandMatch, db: Session, key_metrics: Optional[dict] = None
) -> DemandMatchResponse:
    """Convert DemandMatch to DemandMatchResponse with enriched player data."""
    player_season = match.player_season

    # Get team, league, season info
    team = db.query(Team).filter(Team.id == player_season.team_id).first()
    league = db.query(League).filter(League.id == player_season.league_id).first()
    season = db.query(Season).filter(Season.id == player_season.season_id).first()

    # Get key metrics if specified
    metrics_dict = {}
    if key_metrics:
        from scouting.db.models import MetricDefinition, PlayerMetric

        for metric_code in key_metrics.keys():
            metric_def = (
                db.query(MetricDefinition)
                .filter(MetricDefinition.code == metric_code)
                .first()
            )
            if metric_def:
                player_metric = (
                    db.query(PlayerMetric)
                    .filter(
                        and_(
                            PlayerMetric.player_season_id == player_season.id,
                            PlayerMetric.metric_id == metric_def.id,
                        )
                    )
                    .first()
                )
                if player_metric:
                    metrics_dict[metric_code] = player_metric.value

    player_info = PlayerInfo(
        id=player_season.id,
        name=player_season.player_name,
        team=team.name if team else None,
        league=league.name if league else None,
        season=season.label if season else None,
        position=player_season.position,
        age=calculate_player_age(player_season),
        nationality=player_season.nationality,
        image_url=player_season.image_url,
        market_value=player_season.market_value_eur,
        key_metrics=metrics_dict,
    )

    return DemandMatchResponse(
        id=match.id,
        demand_id=match.demand_id,
        player_season_id=match.player_season_id,
        match_score=match.match_score,
        status=match.status,
        added_date=match.added_date.isoformat(),
        status_updated_date=match.status_updated_date.isoformat(),
        notes=match.notes,
        player=player_info,
    )


# API Endpoints


@router.post("", response_model=DemandDetail, status_code=201)
def create_demand(demand: ClubDemandCreate, db: Session = Depends(get_db)):
    """Create a new club demand."""
    now = datetime.now()

    # Parse deadline if provided
    deadline = None
    if demand.deadline:
        try:
            deadline = datetime.fromisoformat(demand.deadline).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid deadline format")

    # Create demand
    db_demand = ClubDemand(
        club_name=demand.club_name,
        club_contact_name=demand.club_contact_name,
        club_contact_email=demand.club_contact_email,
        created_date=now,
        deadline=deadline,
        status="open",
        priority=demand.priority,
        position=demand.position,
        age_min=demand.age_min,
        age_max=demand.age_max,
        nationality_preferences=demand.nationality_preferences,
        budget_min=demand.budget_min,
        budget_max=demand.budget_max,
        metrics_requirements=demand.metrics_requirements,
        playing_style_notes=demand.playing_style_notes,
        default_season=demand.default_season,
        internal_notes=demand.internal_notes,
    )

    db.add(db_demand)
    db.commit()
    db.refresh(db_demand)

    return demand_to_detail(db_demand, db)


@router.get("", response_model=list[DemandSummary])
def list_demands(
    status: Optional[str] = Query(None),
    club_name: Optional[str] = Query(None),
    position: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List all demands with optional filters."""
    query = db.query(ClubDemand)

    if status:
        query = query.filter(ClubDemand.status == status)

    if club_name:
        query = query.filter(ClubDemand.club_name.ilike(f"%{club_name}%"))

    if position:
        query = query.filter(ClubDemand.position.contains([position]))

    if date_from:
        try:
            from_date = datetime.fromisoformat(date_from).date()
            query = query.filter(ClubDemand.created_date >= from_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format")

    if date_to:
        try:
            to_date = datetime.fromisoformat(date_to).date()
            query = query.filter(ClubDemand.created_date <= to_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format")

    demands = query.order_by(ClubDemand.created_date.desc()).all()
    return [demand_to_summary(d, db) for d in demands]


@router.get("/{demand_id}", response_model=DemandDetail)
def get_demand(demand_id: int, db: Session = Depends(get_db)):
    """Get demand detail."""
    demand = db.query(ClubDemand).filter(ClubDemand.id == demand_id).first()
    if not demand:
        raise HTTPException(status_code=404, detail="Demand not found")

    return demand_to_detail(demand, db)


@router.patch("/{demand_id}", response_model=DemandDetail)
def update_demand(
    demand_id: int, updates: ClubDemandUpdate, db: Session = Depends(get_db)
):
    """Update demand."""
    demand = db.query(ClubDemand).filter(ClubDemand.id == demand_id).first()
    if not demand:
        raise HTTPException(status_code=404, detail="Demand not found")

    # Update fields
    update_data = updates.model_dump(exclude_unset=True)

    # Handle deadline conversion
    if "deadline" in update_data and update_data["deadline"]:
        try:
            update_data["deadline"] = datetime.fromisoformat(
                update_data["deadline"]
            ).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid deadline format")

    for field, value in update_data.items():
        setattr(demand, field, value)

    db.commit()
    db.refresh(demand)

    return demand_to_detail(demand, db)


@router.delete("/{demand_id}", status_code=204)
def delete_demand(demand_id: int, db: Session = Depends(get_db)):
    """Delete demand and associated matches."""
    demand = db.query(ClubDemand).filter(ClubDemand.id == demand_id).first()
    if not demand:
        raise HTTPException(status_code=404, detail="Demand not found")

    db.delete(demand)
    db.commit()
    return None


@router.post("/{demand_id}/match", response_model=list[DemandMatchResponse])
def run_matching(
    demand_id: int,
    match_request: Optional[MatchRequest] = None,
    db: Session = Depends(get_db),
):
    """Run matching algorithm for a demand."""
    demand = (
        db.query(ClubDemand)
        .options(joinedload(ClubDemand.matches))
        .filter(ClubDemand.id == demand_id)
        .first()
    )
    if not demand:
        raise HTTPException(status_code=404, detail="Demand not found")

    # Get matching parameters
    season = None
    limit = 50
    if match_request:
        season = match_request.season
        limit = match_request.limit

    # Find matching players
    matched_players = find_matching_players(db, demand, season=season, limit=limit)

    # Create/update demand matches
    matches = create_demand_matches(db, demand_id, matched_players)

    # Return enriched match data
    return [
        match_to_response(m, db, key_metrics=demand.metrics_requirements)
        for m in matches
    ]


@router.get("/{demand_id}/matches", response_model=list[DemandMatchResponse])
def get_demand_matches(
    demand_id: int,
    status: Optional[str] = Query(None),
    sort_by: str = Query("match_score", regex="^(match_score|added_date)$"),
    db: Session = Depends(get_db),
):
    """Get all matched players for a demand."""
    demand = db.query(ClubDemand).filter(ClubDemand.id == demand_id).first()
    if not demand:
        raise HTTPException(status_code=404, detail="Demand not found")

    query = (
        db.query(DemandMatch)
        .options(joinedload(DemandMatch.player_season))
        .filter(DemandMatch.demand_id == demand_id)
    )

    if status:
        query = query.filter(DemandMatch.status == status)

    # Sort
    if sort_by == "match_score":
        query = query.order_by(DemandMatch.match_score.desc())
    else:  # added_date
        query = query.order_by(DemandMatch.added_date.desc())

    matches = query.all()
    return [
        match_to_response(m, db, key_metrics=demand.metrics_requirements)
        for m in matches
    ]


@router.patch(
    "/{demand_id}/matches/{player_season_id}", response_model=DemandMatchResponse
)
def update_match(
    demand_id: int,
    player_season_id: int,
    updates: DemandMatchUpdate,
    db: Session = Depends(get_db),
):
    """Update match status and/or notes."""
    match = (
        db.query(DemandMatch)
        .filter(
            and_(
                DemandMatch.demand_id == demand_id,
                DemandMatch.player_season_id == player_season_id,
            )
        )
        .first()
    )
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Update fields
    if updates.status:
        match.status = updates.status
        match.status_updated_date = datetime.now()
    if updates.notes is not None:
        match.notes = updates.notes

    db.commit()
    db.refresh(match)

    demand = db.query(ClubDemand).filter(ClubDemand.id == demand_id).first()
    return match_to_response(match, db, key_metrics=demand.metrics_requirements)


@router.post(
    "/{demand_id}/matches/{player_season_id}/propose",
    response_model=DemandMatchResponse,
)
def propose_match(
    demand_id: int, player_season_id: int, db: Session = Depends(get_db)
):
    """Shortcut to set status to proposed."""
    match = (
        db.query(DemandMatch)
        .filter(
            and_(
                DemandMatch.demand_id == demand_id,
                DemandMatch.player_season_id == player_season_id,
            )
        )
        .first()
    )
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match.status = "proposed"
    match.status_updated_date = datetime.now()

    db.commit()
    db.refresh(match)

    demand = db.query(ClubDemand).filter(ClubDemand.id == demand_id).first()
    return match_to_response(match, db, key_metrics=demand.metrics_requirements)


@router.delete("/{demand_id}/matches/{player_season_id}", status_code=204)
def delete_match(
    demand_id: int, player_season_id: int, db: Session = Depends(get_db)
):
    """Remove player from demand matches."""
    match = (
        db.query(DemandMatch)
        .filter(
            and_(
                DemandMatch.demand_id == demand_id,
                DemandMatch.player_season_id == player_season_id,
            )
        )
        .first()
    )
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    db.delete(match)
    db.commit()
    return None
