from typing import Dict, List, Tuple, Optional
import pandas as pd

from sqlalchemy import text
from sqlalchemy.orm import Session


def _norm_name(name: str) -> str:
    return " ".join((name or "").strip().split()).lower()


def fetch_schedule_for_date(session: Session, game_date_est) -> List[dict]:
    """
    Return list of {game_date_est, home_team, away_team} for the date.
    """
    rows = session.execute(
        text(
            """
            select game_date_est, home_team, away_team
            from game_schedule
            where game_date_est = :d
            order by home_team, away_team
            """
        ),
        {"d": game_date_est},
    ).mappings().all()
    return [dict(r) for r in rows]


def load_team_stats_map(session: Session, timeframe: str) -> Dict[str, dict]:
    """
    Load team stats for a timeframe (season_long, last_10, last_5, last_3)
    from team_data.team_stats_{timeframe}.
    Returns map keyed by normalized team_name.
    """
    table = f"team_data.team_stats_{timeframe}"
    rows = session.execute(
        text(
            f"""
            select team_id, team_name, pace, offrtg, defrtg
            from {table}
            """
        )
    ).mappings().all()
    out: Dict[str, dict] = {}
    for r in rows:
        key = _norm_name(r["team_name"])
        out[key] = {
            "team_id": r["team_id"],
            "team_name": r["team_name"],
            "pace": r["pace"],
            "offrtg": r["offrtg"],
            "defrtg": r["defrtg"],
        }
    return out


def compute_league_baselines(session: Session, timeframe: str) -> Tuple[float, float]:
    """
    Return (lg_pace, lg_pp100) for timeframe from team_data.team_stats_{timeframe}.
    lg_pp100 is the league average offensive rating.
    """
    table = f"team_data.team_stats_{timeframe}"
    row = session.execute(
        text(
            f"""
            select avg(pace) as lg_pace, avg(offrtg) as lg_pp100
            from {table}
            """
        )
    ).mappings().one()
    return float(row["lg_pace"] or 0.0), float(row["lg_pp100"] or 0.0)


# --- Team alias resolution helpers ---

# Map normalized schedule keys to a set of variant normalized keys we should try
_ALIAS_VARIANTS: Dict[str, List[str]] = {
    # Los Angeles variants
    "los angeles clippers": ["la clippers", "los angeles clippers", "lac clippers", "los angeles clipper", "la clipper"],
    "la clippers": ["la clippers", "los angeles clippers"],
    "los angeles lakers": ["la lakers", "los angeles lakers", "lal lakers", "los angeles laker", "la laker"],
    "la lakers": ["la lakers", "los angeles lakers"],
    # New York / Brooklyn
    "new york knicks": ["ny knicks", "new york knicks", "n.y. knicks"],
    "brooklyn nets": ["bk nets", "ny nets", "brooklyn nets", "brooklyn net"],
    # Bay Area
    "golden state warriors": ["golden st warriors", "gs warriors", "gsw warriors", "golden state warriors", "golden state warrior"],
    # New Orleans
    "new orleans pelicans": ["no pelicans", "nola pelicans", "new orleans pelicans", "new orleans pelican"],
    # Oklahoma City
    "oklahoma city thunder": ["okc thunder", "oklahoma city thunder", "okc thunders"],
    # Portland
    "portland trail blazers": ["portland trailblazers", "portland blazers", "portland trail blazers", "portland trailblazer"],
    # San Antonio
    "san antonio spurs": ["sa spurs", "san antonio spurs", "s.a. spurs"],
    # Sacramento
    "sacramento kings": ["sac kings", "sacramento kings"],
    # Dallas
    "dallas mavericks": ["dallas mavs", "dal mavericks", "dallas mavericks"],
    # Philadelphia
    "philadelphia 76ers": ["philadelphia sixers", "phila 76ers", "philly 76ers", "76ers", "philadelphia 76ers"],
    # Minnesota
    "minnesota timberwolves": ["minnesota t-wolves", "minnesota wolves", "minnesota timberwolves"],
    # Cleveland
    "cleveland cavaliers": ["cleveland cavs", "cleveland cavaliers"],
    # Abbrev city variants (light)
    "atlanta hawks": ["atl hawks", "atlanta hawks"],
    "boston celtics": ["bos celtics", "boston celtics"],
    "charlotte hornets": ["cha hornets", "charlotte hornets"],
    "chicago bulls": ["chi bulls", "chicago bulls"],
    "denver nuggets": ["den nuggets", "denver nuggets"],
    "detroit pistons": ["det pistons", "detroit pistons"],
    "houston rockets": ["hou rockets", "houston rockets"],
    "indiana pacers": ["ind pacers", "indiana pacers"],
    "memphis grizzlies": ["mem grizzlies", "memphis grizzlies"],
    "miami heat": ["mia heat", "miami heat"],
    "milwaukee bucks": ["mil bucks", "milwaukee bucks"],
    "orlando magic": ["orl magic", "orlando magic"],
    "phoenix suns": ["phx suns", "phoenix suns"],
    "toronto raptors": ["tor raptors", "toronto raptors"],
    "utah jazz": ["uta jazz", "utah jazz"],
    "washington wizards": ["wsh wizards", "washington wizards"],
}


