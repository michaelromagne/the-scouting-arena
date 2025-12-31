from __future__ import annotations

import difflib
import json
import logging
import os
import re
import time
import unicodedata
from datetime import datetime
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, field_validator
from sqlalchemy import asc, desc, extract, or_
from sqlalchemy.orm import Session, aliased

from scouting.app.utils import format_season
from scouting.constants import (
    AGGREGATED_LEAGUE_NAME,
    BIG_5_FILTER_NAME,
    BIG_5_LEAGUES,
    SCOUTING_STATISTICS,
)
from scouting.db.models import (
    Feedback,
    League,
    MetricDefinition,
    MetricSet,
    PlayerMetric,
    PlayerSeason,
    PlayerSimilarity,
    Season,
    Team,
    TeamMetric,
    TeamSeason,
)
from scouting.db.session import get_session_factory, init_db

ETL_TIMEOUT = 36000

logger = logging.getLogger(__name__)

app = FastAPI(title="Scouting API", version="0.1.0")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log validation errors for debugging."""
    logger.error(f"❌ Validation error on {request.url}: {exc.errors()}")
    logger.error(f"   Body: {exc.body}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )


def apply_league_filter(query, league: str, league_model):
    """Apply league filter to query, handling Big 5 special case.

    Args:
        query: SQLAlchemy query object
        league: League name or Big 5 filter
        league_model: The League model/alias to filter on

    Returns:
        Filtered query
    """
    if league == BIG_5_FILTER_NAME:
        # Filter for Big 5 European leagues
        return query.filter(league_model.name.in_(BIG_5_LEAGUES))
    else:
        return query.filter(league_model.name == league)


def _parse_csv_env(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return default
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts or default


def _str2bool(val: str | None, default: bool) -> bool:
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def remove_accents(text: str) -> str:
    """Remove accents from text for normalized searching.

    This allows searches like 'Dembele' to match 'Ousmane Dembélé'.
    """
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


# CORS configuration with safe defaults
_default_cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
_allow_origins = _parse_csv_env("CORS_ALLOW_ORIGINS", _default_cors_origins)
_allow_methods = _parse_csv_env("CORS_ALLOW_METHODS", ["GET", "POST", "OPTIONS"])
_allow_headers = _parse_csv_env(
    "CORS_ALLOW_HEADERS", ["Authorization", "Content-Type", "Accept", "Origin"]
)
_allow_credentials = _str2bool(os.getenv("CORS_ALLOW_CREDENTIALS"), False)

# If wildcard origins, disable credentials to comply with CORS spec
if _allow_origins == ["*"]:
    _allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_methods=_allow_methods,
    allow_headers=_allow_headers,
    allow_credentials=_allow_credentials,
    expose_headers=["Content-Disposition"],
    max_age=600,
)


class CacheBackend:
    def get(self, key: str) -> str | None:  # pragma: no cover - small utility
        raise NotImplementedError

    def set(self, key: str, value: str, ttl_seconds: int) -> None:  # pragma: no cover
        raise NotImplementedError


class MemoryCache(CacheBackend):
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, str]] = {}

    def get(self, key: str) -> str | None:
        now = time.time()
        item = self._store.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at < now:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._store[key] = (time.time() + ttl_seconds, value)


class RedisCache(CacheBackend):
    def __init__(self, url: str, prefix: str) -> None:
        import redis  # type: ignore

        self._r = redis.Redis.from_url(url)
        self._prefix = prefix

    def _k(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def get(self, key: str) -> str | None:
        data = self._r.get(self._k(key))
        return data.decode("utf-8") if data else None

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._r.set(self._k(key), value, ex=ttl_seconds)


def _create_cache_backend() -> CacheBackend:
    url = os.getenv("REDIS_URL")
    prefix = os.getenv("CACHE_PREFIX", "scouting:api:")
    if url:
        try:
            return RedisCache(url, prefix)
        except Exception:
            # Fallback to memory if Redis is unavailable
            return MemoryCache()
    return MemoryCache()


_CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "300"))
_CACHE = _create_cache_backend()


def _suggest_metric_codes(db: Session, code: str, n: int = 5) -> list[str]:
    codes = [c[0] for c in db.query(MetricDefinition.code).all()]
    return difflib.get_close_matches(code, codes, n=n, cutoff=0.4)


def get_db():
    """Yield a database session for request lifetime."""

    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()


class HealthResponse(BaseModel):
    status: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


class ETLTriggerResponse(BaseModel):
    status: str
    message: str
    timestamp: str


@app.post("/admin/trigger-etl", response_model=ETLTriggerResponse)
async def trigger_etl(
    background_tasks: BackgroundTasks,
    password: str = Query(
        ..., description="Admin password (set via ETL_PASSWORD env var)"
    ),
    seasons: str = Query("2425,2526", description="Comma-separated seasons"),
    leagues: str = Query("All", description="Comma-separated leagues or 'All'"),
):
    """Trigger the weekly ETL update process.

    Run in background so response is immediate.
    Requires password for authentication.
    """
    from datetime import datetime

    # Simple password authentication
    expected_password = os.getenv("ETL_PASSWORD")
    if not expected_password:
        raise HTTPException(
            status_code=500, detail="ETL_PASSWORD not configured on server"
        )
    if password != expected_password:
        raise HTTPException(status_code=401, detail="Invalid password")

    # Schedule ETL to run in background
    background_tasks.add_task(run_etl_background, seasons, leagues)

    return ETLTriggerResponse(
        status="started",
        message=f"ETL pipeline triggered for seasons={seasons}, leagues={leagues}",
        timestamp=datetime.now().isoformat(),
    )


async def run_etl_background(seasons: str, leagues: str):
    """Run ETL pipeline in background using the weekly_update.sh script."""
    import subprocess
    import sys

    logger = logging.getLogger(__name__)
    logger.info(f"Starting ETL pipeline for seasons={seasons}, leagues={leagues}")
    logger.info("=" * 80)
    logger.info("ETL JOB STARTED - Logs will appear below")
    logger.info("=" * 80)

    try:
        # Run the weekly update script with output streaming to stdout/stderr
        # This allows logs to appear in Railway's logs in real-time
        process = subprocess.Popen(
            ["bash", "/app/scripts/weekly_update.sh"],
            env={
                **os.environ,
                "SEASONS": seasons,
                "LEAGUES": leagues,
            },
            stdout=sys.stdout,  # Stream directly to Railway logs
            stderr=sys.stderr,  # Stream errors to Railway logs
            text=True,
        )

        # Wait for process to complete (with timeout)
        try:
            returncode = process.wait(timeout=ETL_TIMEOUT)  # 2 hour timeout
        except subprocess.TimeoutExpired:
            process.kill()
            logger.error("=" * 80)
            logger.error("ETL process timed out after 2 hours")
            logger.error("=" * 80)
            return

        logger.info("=" * 80)
        if returncode != 0:
            logger.error(f"ETL JOB FAILED with return code {returncode}")
        else:
            logger.info("ETL JOB COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)

    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"ETL process failed with exception: {e}")
        logger.error("=" * 80)


class MetricOut(BaseModel):
    code: str
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    direction: str
    scale: Optional[str] = None


class PaginatedMetrics(BaseModel):
    total: int
    items: list[MetricOut]


@app.get("/metrics", response_model=PaginatedMetrics)
def list_metrics(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Search by code or name"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """List metric definitions with simple search and pagination."""

    # Cache key
    ck = f"metrics:q={q or ''}:offset={offset}:limit={limit}"
    cached = _CACHE.get(ck)
    if cached:
        return PaginatedMetrics(**json.loads(cached))

    query = db.query(MetricDefinition)
    if q:
        pattern = f"%{q.lower()}%"
        query = query.filter(
            (MetricDefinition.code.ilike(pattern))
            | (MetricDefinition.name.ilike(pattern))
        )
    total = query.count()
    rows = query.order_by(MetricDefinition.code).offset(offset).limit(limit).all()
    items = [
        MetricOut(
            code=r.code,
            name=r.name,
            category=r.category,
            description=r.description,
            direction=r.direction,
            scale=r.scale,
        )
        for r in rows
    ]
    result = PaginatedMetrics(total=total, items=items)
    _CACHE.set(ck, json.dumps(result.model_dump()), _CACHE_TTL)
    return result


@app.on_event("startup")
def _startup() -> None:
    # For proper Alembic-managed schemas, avoid auto-creating tables by default.
    # Enable only for quick local dev by setting AUTO_CREATE_TABLES=true
    if os.getenv("AUTO_CREATE_TABLES", "false").lower() in {"1", "true", "yes", "on"}:
        init_db()


class PlayerItem(BaseModel):
    player_id: int
    player_name: str
    team_name: Optional[str]
    league_name: Optional[str]
    season_label: Optional[str]
    minutes: Optional[int]
    position: Optional[str]
    image_url: Optional[str]
    market_value_eur: Optional[float]
    nationality: Optional[str]
    birth_date: Optional[str]


class PaginatedPlayers(BaseModel):
    total: int
    items: list[PlayerItem]


@app.get("/players", response_model=PaginatedPlayers)
def list_players(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Search player name (ilike)"),
    league: Optional[str] = Query(None, description="Filter by league name"),
    season: Optional[str] = Query(None, description="Filter by season label"),
    team: Optional[str] = Query(None, description="Filter by team name"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1),  # Removed le=200 limit to allow all players
):
    """List players (per season) with optional filters and pagination.

    Returns one row per player-season (with team & league if present).
    """

    query = (
        db.query(PlayerSeason, Team, League, Season)
        .outerjoin(Team, PlayerSeason.team_id == Team.id)
        .outerjoin(League, PlayerSeason.league_id == League.id)
        .outerjoin(Season, PlayerSeason.season_id == Season.id)
    )

    if q:
        # Always create a comprehensive accent-insensitive search
        # Build a regex pattern that matches each character with all its accent variants
        pattern_chars = []
        for char in q.lower():
            if char == "a":
                pattern_chars.append("[aàáâãäåæ]")
            elif char == "e":
                pattern_chars.append("[eèéêë]")
            elif char == "i":
                pattern_chars.append("[iìíîï]")
            elif char == "o":
                pattern_chars.append("[oòóôõöøœ]")
            elif char == "u":
                pattern_chars.append("[uùúûüý]")
            elif char == "n":
                pattern_chars.append("[nñ]")
            elif char == "c":
                pattern_chars.append("[cç]")
            elif char == "s":
                pattern_chars.append("[sś]")
            elif char == "z":
                pattern_chars.append("[zž]")
            elif char == "y":
                pattern_chars.append("[yÿ]")
            elif char == " ":
                pattern_chars.append("\\s+")
            else:
                pattern_chars.append(re.escape(char))

        # Create regex pattern that handles ALL accent combinations
        accent_pattern = "".join(pattern_chars)

        # Use both simple search and comprehensive regex
        search_conditions = [
            PlayerSeason.player_name.ilike(f"%{q}%"),  # Original exact search
            PlayerSeason.player_name.op("~*")(
                f".*{accent_pattern}.*"
            ),  # Comprehensive accent-insensitive
        ]

        query = query.filter(or_(*search_conditions))
    if league:
        query = apply_league_filter(query, league, League)
    if season:
        # Accept both short (e.g., 2425) and long (e.g., 2024-2025) season strings
        season_candidates = {season}
        if re.fullmatch(r"\d{4}", season):
            # short → long
            try:
                season_candidates.add(format_season(season))
            except Exception:
                pass
        if re.fullmatch(r"\d{4}-\d{4}", season):
            # long → short (last two digits)
            y1, y2 = season.split("-")
            season_candidates.add(f"{y1[-2:]}{y2[-2:]}")
        query = query.filter(Season.label.in_(list(season_candidates)))
    if team:
        # Handle combined teams like "Aston Villa & Manchester United"
        query = query.filter(
            or_(
                Team.name == team,
                Team.name.like(f"%{team} & %"),
                Team.name.like(f"% & {team}"),
                Team.name.like(f"% & {team} & %"),
            )
        )

    total = query.count()
    rows = (
        query.order_by(Season.label.desc().nullslast(), PlayerSeason.player_name.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    items = [
        PlayerItem(
            player_id=ps.id,
            player_name=ps.player_name,
            team_name=t.name if t else None,
            league_name=l.name if l else None,
            season_label=s.label if s else None,
            minutes=ps.minutes,
            position=ps.position,
            image_url=ps.image_url,
            market_value_eur=ps.market_value_eur,
            nationality=ps.nationality,
            birth_date=ps.birth_date.isoformat() if ps.birth_date else None,
        )
        for ps, t, l, s in rows
    ]
    return PaginatedPlayers(total=total, items=items)


# ============================================================================
# TEAM ANALYSIS ENDPOINTS
# ============================================================================


class TeamOut(BaseModel):
    id: int
    name: str
    league_name: Optional[str] = None
    league_id: Optional[int] = None


@app.get("/teams/list", response_model=list[TeamOut])
def list_teams_detailed(
    league: Optional[str] = Query(None, description="Filter by league name"),
    season: Optional[str] = Query(None, description="Filter by season label"),
    db: Session = Depends(get_db),
):
    """List all teams with full details, optionally filtered by league and/or season.

    Args:
        league: League name to filter by (e.g., "FRA-Ligue 1")
        season: Season label to filter by (e.g., "2526")
        db: Database session

    Returns:
        List of teams with their IDs and names
    """
    query = db.query(Team, League.name.label("league_name")).join(
        League, Team.league_id == League.id, isouter=True
    )

    # Apply filters if provided
    if season:
        # Filter teams that have team_seasons for this season
        query = (
            query.join(TeamSeason, TeamSeason.team_id == Team.id)
            .join(Season, TeamSeason.season_id == Season.id)
            .filter(Season.label == season)
        )

    if league:
        query = apply_league_filter(query, league, League)

    # Get distinct teams and sort alphabetically
    query = query.distinct().order_by(Team.name)

    results = query.all()

    return [
        TeamOut(
            id=team.id,
            name=team.name,
            league_name=league_name,
            league_id=team.league_id,
        )
        for team, league_name in results
    ]


@app.get("/teams")
def list_teams(db: Session = Depends(get_db)):
    """List all unique team names (for filters and dropdowns).

    Returns:
        List of team name strings
    """
    teams = (
        db.query(Team.name)
        .filter(Team.name.isnot(None))
        .distinct()
        .order_by(Team.name)
        .all()
    )
    return [team[0] for team in teams]


@app.get("/leagues")
def list_leagues(db: Session = Depends(get_db)):
    """List all available leagues."""
    leagues = (
        db.query(League.name)
        .filter(League.name.isnot(None))
        .distinct()
        .order_by(League.name)
        .all()
    )
    return [league[0] for league in leagues]


@app.get("/seasons")
def list_seasons(db: Session = Depends(get_db)):
    """List all available seasons."""
    seasons = (
        db.query(Season.label)
        .filter(Season.label.isnot(None))
        .distinct()
        .order_by(Season.label.desc())
        .all()
    )
    return [season[0] for season in seasons]


@app.get("/positions")
def list_positions(db: Session = Depends(get_db)):
    """List all available positions."""
    positions = (
        db.query(PlayerSeason.position)
        .filter(PlayerSeason.position.isnot(None))
        .distinct()
        .order_by(PlayerSeason.position)
        .all()
    )
    return [position[0] for position in positions]


@app.get("/nations")
def list_nations(db: Session = Depends(get_db)):
    """List all available nations/nationalities."""
    nations = (
        db.query(PlayerSeason.nationality)
        .filter(PlayerSeason.nationality.isnot(None))
        .distinct()
        .order_by(PlayerSeason.nationality)
        .all()
    )
    return [nation[0] for nation in nations]


class PlayerImageOut(BaseModel):
    player_id: int
    player_name: str
    # image_url: Optional[str]  # Temporarily removed - not in DB yet


@app.get("/players/{player_id}/image", response_model=PlayerImageOut)
def get_player_image(player_id: int, db: Session = Depends(get_db)):
    ps = db.query(PlayerSeason).filter(PlayerSeason.id == player_id).one_or_none()
    if not ps:
        raise HTTPException(status_code=404, detail="Player not found")
    return PlayerImageOut(player_id=ps.id, player_name=ps.player_name)


class PlayerMetricOut(BaseModel):
    code: str
    name: str
    category: Optional[str]
    quantile_value: Optional[float]


class PlayerDetail(BaseModel):
    player_id: int
    player_name: str
    team_name: Optional[str]
    league_name: Optional[str]
    season_label: Optional[str]
    minutes: Optional[int]
    position: Optional[str]
    value_m_eur: Optional[float]
    image_url: Optional[str]
    nationality: Optional[str]
    birth_date: Optional[str]  # ISO date string (YYYY-MM-DD)
    metrics: list[PlayerMetricOut]


class SimilarPlayerOut(BaseModel):
    player_id: int
    player_name: str
    team_name: Optional[str]
    league_name: Optional[str]
    season_label: Optional[str]
    position: Optional[str]
    value_m_eur: Optional[float]
    similarity_score: float
    image_url: Optional[str]
    nationality: Optional[str]
    birth_date: Optional[str]  # ISO date string (YYYY-MM-DD)
    age: Optional[int]  # Calculated age


class SimilarPlayersResponse(BaseModel):
    target_player_id: int
    target_player_name: str
    similar_players: list[SimilarPlayerOut]


@app.get("/players/{player_id}", response_model=PlayerDetail)
def get_player_details(
    player_id: int,
    db: Session = Depends(get_db),
    season: Optional[str] = Query(None, description="Season label (2425 or 2024-2025)"),
    league: Optional[str] = Query(
        None,
        description="League name (ignored - player_id already identifies a unique player-season-league)",
    ),
):
    """
    Get detailed information for a specific player.

    Note: player_id is actually a player_season_id which uniquely identifies
    a player in a specific season and league. The league parameter is accepted
    for API compatibility but ignored since the player_id already determines the league.
    """
    # Resolve target player-season (latest if not provided)
    base_q = (
        db.query(PlayerSeason, Team, League, Season)
        .outerjoin(Team, PlayerSeason.team_id == Team.id)
        .outerjoin(League, PlayerSeason.league_id == League.id)
        .outerjoin(Season, PlayerSeason.season_id == Season.id)
        .filter(PlayerSeason.id == player_id)
    )

    if season:
        season_candidates = {season}
        if re.fullmatch(r"\d{4}", season):
            try:
                season_candidates.add(format_season(season))
            except Exception:
                pass
        if re.fullmatch(r"\d{4}-\d{4}", season):
            y1, y2 = season.split("-")
            season_candidates.add(f"{y1[-2:]}{y2[-2:]}")
        base_q = base_q.filter(Season.label.in_(list(season_candidates)))

    # Note: We do NOT filter by league here because player_id (player_season_id)
    # already uniquely identifies a player in a specific league+season

    row = base_q.order_by(Season.label.desc().nullslast()).first()
    if not row:
        raise HTTPException(status_code=404, detail="Player (season) not found")

    player_season, team, league_obj, season_obj = row

    # Load all metrics for this player-season
    mrows = (
        db.query(MetricDefinition, PlayerMetric)
        .join(PlayerMetric, PlayerMetric.metric_id == MetricDefinition.id)
        .filter(PlayerMetric.player_season_id == player_season.id)
        .all()
    )

    # Get market value from player season record
    value_m_eur = player_season.market_value_eur

    metrics = [
        PlayerMetricOut(
            code=md.code,
            name=md.name,
            category=md.category,
            quantile_value=float(pm.value) if pm.value is not None else None,
        )
        for md, pm in mrows
    ]

    return PlayerDetail(
        player_id=player_season.id,
        player_name=player_season.player_name,
        team_name=team.name if team else None,
        league_name=league_obj.name if league_obj else None,
        season_label=season_obj.label if season_obj else None,
        minutes=player_season.minutes,
        position=player_season.position,
        value_m_eur=value_m_eur,
        image_url=player_season.image_url,
        nationality=player_season.nationality,
        birth_date=player_season.birth_date.isoformat()
        if player_season.birth_date
        else None,
        metrics=sorted(
            metrics,
            key=lambda m: (
                (m.category or "zzz"),
                m.code,
            ),  # stable sort by category/code
        ),
    )


class RankingItem(BaseModel):
    player_id: int
    player_name: str
    team_name: Optional[str]
    league_name: Optional[str]
    season_label: Optional[str]
    quantile_value: float
    image_url: Optional[str] = None
    nationality: Optional[str] = None
    birth_date: Optional[str] = None
    value_m_eur: Optional[float] = None


class RankingsResponse(BaseModel):
    metric: str
    direction: str
    total: int
    items: list[RankingItem]


DEFAULT_MIN_MINUTES = 0
DEFAULT_RANKINGS_LIMIT = 25


@app.get("/rankings", response_model=RankingsResponse)
def rankings(
    metric: str = Query(..., description="Metric code (e.g., expected_xg_per_90)"),
    db: Session = Depends(get_db),
    league: Optional[str] = Query(None),
    season: Optional[str] = Query(None),
    pos: Optional[str] = Query(
        None, description="Position filter (e.g., FW, MF, DF, GK)"
    ),
    team: Optional[str] = Query(None, description="Team name filter"),
    nation: Optional[str] = Query(None, description="Player nationality filter"),
    min_minutes: int = Query(DEFAULT_MIN_MINUTES, ge=0),
    min_value: Optional[float] = Query(
        None, description="Minimum market value in millions EUR"
    ),
    max_value: Optional[float] = Query(
        None, description="Maximum market value in millions EUR"
    ),
    min_age: Optional[int] = Query(None, description="Minimum player age", ge=1, le=99),
    max_age: Optional[int] = Query(None, description="Maximum player age", ge=1, le=99),
    limit: int = Query(DEFAULT_RANKINGS_LIMIT, ge=1, le=200),
):
    """Top N rankings by metric with optional filters."""

    md = (
        db.query(MetricDefinition).filter(MetricDefinition.code == metric).one_or_none()
    )
    if not md:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Metric not found",
                "metric": metric,
                "suggestions": _suggest_metric_codes(db, metric),
            },
        )

    # Field player categories that should exclude goalkeepers
    field_player_categories = {
        "Finishing",
        "Passing",
        "Dribbling",
        "Defense",
        "Aerial",
        "Discipline",
        "Penalty",  # Penalty taking (not penalty saving)
    }

    # Check if this metric belongs to a field player category
    metric_category = md.category
    is_field_metric = (
        metric_category in field_player_categories if metric_category else False
    )

    query = (
        db.query(
            PlayerSeason,
            Team,
            League,
            Season,
            PlayerMetric.value,
        )
        .outerjoin(Team, PlayerSeason.team_id == Team.id)
        .outerjoin(League, PlayerSeason.league_id == League.id)
        .outerjoin(Season, PlayerSeason.season_id == Season.id)
        .join(PlayerMetric, PlayerMetric.player_season_id == PlayerSeason.id)
        .filter(PlayerMetric.metric_id == md.id)
    )

    if league:
        query = apply_league_filter(query, league, League)

    if season:
        season_candidates = {season}
        if re.fullmatch(r"\d{4}", season):
            try:
                season_candidates.add(format_season(season))
            except Exception:
                pass
        if re.fullmatch(r"\d{4}-\d{4}", season):
            y1, y2 = season.split("-")
            season_candidates.add(f"{y1[-2:]}{y2[-2:]}")
        query = query.filter(Season.label.in_(list(season_candidates)))

    if pos:
        query = query.filter(PlayerSeason.position == pos)
    elif is_field_metric:
        # Automatically exclude goalkeepers for field player metrics
        query = query.filter(PlayerSeason.position != "GK")

    if team:
        # Find players who played for this team, including those with combined team names from transfers
        # This handles both exact matches ("Aston Villa") and combined names ("Aston Villa & Manchester United")
        team_filter = or_(
            Team.name == team,  # Exact match
            Team.name.like(f"{team} & %"),  # Team is first in combination
            Team.name.like(f"% & {team}"),  # Team is second in combination
            Team.name.like(f"% & {team} & %"),  # Team is in middle of combination
        )
        query = query.filter(team_filter)

    if nation:
        query = query.filter(PlayerSeason.nationality == nation)

    if min_minutes:
        query = query.filter(
            (PlayerSeason.minutes != None) & (PlayerSeason.minutes >= min_minutes)
        )

    if min_value is not None:
        query = query.filter(
            (PlayerSeason.market_value_eur != None)
            & (PlayerSeason.market_value_eur >= min_value)
        )

    if max_value is not None:
        query = query.filter(
            (PlayerSeason.market_value_eur != None)
            & (PlayerSeason.market_value_eur <= max_value)
        )

    # Age filtering based on born_year
    if min_age is not None:
        from datetime import datetime

        current_year = datetime.now().year
        max_birth_year = current_year - min_age
        query = query.filter(
            (PlayerSeason.born_year != None)
            & (PlayerSeason.born_year <= max_birth_year)
        )

    if max_age is not None:
        from datetime import datetime

        current_year = datetime.now().year
        min_birth_year = current_year - max_age
        query = query.filter(
            (PlayerSeason.born_year != None)
            & (PlayerSeason.born_year >= min_birth_year)
        )

    # Cache key
    ck = f"rankings:m={metric}:l={league or ''}:s={season or ''}:p={pos or ''}:t={team or ''}:n={nation or ''}:mm={min_minutes}:minv={min_value or ''}:maxv={max_value or ''}:minage={min_age or ''}:maxage={max_age or ''}:lim={limit}"
    cached = _CACHE.get(ck)
    if cached:
        return RankingsResponse(**json.loads(cached))

    total = query.count()
    orderer = desc if md.direction == "higher_is_better" else asc
    rows = query.order_by(orderer(PlayerMetric.value)).limit(limit).all()

    items = [
        RankingItem(
            player_id=ps.id,
            player_name=ps.player_name,
            team_name=t.name if t else None,
            league_name=l.name if l else None,
            season_label=s.label if s else None,
            quantile_value=float(val),
            image_url=ps.image_url,
            nationality=ps.nationality,
            birth_date=ps.birth_date.isoformat() if ps.birth_date else None,
            value_m_eur=ps.market_value_eur,
        )
        for ps, t, l, s, val in rows
    ]

    res = RankingsResponse(
        metric=md.code, direction=md.direction, total=total, items=items
    )
    _CACHE.set(ck, json.dumps(res.model_dump()), _CACHE_TTL)
    return res


class PlayerRankResponse(BaseModel):
    player_id: int
    player_name: str
    team_name: Optional[str]
    league_name: Optional[str]
    season_label: Optional[str]
    quantile_value: float
    image_url: Optional[str]
    nationality: Optional[str]
    birth_date: Optional[str]
    value_m_eur: Optional[float]
    rank: int
    total: int
    metric: str
    direction: str


@app.get("/players/{player_id}/rank", response_model=PlayerRankResponse)
def get_player_rank(
    player_id: int,
    metric: str = Query(..., description="Metric code (e.g., finishing)"),
    db: Session = Depends(get_db),
    league: Optional[str] = Query(None),
    season: Optional[str] = Query(None),
    pos: Optional[str] = Query(
        None, description="Position filter (e.g., FW, MF, DF, GK)"
    ),
    team: Optional[str] = Query(None, description="Team name filter"),
    nation: Optional[str] = Query(None, description="Player nationality filter"),
    min_minutes: int = Query(DEFAULT_MIN_MINUTES, ge=0),
    min_value: Optional[float] = Query(
        None, description="Minimum market value in millions EUR"
    ),
    max_value: Optional[float] = Query(
        None, description="Maximum market value in millions EUR"
    ),
    min_age: Optional[int] = Query(None, description="Minimum player age", ge=1, le=99),
    max_age: Optional[int] = Query(None, description="Maximum player age", ge=1, le=99),
):
    """Get a specific player's rank for a given metric.

    This endpoint efficiently finds a player's ranking without fetching all rankings.
    It uses a subquery to count players with better scores.
    Returns the quantile/percentile value (0-100), not the raw metric value.

    Supports the same filters as the rankings endpoint to ensure consistent ranking calculations.
    """

    # Get the quantile metric definition for category scores (e.g., "quantile_category_scores_finishing")
    metric_code = metric
    md = (
        db.query(MetricDefinition)
        .filter(MetricDefinition.code == metric_code)
        .one_or_none()
    )
    if not md:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Quantile metric not found",
                "metric": metric,
                "quantile_metric": metric_code,
                "suggestions": _suggest_metric_codes(db, metric),
            },
        )

    # Field player categories that should exclude goalkeepers
    field_player_categories = {
        "Finishing",
        "Passing",
        "Dribbling",
        "Defense",
        "Aerial",
        "Discipline",
        "Penalty",
    }

    metric_category = md.category
    is_field_metric = (
        metric_category in field_player_categories if metric_category else False
    )

    # Get the player's data
    player_query = (
        db.query(
            PlayerSeason,
            Team,
            League,
            Season,
            PlayerMetric.value,
        )
        .outerjoin(Team, PlayerSeason.team_id == Team.id)
        .outerjoin(League, PlayerSeason.league_id == League.id)
        .outerjoin(Season, PlayerSeason.season_id == Season.id)
        .join(PlayerMetric, PlayerMetric.player_season_id == PlayerSeason.id)
        .filter(PlayerMetric.metric_id == md.id)
        .filter(PlayerSeason.id == player_id)
    )

    if league:
        player_query = apply_league_filter(player_query, league, League)

    if season:
        season_candidates = {season}
        if re.fullmatch(r"\d{4}", season):
            try:
                season_candidates.add(format_season(season))
            except Exception:
                pass
        if re.fullmatch(r"\d{4}-\d{4}", season):
            y1, y2 = season.split("-")
            season_candidates.add(f"{y1[-2:]}{y2[-2:]}")
        player_query = player_query.filter(Season.label.in_(list(season_candidates)))

    player_row = player_query.first()

    if not player_row:
        raise HTTPException(
            status_code=404,
            detail="Player not found or no data for this metric/season/league combination",
        )

    ps, t, l, s, player_value = player_row

    # Build base query for counting (same filters as rankings endpoint)
    count_query = (
        db.query(PlayerSeason.id)
        .outerjoin(Team, PlayerSeason.team_id == Team.id)
        .outerjoin(League, PlayerSeason.league_id == League.id)
        .outerjoin(Season, PlayerSeason.season_id == Season.id)
        .join(PlayerMetric, PlayerMetric.player_season_id == PlayerSeason.id)
        .filter(PlayerMetric.metric_id == md.id)
    )

    if league:
        count_query = apply_league_filter(count_query, league, League)

    if season:
        count_query = count_query.filter(Season.label.in_(list(season_candidates)))

    # Apply position filter
    if pos:
        count_query = count_query.filter(PlayerSeason.position == pos)
    elif is_field_metric:
        # Automatically exclude goalkeepers for field player metrics
        count_query = count_query.filter(
            (PlayerSeason.position != "GK") | (PlayerSeason.position == None)
        )

    # Apply team filter
    if team:
        team_filter = or_(
            Team.name == team,
            Team.name.like(f"{team} & %"),
            Team.name.like(f"% & {team}"),
            Team.name.like(f"% & {team} & %"),
        )
        count_query = count_query.filter(team_filter)

    # Apply nation filter
    if nation:
        count_query = count_query.filter(PlayerSeason.nationality == nation)

    # Apply minutes filter
    if min_minutes:
        count_query = count_query.filter(PlayerSeason.minutes >= min_minutes)

    # Apply market value filters
    if min_value is not None:
        count_query = count_query.filter(PlayerSeason.market_value_eur >= min_value)
    if max_value is not None:
        count_query = count_query.filter(PlayerSeason.market_value_eur <= max_value)

    # Apply age filters
    if min_age is not None or max_age is not None:
        current_year = datetime.now().year
        if min_age is not None:
            max_birth_year = current_year - min_age
            count_query = count_query.filter(
                extract("year", PlayerSeason.birth_date) <= max_birth_year
            )
        if max_age is not None:
            min_birth_year = current_year - max_age
            count_query = count_query.filter(
                extract("year", PlayerSeason.birth_date) >= min_birth_year
            )

    # Count total players
    total = count_query.count()

    # Count players with better scores
    if md.direction == "higher_is_better":
        better_query = count_query.filter(PlayerMetric.value > player_value)
    else:
        better_query = count_query.filter(PlayerMetric.value < player_value)

    better_count = better_query.count()
    rank = better_count + 1

    # Cache key (include all filter parameters for proper cache invalidation)
    ck = (
        f"player_rank:pid={player_id}:m={metric}:l={league or ''}:s={season or ''}:"
        f"pos={pos or ''}:team={team or ''}:nation={nation or ''}:min_min={min_minutes}:"
        f"min_val={min_value or ''}:max_val={max_value or ''}:min_age={min_age or ''}:max_age={max_age or ''}"
    )

    result = PlayerRankResponse(
        player_id=ps.id,
        player_name=ps.player_name,
        team_name=t.name if t else None,
        league_name=l.name if l else None,
        season_label=s.label if s else None,
        quantile_value=float(player_value),
        image_url=ps.image_url,
        nationality=ps.nationality,
        birth_date=ps.birth_date.isoformat() if ps.birth_date else None,
        value_m_eur=ps.market_value_eur,
        rank=rank,
        total=total,
        metric=md.code,
        direction=md.direction,
    )

    _CACHE.set(ck, json.dumps(result.model_dump()), _CACHE_TTL)
    return result


class ScatterPoint(BaseModel):
    player_id: int
    player_name: str
    team_name: Optional[str]
    league_name: Optional[str]
    season_label: Optional[str]
    position: Optional[str]
    image_url: Optional[str]
    value_m_eur: Optional[float]
    x: float
    y: float


class ScatterResponse(BaseModel):
    x: str
    y: str
    total: int
    items: list[ScatterPoint]


@app.get("/scatter", response_model=ScatterResponse)
def scatter(
    x: str = Query(..., description="X metric code"),
    y: str = Query(..., description="Y metric code"),
    db: Session = Depends(get_db),
    league: Optional[str] = Query(None),
    season: Optional[str] = Query(None),
    pos: Optional[str] = Query(None),
    team: Optional[str] = Query(None, description="Team name filter"),
    nation: Optional[str] = Query(None, description="Player nationality filter"),
    min_minutes: int = Query(0, ge=0),
    min_value: Optional[float] = Query(
        None, description="Minimum market value in millions EUR"
    ),
    max_value: Optional[float] = Query(
        None, description="Maximum market value in millions EUR"
    ),
    min_age: Optional[int] = Query(None, description="Minimum player age", ge=1, le=99),
    max_age: Optional[int] = Query(None, description="Maximum player age", ge=1, le=99),
    limit: int = Query(5000, ge=1, le=20000),
):
    """Return points for a 2D scatter on two metrics."""

    md_x = db.query(MetricDefinition).filter(MetricDefinition.code == x).one_or_none()
    md_y = db.query(MetricDefinition).filter(MetricDefinition.code == y).one_or_none()
    if not md_x or not md_y:
        sugg = _suggest_metric_codes(db, x if not md_x else y)
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Metric not found",
                "x": x,
                "y": y,
                "suggestions": sugg,
            },
        )

    PMX = aliased(PlayerMetric)
    PMY = aliased(PlayerMetric)

    query = (
        db.query(
            PlayerSeason,
            Team,
            League,
            Season,
            PMX.value.label("xval"),
            PMY.value.label("yval"),
        )
        .outerjoin(Team, PlayerSeason.team_id == Team.id)
        .outerjoin(League, PlayerSeason.league_id == League.id)
        .outerjoin(Season, PlayerSeason.season_id == Season.id)
        .join(
            PMX, (PMX.player_season_id == PlayerSeason.id) & (PMX.metric_id == md_x.id)
        )
        .join(
            PMY, (PMY.player_season_id == PlayerSeason.id) & (PMY.metric_id == md_y.id)
        )
    )

    if league:
        query = apply_league_filter(query, league, League)

    if season:
        season_candidates = {season}
        if re.fullmatch(r"\d{4}", season):
            try:
                season_candidates.add(format_season(season))
            except Exception:
                pass
        if re.fullmatch(r"\d{4}-\d{4}", season):
            y1, y2 = season.split("-")
            season_candidates.add(f"{y1[-2:]}{y2[-2:]}")
        query = query.filter(Season.label.in_(list(season_candidates)))

    if pos:
        query = query.filter(PlayerSeason.position == pos)

    if team:
        team_filter = or_(
            Team.name == team,
            Team.name.like(f"{team} & %"),
            Team.name.like(f"% & {team}"),
            Team.name.like(f"% & {team} & %"),
        )
        query = query.filter(team_filter)

    if nation:
        query = query.filter(PlayerSeason.nationality == nation)

    if min_minutes:
        query = query.filter(
            (PlayerSeason.minutes != None) & (PlayerSeason.minutes >= min_minutes)
        )

    if min_value is not None:
        query = query.filter(
            (PlayerSeason.market_value_eur != None)
            & (PlayerSeason.market_value_eur >= min_value)
        )

    if max_value is not None:
        query = query.filter(
            (PlayerSeason.market_value_eur != None)
            & (PlayerSeason.market_value_eur <= max_value)
        )

    # Age filtering based on born_year
    if min_age is not None:
        # Calculate max birth year for min age (current year - min_age)
        from datetime import datetime

        current_year = datetime.now().year
        max_birth_year = current_year - min_age
        query = query.filter(
            (PlayerSeason.born_year != None)
            & (PlayerSeason.born_year <= max_birth_year)
        )

    if max_age is not None:
        # Calculate min birth year for max age (current year - max_age)
        from datetime import datetime

        current_year = datetime.now().year
        min_birth_year = current_year - max_age
        query = query.filter(
            (PlayerSeason.born_year != None)
            & (PlayerSeason.born_year >= min_birth_year)
        )

    # Cache key
    ck = f"scatter:x={x}:y={y}:l={league or ''}:s={season or ''}:p={pos or ''}:t={team or ''}:n={nation or ''}:mm={min_minutes}:minv={min_value or ''}:maxv={max_value or ''}:minage={min_age or ''}:maxage={max_age or ''}:lim={limit}"
    cached = _CACHE.get(ck)
    if cached:
        return ScatterResponse(**json.loads(cached))

    rows = query.limit(limit).all()
    items = [
        ScatterPoint(
            player_id=ps.id,
            player_name=ps.player_name,
            team_name=t.name if t else None,
            league_name=l.name if l else None,
            season_label=s.label if s else None,
            position=ps.position or "Unknown",
            image_url=ps.image_url,
            value_m_eur=ps.market_value_eur,
            x=float(xv),
            y=float(yv),
        )
        for ps, t, l, s, xv, yv in rows
    ]
    res = ScatterResponse(x=md_x.code, y=md_y.code, total=len(items), items=items)
    _CACHE.set(ck, json.dumps(res.model_dump()), _CACHE_TTL)
    return res


@app.get("/charts/rankings/bar")
def chart_rankings_bar(
    metric: str,
    db: Session = Depends(get_db),
    league: Optional[str] = Query(None),
    season: Optional[str] = Query(None),
    pos: Optional[str] = Query(None),
    team: Optional[str] = Query(None, description="Team name filter"),
    nation: Optional[str] = Query(None, description="Player nationality filter"),
    min_minutes: int = Query(DEFAULT_MIN_MINUTES, ge=0),
    min_value: Optional[float] = Query(
        None, description="Minimum market value in millions EUR"
    ),
    max_value: Optional[float] = Query(
        None, description="Maximum market value in millions EUR"
    ),
    min_age: Optional[int] = Query(None, description="Minimum player age", ge=1, le=99),
    max_age: Optional[int] = Query(None, description="Maximum player age", ge=1, le=99),
    limit: int = Query(DEFAULT_RANKINGS_LIMIT, ge=1, le=200),
):
    md = (
        db.query(MetricDefinition).filter(MetricDefinition.code == metric).one_or_none()
    )
    if not md:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Metric not found",
                "metric": metric,
                "suggestions": _suggest_metric_codes(db, metric),
            },
        )

    query = (
        db.query(
            PlayerSeason,
            Team,
            League,
            Season,
            PlayerMetric.value,
        )
        .outerjoin(Team, PlayerSeason.team_id == Team.id)
        .outerjoin(League, PlayerSeason.league_id == League.id)
        .outerjoin(Season, PlayerSeason.season_id == Season.id)
        .join(PlayerMetric, PlayerMetric.player_season_id == PlayerSeason.id)
        .filter(PlayerMetric.metric_id == md.id)
    )

    if league:
        query = apply_league_filter(query, league, League)

    if season:
        season_candidates = {season}
        if re.fullmatch(r"\d{4}", season):
            try:
                season_candidates.add(format_season(season))
            except Exception:
                pass
        if re.fullmatch(r"\d{4}-\d{4}", season):
            y1, y2 = season.split("-")
            season_candidates.add(f"{y1[-2:]}{y2[-2:]}")
        query = query.filter(Season.label.in_(list(season_candidates)))

    if pos:
        query = query.filter(PlayerSeason.position == pos)

    if team:
        team_filter = or_(
            Team.name == team,
            Team.name.like(f"{team} & %"),
            Team.name.like(f"% & {team}"),
            Team.name.like(f"% & {team} & %"),
        )
        query = query.filter(team_filter)

    if nation:
        query = query.filter(PlayerSeason.nationality == nation)

    if min_minutes:
        query = query.filter(
            (PlayerSeason.minutes != None) & (PlayerSeason.minutes >= min_minutes)
        )

    if min_value is not None:
        query = query.filter(
            (PlayerSeason.market_value_eur != None)
            & (PlayerSeason.market_value_eur >= min_value)
        )

    if max_value is not None:
        query = query.filter(
            (PlayerSeason.market_value_eur != None)
            & (PlayerSeason.market_value_eur <= max_value)
        )

    # Age filtering based on born_year
    if min_age is not None:
        from datetime import datetime

        current_year = datetime.now().year
        max_birth_year = current_year - min_age
        query = query.filter(
            (PlayerSeason.born_year != None)
            & (PlayerSeason.born_year <= max_birth_year)
        )

    if max_age is not None:
        from datetime import datetime

        current_year = datetime.now().year
        min_birth_year = current_year - max_age
        query = query.filter(
            (PlayerSeason.born_year != None)
            & (PlayerSeason.born_year >= min_birth_year)
        )

    # Cache key
    ck = f"chart:bar:m={metric}:l={league or ''}:s={season or ''}:p={pos or ''}:t={team or ''}:n={nation or ''}:mm={min_minutes}:minv={min_value or ''}:maxv={max_value or ''}:minage={min_age or ''}:maxage={max_age or ''}:lim={limit}"
    cached = _CACHE.get(ck)
    if cached:
        return Response(content=cached, media_type="application/json")

    orderer = desc if md.direction == "higher_is_better" else asc
    rows = query.order_by(orderer(PlayerMetric.value)).limit(limit).all()

    data = [
        {
            "player": ps.player_name,
            "team": t.name if t else None,
            "value": float(val),
            "player_id": ps.id,
            "hover_text": f"{ps.player_name} — {t.name if t else ''} ({l.name if l else ''})\n{md.code}: {float(val):.3f}{f' • Market Value: €{ps.market_value_eur:.1f}M' if ps.market_value_eur else ''}",
        }
        for ps, t, l, _, val in rows
    ]
    df = pd.DataFrame(data)
    if df.empty:
        # Return empty figure
        fig = px.bar(pd.DataFrame({"player": [], "value": []}), x="player", y="value")
    else:
        fig = px.bar(
            df,
            x="player",
            y="value",
            color="value",
            color_continuous_scale="RdYlGn",
            title=f"Top {limit} • {md.code}{' • ' + league if league else ''} {season or ''}",
            labels={"player": "Player", "value": md.code},
        )

        # Manually set customdata to ensure player_id is included
        hover_texts = df["hover_text"].tolist()
        player_ids = df["player_id"].tolist()
        customdata_arrays = [
            [hover_text, player_id]
            for hover_text, player_id in zip(hover_texts, player_ids)
        ]

        fig.update_traces(customdata=customdata_arrays)
        fig.update_traces(
            hovertemplate="%{customdata[0]}<extra></extra>", selector=dict(type="bar")
        )
        fig.update_layout(
            xaxis_tickangle=45,
            margin=dict(l=10, r=10, t=30, b=100),
            # Add subtle indication that bars are clickable
            annotations=[
                dict(
                    text="💡 Click any bar to view player details",
                    xref="paper",
                    yref="paper",
                    x=0.98,
                    y=0.02,
                    xanchor="right",
                    yanchor="bottom",
                    showarrow=False,
                    font=dict(size=12, color="gray"),
                )
            ],
        )

    fig_json = pio.to_json(fig, pretty=False)
    if fig_json is not None:
        _CACHE.set(ck, fig_json, _CACHE_TTL)
        return Response(content=fig_json, media_type="application/json")
    else:
        return Response(
            content='{"error": "Chart generation failed"}',
            media_type="application/json",
        )


@app.get("/charts/scatter/metrics")
def chart_scatter_metrics(
    x: str,
    y: str,
    db: Session = Depends(get_db),
    league: Optional[str] = Query(None),
    season: Optional[str] = Query(None),
    pos: Optional[str] = Query(None),
    team: Optional[str] = Query(None, description="Team name filter"),
    nation: Optional[str] = Query(None, description="Player nationality filter"),
    min_minutes: int = Query(DEFAULT_MIN_MINUTES, ge=0),
    min_value: Optional[float] = Query(
        None, description="Minimum market value in millions EUR"
    ),
    max_value: Optional[float] = Query(
        None, description="Maximum market value in millions EUR"
    ),
    min_age: Optional[int] = Query(None, description="Minimum player age", ge=1, le=99),
    max_age: Optional[int] = Query(None, description="Maximum player age", ge=1, le=99),
    limit: int = Query(5000, ge=1, le=20000),
):
    md_x = db.query(MetricDefinition).filter(MetricDefinition.code == x).one_or_none()
    md_y = db.query(MetricDefinition).filter(MetricDefinition.code == y).one_or_none()
    if not md_x or not md_y:
        sugg = _suggest_metric_codes(db, x if not md_x else y)
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Metric not found",
                "x": x,
                "y": y,
                "suggestions": sugg,
            },
        )

    PMX = aliased(PlayerMetric)
    PMY = aliased(PlayerMetric)

    query = (
        db.query(
            PlayerSeason,
            Team,
            League,
            Season,
            PMX.value.label("xval"),
            PMY.value.label("yval"),
        )
        .outerjoin(Team, PlayerSeason.team_id == Team.id)
        .outerjoin(League, PlayerSeason.league_id == League.id)
        .outerjoin(Season, PlayerSeason.season_id == Season.id)
        .join(
            PMX, (PMX.player_season_id == PlayerSeason.id) & (PMX.metric_id == md_x.id)
        )
        .join(
            PMY, (PMY.player_season_id == PlayerSeason.id) & (PMY.metric_id == md_y.id)
        )
    )

    if league:
        query = apply_league_filter(query, league, League)

    if season:
        season_candidates = {season}
        if re.fullmatch(r"\d{4}", season):
            try:
                season_candidates.add(format_season(season))
            except Exception:
                pass
        if re.fullmatch(r"\d{4}-\d{4}", season):
            y1, y2 = season.split("-")
            season_candidates.add(f"{y1[-2:]}{y2[-2:]}")
        query = query.filter(Season.label.in_(list(season_candidates)))

    if pos:
        query = query.filter(PlayerSeason.position == pos)

    if team:
        team_filter = or_(
            Team.name == team,
            Team.name.like(f"{team} & %"),
            Team.name.like(f"% & {team}"),
            Team.name.like(f"% & {team} & %"),
        )
        query = query.filter(team_filter)

    if nation:
        query = query.filter(PlayerSeason.nationality == nation)

    if min_minutes:
        query = query.filter(
            (PlayerSeason.minutes != None) & (PlayerSeason.minutes >= min_minutes)
        )

    if min_value is not None:
        query = query.filter(
            (PlayerSeason.market_value_eur != None)
            & (PlayerSeason.market_value_eur >= min_value)
        )

    if max_value is not None:
        query = query.filter(
            (PlayerSeason.market_value_eur != None)
            & (PlayerSeason.market_value_eur <= max_value)
        )

    # Age filtering based on born_year
    if min_age is not None:
        from datetime import datetime

        current_year = datetime.now().year
        max_birth_year = current_year - min_age
        query = query.filter(
            (PlayerSeason.born_year != None)
            & (PlayerSeason.born_year <= max_birth_year)
        )

    if max_age is not None:
        from datetime import datetime

        current_year = datetime.now().year
        min_birth_year = current_year - max_age
        query = query.filter(
            (PlayerSeason.born_year != None)
            & (PlayerSeason.born_year >= min_birth_year)
        )

    # Cache key
    ck = f"chart:scatter:x={x}:y={y}:l={league or ''}:s={season or ''}:p={pos or ''}:t={team or ''}:n={nation or ''}:mm={min_minutes}:minv={min_value or ''}:maxv={max_value or ''}:minage={min_age or ''}:maxage={max_age or ''}:lim={limit}"
    cached = _CACHE.get(ck)
    if cached:
        return Response(content=cached, media_type="application/json")

    rows = query.limit(limit).all()
    data = [
        {
            "player": ps.player_name,
            "team": t.name if t else None,
            "league": l.name if l else None,
            "season": s.label if s else None,
            "position": ps.position or "Unknown",
            "x": float(xv),
            "y": float(yv),
            "hover_text": f"{ps.player_name} — {ps.position or 'Unknown'} — {t.name if t else ''} ({l.name if l else ''})<br>{x}: {float(xv):.3f} • {y}: {float(yv):.3f}",
        }
        for ps, t, l, s, xv, yv in rows
    ]

    df = pd.DataFrame(data)
    if df.empty:
        fig = px.scatter(pd.DataFrame({"x": [], "y": []}), x="x", y="y")
    else:
        # Create scatter plot manually by position to avoid hover duplication
        fig = go.Figure()
        position_colors = {
            "GK": "#FF6B35",  # Orange for goalkeepers
            "DF": "#2563EB",  # Bright blue for defenders
            "MF": "#00E673",  # Darker green for midfielders
            "FW": "#DC2626",  # Bright red for forwards
            "FW,MF": "#8B5CF6",  # Purple for forward/midfielders
            "MF,DF": "#06B6D4",  # Cyan for midfielder/defenders
            "DF,MF": "#06B6D4",  # Cyan for defender/midfielders
            "Unknown": "#9CA3AF",  # Gray for unknown positions
        }

        for position in df["position"].unique():
            position_data = df[df["position"] == position]
            fig.add_trace(
                go.Scatter(
                    x=position_data["x"],
                    y=position_data["y"],
                    mode="markers",
                    marker=dict(
                        size=12, color=position_colors.get(position, "#9CA3AF")
                    ),
                    name=position,
                    text=position_data["hover_text"],
                    hovertemplate="%{text}<extra></extra>",
                )
            )

        fig.update_layout(
            title=f"{x} vs {y}{' • ' + league if league else ''} {season or ''}",
            xaxis_title=x,
            yaxis_title=y,
            margin=dict(l=10, r=10, t=30, b=20),
        )

    fig_json = pio.to_json(fig, pretty=False)
    if fig_json is not None:
        _CACHE.set(ck, fig_json, _CACHE_TTL)
        return Response(content=fig_json, media_type="application/json")
    else:
        return Response(
            content='{"error": "Chart generation failed"}',
            media_type="application/json",
        )


@app.get("/charts/players/{player_id}/radar")
def chart_player_radar(
    player_id: int,
    db: Session = Depends(get_db),
    season: Optional[str] = Query(None, description="Season label (2425 or 2024-2025)"),
    league: Optional[str] = Query(AGGREGATED_LEAGUE_NAME, description="League name"),
):
    """Generate a radar chart showing player performance across key categories.

    Categories are selected based on player position:
    - Goalkeepers (GK): Penalty Specialist, Reflexes & Saves, Sweeper Play, Footwork & Distribution, Air Dominance
    - Field Players: Aerial, Passing, Defense, Discipline, Finishing, Penalty, Dribbling
    """

    # Define categories based on player position
    goalkeeper_categories = [
        "Penalty Specialist",
        "Reflexes & Saves",
        "Sweeper Play",
        "Footwork & Distribution",
        "Air Dominance",
    ]

    field_player_categories = [
        "Aerial",
        "Passing",
        "Defense",
        "Discipline",
        "Finishing",
        "Penalty",
        "Dribbling",
    ]

    # Get player data
    base_q = (
        db.query(PlayerSeason, Team, League, Season)
        .outerjoin(Team, PlayerSeason.team_id == Team.id)
        .outerjoin(League, PlayerSeason.league_id == League.id)
        .outerjoin(Season, PlayerSeason.season_id == Season.id)
        .filter(PlayerSeason.id == player_id)
    )

    if season:
        season_candidates = {season}
        if re.fullmatch(r"\d{4}", season):
            try:
                season_candidates.add(format_season(season))
            except Exception:
                pass
        if re.fullmatch(r"\d{4}-\d{4}", season):
            y1, y2 = season.split("-")
            season_candidates.add(f"{y1[-2:]}{y2[-2:]}")
        base_q = base_q.filter(Season.label.in_(list(season_candidates)))

    if league:
        base_q = base_q.filter(League.name == league)

    row = base_q.order_by(Season.label.desc().nullslast()).first()
    if not row:
        raise HTTPException(status_code=404, detail="Player (season) not found")

    ps, t, l, s = row

    # Get all metrics for this player-season
    mrows = (
        db.query(MetricDefinition, PlayerMetric)
        .join(PlayerMetric, PlayerMetric.metric_id == MetricDefinition.id)
        .filter(PlayerMetric.player_season_id == ps.id)
        .all()
    )

    # Build metrics dictionary
    metrics_dict = {
        md.code: (pm.value if pm.value is not None else 0) for md, pm in mrows
    }

    # Choose categories based on player position
    player_position = ps.position or ""
    is_goalkeeper = player_position.upper() in ["GK", "GOALKEEPER"]

    broad_categories = (
        goalkeeper_categories if is_goalkeeper else field_player_categories
    )

    # Get direct broad category scores
    radar_data = []
    categories = []

    for category_code in broad_categories:
        # Convert category name to database metric code format (lowercase with underscores)
        metric_code = category_code.lower().replace(" ", "_")
        value = metrics_dict.get(metric_code, 0)
        radar_data.append(float(value))
        categories.append(category_code)

    # Calculate dynamic range based on actual data values (like in existing Streamlit app)
    if radar_data:
        min_val = min(radar_data) - 0.5  # Add some padding
        max_val = max(radar_data) + 0.5
        # Ensure we have a reasonable minimum range
        if max_val - min_val < 2:
            center = (min_val + max_val) / 2
            min_val = center - 1
            max_val = center + 1
    else:
        min_val, max_val = -1, 3

    # Create radar chart
    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=radar_data + [radar_data[0]],  # Close the radar chart
            theta=categories + [categories[0]],
            fill="toself",
            fillcolor="rgba(79, 70, 229, 0.2)",  # Navy with transparency
            line=dict(color="rgb(79, 70, 229)", width=3),  # Navy line
            marker=dict(color="rgb(79, 70, 229)", size=8),
            name=ps.player_name,
            hovertemplate="<b>%{theta}</b><br>Score: %{r:.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[min_val, max_val],
                gridcolor="rgba(0,0,0,0.1)",
                tickfont=dict(size=10, color="gray"),
            ),
            angularaxis=dict(
                tickfont=dict(size=12, color="#374151"), gridcolor="rgba(0,0,0,0.1)"
            ),
            bgcolor="rgba(255,255,255,0)",
        ),
        showlegend=False,
        title=dict(
            text=f"{ps.player_name} Performance Radar<br><sub>{l.name if l else 'Unknown League'} • {s.label if s else 'Unknown Season'}</sub>",
            x=0.5,
            font=dict(size=16, color="#1F2937"),
        ),
        margin=dict(l=20, r=20, t=80, b=20),
        autosize=True,
    )

    # Cache the result
    safe_season = season or "latest"
    safe_league = (league or "all").replace("(", "").replace(")", "").replace(" ", "_")
    cache_key = f"radar:{player_id}:{safe_season}:{safe_league}"
    fig_json = pio.to_json(fig, pretty=False)

    if fig_json is not None:
        try:
            _CACHE.set(cache_key, fig_json, _CACHE_TTL)
        except Exception:
            pass  # Continue without caching if there's an issue
        return Response(content=fig_json, media_type="application/json")
    else:
        return Response(
            content='{"error": "Chart generation failed"}',
            media_type="application/json",
        )


def get_player_similarities_from_db(
    db: Session,
    player_id: int,
    season: str = "2425",
    metric_set_code: str = "core_per90",
    k: int = 10,
    min_minutes: int = 0,
    pos: Optional[str] = None,
    nation: Optional[str] = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    league: Optional[str] = None,
) -> list[SimilarPlayerOut]:
    """Query pre-computed player similarities from database.

    Args:
        db: Database session
        player_id: Target player ID
        season: Season label
        metric_set_code: Metric set code
        k: Number of similar players to return
        min_minutes: Minimum minutes played filter
        pos: Position filter
        nation: Nationality filter
        min_value: Minimum market value filter
        max_value: Maximum market value filter
        min_age: Minimum player age filter
        max_age: Maximum player age filter
        league: League filter (supports Big 5 European Leagues)

    Returns:
        List of similar players with similarity scores
    """
    # Get season and metric set
    season_obj = db.query(Season).filter(Season.label == season).first()
    metric_set = db.query(MetricSet).filter(MetricSet.code == metric_set_code).first()

    if not season_obj or not metric_set:
        return []

    # Alias for the similar player's PlayerSeason
    similar_player_seasons = aliased(PlayerSeason)

    # Query similarities from database - now using player_season_id
    similar_players_query = (
        db.query(
            PlayerSimilarity,
            similar_player_seasons.player_name.label("similar_player_name"),
            similar_player_seasons.position.label("similar_position"),
            Team.name.label("similar_team_name"),
            similar_player_seasons.image_url.label("similar_player_image_url"),
            similar_player_seasons.id.label("similar_player_season_id"),
            similar_player_seasons.market_value_eur.label("similar_market_value_eur"),
            similar_player_seasons.nationality.label("similar_nationality"),
            similar_player_seasons.birth_date.label("similar_birth_date"),
            League.name.label("similar_league_name"),
        )
        .join(
            similar_player_seasons,
            PlayerSimilarity.similar_player_season_id == similar_player_seasons.id,
        )
        .outerjoin(Team, similar_player_seasons.team_id == Team.id)
        .outerjoin(League, similar_player_seasons.league_id == League.id)
        .filter(
            PlayerSimilarity.player_season_id == player_id,
            PlayerSimilarity.season_id == season_obj.id,
            PlayerSimilarity.metric_set_id == metric_set.id,
        )
    )

    # Apply league filter (handles Big 5 and other leagues)
    if league:
        similar_players_query = apply_league_filter(
            similar_players_query, league, League
        )

    # Apply filters
    if min_minutes > 0:
        similar_players_query = similar_players_query.filter(
            (similar_player_seasons.minutes != None)
            & (similar_player_seasons.minutes >= min_minutes)
        )

    if pos:
        similar_players_query = similar_players_query.filter(
            similar_player_seasons.position == pos
        )

    if nation:
        similar_players_query = similar_players_query.filter(
            similar_player_seasons.nationality == nation
        )

    if min_value is not None:
        similar_players_query = similar_players_query.filter(
            (similar_player_seasons.market_value_eur != None)
            & (similar_player_seasons.market_value_eur >= min_value)
        )

    if max_value is not None:
        similar_players_query = similar_players_query.filter(
            (similar_player_seasons.market_value_eur != None)
            & (similar_player_seasons.market_value_eur <= max_value)
        )

    # Age filtering based on birth_date
    if min_age is not None:
        current_year = datetime.now().year
        max_birth_year = current_year - min_age
        similar_players_query = similar_players_query.filter(
            (similar_player_seasons.birth_date != None)
            & (extract("year", similar_player_seasons.birth_date) <= max_birth_year)
        )

    if max_age is not None:
        current_year = datetime.now().year
        min_birth_year = current_year - max_age
        similar_players_query = similar_players_query.filter(
            (similar_player_seasons.birth_date != None)
            & (extract("year", similar_player_seasons.birth_date) >= min_birth_year)
        )

    similar_players_query = (
        similar_players_query.order_by(
            PlayerSimilarity.distance.asc()
        )  # Smaller distance = more similar
        .limit(k * 3)  # Get more records to account for potential duplicates
        .all()
    )

    # Convert to SimilarPlayerOut objects and deduplicate by player_season_id
    similar_players = []
    seen_player_session_ids = set()

    for (
        similarity,
        similar_player_name,
        similar_position,
        similar_team_name,
        similar_player_image_url,
        similar_player_season_id,
        similar_market_value_eur,
        similar_nationality,
        similar_birth_date,
        similar_league_name,
    ) in similar_players_query:
        # Skip if we've already seen this player_season
        if similar_player_season_id in seen_player_session_ids:
            continue

        seen_player_session_ids.add(similar_player_season_id)

        # Convert distance back to similarity score (1 - distance)
        similarity_score = 1.0 - similarity.distance

        # Calculate age from birth_date
        age = None
        if similar_birth_date:
            current_year = datetime.now().year
            birth_year = similar_birth_date.year
            age = current_year - birth_year

        similar_players.append(
            SimilarPlayerOut(
                player_id=similar_player_season_id,
                player_name=similar_player_name,
                team_name=similar_team_name,
                league_name=similar_league_name or AGGREGATED_LEAGUE_NAME,
                season_label=season,
                position=similar_position,
                value_m_eur=similar_market_value_eur,
                similarity_score=round(similarity_score, 3),
                image_url=similar_player_image_url,
                nationality=similar_nationality,
                birth_date=similar_birth_date.isoformat()
                if similar_birth_date
                else None,
                age=age,
            )
        )

        # Stop when we have k unique players
        if len(similar_players) >= k:
            break

    return similar_players


@app.get("/players/{player_id}/similar", response_model=SimilarPlayersResponse)
def get_similar_players(
    player_id: int,
    db: Session = Depends(get_db),
    season: Optional[str] = Query("2526", description="Season for similarity lookup"),
    league: Optional[str] = Query(
        AGGREGATED_LEAGUE_NAME, description="League for similarity lookup"
    ),
    k: int = Query(10, description="Number of similar players to return", ge=1, le=50),
    min_minutes: int = Query(0, description="Minimum minutes played", ge=0),
    pos: Optional[str] = Query(
        None, description="Position filter (e.g., FW, MF, DF, GK)"
    ),
    nation: Optional[str] = Query(None, description="Player nationality filter"),
    min_value: Optional[float] = Query(
        None, description="Minimum market value in millions EUR"
    ),
    max_value: Optional[float] = Query(
        None, description="Maximum market value in millions EUR"
    ),
    min_age: Optional[int] = Query(None, description="Minimum player age", ge=1, le=99),
    max_age: Optional[int] = Query(None, description="Maximum player age", ge=1, le=99),
):
    """Find k most similar players from pre-computed similarities in database.

    This endpoint serves pre-computed similarities that were calculated during ETL processing
    and stored in the database. Similarities are based on cosine similarity using standardized per_90 metrics.
    """

    # Get the target player info
    target_player_query = (
        db.query(PlayerSeason.player_name).filter(PlayerSeason.id == player_id).first()
    )

    if not target_player_query:
        raise HTTPException(status_code=404, detail="Player not found")

    target_player_name = target_player_query.player_name

    # Use provided season or default to "2425"
    effective_season = season or "2425"

    # Query similarities from database
    similar_players = get_player_similarities_from_db(
        db=db,
        player_id=player_id,
        season=effective_season,
        metric_set_code="core_per90",
        k=k,
        min_minutes=min_minutes,
        pos=pos,
        nation=nation,
        min_value=min_value,
        max_value=max_value,
        min_age=min_age,
        max_age=max_age,
        league=league,
    )

    return SimilarPlayersResponse(
        target_player_id=player_id,
        target_player_name=target_player_name,
        similar_players=similar_players,
    )


@app.get("/players/{player_id}/leagues")
def get_player_leagues(player_id: int, db: Session = Depends(get_db)):
    """List leagues where a specific player has played.

    Note: player_id here refers to a player_season_id. We find all leagues
    for the same player_name.
    """
    # First get the player_name for the given player_season_id
    ps = db.query(PlayerSeason.player_name).filter(PlayerSeason.id == player_id).first()
    if not ps:
        return [AGGREGATED_LEAGUE_NAME]

    # Then find all leagues this player has played in
    leagues = (
        db.query(League.name)
        .join(PlayerSeason, PlayerSeason.league_id == League.id)
        .filter(PlayerSeason.player_name == ps.player_name)
        .filter(League.name.isnot(None))
        .distinct()
        .order_by(League.name)
        .all()
    )

    # Extract league names and always include "Aggregated (All Leagues)" as an option
    league_names = [league[0] for league in leagues]
    if AGGREGATED_LEAGUE_NAME not in league_names:
        league_names.insert(0, AGGREGATED_LEAGUE_NAME)

    return league_names


class MetricCategoryOut(BaseModel):
    category: str
    description: Optional[str] = None
    metric_count: int
    sample_metrics: list[str]


@app.get("/metrics/categories")
def list_metric_categories(db: Session = Depends(get_db)):
    """List all metric categories with descriptions and sample metrics.

    This endpoint showcases the rich metric information from FBREF statistics
    that's loaded from the statistics.csv file with detailed category definitions.
    """
    logger = logging.getLogger(__name__)

    # Cache key
    ck = "metrics:categories"
    cached = _CACHE.get(ck)
    if cached:
        logger.debug("DEBUG: Returning cached categories")
        return json.loads(cached)

    logger.debug("DEBUG: Categories not cached, computing fresh...")

    # Get category definitions from SCOUTING_STATISTICS CSV
    category_definitions = (
        SCOUTING_STATISTICS.groupby("category")
        .agg(
            {
                "category_definition": "first"  # Get the category definition (same for all metrics in category)
            }
        )
        .to_dict()["category_definition"]
    )

    # Get all metrics from database
    metrics = db.query(MetricDefinition).order_by(MetricDefinition.code).all()

    # Create a mapping from metric code to category based on statistics.csv
    # Handle case differences: database has 'standard_gls', CSV has 'Standard_Gls'
    metric_to_category = {}

    # Debug: use logging instead of print
    logger = logging.getLogger(__name__)
    logger.debug(f"DEBUG: SCOUTING_STATISTICS shape: {SCOUTING_STATISTICS.shape}")
    logger.debug("DEBUG: First few rows of statistics:")
    logger.debug(str(SCOUTING_STATISTICS.head()))

    for _, row in SCOUTING_STATISTICS.iterrows():
        csv_stat = row["stat"]
        csv_category = row["category"]

        # Try exact match first
        metric_to_category[csv_stat] = csv_category

        # Try lowercase version (database format)
        metric_to_category[csv_stat.lower()] = csv_category

        # Try with underscores (database format)
        db_format = csv_stat.lower().replace(" ", "_")
        metric_to_category[db_format] = csv_category

    logger.debug(f"DEBUG: Created {len(metric_to_category)} metric mappings")
    logger.debug(f"DEBUG: Sample mappings: {list(metric_to_category.items())[:5]}")

    categories = {}
    for metric in metrics:
        # Map metric code to category using the statistics.csv mapping
        category = metric_to_category.get(metric.code, "Other")
        if category not in categories:
            # Use the category definition from SCOUTING_STATISTICS CSV
            description = category_definitions.get(category, "No description available")
            categories[category] = {
                "description": description,
                "metrics": [],
            }
        categories[category]["metrics"].append(metric.code)

    # Build response
    result = []
    for category, data in categories.items():
        result.append(
            MetricCategoryOut(
                category=category,
                description=data[
                    "description"
                ],  # Rich descriptions from statistics.csv
                metric_count=len(data["metrics"]),
                sample_metrics=data["metrics"][:5],  # Show first 5 metrics as samples
            )
        )

    # Sort by category name
    result.sort(key=lambda x: x.category)

    _CACHE.set(ck, json.dumps([r.model_dump() for r in result]), _CACHE_TTL)
    return result


# Additional Team Analysis Models (TeamOut is defined earlier)


class TeamMetricValue(BaseModel):
    quantile_value: float


class TeamStatsOut(BaseModel):
    team_id: int
    team_name: str
    league_name: Optional[str] = None
    season_label: Optional[str] = None
    games_played: Optional[int] = None
    metrics: dict[str, TeamMetricValue]


class TopPlayerOut(BaseModel):
    player_id: int
    player_name: str
    position: Optional[str] = None
    quantile_value: float
    image_url: Optional[str] = None


class ElitePlayerOut(BaseModel):
    """Elite player (top 10%) with their elite categories."""

    player_id: int
    player_name: str
    position: Optional[str] = None
    image_url: Optional[str] = None
    team_name: Optional[str] = None
    market_value_eur: Optional[float] = None
    birth_date: Optional[str] = None  # ISO date string
    minutes: Optional[int] = None
    elite_categories: dict[
        str, float
    ]  # Category -> quantile value (e.g., {"Finishing": 98.5})
    max_quantile: float  # Highest quantile value across all categories


class TeamComparisonOut(BaseModel):
    team1: TeamStatsOut
    team2: TeamStatsOut
    elite_players_team1: list[ElitePlayerOut]
    elite_players_team2: list[ElitePlayerOut]
    top_value_team1: list[ElitePlayerOut]
    top_value_team2: list[ElitePlayerOut]


@app.get("/teams/{team_id}/stats", response_model=TeamStatsOut)
def get_team_stats(
    team_id: int,
    season: str = Query("2526", description="Season label"),
    db: Session = Depends(get_db),
):
    """Get all statistics for a team in a specific season.

    Args:
        team_id: Team ID
        season: Season label (e.g., "2526")
        db: Database session

    Returns:
        Team stats including all metrics with quantile values
    """
    # Get team_season
    team_season = (
        db.query(TeamSeason, Team.name, League.name, Season.label)
        .join(Team, TeamSeason.team_id == Team.id)
        .join(League, TeamSeason.league_id == League.id, isouter=True)
        .join(Season, TeamSeason.season_id == Season.id, isouter=True)
        .filter(TeamSeason.team_id == team_id)
        .filter(Season.label == season)
        .first()
    )

    if not team_season:
        raise HTTPException(
            status_code=404, detail=f"Team {team_id} not found for season {season}"
        )

    ts, team_name, league_name, season_label = team_season

    # Get all metrics for this team_season
    metrics_query = (
        db.query(TeamMetric, MetricDefinition.code)
        .join(MetricDefinition, TeamMetric.metric_id == MetricDefinition.id)
        .filter(TeamMetric.team_season_id == ts.id)
        .all()
    )

    metrics_dict = {}
    for metric, code in metrics_query:
        metrics_dict[code] = TeamMetricValue(
            quantile_value=metric.value,
        )

    return TeamStatsOut(
        team_id=team_id,
        team_name=team_name,
        league_name=league_name,
        season_label=season_label,
        games_played=ts.games_played,
        metrics=metrics_dict,
    )


@app.get("/teams/compare", response_model=TeamComparisonOut)
def compare_teams(
    team1_id: int = Query(..., description="First team ID"),
    team2_id: int = Query(..., description="Second team ID"),
    season: str = Query(
        "2526", description="Season label (deprecated, use season1 and season2)"
    ),
    season1: Optional[str] = Query(None, description="Season label for team 1"),
    season2: Optional[str] = Query(None, description="Season label for team 2"),
    top_n: int = Query(3, description="Number of top players to return per category"),
    db: Session = Depends(get_db),
):
    """Compare two teams and get top players for each metric category.

    Args:
        team1_id: First team ID
        team2_id: Second team ID
        season: Season label (deprecated, use season1 and season2)
        season1: Season label for team 1 (e.g., "2526")
        season2: Season label for team 2 (e.g., "2425")
        top_n: Number of top players to return per category
        db: Database session

    Returns:
        Comparison including team stats and top players by category
    """
    # Use separate seasons if provided, otherwise fall back to single season parameter
    effective_season1 = season1 or season
    effective_season2 = season2 or season

    # Get stats for both teams
    team1_stats = get_team_stats(team1_id, effective_season1, db)
    team2_stats = get_team_stats(team2_id, effective_season2, db)

    # Build mapping from category names to the quantile metric codes in DB
    # The DB has quantile metrics like "quantile_finishing", "quantile_passing", etc.
    # These contain the quantile values we need for ranking players
    category_metrics = {}
    for _, row in SCOUTING_STATISTICS.iterrows():
        csv_category = row["category"]

        if csv_category not in category_metrics:
            # The quantile metric code has "quantile_" prefix
            base_code = csv_category.lower().replace(" ", "_").replace("&", "and")
            quantile_code = f"quantile_category_scores_{base_code}"
            category_metrics[csv_category] = [quantile_code]

    # Get elite players (top 10%) and their elite categories
    def get_elite_players_with_strengths(
        team_id: int, team_name: str, season_label: str, league_name: str
    ) -> list[ElitePlayerOut]:
        """Get players in top 90% quantile and show their elite categories (>90).

        Returns list of players with their elite categories, sorted by max quantile desc.
        Max 5 players shown.
        """
        logger.debug(
            f"🔍 Getting elite players for team: '{team_name}', season: '{season_label}'"
        )

        # Get all quantile metrics for all categories
        all_metric_codes = []
        for category, codes in category_metrics.items():
            all_metric_codes.extend(codes)

        metric_ids = (
            db.query(MetricDefinition.id, MetricDefinition.code)
            .filter(MetricDefinition.code.in_(all_metric_codes))
            .all()
        )
        metric_id_to_code = {mid: code for mid, code in metric_ids}
        metric_ids_list = list(metric_id_to_code.keys())

        if not metric_ids_list:
            logger.warning("   ⚠️  No metric IDs found")
            return []

        # Get ALL metrics for ALL players from this team
        players_query = (
            db.query(
                PlayerSeason.id,
                PlayerSeason.player_name,
                PlayerSeason.position,
                PlayerSeason.image_url,
                PlayerSeason.market_value_eur,
                PlayerSeason.birth_date,
                PlayerSeason.minutes,
                PlayerMetric.value,
                PlayerMetric.metric_id,
            )
            .join(PlayerMetric, PlayerMetric.player_season_id == PlayerSeason.id)
            .join(Team, PlayerSeason.team_id == Team.id)
            .join(Season, PlayerSeason.season_id == Season.id)
            .join(League, Team.league_id == League.id)
            .filter(Team.name == team_name)
            .filter(Season.label == season_label)
            .filter(League.name == AGGREGATED_LEAGUE_NAME)
            .filter(PlayerMetric.metric_id.in_(metric_ids_list))
            .all()
        )

        logger.debug(f"   Found {len(players_query)} player-metric records")

        # Build player profiles with all their metrics
        player_profiles = {}
        for (
            player_id,
            name,
            pos,
            img,
            market_value,
            birth_date,
            minutes,
            quantile_value,
            metric_id,
        ) in players_query:
            if player_id not in player_profiles:
                player_profiles[player_id] = {
                    "player_id": player_id,
                    "player_name": name,
                    "position": pos,
                    "image_url": img,
                    "market_value_eur": market_value,
                    "birth_date": birth_date,
                    "minutes": minutes,
                    "metrics": {},  # metric_code -> quantile_value
                }

            metric_code = metric_id_to_code.get(metric_id)
            if metric_code and quantile_value is not None:
                player_profiles[player_id]["metrics"][metric_code] = quantile_value

        # Map metric codes to categories
        code_to_category = {}
        for category, codes in category_metrics.items():
            for code in codes:
                code_to_category[code] = category

        # Exclude Discipline category for all players
        excluded_categories = {"Discipline"}

        # Filter to elite players (have at least one metric > 90 or 98 for GK) and identify their elite categories
        elite_players = []
        for player_id, profile in player_profiles.items():
            elite_categories = {}  # Changed to dict: category -> quantile_value
            max_quantile = 0

            for metric_code, quantile_value in profile["metrics"].items():
                if quantile_value > max_quantile:
                    max_quantile = quantile_value

                category = code_to_category.get(metric_code)
                if category and category not in excluded_categories:
                    # All players (field players and goalkeepers) require 90% (top 10%)
                    threshold = 90
                    if quantile_value > threshold:
                        # Store the highest quantile for this category
                        if (
                            category not in elite_categories
                            or quantile_value > elite_categories[category]
                        ):
                            elite_categories[category] = quantile_value

            # Only include if player has at least one elite category
            if elite_categories:
                elite_players.append(
                    ElitePlayerOut(
                        player_id=profile["player_id"],
                        player_name=profile["player_name"],
                        position=profile["position"],
                        image_url=profile["image_url"],
                        team_name=team_name,
                        market_value_eur=profile.get("market_value_eur"),
                        birth_date=profile.get("birth_date").isoformat()
                        if profile.get("birth_date")
                        else None,
                        minutes=profile.get("minutes"),
                        elite_categories=elite_categories,  # Now a dict with quantile values
                        max_quantile=max_quantile,  # For sorting
                    )
                )

        # Sort by quantile values in descending order (highest first, then 2nd highest, etc.)
        # This ensures players with multiple top percentiles rank higher
        # If tied, field players rank above goalkeepers
        def sort_key(player):
            # Get all quantile values sorted descending
            quantiles = sorted(player.elite_categories.values(), reverse=True)
            # Pad with zeros to ensure consistent comparison
            quantiles.extend([0] * (10 - len(quantiles)))
            # Check if goalkeeper (position is "GK" or "GOALKEEPER")
            is_gk = player.position and player.position.upper() in ["GK", "GOALKEEPER"]
            # Return tuple: quantiles first, then is_gk (False=0 comes before True=1, so field players first)
            return tuple(quantiles) + (is_gk,)

        elite_players.sort(key=sort_key, reverse=True)
        elite_players = elite_players[:5]

        logger.debug(
            f"   ✅ Found {len(elite_players)} elite players (top 90% in at least one category)"
        )
        for player in elite_players:
            logger.debug(
                f"      {player.player_name}: {', '.join(player.elite_categories)} (max: {player.max_quantile:.1f}%)"
            )

        return elite_players

    # Get top players by market value (separate from elite players)
    def get_top_market_value_players(
        team_id: int, team_name: str, season_label: str, top_n: int = 3
    ) -> list[ElitePlayerOut]:
        """Get top N players by market value for a team, regardless of performance.

        Filters strictly on Aggregated league and deduplicates by player name.

        Args:
            team_id: Team ID
            team_name: Team name
            season_label: Season label
            top_n: Number of top players to return

        Returns:
            List of top players by market value with empty elite_categories
        """
        # Fetch all players ordered by market value descending
        all_players = (
            db.query(
                PlayerSeason.id,
                PlayerSeason.player_name,
                PlayerSeason.position,
                PlayerSeason.image_url,
                PlayerSeason.market_value_eur,
                PlayerSeason.birth_date,
                PlayerSeason.minutes,
            )
            .join(Team, PlayerSeason.team_id == Team.id)
            .join(Season, PlayerSeason.season_id == Season.id)
            .join(League, Team.league_id == League.id)
            .filter(Team.name == team_name)
            .filter(Season.label == season_label)
            .filter(League.name == AGGREGATED_LEAGUE_NAME)
            .filter(PlayerSeason.market_value_eur.isnot(None))
            .filter(PlayerSeason.market_value_eur > 0)
            .order_by(PlayerSeason.market_value_eur.desc())
            .all()
        )

        # Deduplicate by player name, keeping first (highest market value) for each
        seen_players = set()
        players_query = []
        for player in all_players:
            player_name = player[1]  # player_name is at index 1
            if player_name not in seen_players:
                seen_players.add(player_name)
                players_query.append(player)
                if len(players_query) == top_n:
                    break

        return [
            ElitePlayerOut(
                player_id=player_id,
                player_name=name,
                position=pos,
                image_url=img,
                team_name=team_name,
                market_value_eur=market_value,
                birth_date=birth_date.isoformat() if birth_date else None,
                minutes=minutes,
                elite_categories={},  # Empty for market value players
                max_quantile=0,
            )
            for player_id, name, pos, img, market_value, birth_date, minutes in players_query
        ]

    team1_elite_players = get_elite_players_with_strengths(
        team1_id, team1_stats.team_name, effective_season1, team1_stats.league_name
    )
    team2_elite_players = get_elite_players_with_strengths(
        team2_id, team2_stats.team_name, effective_season2, team2_stats.league_name
    )

    # Get top market value players separately
    team1_top_value = get_top_market_value_players(
        team1_id, team1_stats.team_name, effective_season1, top_n=3
    )
    team2_top_value = get_top_market_value_players(
        team2_id, team2_stats.team_name, effective_season2, top_n=3
    )

    logger.debug("\n📦 Final response summary:")
    logger.debug(
        f"   Team 1 ({team1_stats.team_name}): {len(team1_elite_players)} elite players"
    )
    logger.debug(
        f"   Team 2 ({team2_stats.team_name}): {len(team2_elite_players)} elite players"
    )

    return TeamComparisonOut(
        team1=team1_stats,
        team2=team2_stats,
        elite_players_team1=team1_elite_players,
        elite_players_team2=team2_elite_players,
        top_value_team1=team1_top_value,
        top_value_team2=team2_top_value,
    )


class TeamRankingItem(BaseModel):
    """Team ranking item for a specific category."""

    team_id: int
    team_name: str
    league_name: Optional[str]
    season_label: Optional[str]
    quantile_value: float
    games_played: Optional[int]


@app.get("/teams/rankings", response_model=list[TeamRankingItem])
def get_team_rankings(
    category: str = Query(
        ...,
        description="Category: complete, entertaining, finishing, passing, dribbling, defense, aerial, gk",
    ),
    league: str = Query("Aggregated (All Leagues)", description="League name"),
    season: str = Query("2526", description="Season label"),
    limit: int = Query(20, description="Number of teams to return", ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get team rankings for a specific category using actual category scores.

    Uses raw category scores (not quantiles) for more precise rankings and fewer ties.

    Categories:
    - complete: Overall performance (average of all field categories + GK weighted 1/5)
    - entertaining: Sum of Finishing + Passing + Dribbling
    - finishing, passing, dribbling, defense, aerial: Individual categories
    - gk: Goalkeeper performance (reflexes_&_saves)

    Args:
        category: Ranking category
        league: League name
        season: Season label
        limit: Number of teams to return
        db: Database session

    Returns:
        List of teams ranked by category score (higher is better)
    """
    logger.debug(
        f"🏆 Getting team rankings: category={category}, league={league}, season={season}"
    )

    # Map category to metric code(s) - use actual category scores, not quantiles
    category_lower = category.lower()

    if category_lower == "complete":
        # Complete = average of all field categories + GK (weighted 1/5)
        metric_codes = [
            "finishing",
            "passing",
            "dribbling",
            "defense",
            "aerial",
        ]
        gk_metric = "reflexes_&_saves"
    elif category_lower == "entertaining":
        # Entertaining = Sum of Finishing + Passing + Dribbling
        metric_codes = [
            "finishing",
            "passing",
            "dribbling",
        ]
        gk_metric = None
    elif category_lower == "gk":
        metric_codes = ["reflexes_&_saves"]
        gk_metric = None
    else:
        # Individual category - use the category score directly
        metric_codes = [category_lower]
        gk_metric = None

    # Get team_seasons for this league and season
    query = (
        db.query(TeamSeason, Team, League, Season)
        .join(Team, TeamSeason.team_id == Team.id)
        .join(League, TeamSeason.league_id == League.id)
        .join(Season, TeamSeason.season_id == Season.id)
        .filter(Season.label == season)
    )

    # Apply league filter (handles Big 5 and other leagues)
    if league:
        query = apply_league_filter(query, league, League)

    team_seasons = query.all()

    if not team_seasons:
        logger.warning(f"No teams found for league={league}, season={season}")
        return []

    # Get metric IDs
    metric_defs = (
        db.query(MetricDefinition)
        .filter(
            MetricDefinition.code.in_(metric_codes + ([gk_metric] if gk_metric else []))
        )
        .all()
    )

    code_to_id = {md.code: md.id for md in metric_defs}

    # Calculate scores for each team
    team_scores = []
    for ts, team, league_obj, season_obj in team_seasons:
        # Get metrics for this team_season
        metrics_query = (
            db.query(TeamMetric)
            .filter(TeamMetric.team_season_id == ts.id)
            .filter(TeamMetric.metric_id.in_(list(code_to_id.values())))
            .all()
        )

        metrics_dict = {m.metric_id: m.value for m in metrics_query}

        # Calculate score based on category
        if category_lower == "complete":
            # Average of field categories + GK weighted 1/5
            field_values = [
                metrics_dict.get(code_to_id[code], 0) for code in metric_codes
            ]
            gk_value = (
                metrics_dict.get(code_to_id[gk_metric], 0)
                if gk_metric and gk_metric in code_to_id
                else 0
            )

            # Average field categories, then add GK weighted by 1/5
            if field_values:
                field_avg = sum(field_values) / len(field_values)
                score = field_avg + (gk_value / 5)
            else:
                score = 0
        elif category_lower == "entertaining":
            # Sum of Finishing + Passing + Dribbling category scores
            values = [
                metrics_dict.get(code_to_id[code], 0)
                for code in metric_codes
                if code in code_to_id
            ]
            score = sum(values)
        else:
            # Single category - just use the category score value
            metric_id = code_to_id.get(metric_codes[0])
            score = metrics_dict.get(metric_id, 0) if metric_id else 0

        team_scores.append(
            TeamRankingItem(
                team_id=team.id,
                team_name=team.name,
                league_name=league_obj.name,
                season_label=season_obj.label,
                quantile_value=score,
                games_played=ts.games_played,
            )
        )

    # Sort by score descending and limit
    team_scores.sort(key=lambda x: x.quantile_value, reverse=True)
    return team_scores[:limit]


