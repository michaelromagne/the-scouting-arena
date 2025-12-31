from __future__ import annotations

from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for the scouting project."""


class League(Base):
    __tablename__ = "leagues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    teams: Mapped[list[Team]] = relationship("Team", back_populates="league")  # type: ignore[name-defined]


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    start_year: Mapped[Optional[int]] = mapped_column(Integer)
    end_year: Mapped[Optional[int]] = mapped_column(Integer)

    player_seasons: Mapped[list[PlayerSeason]] = relationship(
        "PlayerSeason", back_populates="season"
    )  # type: ignore[name-defined]


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("name", "league_id", name="uq_team_name_league"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    league_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("leagues.id", ondelete="SET NULL")
    )

    league: Mapped[Optional[League]] = relationship("League", back_populates="teams")
    player_seasons: Mapped[list[PlayerSeason]] = relationship(
        "PlayerSeason", back_populates="team"
    )  # type: ignore[name-defined]
    team_seasons: Mapped[list[TeamSeason]] = relationship(
        "TeamSeason", back_populates="team"
    )  # type: ignore[name-defined]


class PlayerSeason(Base):
    """Player data for a specific season/team/league combination.

    This is the main player table - each row represents a player's data
    for a specific season, team, and league. Player identity is determined
    by (player_name, team_id, season_id, league_id).
    """

    __tablename__ = "player_seasons"
    __table_args__ = (
        UniqueConstraint(
            "player_name",
            "season_id",
            "team_id",
            "league_id",
            name="uq_player_team_season_league",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_name: Mapped[str] = mapped_column(String, nullable=False)
    team_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL")
    )
    season_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("seasons.id", ondelete="SET NULL")
    )
    league_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("leagues.id", ondelete="SET NULL")
    )

    # Player identity/attributes
    nationality: Mapped[Optional[str]] = mapped_column(String)
    born_year: Mapped[Optional[int]] = mapped_column(Integer)
    birth_date: Mapped[Optional[Date]] = mapped_column(Date)
    position: Mapped[Optional[str]] = mapped_column(String)

    # Season-specific stats
    minutes: Mapped[Optional[int]] = mapped_column(Integer)
    market_value_eur: Mapped[Optional[float]] = mapped_column(Float)
    image_url: Mapped[Optional[str]] = mapped_column(String)

    # Relationships
    team: Mapped[Optional[Team]] = relationship("Team", back_populates="player_seasons")
    season: Mapped[Optional[Season]] = relationship(
        "Season", back_populates="player_seasons"
    )
    league: Mapped[Optional[League]] = relationship("League")
    metrics: Mapped[list[PlayerMetric]] = relationship(
        "PlayerMetric", back_populates="player_season"
    )  # type: ignore[name-defined]


class MetricDefinition(Base):
    __tablename__ = "metric_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text)
    direction: Mapped[str] = mapped_column(
        String, nullable=False, default="higher_is_better"
    )
    scale: Mapped[Optional[str]] = mapped_column(String)

    __table_args__ = (
        CheckConstraint(
            "direction IN ('higher_is_better','lower_is_better')",
            name="ck_metric_direction",
        ),
    )

    player_metrics: Mapped[list[PlayerMetric]] = relationship(
        "PlayerMetric", back_populates="metric"
    )  # type: ignore[name-defined]


class PlayerMetric(Base):
    __tablename__ = "player_metrics"
    __table_args__ = (
        UniqueConstraint(
            "player_season_id", "metric_id", name="uq_playerseason_metric"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_season_id: Mapped[int] = mapped_column(
        ForeignKey("player_seasons.id", ondelete="CASCADE"), nullable=False
    )
    metric_id: Mapped[int] = mapped_column(
        ForeignKey("metric_definitions.id", ondelete="CASCADE"), nullable=False
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    percentile: Mapped[Optional[float]] = mapped_column(Float)

    player_season: Mapped[PlayerSeason] = relationship(
        "PlayerSeason", back_populates="metrics"
    )
    metric: Mapped[MetricDefinition] = relationship(
        "MetricDefinition", back_populates="player_metrics"
    )


class MetricSet(Base):
    __tablename__ = "metric_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    player_similarities: Mapped[list[PlayerSimilarity]] = relationship(
        "PlayerSimilarity", back_populates="metric_set"
    )  # type: ignore[name-defined]


class PlayerSimilarity(Base):
    """Similarity between two player_seasons."""

    __tablename__ = "player_similarities"
    __table_args__ = (
        UniqueConstraint(
            "season_id",
            "metric_set_id",
            "player_season_id",
            "similar_player_season_id",
            name="uq_player_similarity",
        ),
        CheckConstraint(
            "player_season_id <> similar_player_season_id", name="ck_different_players"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    season_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("seasons.id", ondelete="CASCADE")
    )
    metric_set_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("metric_sets.id", ondelete="CASCADE")
    )
    player_season_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("player_seasons.id", ondelete="CASCADE"), nullable=False
    )
    similar_player_season_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("player_seasons.id", ondelete="CASCADE"), nullable=False
    )
    distance: Mapped[float] = mapped_column(
        Float, nullable=False
    )  # smaller = more similar

    # Relationships
    season: Mapped[Optional[Season]] = relationship("Season")
    metric_set: Mapped[Optional[MetricSet]] = relationship(
        "MetricSet", back_populates="player_similarities"
    )
    player_season: Mapped[PlayerSeason] = relationship(
        "PlayerSeason", foreign_keys=[player_season_id]
    )
    similar_player_season: Mapped[PlayerSeason] = relationship(
        "PlayerSeason", foreign_keys=[similar_player_season_id]
    )


class TeamSeason(Base):
    """Team performance data for a specific season/league combination.

    This table stores team-level statistics for each season, parallel to
    PlayerSeason but for teams instead of individual players.
    """

    __tablename__ = "team_seasons"
    __table_args__ = (
        UniqueConstraint(
            "team_id",
            "season_id",
            "league_id",
            name="uq_team_season_league",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    season_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("seasons.id", ondelete="SET NULL")
    )
    league_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("leagues.id", ondelete="SET NULL")
    )

    # Season-specific stats
    games_played: Mapped[Optional[int]] = mapped_column(Integer)

    # Relationships
    team: Mapped[Team] = relationship("Team", back_populates="team_seasons")
    season: Mapped[Optional[Season]] = relationship("Season")
    league: Mapped[Optional[League]] = relationship("League")
    metrics: Mapped[list[TeamMetric]] = relationship(
        "TeamMetric", back_populates="team_season", cascade="all, delete-orphan"
    )  # type: ignore[name-defined]


class TeamMetric(Base):
    """Individual metric value for a team in a season.

    Similar to PlayerMetric but for team-level statistics.
    """

    __tablename__ = "team_metrics"
    __table_args__ = (
        UniqueConstraint("team_season_id", "metric_id", name="uq_teamseason_metric"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_season_id: Mapped[int] = mapped_column(
        ForeignKey("team_seasons.id", ondelete="CASCADE"), nullable=False
    )
    metric_id: Mapped[int] = mapped_column(
        ForeignKey("metric_definitions.id", ondelete="CASCADE"), nullable=False
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    percentile: Mapped[Optional[float]] = mapped_column(Float)

    team_season: Mapped[TeamSeason] = relationship(
        "TeamSeason", back_populates="metrics"
    )
    metric: Mapped[MetricDefinition] = relationship("MetricDefinition")


class Feedback(Base):
    """User feedback submissions."""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sentiment: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    page: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime, nullable=False)
