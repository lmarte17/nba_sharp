import argparse
from typing import Optional
from sqlalchemy import text

# Support running as a module (python -m db.create_tables) and as a script
try:
    from .database import Base, get_engine
    # Import models so their metadata is registered with Base
    from . import models  # noqa: F401
    from .models import (
        TeamStats,
        PlayerStatsSeasonLong,
        PlayerStatsLast10,
        PlayerStatsLast5,
        PlayerStatsLast3,
        GameMatchup,
        PlayerProjection,
    )  # explicit for targeted create if needed
except ImportError:
    import sys
    from pathlib import Path

    # Add project root to sys.path so `db` package is importable
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from db.database import Base, get_engine  # type: ignore
    from db import models  # type: ignore  # noqa: F401
    from db.models import (  # type: ignore
        TeamStats,
        PlayerStatsSeasonLong,
        PlayerStatsLast10,
        PlayerStatsLast5,
        PlayerStatsLast3,
        GameMatchup,
        PlayerProjection,
    )


def create_all(database_url: Optional[str] = None) -> None:
    engine = get_engine(database_url)
    # Ensure the 'team_data' schema exists for models that target it (e.g., TeamStats)
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS team_data"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS player_data"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS analysis"))
    # Create all tables registered on Base
    Base.metadata.create_all(bind=engine)
    # Ensure TeamStats specifically exists in case metadata discovery was incomplete
    TeamStats.__table__.create(bind=engine, checkfirst=True)
    # Ensure PlayerStats tables exist across timeframes
    PlayerStatsSeasonLong.__table__.create(bind=engine, checkfirst=True)
    PlayerStatsLast10.__table__.create(bind=engine, checkfirst=True)
    PlayerStatsLast5.__table__.create(bind=engine, checkfirst=True)
    PlayerStatsLast3.__table__.create(bind=engine, checkfirst=True)
    # Ensure analysis tables exist
    GameMatchup.__table__.create(bind=engine, checkfirst=True)
    PlayerProjection.__table__.create(bind=engine, checkfirst=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create database tables")
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database URL. If omitted, uses DATABASE_URL env var.",
    )
    args = parser.parse_args()

    create_all(args.database_url)
    print("Tables created (no-op for existing tables)")


if __name__ == "__main__":
    main()