class NationalTeamOut(BaseModel):
    """National team elite players showcase."""

    nationality: str
    season_label: str
    elite_players: list[ElitePlayerOut]
    top_value_players: list[ElitePlayerOut]


@app.get("/national-teams/{nationality}", response_model=NationalTeamOut)
def get_national_team_elite_players(
    nationality: str,
    season: str = Query("2526", description="Season label"),
    limit: int = Query(
        10, ge=1, le=20, description="Number of elite players to return"
    ),
    db: Session = Depends(get_db),
):
    """Get elite players (top 10%) for a specific nationality.

    Shows players who are in the top 90% quantile (or 100% for goalkeepers)
    in at least one category, sorted by their highest quantile value.

    Args:
        nationality: Player nationality (e.g., "France", "Brazil")
        season: Season label (e.g., "2526")
        limit: Maximum number of elite players to return (default 10, max 20)
        db: Database session

    Returns:
        NationalTeamOut with elite players and their strengths
    """
    logger.debug(
        f"\n🌍 Getting elite players for nationality: '{nationality}', season: '{season}'"
    )

    # Get all metric definitions for quantile category scores
    metric_defs = (
        db.query(MetricDefinition)
        .filter(MetricDefinition.code.like("quantile_category_scores_%"))
        .all()
    )

    if not metric_defs:
        logger.warning("   No quantile category score metrics found in database")
        return NationalTeamOut(
            nationality=nationality, season_label=season, elite_players=[]
        )

    metric_ids_list = [md.id for md in metric_defs]
    metric_id_to_code = {md.id: md.code for md in metric_defs}

    logger.debug(f"Metric id to code mapping: {metric_id_to_code}")

    # Build category -> list of metric codes
    category_metrics = {}
    for id, code in metric_id_to_code.items():
        # Extract category from code: quantile_category_scores_finishing -> Finishing
        logger.debug(f"Category id: {id}, code: {code}")
        if code and code.startswith("quantile_category_scores_"):
            base_category = (
                code.replace("quantile_category_scores_", "").replace("_", " ").title()
            )
            if base_category not in category_metrics:
                category_metrics[base_category] = []
            category_metrics[base_category].append(code)

    logger.debug(f"   Found {len(category_metrics)} categories to analyze")

    # Fetch all players from this nationality in the aggregated league
    players_query = (
        db.query(
            PlayerSeason.id,
            PlayerSeason.player_name,
            PlayerSeason.position,
            PlayerSeason.image_url,
            PlayerSeason.market_value_eur,
            PlayerSeason.birth_date,
            PlayerSeason.minutes,
            Team.name,
            PlayerMetric.value,
            PlayerMetric.metric_id,
        )
        .join(PlayerMetric, PlayerMetric.player_season_id == PlayerSeason.id)
        .join(Team, PlayerSeason.team_id == Team.id)
        .join(Season, PlayerSeason.season_id == Season.id)
        .join(League, Team.league_id == League.id)
        .filter(PlayerSeason.nationality == nationality)
        .filter(Season.label == season)
        .filter(League.name == AGGREGATED_LEAGUE_NAME)
        .filter(PlayerMetric.metric_id.in_(metric_ids_list))
        .all()
    )

    logger.debug(f"   Found {len(players_query)} player-metric records")

    if not players_query:
        logger.warning(f"   No players found for nationality '{nationality}'")
        return NationalTeamOut(
            nationality=nationality, season_label=season, elite_players=[]
        )

    # Build player profiles with all their metrics
    player_profiles = {}
    for (
        player_id,
        name,
        pos,
        img,
        market_value,
        birth_date,
        minutes,
        team_name,
        quantile_value,
        metric_id,
    ) in players_query:
        if player_id not in player_profiles:
            player_profiles[player_id] = {
                "player_id": player_id,
                "player_name": name,
                "position": pos,
                "image_url": img,
                "market_value_eur": market_value,
                "birth_date": birth_date,
                "minutes": minutes,
                "team_name": team_name,
                "metrics": {},  # metric_code -> quantile_value
            }

        metric_code = metric_id_to_code.get(metric_id)
        if metric_code and quantile_value is not None:
            player_profiles[player_id]["metrics"][metric_code] = quantile_value

    # Map metric codes to categories
    code_to_category = {}
    for category, codes in category_metrics.items():
        for code in codes:
            code_to_category[code] = category

    # Exclude Discipline category for all players
    excluded_categories = {"Discipline"}

    # Filter to elite players
    elite_players = []
    for player_id, profile in player_profiles.items():
        elite_categories = {}  # category -> quantile_value
        max_quantile = 0

        for metric_code, quantile_value in profile["metrics"].items():
            if quantile_value > max_quantile:
                max_quantile = quantile_value

            category = code_to_category.get(metric_code)
            if category and category not in excluded_categories:
                # All players (field players and goalkeepers) require 90% (top 10%)
                threshold = 90
                if quantile_value > threshold:
                    # Store the highest quantile for this category
                    if (
                        category not in elite_categories
                        or quantile_value > elite_categories[category]
                    ):
                        elite_categories[category] = quantile_value

        # Only include if player has at least one elite category
        if elite_categories:
            elite_players.append(
                ElitePlayerOut(
                    player_id=profile["player_id"],
                    player_name=profile["player_name"],
                    position=profile["position"],
                    image_url=profile["image_url"],
                    team_name=profile.get("team_name"),
                    market_value_eur=profile.get("market_value_eur"),
                    birth_date=profile.get("birth_date").isoformat()
                    if profile.get("birth_date")
                    else None,
                    minutes=profile.get("minutes"),
                    elite_categories=elite_categories,
                    max_quantile=max_quantile,
                )
            )

    # Sort by quantile values in descending order (highest first, then 2nd highest, etc.)
    # This ensures players with multiple top percentiles rank higher
    # If tied, field players rank above goalkeepers
    def sort_key(player):
        # Get all quantile values sorted descending
        quantiles = sorted(player.elite_categories.values(), reverse=True)
        # Pad with zeros to ensure consistent comparison
        quantiles.extend([0] * (10 - len(quantiles)))
        # Check if goalkeeper (position is "GK" or "GOALKEEPER")
        is_gk = player.position and player.position.upper() in ["GK", "GOALKEEPER"]
        # Return tuple: quantiles first, then is_gk (False=0 comes before True=1, so field players first)
        return tuple(quantiles) + (is_gk,)

    elite_players.sort(key=sort_key, reverse=True)
    elite_players = elite_players[:limit]

    logger.debug(f"   ✅ Found {len(elite_players)} elite players for {nationality}")
    for player in elite_players:
        logger.debug(
            f"      {player.player_name}: {list(player.elite_categories.keys())} (max: {player.max_quantile:.1f}%)"
        )

    # Get top 3 players by market value (separate from elite players)
    # Filter strictly on Aggregated league, fetch all matching players, then deduplicate in Python
    all_players_query = (
        db.query(
            PlayerSeason.id,
            PlayerSeason.player_name,
            PlayerSeason.position,
            PlayerSeason.image_url,
            PlayerSeason.market_value_eur,
            PlayerSeason.birth_date,
            PlayerSeason.minutes,
            Team.name,
        )
        .join(Team, PlayerSeason.team_id == Team.id)
        .join(Season, PlayerSeason.season_id == Season.id)
        .join(League, Team.league_id == League.id)
        .filter(PlayerSeason.nationality == nationality)
        .filter(Season.label == season)
        .filter(League.name == AGGREGATED_LEAGUE_NAME)
        .filter(PlayerSeason.market_value_eur.isnot(None))
        .filter(PlayerSeason.market_value_eur > 0)
        .order_by(PlayerSeason.market_value_eur.desc())
        .all()
    )

    # Deduplicate by player name, keeping the first (highest market value) for each
    seen_players = set()
    top_value_players_query = []
    for player in all_players_query:
        player_name = player[1]  # player_name is at index 1
        if player_name not in seen_players:
            seen_players.add(player_name)
            top_value_players_query.append(player)
            if len(top_value_players_query) == 3:
                break

    top_value_players = [
        ElitePlayerOut(
            player_id=player_id,
            player_name=name,
            position=pos,
            image_url=img,
            team_name=team_name,
            market_value_eur=market_value,
            birth_date=birth_date.isoformat() if birth_date else None,
            minutes=minutes,
            elite_categories={},  # Empty for market value players
            max_quantile=0,
        )
        for player_id, name, pos, img, market_value, birth_date, minutes, team_name in top_value_players_query
    ]

    return NationalTeamOut(
        nationality=nationality,
        season_label=season,
        elite_players=elite_players,
        top_value_players=top_value_players,
    )


