"""
Player Projections System

This module builds comprehensive player fantasy projections by:
1. Loading daily projections CSV with baseline data
2. Extracting historical player stats across multiple time periods
3. Extracting team stats for context
4. Computing advanced metrics and rate-based stats
5. Generating final weighted projections
"""
import argparse
import datetime
from pathlib import Path
from typing import Dict, Optional
import sys

import pandas as pd
import numpy as np

# Handle imports for both direct and module execution
try:
    from db.database import get_engine, get_session_maker
    from db.db_extract import (
        load_player_stats_dataframe,
        load_team_stats_dataframe,
        load_game_matchup_dataframe,
    )
    from analysis.utils import DataUtils, NameMatcher
except ImportError:
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from db.database import get_engine, get_session_maker  # type: ignore
    from db.db_extract import (  # type: ignore
        load_player_stats_dataframe,
        load_team_stats_dataframe,
        load_game_matchup_dataframe,
    )
    from analysis.utils import DataUtils, NameMatcher  # type: ignore


# Time periods for analysis
PERIODS = ['sl', 'l10', 'l5', 'l3']
PERIOD_NAMES = {
    'sl': 'season_long',
    'l10': 'last_10',
    'l5': 'last_5',
    'l3': 'last_3',
}

# Team abbreviation to full name mapping
TEAM_ABB_TO_FULL = {
    'ATL': 'Atlanta Hawks',
    'BOS': 'Boston Celtics',
    'BKN': 'Brooklyn Nets',
    'CHA': 'Charlotte Hornets',
    'CHI': 'Chicago Bulls',
    'CLE': 'Cleveland Cavaliers',
    'DAL': 'Dallas Mavericks',
    'DEN': 'Denver Nuggets',
    'DET': 'Detroit Pistons',
    'GS': 'Golden State Warriors',
    'GSW': 'Golden State Warriors',
    'HOU': 'Houston Rockets',
    'IND': 'Indiana Pacers',
    'LAC': 'LA Clippers',
    'LAL': 'Los Angeles Lakers',
    'MEM': 'Memphis Grizzlies',
    'MIA': 'Miami Heat',
    'MIL': 'Milwaukee Bucks',
    'MIN': 'Minnesota Timberwolves',
    'NO': 'New Orleans Pelicans',
    'NOP': 'New Orleans Pelicans',
    'NY': 'New York Knicks',
    'NYK': 'New York Knicks',
    'OKC': 'Oklahoma City Thunder',
    'ORL': 'Orlando Magic',
    'PHI': 'Philadelphia 76ers',
    'PHO': 'Phoenix Suns',
    'PHX': 'Phoenix Suns',
    'POR': 'Portland Trail Blazers',
    'SA': 'San Antonio Spurs',
    'SAS': 'San Antonio Spurs',
    'SAC': 'Sacramento Kings',
    'TOR': 'Toronto Raptors',
    'UTA': 'Utah Jazz',
    'WAS': 'Washington Wizards',
}

# Base stats to extract from player data
BASE_STATS = ['gp', 'usg_pct', 'fp', 'touches', 'min', 'poss']

# Projection method weights (higher = more importance)
# TPM = Touches Per Minute method
# IT = Implied Touches method
TPM_WEIGHTS = {
    'sl': 1,
    'l10': 4,
    'l5': 8,  # Highest weight - most recent form
    'l3': 4,
}

IT_WEIGHTS = {
    'sl': 1,
    'l10': 3,
    'l5': 6,
    'l3': 3,
}


