from sqlalchemy import Date, DateTime, Integer, String, UniqueConstraint, func, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class GameSchedule(Base):
    __tablename__ = "game_schedule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Local game date in EST (America/New_York), stored as a calendar date
    game_date_est: Mapped[object] = mapped_column(Date, nullable=False)
    away_team: Mapped[str] = mapped_column(String(64), nullable=False)
    home_team: Mapped[str] = mapped_column(String(64), nullable=False)

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "game_date_est", "away_team", "home_team", name="uq_game_schedule_date_teams"
        ),
    )



class TeamStats(Base):
    __tablename__ = "team_stats"
    __table_args__ = {"schema": "team_data"}

    # Composite primary key to uniquely identify a team's stats snapshot on a given date
    team_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    current_date: Mapped[object] = mapped_column(Date, primary_key=True, nullable=False)

    team_name: Mapped[str] = mapped_column(String(64), nullable=False)

    # Base counting and rate stats
    gp: Mapped[int] = mapped_column(Integer, nullable=True)
    w: Mapped[int] = mapped_column(Integer, nullable=True)
    l: Mapped[int] = mapped_column(Integer, nullable=True)
    min: Mapped[float] = mapped_column(Float, nullable=True)
    pts: Mapped[float] = mapped_column(Float, nullable=True)
    fgm: Mapped[float] = mapped_column(Float, nullable=True)
    fga: Mapped[float] = mapped_column(Float, nullable=True)
    fg_pct: Mapped[float] = mapped_column(Float, nullable=True)
    three_pm: Mapped[float] = mapped_column(Float, nullable=True)
    three_pa: Mapped[float] = mapped_column(Float, nullable=True)
    three_p_pct: Mapped[float] = mapped_column(Float, nullable=True)
    ftm: Mapped[float] = mapped_column(Float, nullable=True)
    fta: Mapped[float] = mapped_column(Float, nullable=True)
    ft_pct: Mapped[float] = mapped_column(Float, nullable=True)
    oreb: Mapped[float] = mapped_column(Float, nullable=True)
    dreb: Mapped[float] = mapped_column(Float, nullable=True)
    reb: Mapped[float] = mapped_column(Float, nullable=True)
    ast: Mapped[float] = mapped_column(Float, nullable=True)
    tov: Mapped[float] = mapped_column(Float, nullable=True)
    stl: Mapped[float] = mapped_column(Float, nullable=True)
    blk: Mapped[float] = mapped_column(Float, nullable=True)
    pf: Mapped[float] = mapped_column(Float, nullable=True)
    plus_minus: Mapped[float] = mapped_column(Float, nullable=True)

    # Advanced metrics
    offrtg: Mapped[float] = mapped_column(Float, nullable=True)
    defrtg: Mapped[float] = mapped_column(Float, nullable=True)
    netrtg: Mapped[float] = mapped_column(Float, nullable=True)
    ast_pct: Mapped[float] = mapped_column(Float, nullable=True)
    ast_to: Mapped[float] = mapped_column(Float, nullable=True)
    ast_ratio: Mapped[float] = mapped_column(Float, nullable=True)
    oreb_pct: Mapped[float] = mapped_column(Float, nullable=True)
    dreb_pct: Mapped[float] = mapped_column(Float, nullable=True)
    reb_pct: Mapped[float] = mapped_column(Float, nullable=True)
    tov_pct: Mapped[float] = mapped_column(Float, nullable=True)
    efg_pct: Mapped[float] = mapped_column(Float, nullable=True)
    ts_pct: Mapped[float] = mapped_column(Float, nullable=True)
    pace: Mapped[float] = mapped_column(Float, nullable=True)
    pie: Mapped[float] = mapped_column(Float, nullable=True)
    poss: Mapped[float] = mapped_column(Float, nullable=True)


