import argparse
import os
from datetime import datetime
from typing import Optional

# Import DB infra
try:
    from db.create_tables import create_all
    from db.database import get_engine, get_session_maker
    from db.db_insert.ingest_team_stats_to_db import run as run_team_ingest
    from db.db_insert.ingest_player_stats_to_db import run as run_player_ingest
    from db.db_insert.ingest_today_nba_events_to_db import (
        upsert_game_schedule,
        parse_events,
        to_est_date,
    )
    from odds_api_retrieval.get_today_nba_events import (
        DEFAULT_BASE_API_URL,
        SPORT_KEY,
        build_events_url,
        fetch_json,
        iso_utc_range_for_local_day,
    )
except ImportError:
    # Support running as a direct script via absolute path
    import sys
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from db.create_tables import create_all  # type: ignore
    from db.database import get_engine, get_session_maker  # type: ignore
    from db.db_insert.ingest_team_stats_to_db import run as run_team_ingest  # type: ignore
    from db.db_insert.ingest_player_stats_to_db import run as run_player_ingest  # type: ignore
    from db.db_insert.ingest_today_nba_events_to_db import (  # type: ignore
        upsert_game_schedule,
        parse_events,
        to_est_date,
    )
    from odds_api_retrieval.get_today_nba_events import (  # type: ignore
        DEFAULT_BASE_API_URL,
        SPORT_KEY,
        build_events_url,
        fetch_json,
        iso_utc_range_for_local_day,
    )


def update_game_schedule(
    *,
    database_url: str,
    base_url: str,
    tz_name: str,
    local_date_str: Optional[str],
) -> int:
    """
    Fetch today's NBA events (in the provided timezone) and upsert into game_schedule.
    Returns number of inserted rows (conflicts ignored).
    """
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(tz_name)
    if local_date_str:
        try:
            local_day = datetime.strptime(local_date_str, "%Y-%m-%d").replace(tzinfo=tz)
        except ValueError as exc:
            raise SystemExit(f"Invalid --date format, expected YYYY-MM-DD: {exc}")
    else:
        local_day = datetime.now(tz)

    start_iso, end_iso = iso_utc_range_for_local_day(local_day, tz)
    url = build_events_url(
        base_api_url=base_url,
        sport_key=SPORT_KEY,
        commence_from_iso=start_iso,
        commence_to_iso=end_iso,
        date_format="iso",
    )

    payload = fetch_json(url)
    events = parse_events(payload)

    rows = []
    for ev in events:
        commence_time = ev.get("commence_time")
        home_team = ev.get("home_team")
        away_team = ev.get("away_team")
        if not (commence_time and home_team and away_team):
            continue
        game_date_est = to_est_date(commence_time, tz_name=tz_name)
        rows.append(
            {
                "game_date_est": game_date_est,
                "away_team": away_team,
                "home_team": home_team,
            }
        )

    engine = get_engine(database_url)
    SessionLocal = get_session_maker(engine)
    inserted = 0
    with SessionLocal() as session:
        with session.begin():
            inserted = upsert_game_schedule(session, rows)
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description="Run daily DB update: tables, events, team & player stats")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="SQLAlchemy database URL. If omitted, uses DATABASE_URL env var.",
    )
    parser.add_argument("--season", default="2025-26", help="Season string, e.g., 2025-26")
    parser.add_argument(
        "--season-type", default="Regular Season", help="Season type, e.g., Regular Season"
    )
    parser.add_argument(
        "--per-mode", default="PerGame", help="Per mode, e.g., PerGame or Per100Possessions"
    )
    parser.add_argument(
        "--events-base-url",
        default=os.environ.get("ODDS_API_BASE_URL", DEFAULT_BASE_API_URL),
        help="Base API URL for events (default from ODDS_API_BASE_URL or module default)",
    )
    parser.add_argument("--tz", default="America/New_York", help="Timezone for events day window")
    parser.add_argument(
        "--date",
        default=None,
        help="Local date in YYYY-MM-DD (interpreted in --tz). Defaults to today's date in --tz.",
    )
    args = parser.parse_args()

    if not args.database_url:
        raise RuntimeError("DATABASE_URL env var or --database-url must be provided")

    # 1) Ensure schemas/tables exist
    print("Ensuring database schemas and tables exist...")
    create_all(args.database_url)

    # 2) Update game schedule for the day
    print("Updating game_schedule for the requested day...")
    inserted = update_game_schedule(
        database_url=args.database_url,
        base_url=args.events_base_url,
        tz_name=args.tz,
        local_date_str=args.date,
    )
    print(f"Upserted {inserted} rows into game_schedule (conflicts ignored)")

    # 3) Ingest team stats across timeframes
    print("Ingesting team stats across timeframes...")
    run_team_ingest(
        season=args.season,
        season_type=args.season_type,
        per_mode=args.per_mode,
        database_url=args.database_url,
    )

    # 4) Ingest player stats across timeframes
    print("Ingesting player stats across timeframes...")
    run_player_ingest(
        season=args.season,
        season_type=args.season_type,
        per_mode=args.per_mode,
        database_url=args.database_url,
    )

    print("Daily update completed.")


if __name__ == "__main__":
    main()