def load_daily_projections(csv_path: Path) -> pd.DataFrame:
    """
    Load the daily projections CSV and extract relevant columns.
    
    Returns DataFrame with columns:
    - player (renamed from Name)
    - pos
    - team
    - opp
    - salary
    - proj_mins (renamed from Min)
    - ownership (renamed from Adj Own)
    - status
    - game_info (renamed from gameInfo)
    """
    df = pd.read_csv(csv_path)
    
    # Extract and rename relevant columns
    columns_map = {
        'Name': 'player',
        'Pos': 'pos',
        'Team': 'team',
        'Opp': 'opp',
        'Salary': 'salary',
        'Min': 'proj_mins',
        'Adj Own': 'ownership',
        'Status': 'status',
    }
    
    # Check for gameInfo column (might be case-sensitive)
    game_info_col = None
    for col in df.columns:
        if col.lower() == 'gameinfo':
            game_info_col = col
            break
    
    if game_info_col:
        columns_map[game_info_col] = 'game_info'
    
    # Select and rename columns
    available_cols = {k: v for k, v in columns_map.items() if k in df.columns}
    df = df[list(available_cols.keys())].copy()
    df = df.rename(columns=available_cols)
    
    # Clean data
    df['player'] = df['player'].str.strip()
    df['salary'] = pd.to_numeric(df['salary'], errors='coerce')
    df['proj_mins'] = pd.to_numeric(df['proj_mins'], errors='coerce')
    df['ownership'] = pd.to_numeric(df['ownership'], errors='coerce')
    
    # Fill missing values
    df['status'] = df['status'].fillna('')
    if 'game_info' not in df.columns:
        df['game_info'] = ''
    
    # Filter out players without salary info
    initial_count = len(df)
    df = df[df['salary'].notna()].copy()
    no_salary_count = initial_count - len(df)
    if no_salary_count > 0:
        print(f"Filtered {no_salary_count} players with no salary info")
    
    # Filter out players with less than 15 projected minutes
    before_mins_filter = len(df)
    df = df[df['proj_mins'] >= 15].copy()
    low_mins_count = before_mins_filter - len(df)
    if low_mins_count > 0:
        print(f"Filtered {low_mins_count} players with < 15 projected minutes")
    
    # Map team abbreviations to full names for database lookups
    df['team_full_name'] = df['team'].map(TEAM_ABB_TO_FULL)
    df['opp_full_name'] = df['opp'].map(TEAM_ABB_TO_FULL)
    
    # Warn about unmapped teams
    unmapped_teams = df[df['team_full_name'].isna()]['team'].unique()
    if len(unmapped_teams) > 0:
        print(f"Warning: Unmapped team abbreviations: {list(unmapped_teams)}")
    
    unmapped_opps = df[df['opp_full_name'].isna()]['opp'].unique()
    if len(unmapped_opps) > 0:
        print(f"Warning: Unmapped opponent abbreviations: {list(unmapped_opps)}")
    
    return df


def load_all_player_stats(session) -> Dict[str, pd.DataFrame]:
    """
    Load player stats for all time periods.
    
    Returns dict mapping period keys (sl, l10, l5, l3) to DataFrames.
    """
    player_dfs = {}
    
    for period_key, period_name in PERIOD_NAMES.items():
        df = load_player_stats_dataframe(session, period_name)
        player_dfs[period_key] = df
    
    return player_dfs


def load_all_team_stats(session) -> Dict[str, pd.DataFrame]:
    """
    Load team stats for all time periods.
    
    Returns dict mapping period keys (sl, l10, l5, l3) to DataFrames.
    """
    team_dfs = {}
    
    for period_key, period_name in PERIOD_NAMES.items():
        df = load_team_stats_dataframe(session, period_name)
        team_dfs[period_key] = df
    
    return team_dfs


def build_name_mapping(df: pd.DataFrame, player_dfs: Dict[str, pd.DataFrame]) -> Dict[str, str]:
    """
    Build a mapping from daily projection names to database player names
    using fuzzy matching.
    
    Args:
        df: Daily projections DataFrame
        player_dfs: Dict of player stats DataFrames
        
    Returns:
        Dict mapping projection names to database names
    """
    # Get all unique player names from database (use season long as reference)
    db_players = player_dfs['sl']['player'].unique().tolist()
    
    # Get names from daily projections
    proj_players = df['player'].unique().tolist()
    
    # Build mapping using fuzzy matching
    name_map = NameMatcher.build_name_map(proj_players, db_players, threshold=0.80)
    
    # Report unmapped names
    unmapped = [p for p in proj_players if p not in name_map]
    if unmapped:
        print(f"Warning: {len(unmapped)} players could not be matched to database:")
        for name in unmapped[:10]:  # Show first 10
            print(f"  - {name}")
        if len(unmapped) > 10:
            print(f"  ... and {len(unmapped) - 10} more")
    
    return name_map