class GameMatchup(Base):
    __tablename__ = "game_matchup"
    __table_args__ = {"schema": "analysis"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identity
    game_date_est: Mapped[object] = mapped_column(Date, nullable=False)
    team_name: Mapped[str] = mapped_column(String(64), nullable=False)
    opp_team_name: Mapped[str] = mapped_column(String(64), nullable=False)
    is_home: Mapped[bool] = mapped_column(Boolean, nullable=False)
    team_id: Mapped[int] = mapped_column(Integer, nullable=True)
    opp_team_id: Mapped[int] = mapped_column(Integer, nullable=True)

    # Pace & Possession - Season Long (sl)
    pace_sl: Mapped[float] = mapped_column(Float, nullable=True)
    opp_pace_sl: Mapped[float] = mapped_column(Float, nullable=True)
    lg_pace_sl: Mapped[float] = mapped_column(Float, nullable=True)
    poss_above_lg_sl: Mapped[float] = mapped_column(Float, nullable=True)
    implied_poss_sl: Mapped[float] = mapped_column(Float, nullable=True)

    # Efficiency - Season Long
    offrtg_sl: Mapped[float] = mapped_column(Float, nullable=True)
    defrtg_sl: Mapped[float] = mapped_column(Float, nullable=True)
    opp_offrtg_sl: Mapped[float] = mapped_column(Float, nullable=True)
    opp_defrtg_sl: Mapped[float] = mapped_column(Float, nullable=True)
    lg_pp100_sl: Mapped[float] = mapped_column(Float, nullable=True)

    # HCA adjustments - Season Long
    hca_poss_adj_sl: Mapped[float] = mapped_column(Float, nullable=True)
    hca_pp100_adj_sl: Mapped[float] = mapped_column(Float, nullable=True)

    # Outputs - Season Long
    exp_pp100_sl: Mapped[float] = mapped_column(Float, nullable=True)
    opp_exp_pp100_sl: Mapped[float] = mapped_column(Float, nullable=True)
    proj_pts_sl: Mapped[float] = mapped_column(Float, nullable=True)
    opp_proj_pts_sl: Mapped[float] = mapped_column(Float, nullable=True)
    proj_total_sl: Mapped[float] = mapped_column(Float, nullable=True)
    matchup_sl: Mapped[float] = mapped_column(Float, nullable=True)
    pts_allowed_pg_sl: Mapped[float] = mapped_column(Float, nullable=True)

    # Pace & Possession - Last 10 (l10)
    pace_l10: Mapped[float] = mapped_column(Float, nullable=True)
    opp_pace_l10: Mapped[float] = mapped_column(Float, nullable=True)
    lg_pace_l10: Mapped[float] = mapped_column(Float, nullable=True)
    poss_above_lg_l10: Mapped[float] = mapped_column(Float, nullable=True)
    implied_poss_l10: Mapped[float] = mapped_column(Float, nullable=True)

    # Efficiency - Last 10
    offrtg_l10: Mapped[float] = mapped_column(Float, nullable=True)
    defrtg_l10: Mapped[float] = mapped_column(Float, nullable=True)
    opp_offrtg_l10: Mapped[float] = mapped_column(Float, nullable=True)
    opp_defrtg_l10: Mapped[float] = mapped_column(Float, nullable=True)
    lg_pp100_l10: Mapped[float] = mapped_column(Float, nullable=True)

    # HCA adjustments - Last 10
    hca_poss_adj_l10: Mapped[float] = mapped_column(Float, nullable=True)
    hca_pp100_adj_l10: Mapped[float] = mapped_column(Float, nullable=True)

    # Outputs - Last 10
    exp_pp100_l10: Mapped[float] = mapped_column(Float, nullable=True)
    opp_exp_pp100_l10: Mapped[float] = mapped_column(Float, nullable=True)
    proj_pts_l10: Mapped[float] = mapped_column(Float, nullable=True)
    opp_proj_pts_l10: Mapped[float] = mapped_column(Float, nullable=True)
    proj_total_l10: Mapped[float] = mapped_column(Float, nullable=True)
    matchup_l10: Mapped[float] = mapped_column(Float, nullable=True)
    pts_allowed_pg_l10: Mapped[float] = mapped_column(Float, nullable=True)

    # Pace & Possession - Last 5 (l5)
    pace_l5: Mapped[float] = mapped_column(Float, nullable=True)
    opp_pace_l5: Mapped[float] = mapped_column(Float, nullable=True)
    lg_pace_l5: Mapped[float] = mapped_column(Float, nullable=True)
    poss_above_lg_l5: Mapped[float] = mapped_column(Float, nullable=True)
    implied_poss_l5: Mapped[float] = mapped_column(Float, nullable=True)

    # Efficiency - Last 5
    offrtg_l5: Mapped[float] = mapped_column(Float, nullable=True)
    defrtg_l5: Mapped[float] = mapped_column(Float, nullable=True)
    opp_offrtg_l5: Mapped[float] = mapped_column(Float, nullable=True)
    opp_defrtg_l5: Mapped[float] = mapped_column(Float, nullable=True)
    lg_pp100_l5: Mapped[float] = mapped_column(Float, nullable=True)

    # HCA adjustments - Last 5
    hca_poss_adj_l5: Mapped[float] = mapped_column(Float, nullable=True)
    hca_pp100_adj_l5: Mapped[float] = mapped_column(Float, nullable=True)

    # Outputs - Last 5
    exp_pp100_l5: Mapped[float] = mapped_column(Float, nullable=True)
    opp_exp_pp100_l5: Mapped[float] = mapped_column(Float, nullable=True)
    proj_pts_l5: Mapped[float] = mapped_column(Float, nullable=True)
    opp_proj_pts_l5: Mapped[float] = mapped_column(Float, nullable=True)
    proj_total_l5: Mapped[float] = mapped_column(Float, nullable=True)
    matchup_l5: Mapped[float] = mapped_column(Float, nullable=True)
    pts_allowed_pg_l5: Mapped[float] = mapped_column(Float, nullable=True)

    # Pace & Possession - Last 3 (l3)
    pace_l3: Mapped[float] = mapped_column(Float, nullable=True)
    opp_pace_l3: Mapped[float] = mapped_column(Float, nullable=True)
    lg_pace_l3: Mapped[float] = mapped_column(Float, nullable=True)
    poss_above_lg_l3: Mapped[float] = mapped_column(Float, nullable=True)
    implied_poss_l3: Mapped[float] = mapped_column(Float, nullable=True)

    # Efficiency - Last 3
    offrtg_l3: Mapped[float] = mapped_column(Float, nullable=True)
    defrtg_l3: Mapped[float] = mapped_column(Float, nullable=True)
    opp_offrtg_l3: Mapped[float] = mapped_column(Float, nullable=True)
    opp_defrtg_l3: Mapped[float] = mapped_column(Float, nullable=True)
    lg_pp100_l3: Mapped[float] = mapped_column(Float, nullable=True)

    # HCA adjustments - Last 3
    hca_poss_adj_l3: Mapped[float] = mapped_column(Float, nullable=True)
    hca_pp100_adj_l3: Mapped[float] = mapped_column(Float, nullable=True)

    # Outputs - Last 3
    exp_pp100_l3: Mapped[float] = mapped_column(Float, nullable=True)
    opp_exp_pp100_l3: Mapped[float] = mapped_column(Float, nullable=True)
    proj_pts_l3: Mapped[float] = mapped_column(Float, nullable=True)
    opp_proj_pts_l3: Mapped[float] = mapped_column(Float, nullable=True)
    proj_total_l3: Mapped[float] = mapped_column(Float, nullable=True)
    matchup_l3: Mapped[float] = mapped_column(Float, nullable=True)
    pts_allowed_pg_l3: Mapped[float] = mapped_column(Float, nullable=True)

    # Metadata
    calc_version: Mapped[str] = mapped_column(String(16), nullable=True)

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "game_date_est",
            "team_name",
            "opp_team_name",
            name="uq_game_matchup_date_teams",
        ),
        {"schema": "analysis"},
    )

