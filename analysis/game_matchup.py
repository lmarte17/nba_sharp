import argparse
import datetime
from typing import Dict, Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from db.database import get_engine, get_session_maker
    from db.models import GameMatchup
    from db.db_extract import (
        fetch_schedule_for_date,
        load_team_stats_map,
        compute_league_baselines,
        resolve_team_record,
    )
except ImportError:
    # Support running directly
    import sys
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from db.database import get_engine, get_session_maker  # type: ignore
    from db.models import GameMatchup  # type: ignore
    from db.db_extract import (  # type: ignore
        fetch_schedule_for_date,
        load_team_stats_map,
        compute_league_baselines,
        resolve_team_record,
    )


TIMEFRAMES = {
    "sl": "season_long",
    "l10": "last_10",
    "l5": "last_5",
    "l3": "last_3",
}


def _r2(v):
    if v is None:
        return None
    try:
        return round(float(v), 2)
    except Exception:
        return None


def _compute_horizon(
    team: Dict[str, float],
    opp: Dict[str, float],
    lg_pace: float,
    lg_pp100: float,
    is_home: bool,
) -> Dict[str, Optional[float]]:
    # HCA adjustments
    hca_poss_adj = 0.3 if is_home else -0.3
    hca_pp100_adj = 0.5 if is_home else -0.5
    opp_hca_poss_adj = -hca_poss_adj
    opp_hca_pp100_adj = -hca_pp100_adj

    team_pace = float(team.get("pace") or 0.0)
    opp_pace = float(opp.get("pace") or 0.0)
    team_offrtg = float(team.get("offrtg") or 0.0)
    team_defrtg = float(team.get("defrtg") or 0.0)
    opp_offrtg = float(opp.get("offrtg") or 0.0)
    opp_defrtg = float(opp.get("defrtg") or 0.0)

    team_pace_adj = team_pace + hca_poss_adj
    opp_pace_adj = opp_pace + opp_hca_poss_adj
    implied_poss = (team_pace_adj + opp_pace_adj) / 2.0

    poss_above_lg = team_pace - lg_pace

    exp_pp100_unadj = lg_pp100 + 0.5 * (team_offrtg - lg_pp100) + 0.5 * (lg_pp100 - opp_defrtg)
    exp_pp100 = exp_pp100_unadj + hca_pp100_adj

    opp_exp_pp100_unadj = lg_pp100 + 0.5 * (opp_offrtg - lg_pp100) + 0.5 * (lg_pp100 - team_defrtg)
    opp_exp_pp100 = opp_exp_pp100_unadj + opp_hca_pp100_adj

    proj_pts = exp_pp100 * implied_poss / 100.0
    opp_proj_pts = opp_exp_pp100 * implied_poss / 100.0
    proj_total = proj_pts + opp_proj_pts
    matchup = proj_pts - opp_proj_pts

    pts_allowed_pg = team_defrtg * team_pace / 100.0

    return {
        "pace": _r2(team_pace),
        "opp_pace": _r2(opp_pace),
        "lg_pace": _r2(lg_pace),
        "poss_above_lg": _r2(poss_above_lg),
        "implied_poss": _r2(implied_poss),
        "offrtg": _r2(team_offrtg),
        "defrtg": _r2(team_defrtg),
        "opp_offrtg": _r2(opp_offrtg),
        "opp_defrtg": _r2(opp_defrtg),
        "lg_pp100": _r2(lg_pp100),
        "hca_poss_adj": _r2(hca_poss_adj),
        "hca_pp100_adj": _r2(hca_pp100_adj),
        "exp_pp100": _r2(exp_pp100),
        "opp_exp_pp100": _r2(opp_exp_pp100),
        "proj_pts": _r2(proj_pts),
        "opp_proj_pts": _r2(opp_proj_pts),
        "proj_total": _r2(proj_total),
        "matchup": _r2(matchup),
        "pts_allowed_pg": _r2(pts_allowed_pg),
    }


def _suffixize(prefix: str, h: str) -> str:
    return f"{prefix}_{h}"


