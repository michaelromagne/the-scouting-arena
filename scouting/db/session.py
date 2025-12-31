from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


def get_database_url() -> str:
    """Return the SQLAlchemy database URL.

    Order of precedence:
      - DATABASE_URL env var
      - Default to local Postgres
    """

    url = os.getenv("DATABASE_URL")
    if url:
        print("Using database URL from environment variable")
        return url
    # Default local dev database
    return "postgresql+psycopg://scout:scout@localhost:5432/scouting"


def create_db_engine(echo: bool = False) -> Engine:
    """Create and return a SQLAlchemy engine.

    Args:
        echo: Whether to echo SQL statements.
    """
    # Optimize for Railway's network latency and bulk operations
    return create_engine(
        get_database_url(),
        echo=echo,
        pool_pre_ping=True,
        pool_size=10,  # Smaller pool for Railway's connection limits
        max_overflow=20,  # Allow more connections during bulk ops
        pool_timeout=120,  # Longer timeout for Railway bulk operations
        pool_recycle=1800,  # Recycle connections every 30 minutes
        connect_args={
            "connect_timeout": 120,  # 2 minutes for initial connection
            "application_name": "scouting_etl",
            "options": "-c statement_timeout=300000",  # 5 minutes statement timeout
        },
    )


def init_db(engine: Engine | None = None) -> None:
    """Create all tables if they do not exist.

    Args:
        engine: Optional pre-created engine.
    """

    local_engine = engine or create_db_engine()

    # Use checkfirst=True to avoid conflicts with existing tables
    try:
        Base.metadata.create_all(bind=local_engine, checkfirst=True)
    except Exception as e:
        # Log the error but don't fail startup if tables already exist
        print(f"Warning: Database initialization error (tables may already exist): {e}")
        # Continue startup - the tables likely already exist


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Return a configured session factory bound to the engine."""

    local_engine = engine or create_db_engine()
    return sessionmaker(bind=local_engine, autoflush=False, autocommit=False)


@contextmanager
def session_scope(engine: Engine | None = None) -> Iterator[Session]:
    """Provide a transactional scope around a series of operations.

    Args:
        engine: Optional SQLAlchemy engine to bind the session to.
    """

    factory = get_session_factory(engine)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