class PlayerStatsBase(Base):
    __abstract__ = True
    __table_args__ = {"schema": "player_data"}

    # Composite primary key to uniquely identify a player's stats snapshot on a given date
    player_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    current_date: Mapped[object] = mapped_column(Date, primary_key=True, nullable=False)

    player: Mapped[str] = mapped_column(String(128), nullable=False)
    team: Mapped[str] = mapped_column(String(16), nullable=True)
    age: Mapped[int] = mapped_column(Integer, nullable=True)

    gp: Mapped[int] = mapped_column(Integer, nullable=True)
    w: Mapped[int] = mapped_column(Integer, nullable=True)
    l: Mapped[int] = mapped_column(Integer, nullable=True)
    min: Mapped[float] = mapped_column(Float, nullable=True)
    pts: Mapped[float] = mapped_column(Float, nullable=True)
    fgm: Mapped[float] = mapped_column(Float, nullable=True)
    fga: Mapped[float] = mapped_column(Float, nullable=True)
    fg_pct: Mapped[float] = mapped_column(Float, nullable=True)
    three_pm: Mapped[float] = mapped_column(Float, nullable=True)
    three_pa: Mapped[float] = mapped_column(Float, nullable=True)
    three_p_pct: Mapped[float] = mapped_column(Float, nullable=True)
    ftm: Mapped[float] = mapped_column(Float, nullable=True)
    fta: Mapped[float] = mapped_column(Float, nullable=True)
    ft_pct: Mapped[float] = mapped_column(Float, nullable=True)
    oreb: Mapped[float] = mapped_column(Float, nullable=True)
    dreb: Mapped[float] = mapped_column(Float, nullable=True)
    reb: Mapped[float] = mapped_column(Float, nullable=True)
    ast: Mapped[float] = mapped_column(Float, nullable=True)
    tov: Mapped[float] = mapped_column(Float, nullable=True)
    stl: Mapped[float] = mapped_column(Float, nullable=True)
    blk: Mapped[float] = mapped_column(Float, nullable=True)
    pf: Mapped[float] = mapped_column(Float, nullable=True)
    fp: Mapped[float] = mapped_column(Float, nullable=True)
    dd2: Mapped[int] = mapped_column(Integer, nullable=True)
    tdthree_: Mapped[int] = mapped_column(Integer, nullable=True)
    plus_minus: Mapped[float] = mapped_column(Float, nullable=True)

    offrtg: Mapped[float] = mapped_column(Float, nullable=True)
    defrtg: Mapped[float] = mapped_column(Float, nullable=True)
    netrtg: Mapped[float] = mapped_column(Float, nullable=True)
    ast_pct: Mapped[float] = mapped_column(Float, nullable=True)
    ast_to: Mapped[float] = mapped_column(Float, nullable=True)
    ast_ratio: Mapped[float] = mapped_column(Float, nullable=True)
    oreb_pct: Mapped[float] = mapped_column(Float, nullable=True)
    dreb_pct: Mapped[float] = mapped_column(Float, nullable=True)
    reb_pct: Mapped[float] = mapped_column(Float, nullable=True)
    tov_pct: Mapped[float] = mapped_column(Float, nullable=True)
    efg_pct: Mapped[float] = mapped_column(Float, nullable=True)
    ts_pct: Mapped[float] = mapped_column(Float, nullable=True)
    usg_pct: Mapped[float] = mapped_column(Float, nullable=True)
    pace: Mapped[float] = mapped_column(Float, nullable=True)
    pie: Mapped[float] = mapped_column(Float, nullable=True)
    poss: Mapped[float] = mapped_column(Float, nullable=True)

    touches: Mapped[float] = mapped_column(Float, nullable=True)
    front_ct_touches: Mapped[float] = mapped_column(Float, nullable=True)
    time_of_poss: Mapped[float] = mapped_column(Float, nullable=True)
    avg_sec_per_touch: Mapped[float] = mapped_column(Float, nullable=True)
    avg_drib_per_touch: Mapped[float] = mapped_column(Float, nullable=True)
    pts_per_touch: Mapped[float] = mapped_column(Float, nullable=True)
    elbow_touches: Mapped[float] = mapped_column(Float, nullable=True)
    post_ups: Mapped[float] = mapped_column(Float, nullable=True)
    paint_touches: Mapped[float] = mapped_column(Float, nullable=True)
    pts_per_elbow_touch: Mapped[float] = mapped_column(Float, nullable=True)
    pts_per_post_touch: Mapped[float] = mapped_column(Float, nullable=True)
    pts_per_paint_touch: Mapped[float] = mapped_column(Float, nullable=True)