def _candidate_keys_for(name_norm: str) -> List[str]:
    # return variants we should test for this name
    if name_norm in _ALIAS_VARIANTS:
        return list(dict.fromkeys([_norm_name(v) for v in _ALIAS_VARIANTS[name_norm]]))
    # generic substitutions
    tokens = name_norm.split()
    out: List[str] = [name_norm]
    sub_map = {
        "los angeles": ["la", "los angeles"],
        "new york": ["ny", "new york"],
        "san antonio": ["sa", "san antonio"],
        "golden state": ["gs", "golden st", "golden state"],
        "new orleans": ["no", "nola", "new orleans"],
        "oklahoma city": ["okc", "oklahoma city"],
    }
    for phrase, variants in sub_map.items():
        if phrase in name_norm:
            for v in variants:
                out.append(name_norm.replace(phrase, v))
    # de-dup and normalize
    return list(dict.fromkeys([_norm_name(v) for v in out]))


def resolve_team_record(stats_map: Dict[str, dict], schedule_name: str) -> Tuple[Optional[dict], Optional[str]]:
    """
    Try to resolve a schedule team name to a record in stats_map.
    Returns (record, matched_key). If not found, returns (None, None).
    """
    norm = _norm_name(schedule_name)
    if norm in stats_map:
        return stats_map[norm], norm

    # Try alias variants
    for cand in _candidate_keys_for(norm):
        if cand in stats_map:
            return stats_map[cand], cand

    # Fallback: nickname token match (last token) if unique
    parts = norm.split()
    if parts:
        nickname = parts[-1]
        candidates = [k for k in stats_map.keys() if nickname in k.split()]
        if len(candidates) == 1:
            k = candidates[0]
            return stats_map[k], k

    return None, None


def load_player_stats_dataframe(session: Session, timeframe: str) -> pd.DataFrame:
    """
    Load player stats for a timeframe (season_long, last_10, last_5, last_3)
    from player_data.player_stats_{timeframe}.
    
    Returns a DataFrame with all player stats.
    """
    table = f"player_data.player_stats_{timeframe}"
    
    query = f"""
        SELECT 
            player_id,
            player,
            team,
            age,
            gp,
            w,
            l,
            min,
            pts,
            fgm,
            fga,
            fg_pct,
            three_pm,
            three_pa,
            three_p_pct,
            ftm,
            fta,
            ft_pct,
            oreb,
            dreb,
            reb,
            ast,
            tov,
            stl,
            blk,
            pf,
            fp,
            dd2,
            tdthree_,
            plus_minus,
            offrtg,
            defrtg,
            netrtg,
            ast_pct,
            ast_to,
            ast_ratio,
            oreb_pct,
            dreb_pct,
            reb_pct,
            tov_pct,
            efg_pct,
            ts_pct,
            usg_pct,
            pace,
            pie,
            poss,
            touches,
            front_ct_touches,
            time_of_poss,
            avg_sec_per_touch,
            avg_drib_per_touch,
            pts_per_touch,
            elbow_touches,
            post_ups,
            paint_touches,
            pts_per_elbow_touch,
            pts_per_post_touch,
            pts_per_paint_touch
        FROM {table}
    """
    
    df = pd.read_sql(text(query), session.connection())
    return df