def _build_row(
    game_date: datetime.date,
    team_side: str,
    home_stats: Dict[str, dict],
    away_stats: Dict[str, dict],
    baselines: Dict[str, tuple],
) -> Optional[dict]:
    is_home = team_side == "home"
    team = home_stats if is_home else away_stats
    opp = away_stats if is_home else home_stats

    # Require at least team and opp to exist in SL horizon to emit a row
    if not team or not opp:
        return None

    base = {
        "game_date_est": game_date,
        "team_name": team.get("team_name"),
        "opp_team_name": opp.get("team_name"),
        "is_home": is_home,
        "team_id": team.get("team_id"),
        "opp_team_id": opp.get("team_id"),
        "calc_version": "v1",
    }

    # For each timeframe/horizon, compute metrics if both sides present
    for h_key, tf in TIMEFRAMES.items():
        if team.get(tf) is None or opp.get(tf) is None:
            # Populate empty fields for consistency
            for field in (
                "pace",
                "opp_pace",
                "lg_pace",
                "poss_above_lg",
                "implied_poss",
                "offrtg",
                "defrtg",
                "opp_offrtg",
                "opp_defrtg",
                "lg_pp100",
                "hca_poss_adj",
                "hca_pp100_adj",
                "exp_pp100",
                "opp_exp_pp100",
                "proj_pts",
                "opp_proj_pts",
                "proj_total",
                "matchup",
                "pts_allowed_pg",
            ):
                base[_suffixize(field, h_key)] = None
            continue

        lg_pace, lg_pp100 = baselines[h_key]
        comp = _compute_horizon(team[tf], opp[tf], lg_pace, lg_pp100, is_home=is_home)
        for field, value in comp.items():
            base[_suffixize(field, h_key)] = value

    return base


def run(game_date: datetime.date, database_url: Optional[str]) -> int:
    engine = get_engine(database_url)
    SessionLocal = get_session_maker(engine)

    # Ensure schema/table exist in case create_tables wasn't run
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS analysis"))
        # If an old deferrable unique constraint exists, drop it; ON CONFLICT can't use it
        conn.execute(
            text(
                "ALTER TABLE analysis.game_matchup DROP CONSTRAINT IF EXISTS uq_game_matchup_date_teams"
            )
        )
        # Ensure a non-deferrable unique index exists for ON CONFLICT arbiter
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_game_matchup_date_teams ON analysis.game_matchup (game_date_est, team_name, opp_team_name)"
            )
        )
    GameMatchup.__table__.create(bind=engine, checkfirst=True)

    with SessionLocal() as session:
        # Load schedule
        schedule = fetch_schedule_for_date(session, game_date)
        if not schedule:
            return 0

        # Load team stats maps per timeframe and baselines
        team_maps: Dict[str, Dict[str, dict]] = {}
        baselines: Dict[str, tuple] = {}
        for h_key, tf in TIMEFRAMES.items():
            # Build maps keyed by normalized name, but we need to preserve two lookups (home/away)
            raw_map = load_team_stats_map(session, tf)
            # Build a two-level map: normalized_name -> per-timeframe dict
            team_maps[h_key] = raw_map
            baselines[h_key] = compute_league_baselines(session, tf)

        inserted = 0
        rows_to_upsert = []
        for g in schedule:
            home_name = g["home_team"]
            away_name = g["away_team"]

            def pick(name: str) -> Dict[str, dict]:
                # Compose a record aggregating all timeframes for a single team, using alias resolution
                payload: Dict[str, dict] = {"team_name": name}
                team_id_val: Optional[int] = None
                for h_key, tf in TIMEFRAMES.items():
                    stats_map = team_maps[h_key]
                    rec, _ = resolve_team_record(stats_map, name)
                    payload[tf] = rec
                    if rec and team_id_val is None:
                        team_id_val = rec.get("team_id")
                if team_id_val is not None:
                    payload["team_id"] = team_id_val
                return payload

            home_payload = pick(home_name)
            away_payload = pick(away_name)

            # Compute baselines per horizon once
            base_map = {h: baselines[h] for h in TIMEFRAMES.keys()}

            home_row = _build_row(game_date, "home", home_payload, away_payload, base_map)
            away_row = _build_row(game_date, "away", home_payload, away_payload, base_map)
            if home_row:
                rows_to_upsert.append(home_row)
            if away_row:
                rows_to_upsert.append(away_row)

        if not rows_to_upsert:
            return 0

        # Upsert rows (avoid nested transactions on an already-active Session)
        stmt = pg_insert(GameMatchup.__table__).values(rows_to_upsert)
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                GameMatchup.game_date_est,
                GameMatchup.team_name,
                GameMatchup.opp_team_name,
            ],
            set_={
                c.name: getattr(stmt.excluded, c.name)
                for c in GameMatchup.__table__.columns
                if c.name not in ("id", "created_at")
            },
        )
        result = session.execute(stmt)
        session.commit()
        inserted = getattr(result, "rowcount", 0) or 0
        return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute and upsert game matchup rows for a date.")
    parser.add_argument(
        "--date",
        default=None,
        help="Game date (EST) in YYYY-MM-DD. Defaults to today's date in America/New_York.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database URL. If omitted, uses DATABASE_URL env var.",
    )
    args = parser.parse_args()

    if args.date:
        game_date = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        # Use today's local date (system timezone) as EST date surrogate
        game_date = datetime.date.today()

    count = run(game_date, args.database_url)
    print(f"Upserted/updated {count} game_matchup rows for {game_date}")


if __name__ == "__main__":
    main()


