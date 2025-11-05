import argparse
import os
from datetime import datetime
from typing import Iterable, List

from zoneinfo import ZoneInfo
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

# Import Odds helpers
try:
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

    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from odds_api_retrieval.get_today_nba_events import (  # type: ignore
        DEFAULT_BASE_API_URL,
        SPORT_KEY,
        build_events_url,
        fetch_json,
        iso_utc_range_for_local_day,
    )

# Import DB utilities and models
try:
    from db.database import get_engine, get_session_maker
    from db.models import GameSchedule
except ImportError:
    import sys
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from db.database import get_engine, get_session_maker  # type: ignore
    from db.models import GameSchedule  # type: ignore


def parse_events(payload: dict) -> List[dict]:
    events = payload.get("events")
    if events is None:
        events = payload.get("data", [])
    if not isinstance(events, list):
        return []
    return events


def to_est_date(commence_time_iso: str, tz_name: str = "America/New_York") -> datetime.date:
    iso_norm = commence_time_iso.replace("Z", "+00:00")
    dt_utc = datetime.fromisoformat(iso_norm)
    local_dt = dt_utc.astimezone(ZoneInfo(tz_name))
    return local_dt.date()


def upsert_game_schedule(session: Session, rows: Iterable[dict]) -> int:
    if not rows:
        return 0
    stmt = pg_insert(GameSchedule.__table__).values(list(rows))
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["game_date_est", "away_team", "home_team"]
    )
    result = session.execute(stmt)
    return getattr(result, "rowcount", 0) or 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch today's NBA events and upsert into game_schedule (EST date).",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("ODDS_API_BASE_URL", DEFAULT_BASE_API_URL),
        help="Base API URL (default from ODDS_API_BASE_URL or http://localhost:8000/api)",
    )
    parser.add_argument(
        "--tz",
        default="America/New_York",
        help="Timezone to interpret the local day for querying and EST date storage",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Local date in YYYY-MM-DD (interpreted in --tz). Defaults to today's date in --tz.",
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="Database URL. If omitted, uses DATABASE_URL env var.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write to DB; just print how many rows would be upserted.",
    )
    args = parser.parse_args()

    tz = ZoneInfo(args.tz)
    if args.date:
        try:
            local_day = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=tz)
        except ValueError as exc:
            raise SystemExit(f"Invalid --date format, expected YYYY-MM-DD: {exc}")
    else:
        local_day = datetime.now(tz)

    start_iso, end_iso = iso_utc_range_for_local_day(local_day, tz)
    url = build_events_url(
        base_api_url=args.base_url,
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
        game_date_est = to_est_date(commence_time, tz_name=args.tz)
        rows.append(
            {
                "game_date_est": game_date_est,
                "away_team": away_team,
                "home_team": home_team,
            }
        )

    if args.dry_run:
        print(f"Would upsert {len(rows)} rows into game_schedule")
        return

    engine = get_engine(args.database_url)
    SessionLocal = get_session_maker(engine)
    inserted = 0
    with SessionLocal() as session:
        with session.begin():
            inserted = upsert_game_schedule(session, rows)
    print(f"Upserted {inserted} rows into game_schedule (conflicts ignored)")


if __name__ == "__main__":
    main()