@app.get("/teams/{team_id}/top-players", response_model=list[TopPlayerOut])
def get_team_top_players(
    team_id: int,
    season: str = Query("2526", description="Season label"),
    category: str = Query(
        ..., description="Metric category (e.g., 'finishing', 'passing')"
    ),
    limit: int = Query(3, description="Number of top players to return", ge=1, le=10),
    db: Session = Depends(get_db),
):
    """Get top N players from a team for a specific metric category.

    Args:
        team_id: Team ID
        season: Season label (e.g., "2526")
        category: Metric category name
        limit: Number of top players to return (1-10)
        db: Database session

    Returns:
        List of top players with their average quantile value in the category
    """
    # Get metrics for this category
    metric_codes = []
    for _, row in SCOUTING_STATISTICS.iterrows():
        if row["category"].lower() == category.lower():
            csv_stat = row["stat"]
            db_format = csv_stat.lower().replace(" ", "_")
            metric_codes.append(db_format)

    if not metric_codes:
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")

    # Get metric IDs
    metric_ids = (
        db.query(MetricDefinition.id)
        .filter(MetricDefinition.code.in_(metric_codes))
        .all()
    )
    metric_ids = [m[0] for m in metric_ids]

    if not metric_ids:
        raise HTTPException(
            status_code=404, detail=f"No metrics found for category '{category}'"
        )

    # Get top players
    players_query = (
        db.query(
            PlayerSeason.id,
            PlayerSeason.player_name,
            PlayerSeason.position,
            PlayerSeason.image_url,
            PlayerMetric.value,
        )
        .join(PlayerMetric, PlayerMetric.player_season_id == PlayerSeason.id)
        .join(Team, PlayerSeason.team_id == Team.id)
        .join(Season, PlayerSeason.season_id == Season.id)
        .filter(Team.id == team_id)
        .filter(Season.label == season)
        .filter(PlayerMetric.metric_id.in_(metric_ids))
        .order_by(PlayerMetric.value.desc().nullslast())
        .all()
    )

    # Group by player and calculate average
    player_scores = {}
    for player_id, name, pos, img, value in players_query:
        if player_id not in player_scores:
            player_scores[player_id] = {
                "player_id": player_id,
                "player_name": name,
                "position": pos,
                "image_url": img,
                "total_value": 0,
                "count": 0,
            }
        if value is not None:
            player_scores[player_id]["total_value"] += value
            player_scores[player_id]["count"] += 1

    # Build result list
    result = []
    for pid, data in player_scores.items():
        if data["count"] > 0:
            avg_value = data["total_value"] / data["count"]
            result.append(
                TopPlayerOut(
                    player_id=data["player_id"],
                    player_name=data["player_name"],
                    position=data["position"],
                    quantile_value=avg_value,
                    image_url=data["image_url"],
                )
            )

    # Sort by quantile value and return top N
    result.sort(key=lambda x: x.quantile_value or 0, reverse=True)
    return result[:limit]