class PlayerStatsSeasonLong(PlayerStatsBase):
    __tablename__ = "player_stats_season_long"


class PlayerStatsLast10(PlayerStatsBase):
    __tablename__ = "player_stats_last_10"


class PlayerStatsLast5(PlayerStatsBase):
    __tablename__ = "player_stats_last_5"


class PlayerStatsLast3(PlayerStatsBase):
    __tablename__ = "player_stats_last_3"


class PlayerProjection(Base):
    __tablename__ = "player_projection"
    __table_args__ = {"schema": "analysis"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identity
    game_date: Mapped[object] = mapped_column(Date, nullable=False)
    player: Mapped[str] = mapped_column(String(128), nullable=False)
    db_player: Mapped[str] = mapped_column(String(128), nullable=True)  # Matched database player name
    pos: Mapped[str] = mapped_column(String(16), nullable=True)
    team: Mapped[str] = mapped_column(String(16), nullable=False)  # Team abbreviation
    team_full_name: Mapped[str] = mapped_column(String(64), nullable=True)
    opp: Mapped[str] = mapped_column(String(16), nullable=False)  # Opponent abbreviation
    opp_full_name: Mapped[str] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=True)
    game_info: Mapped[str] = mapped_column(String(64), nullable=True)

    # Base Projections
    salary: Mapped[float] = mapped_column(Float, nullable=False)
    proj_mins: Mapped[float] = mapped_column(Float, nullable=False)
    ownership: Mapped[float] = mapped_column(Float, nullable=True)

    # Final Projections (KEY OUTPUTS)
    fp_proj: Mapped[float] = mapped_column(Float, nullable=True)
    projected_value: Mapped[float] = mapped_column(Float, nullable=True)

    # Team Aggregates
    team_salary: Mapped[float] = mapped_column(Float, nullable=True)
    salary_share: Mapped[float] = mapped_column(Float, nullable=True)
    team_ownership: Mapped[float] = mapped_column(Float, nullable=True)
    team_minutes: Mapped[float] = mapped_column(Float, nullable=True)
    minutes_avail: Mapped[float] = mapped_column(Float, nullable=True)

    # Season Long (sl) Metrics
    gp_sl: Mapped[float] = mapped_column(Float, nullable=True)
    usg_pct_sl: Mapped[float] = mapped_column(Float, nullable=True)
    fp_sl: Mapped[float] = mapped_column(Float, nullable=True)
    touches_sl: Mapped[float] = mapped_column(Float, nullable=True)
    min_sl: Mapped[float] = mapped_column(Float, nullable=True)
    poss_sl: Mapped[float] = mapped_column(Float, nullable=True)
    fppm_sl: Mapped[float] = mapped_column(Float, nullable=True)
    fppt_sl: Mapped[float] = mapped_column(Float, nullable=True)
    fppp_sl: Mapped[float] = mapped_column(Float, nullable=True)
    tpm_sl: Mapped[float] = mapped_column(Float, nullable=True)
    tpp_sl: Mapped[float] = mapped_column(Float, nullable=True)
    team_poss_sl: Mapped[float] = mapped_column(Float, nullable=True)
    poss_pct_sl: Mapped[float] = mapped_column(Float, nullable=True)
    implied_poss_sl: Mapped[float] = mapped_column(Float, nullable=True)
    touches_ip_sl: Mapped[float] = mapped_column(Float, nullable=True)
    touches_tpm_sl: Mapped[float] = mapped_column(Float, nullable=True)
    fp_proj_it_sl: Mapped[float] = mapped_column(Float, nullable=True)
    fp_proj_tpm_sl: Mapped[float] = mapped_column(Float, nullable=True)
    team_fp_sl: Mapped[float] = mapped_column(Float, nullable=True)
    fp_per_sl: Mapped[float] = mapped_column(Float, nullable=True)

    # Last 10 (l10) Metrics
    gp_l10: Mapped[float] = mapped_column(Float, nullable=True)
    usg_pct_l10: Mapped[float] = mapped_column(Float, nullable=True)
    fp_l10: Mapped[float] = mapped_column(Float, nullable=True)
    touches_l10: Mapped[float] = mapped_column(Float, nullable=True)
    min_l10: Mapped[float] = mapped_column(Float, nullable=True)
    poss_l10: Mapped[float] = mapped_column(Float, nullable=True)
    fppm_l10: Mapped[float] = mapped_column(Float, nullable=True)
    fppt_l10: Mapped[float] = mapped_column(Float, nullable=True)
    fppp_l10: Mapped[float] = mapped_column(Float, nullable=True)
    tpm_l10: Mapped[float] = mapped_column(Float, nullable=True)
    tpp_l10: Mapped[float] = mapped_column(Float, nullable=True)
    team_poss_l10: Mapped[float] = mapped_column(Float, nullable=True)
    poss_pct_l10: Mapped[float] = mapped_column(Float, nullable=True)
    implied_poss_l10: Mapped[float] = mapped_column(Float, nullable=True)
    touches_ip_l10: Mapped[float] = mapped_column(Float, nullable=True)
    touches_tpm_l10: Mapped[float] = mapped_column(Float, nullable=True)
    fp_proj_it_l10: Mapped[float] = mapped_column(Float, nullable=True)
    fp_proj_tpm_l10: Mapped[float] = mapped_column(Float, nullable=True)
    team_fp_l10: Mapped[float] = mapped_column(Float, nullable=True)
    fp_per_l10: Mapped[float] = mapped_column(Float, nullable=True)

    # Last 5 (l5) Metrics
    gp_l5: Mapped[float] = mapped_column(Float, nullable=True)
    usg_pct_l5: Mapped[float] = mapped_column(Float, nullable=True)
    fp_l5: Mapped[float] = mapped_column(Float, nullable=True)
    touches_l5: Mapped[float] = mapped_column(Float, nullable=True)
    min_l5: Mapped[float] = mapped_column(Float, nullable=True)
    poss_l5: Mapped[float] = mapped_column(Float, nullable=True)
    fppm_l5: Mapped[float] = mapped_column(Float, nullable=True)
    fppt_l5: Mapped[float] = mapped_column(Float, nullable=True)
    fppp_l5: Mapped[float] = mapped_column(Float, nullable=True)
    tpm_l5: Mapped[float] = mapped_column(Float, nullable=True)
    tpp_l5: Mapped[float] = mapped_column(Float, nullable=True)
    team_poss_l5: Mapped[float] = mapped_column(Float, nullable=True)
    poss_pct_l5: Mapped[float] = mapped_column(Float, nullable=True)
    implied_poss_l5: Mapped[float] = mapped_column(Float, nullable=True)
    touches_ip_l5: Mapped[float] = mapped_column(Float, nullable=True)
    touches_tpm_l5: Mapped[float] = mapped_column(Float, nullable=True)
    fp_proj_it_l5: Mapped[float] = mapped_column(Float, nullable=True)
    fp_proj_tpm_l5: Mapped[float] = mapped_column(Float, nullable=True)
    team_fp_l5: Mapped[float] = mapped_column(Float, nullable=True)
    fp_per_l5: Mapped[float] = mapped_column(Float, nullable=True)

    # Last 3 (l3) Metrics
    gp_l3: Mapped[float] = mapped_column(Float, nullable=True)
    usg_pct_l3: Mapped[float] = mapped_column(Float, nullable=True)
    fp_l3: Mapped[float] = mapped_column(Float, nullable=True)
    touches_l3: Mapped[float] = mapped_column(Float, nullable=True)
    min_l3: Mapped[float] = mapped_column(Float, nullable=True)
    poss_l3: Mapped[float] = mapped_column(Float, nullable=True)
    fppm_l3: Mapped[float] = mapped_column(Float, nullable=True)
    fppt_l3: Mapped[float] = mapped_column(Float, nullable=True)
    fppp_l3: Mapped[float] = mapped_column(Float, nullable=True)
    tpm_l3: Mapped[float] = mapped_column(Float, nullable=True)
    tpp_l3: Mapped[float] = mapped_column(Float, nullable=True)
    team_poss_l3: Mapped[float] = mapped_column(Float, nullable=True)
    poss_pct_l3: Mapped[float] = mapped_column(Float, nullable=True)
    implied_poss_l3: Mapped[float] = mapped_column(Float, nullable=True)
    touches_ip_l3: Mapped[float] = mapped_column(Float, nullable=True)
    touches_tpm_l3: Mapped[float] = mapped_column(Float, nullable=True)
    fp_proj_it_l3: Mapped[float] = mapped_column(Float, nullable=True)
    fp_proj_tpm_l3: Mapped[float] = mapped_column(Float, nullable=True)
    team_fp_l3: Mapped[float] = mapped_column(Float, nullable=True)
    fp_per_l3: Mapped[float] = mapped_column(Float, nullable=True)

    # Metadata
    calc_version: Mapped[str] = mapped_column(String(16), nullable=True)

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "game_date",
            "player",
            "team",
            name="uq_player_projection_date_player_team",
        ),
        {"schema": "analysis"},
    )