def merge_player_stats(df: pd.DataFrame, player_dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Merge historical player stats for all periods into the main DataFrame.
    
    Creates columns like: usg_pct_sl, usg_pct_l10, fp_l5, touches_l3, etc.
    """
    # Build name mapping
    name_map = build_name_mapping(df, player_dfs)
    
    # Map names in the daily projections to database names
    df['db_player'] = df['player'].map(name_map)
    
    # For each period and stat, lookup values
    for period in PERIODS:
        player_df = player_dfs[period]
        
        for stat in BASE_STATS:
            col_name = f"{stat}_{period}"
            
            # For each row in df, lookup the stat value
            df[col_name] = df['db_player'].apply(
                lambda x: DataUtils.xlookup(
                    x,
                    player_df['player'],
                    player_df[stat],
                    if_not_found=0.0
                ) if pd.notna(x) else 0.0
            )
    
    return df


def handle_missing_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle players with missing recent data by copying from longer periods.
    
    If a player's l3 stats are all zero, copy from l5.
    If l5 is also zero, copy from l10, etc.
    Drop players with all zeros across all periods.
    """
    # Work backwards from shortest to longest period
    periods_reverse = ['l3', 'l5', 'l10', 'sl']
    
    for i, period in enumerate(periods_reverse[:-1]):
        next_period = periods_reverse[i + 1]
        
        # Check if all base stats for this period are zero
        period_cols = [f"{stat}_{period}" for stat in BASE_STATS]
        all_zero = (df[period_cols] == 0).all(axis=1)
        
        # Copy from next period for rows with all zeros
        next_period_cols = [f"{stat}_{next_period}" for stat in BASE_STATS]
        for period_col, next_col in zip(period_cols, next_period_cols):
            df.loc[all_zero, period_col] = df.loc[all_zero, next_col]
    
    # Drop players where all periods are still zero
    all_period_cols = [f"{stat}_{period}" for period in PERIODS for stat in BASE_STATS]
    all_zero_mask = (df[all_period_cols] == 0).all(axis=1)
    
    if all_zero_mask.any():
        dropped_count = all_zero_mask.sum()
        print(f"Dropping {dropped_count} players with no historical data")
        df = df[~all_zero_mask].copy()
    
    return df


def calculate_rate_stats(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """
    Calculate rate-based statistics for a specific period.
    
    Adds columns:
    - fppm_{period}: Fantasy Points Per Minute
    - fppt_{period}: Fantasy Points Per Touch
    - fppp_{period}: Fantasy Points Per Possession
    - tpm_{period}: Touches Per Minute
    - tpp_{period}: Touches Per Possession
    """
    # Fantasy Points Per Minute
    df[f'fppm_{period}'] = df.apply(
        lambda row: DataUtils.safe_divide(
            row[f'fp_{period}'],
            row[f'min_{period}']
        ),
        axis=1
    )
    
    # Fantasy Points Per Touch
    df[f'fppt_{period}'] = df.apply(
        lambda row: DataUtils.safe_divide(
            row[f'fp_{period}'],
            row[f'touches_{period}']
        ),
        axis=1
    )
    
    # Fantasy Points Per Possession (per game possession)
    df[f'fppp_{period}'] = df.apply(
        lambda row: DataUtils.safe_divide(
            row[f'fp_{period}'],
            DataUtils.safe_divide(row[f'poss_{period}'], row[f'gp_{period}'], 1.0)
        ),
        axis=1
    )
    
    # Touches Per Minute
    df[f'tpm_{period}'] = df.apply(
        lambda row: DataUtils.safe_divide(
            row[f'touches_{period}'],
            row[f'min_{period}']
        ),
        axis=1
    )
    
    # Touches Per Possession (per game possession)
    df[f'tpp_{period}'] = df.apply(
        lambda row: DataUtils.safe_divide(
            row[f'touches_{period}'],
            DataUtils.safe_divide(row[f'poss_{period}'], row[f'gp_{period}'], 1.0)
        ),
        axis=1
    )
    
    return df


def calculate_team_context(
    df: pd.DataFrame, 
    team_dfs: Dict[str, pd.DataFrame],
    period: str
) -> pd.DataFrame:
    """
    Calculate team-level context statistics for a period.
    
    Adds columns:
    - poss_pct_{period}: Player's possession percentage of team
    """
    team_df = team_dfs[period]
    
    # Get team possessions for each player using full team name
    df[f'team_poss_{period}'] = df['team_full_name'].apply(
        lambda x: DataUtils.xlookup(
            x,
            team_df['team_name'],
            team_df['poss'],
            if_not_found=0.0
        ) if pd.notna(x) else 0.0
    )
    
    # Calculate possession percentage (player's share of team possessions)
    df[f'poss_pct_{period}'] = df.apply(
        lambda row: DataUtils.safe_divide(
            row[f'poss_{period}'],
            row[f'team_poss_{period}']
        ) * 100.0,
        axis=1
    )
    
    return df


def calculate_touch_projections(
    df: pd.DataFrame,
    matchup_df: pd.DataFrame,
    period: str
) -> pd.DataFrame:
    """
    Calculate implied touch projections using two methods.
    
    Adds columns:
    - touches_ip_{period}: Implied Touches from Implied Possessions
    - touches_tpm_{period}: Implied Touches from Touches Per Minute
    """
    # Merge matchup data for implied possessions
    # Match on team name to get the implied_poss for this period
    matchup_col = f'implied_poss_{period}'
    
    if matchup_col in matchup_df.columns:
        # Create a lookup for team -> implied_poss using full team name
        team_to_poss = matchup_df.set_index('team_name')[matchup_col].to_dict()
        
        df[f'implied_poss_{period}'] = df['team_full_name'].map(team_to_poss).fillna(0.0)
    else:
        df[f'implied_poss_{period}'] = 0.0
    
    # Method 1: Implied Touches from Implied Possessions
    # touches_ip = (poss_pct / 100) * tpp * implied_poss
    df[f'touches_ip_{period}'] = (
        (df[f'poss_pct_{period}'] / 100.0) * 
        df[f'tpp_{period}'] * 
        df[f'implied_poss_{period}']
    )
    
    # Method 2: Implied Touches from Touches Per Minute
    # touches_tpm = tpm * proj_mins
    df[f'touches_tpm_{period}'] = (
        df[f'tpm_{period}'] * 
        df['proj_mins']
    )
    
    return df


def calculate_fantasy_projections(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """
    Calculate fantasy point projections using both methods.
    
    Adds columns:
    - fp_proj_it_{period}: Fantasy Points from Implied Touches method
    - fp_proj_tpm_{period}: Fantasy Points from Touches Per Minute method
    """
    # Method 1: FP from Implied Touches
    df[f'fp_proj_it_{period}'] = (
        df[f'fppt_{period}'] * df[f'touches_ip_{period}']
    )
    
    # Method 2: FP from Touches Per Minute
    df[f'fp_proj_tpm_{period}'] = (
        df[f'fppt_{period}'] * df[f'touches_tpm_{period}']
    )
    
    return df


def calculate_team_fantasy_context(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """
    Calculate team-level fantasy point aggregations.
    
    Adds columns:
    - team_fp_{period}: Total team fantasy points
    - fp_per_{period}: Player's fantasy point percentage of team
    """
    # Calculate team total fantasy points for historical period
    df[f'team_fp_{period}'] = df.apply(
        lambda row: DataUtils.sumif(
            df['team'],
            row['team'],
            df[f'fp_{period}']
        ),
        axis=1
    )
    
    # Calculate player's percentage of team fantasy points
    df[f'fp_per_{period}'] = df.apply(
        lambda row: DataUtils.safe_divide(
            row[f'fp_{period}'],
            row[f'team_fp_{period}']
        ) * 100.0,
        axis=1
    )
    
    return df


def calculate_team_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate team-level aggregates from today's projections.
    
    Adds columns:
    - team_salary: Total team salary
    - salary_share: Player's % of team salary
    - team_ownership: Total team ownership
    - team_minutes: Total projected minutes for team
    - minutes_avail: Available minutes (240 - team_minutes)
    """
    # Team salary
    df['team_salary'] = df.apply(
        lambda row: DataUtils.sumif(
            df['team'],
            row['team'],
            df['salary']
        ),
        axis=1
    )
    
    # Salary share
    df['salary_share'] = df.apply(
        lambda row: DataUtils.safe_divide(
            row['salary'],
            row['team_salary']
        ) * 100.0,
        axis=1
    )
    
    # Team ownership
    df['team_ownership'] = df.apply(
        lambda row: DataUtils.sumif(
            df['team'],
            row['team'],
            df['ownership']
        ),
        axis=1
    )
    
    # Team minutes
    df['team_minutes'] = df.apply(
        lambda row: DataUtils.sumif(
            df['team'],
            row['team'],
            df['proj_mins']
        ),
        axis=1
    )
    
    # Available minutes (regulation game = 240 minutes total)
    df['minutes_avail'] = 240.0 - df['team_minutes']
    
    return df


def calculate_final_projection(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate the final weighted fantasy point projection.
    
    Combines all 8 projection methods (4 periods × 2 methods) using weights.
    
    Adds columns:
    - fp_proj: Final weighted fantasy point projection
    - projected_value: Points per $1000 of salary
    """
    # Collect all projection columns
    proj_cols = []
    weights = []
    
    for period in PERIODS:
        # IT method
        proj_cols.append(f'fp_proj_it_{period}')
        weights.append(IT_WEIGHTS[period])
        
        # TPM method
        proj_cols.append(f'fp_proj_tpm_{period}')
        weights.append(TPM_WEIGHTS[period])
    
    # Calculate weighted average
    total_weight = sum(weights)
    
    df['fp_proj'] = 0.0
    for col, weight in zip(proj_cols, weights):
        df['fp_proj'] += (df[col] * weight) / total_weight
    
    # Calculate value (points per $1000)
    df['projected_value'] = df.apply(
        lambda row: DataUtils.safe_divide(
            row['fp_proj'],
            row['salary'] / 1000.0
        ),
        axis=1
    )
    
    return df


def build_projections(
    daily_proj_path: Path,
    game_date: datetime.date,
    database_url: Optional[str] = None,
    save_to_db: bool = False
) -> pd.DataFrame:
    """
    Main function to build player projections.
    
    Args:
        daily_proj_path: Path to daily_proj.csv file
        game_date: Date for the projections (for matchup data)
        database_url: Optional database URL
        save_to_db: Whether to save projections to database (default: False)
        
    Returns:
        DataFrame with complete projections
    """
    print(f"Building player projections for {game_date}")
    
    # Load daily projections
    print("Loading daily projections CSV...")
    df = load_daily_projections(daily_proj_path)
    print(f"Loaded {len(df)} players")
    
    # Add game date column
    df['game_date'] = game_date
    
    # Connect to database
    engine = get_engine(database_url)
    SessionLocal = get_session_maker(engine)
    
    with SessionLocal() as session:
        # Load historical data
        print("Loading player stats from database...")
        player_dfs = load_all_player_stats(session)
        
        print("Loading team stats from database...")
        team_dfs = load_all_team_stats(session)
        
        print("Loading game matchup data...")
        matchup_df = load_game_matchup_dataframe(session, game_date)
        
        if matchup_df.empty:
            print(f"Warning: No matchup data found for {game_date}")
            print("Run game_matchup.py first to generate matchup data")
    
    # Merge player stats
    print("Merging player historical stats...")
    df = merge_player_stats(df, player_dfs)
    
    # Handle missing data
    print("Handling missing data...")
    df = handle_missing_data(df)
    
    # Calculate metrics for each period
    for period in PERIODS:
        print(f"Calculating metrics for {period}...")
        
        # Rate stats
        df = calculate_rate_stats(df, period)
        
        # Team context
        df = calculate_team_context(df, team_dfs, period)
        
        # Touch projections
        df = calculate_touch_projections(df, matchup_df, period)
        
        # Fantasy projections
        df = calculate_fantasy_projections(df, period)
        
        # Team fantasy context
        df = calculate_team_fantasy_context(df, period)
    
    # Calculate team aggregates
    print("Calculating team aggregates...")
    df = calculate_team_aggregates(df)
    
    # Calculate final projection
    print("Calculating final weighted projections...")
    df = calculate_final_projection(df)
    
    print("Projections complete!")
    
    # Save to database if requested
    if save_to_db:
        print("Saving projections to database...")
        try:
            from db.db_insert.ingest_player_projections_to_db import upsert_projections
            count = upsert_projections(df, database_url)
            print(f"Saved {count} projections to database")
        except Exception as e:
            print(f"Error saving to database: {e}")
            print("Continuing with CSV export...")
    
    return df


def save_projections(df: pd.DataFrame, output_path: Path) -> None:
    """Save projections to CSV file."""
    # Save all columns for inspection
    output_df = df.copy()
    
    # Sort by projected fantasy points descending
    output_df = output_df.sort_values('fp_proj', ascending=False)
    
    # Reorder columns to put key columns first
    key_cols = ['game_date', 'player', 'pos', 'team', 'opp', 'salary', 'proj_mins', 
                'ownership', 'fp_proj', 'projected_value']
    other_cols = [col for col in output_df.columns if col not in key_cols]
    output_df = output_df[key_cols + other_cols]
    
    # Save with all columns
    output_df.to_csv(output_path, index=False, float_format='%.2f')
    print(f"Saved projections to {output_path}")
    print(f"Columns: {len(output_df.columns)}")
    print(f"Players: {len(output_df)}")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Build NBA player fantasy projections"
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Game date in YYYY-MM-DD format (default: today)",
    )
    parser.add_argument(
        "--csv",
        default=None,
        help="Path to daily_proj.csv (default: analysis/daily_player_intake/daily_proj.csv)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path for projections CSV (default: analysis/daily_player_intake/player_projections_{date}.csv)",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database URL (default: from DATABASE_URL env var)",
    )
    parser.add_argument(
        "--save-to-db",
        action="store_true",
        help="Save projections to database (default: False)",
    )
    
    args = parser.parse_args()
    
    # Determine date
    if args.date:
        game_date = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        game_date = datetime.date.today()
    
    # Determine CSV path
    if args.csv:
        csv_path = Path(args.csv)
    else:
        # Default path
        script_dir = Path(__file__).parent
        csv_path = script_dir / "daily_player_intake" / "daily_proj.csv"
    
    if not csv_path.exists():
        print(f"Error: CSV file not found at {csv_path}")
        sys.exit(1)
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        script_dir = Path(__file__).parent
        output_path = script_dir / "daily_player_intake" / f"player_projections_{game_date}.csv"
    
    # Build projections
    df = build_projections(csv_path, game_date, args.database_url, args.save_to_db)
    
    # Save projections to CSV
    save_projections(df, output_path)
    
    # Print summary
    print("\n=== Projection Summary ===")
    print(f"Total players: {len(df)}")
    print(f"\nTop 10 by Projected Fantasy Points:")
    top_10 = df.nlargest(10, 'fp_proj')[['player', 'team', 'salary', 'fp_proj', 'projected_value']]
    print(top_10.to_string(index=False))
    
    print(f"\nTop 10 by Projected Value (pts/$1k):")
    top_value = df.nlargest(10, 'projected_value')[['player', 'team', 'salary', 'fp_proj', 'projected_value']]
    print(top_value.to_string(index=False))


if __name__ == "__main__":
    main()