class TeamRankingItem(BaseModel):
    """Team ranking item with team info and category score value."""

    team_id: int
    team_name: str
    league_name: str | None
    season_label: str | None
    quantile_value: float  # Actually contains category score, not quantile (kept name for API compatibility)
    games_played: int | None


class FeedbackSubmission(BaseModel):
    """User feedback submission."""

    sentiment: int
    comment: str | None = None
    page: str
    timestamp: str

    @field_validator("comment", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        """Convert empty strings to None."""
        if v == "":
            return None
        return v


def send_feedback_email_background(feedback_data: dict):
    """Send feedback email in background thread (non-blocking)."""
    try:
        resend_api_key = os.getenv("RESEND_API_KEY")
        recipient_email = "thescoutingarena@gmail.com"

        if resend_api_key:
            import requests

            # Sentiment emoji mapping
            sentiment_emoji = {1: "😞", 2: "😐", 3: "🙂", 4: "😀"}
            sentiment_label = {1: "Poor", 2: "Okay", 3: "Good", 4: "Great"}

            # Email body
            email_body = f"""
New feedback received from The Scouting Arena:

📍 Page: {feedback_data["page"]}
{sentiment_emoji.get(feedback_data["sentiment"], "❓")} Sentiment: {sentiment_label.get(feedback_data["sentiment"], "Unknown")} ({feedback_data["sentiment"]}/4)
💬 Comment: {feedback_data["comment"] or "(No comment provided)"}
🕐 Timestamp: {feedback_data["timestamp"]}

---
This is an automated message from The Scouting Arena feedback system.
            """

            response = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": "The Scouting Arena <feedback@resend.dev>",
                    "to": [recipient_email],
                    "subject": f"🎯 New Feedback: {feedback_data['page']}",
                    "text": email_body,
                },
                timeout=10,
            )

            if response.status_code == 200:
                logger.info(f"📧 Email notification sent to {recipient_email}")
            else:
                logger.error(
                    f"❌ Failed to send email: {response.status_code} - {response.text}"
                )
        else:
            logger.warning(
                "⚠️ RESEND_API_KEY not configured, skipping email notification"
            )
    except Exception as e:
        logger.error(f"❌ Failed to send email notification: {e}")