def load_team_stats_dataframe(session: Session, timeframe: str) -> pd.DataFrame:
    """
    Load team stats for a timeframe (season_long, last_10, last_5, last_3)
    from team_data.team_stats_{timeframe}.
    
    Returns a DataFrame with all team stats.
    """
    table = f"team_data.team_stats_{timeframe}"
    
    query = f"""
        SELECT 
            team_id,
            team_name,
            gp,
            w,
            l,
            min,
            pts,
            fgm,
            fga,
            fg_pct,
            three_pm,
            three_pa,
            three_p_pct,
            ftm,
            fta,
            ft_pct,
            oreb,
            dreb,
            reb,
            ast,
            tov,
            stl,
            blk,
            pf,
            plus_minus,
            offrtg,
            defrtg,
            netrtg,
            ast_pct,
            ast_to,
            ast_ratio,
            oreb_pct,
            dreb_pct,
            reb_pct,
            tov_pct,
            efg_pct,
            ts_pct,
            pace,
            pie,
            poss
        FROM {table}
    """
    
    df = pd.read_sql(text(query), session.connection())
    return df


def load_game_matchup_dataframe(session: Session, game_date_est) -> pd.DataFrame:
    """
    Load game matchup data for a specific date from analysis.game_matchup.
    
    Returns a DataFrame with matchup data for all teams on the specified date.
    """
    query = """
        SELECT 
            game_date_est,
            team_name,
            opp_team_name,
            is_home,
            team_id,
            opp_team_id,
            pace_sl, opp_pace_sl, lg_pace_sl, poss_above_lg_sl, implied_poss_sl,
            offrtg_sl, defrtg_sl, opp_offrtg_sl, opp_defrtg_sl, lg_pp100_sl,
            hca_poss_adj_sl, hca_pp100_adj_sl,
            exp_pp100_sl, opp_exp_pp100_sl, proj_pts_sl, opp_proj_pts_sl,
            proj_total_sl, matchup_sl, pts_allowed_pg_sl,
            pace_l10, opp_pace_l10, lg_pace_l10, poss_above_lg_l10, implied_poss_l10,
            offrtg_l10, defrtg_l10, opp_offrtg_l10, opp_defrtg_l10, lg_pp100_l10,
            hca_poss_adj_l10, hca_pp100_adj_l10,
            exp_pp100_l10, opp_exp_pp100_l10, proj_pts_l10, opp_proj_pts_l10,
            proj_total_l10, matchup_l10, pts_allowed_pg_l10,
            pace_l5, opp_pace_l5, lg_pace_l5, poss_above_lg_l5, implied_poss_l5,
            offrtg_l5, defrtg_l5, opp_offrtg_l5, opp_defrtg_l5, lg_pp100_l5,
            hca_poss_adj_l5, hca_pp100_adj_l5,
            exp_pp100_l5, opp_exp_pp100_l5, proj_pts_l5, opp_proj_pts_l5,
            proj_total_l5, matchup_l5, pts_allowed_pg_l5,
            pace_l3, opp_pace_l3, lg_pace_l3, poss_above_lg_l3, implied_poss_l3,
            offrtg_l3, defrtg_l3, opp_offrtg_l3, opp_defrtg_l3, lg_pp100_l3,
            hca_poss_adj_l3, hca_pp100_adj_l3,
            exp_pp100_l3, opp_exp_pp100_l3, proj_pts_l3, opp_proj_pts_l3,
            proj_total_l3, matchup_l3, pts_allowed_pg_l3,
            calc_version
        FROM analysis.game_matchup
        WHERE game_date_est = :d
    """
    
    df = pd.read_sql(text(query), session.connection(), params={"d": game_date_est})
    return df


