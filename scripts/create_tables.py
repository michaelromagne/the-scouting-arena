#!/usr/bin/env python3
"""Create all database tables from SQLAlchemy models."""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine

from scouting.db.models import Base

if __name__ == "__main__":
    # Get database URL from environment
    database_url = os.getenv(
        "DATABASE_URL", "postgresql://scout:scout@localhost:5432/scouting"
    )

    print(f"Creating tables in database: {database_url}")

    # Create engine
    engine = create_engine(database_url)

    # Create all tables
    Base.metadata.create_all(engine)

    print("✓ All tables created successfully!")