@app.post("/feedback")
async def submit_feedback(
    request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """
    Store user feedback in database and send email notification in background.

    Args:
        request: HTTP request
        background_tasks: FastAPI background tasks
        db: Database session

    Returns:
        Success message (immediate, email sent in background)
    """
    from datetime import datetime

    logger.info(f"🎯 Feedback endpoint hit with method: {request.method}")
    logger.info(f"📍 Request URL: {request.url}")
    logger.info(f"📋 Request headers: {dict(request.headers)}")

    # Manually parse the JSON body
    try:
        body = await request.json()
        logger.info(f"📦 Request body received: {body}")
        feedback = FeedbackSubmission(**body)
    except Exception as e:
        logger.error(f"❌ Failed to parse feedback request: {e}")
        raise HTTPException(status_code=422, detail=f"Invalid request body: {e}")

    logger.info(f"📥 Received feedback request: {feedback.model_dump()}")

    # Log feedback
    logger.info(
        f"📝 Feedback received: sentiment={feedback.sentiment}, page={feedback.page}"
    )
    if feedback.comment:
        logger.info(f"   Comment: {feedback.comment}")

    # Save to database (fast, synchronous)
    try:
        db_feedback = Feedback(
            sentiment=feedback.sentiment,
            comment=feedback.comment,
            page=feedback.page,
            timestamp=feedback.timestamp,
            created_at=datetime.utcnow(),
        )
        db.add(db_feedback)
        db.commit()
        logger.info(f"✅ Feedback saved to database (ID: {db_feedback.id})")
    except Exception as e:
        logger.error(f"❌ Failed to save feedback to database: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Failed to save feedback to database"
        )

    # Send email in background (non-blocking, returns immediately)
    background_tasks.add_task(
        send_feedback_email_background,
        {
            "sentiment": feedback.sentiment,
            "comment": feedback.comment,
            "page": feedback.page,
            "timestamp": feedback.timestamp,
        },
    )

    return {"status": "success", "message": "Thank you for your feedback!"}
