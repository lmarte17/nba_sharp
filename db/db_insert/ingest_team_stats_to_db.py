import argparse
import os
from typing import Dict

import pandas as pd
from sqlalchemy import text

# Support running as a module and as a script by fixing sys.path when needed
try:
    from db.database import get_engine
    from stats_retrieval.fetch_and_merge_team_stats import fetch_and_merge_team_stats
except ImportError:
    import sys
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from db.database import get_engine  # type: ignore
    from stats_retrieval.fetch_and_merge_team_stats import fetch_and_merge_team_stats  # type: ignore


TIMEFRAME_TO_LAST_N: Dict[str, int] = {
    "season_long": 0,
    "last_10": 10,
    "last_5": 5,
    "last_3": 3,
}


def upsert_dataframe(df: pd.DataFrame, table_name: str, database_url: str) -> None:
    engine = get_engine(database_url)
    with engine.begin() as conn:
        # Ensure schema exists before writing
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS team_data"))
        df.to_sql(
            name=table_name,
            con=conn,
            schema="team_data",
            if_exists="replace",
            index=False,
        )


def run(season: str, season_type: str, per_mode: str, database_url: str) -> None:
    for timeframe, last_n in TIMEFRAME_TO_LAST_N.items():
        print(f"Fetching stats for timeframe '{timeframe}' (last_n_games={last_n})...")
        df = fetch_and_merge_team_stats(
            season=season,
            season_type=season_type,
            per_mode=per_mode,
            last_n_games=last_n,
        )
        if df is None or df.empty:
            print(f"No data returned for timeframe '{timeframe}'. Skipping.")
            continue

        table_name = f"team_stats_{timeframe}"
        print(f"Writing {len(df)} rows to team_data.{table_name}...")
        upsert_dataframe(df, table_name, database_url)
        print(f"Wrote team_data.{table_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest NBA team stats into Postgres tables for multiple timeframes.")
    parser.add_argument("--season", default="2024-25", help="Season string, e.g., 2024-25")
    parser.add_argument("--season-type", default="Regular Season", help="Season type, e.g., Regular Season")
    parser.add_argument("--per-mode", default="PerGame", help="Per mode, e.g., PerGame or Per100Possessions")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="SQLAlchemy database URL. If omitted, uses DATABASE_URL env var.",
    )
    args = parser.parse_args()

    if not args.database_url:
        raise RuntimeError("DATABASE_URL env var or --database-url must be provided")

    run(
        season=args.season,
        season_type=args.season_type,
        per_mode=args.per_mode,
        database_url=args.database_url,
    )


if __name__ == "__main__":
    main()


