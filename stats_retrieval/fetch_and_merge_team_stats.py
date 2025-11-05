from nba_api.stats.endpoints import leaguedashteamstats # Removed leaguedashteamptstats

import pandas as pd
import time
import datetime
from sqlalchemy import create_engine

def fetch_and_merge_team_stats(season='2024-25', season_type='Regular Season', per_mode='PerGame', last_n_games=0):
    """
    Fetches team stats from multiple endpoints and merges them.

    This fetches data from:
    1. leaguedashteamstats (MeasureType='Base')
    2. leaguedashteamstats (MeasureType='Advanced')
    """

    print(f"Starting to fetch team stats for {season} (Last {last_n_games} Games)...")

    # Define common parameters
    common_params = {
        'season': season,
        'season_type_all_star': season_type,
        'per_mode_detailed': per_mode,
        'league_id_nullable': '00',
        'last_n_games': last_n_games
    }

    # --- 1. Fetch 'Base' stats (our main dataframe) ---
    print("Fetching 'Base' stats...")
    try:
        stats = leaguedashteamstats.LeagueDashTeamStats(**common_params, measure_type_detailed_defense='Base')
        final_df = stats.get_data_frames()[0]
        # These are the columns we will merge on
        merge_keys = ['TEAM_ID', 'TEAM_NAME']
        time.sleep(0.6) # Be polite to the API
    except Exception as e:
        print(f"Error fetching 'Base' stats: {e}")
        return None

    # --- 2. Fetch 'Advanced' stats from leaguedashteamstats ---
    # Removed 'Usage' and 'Misc' as requested
    measure_types = ['Advanced']

    for measure_type in measure_types:
        print(f"Fetching '{measure_type}' stats...")
        try:
            stats = leaguedashteamstats.LeagueDashTeamStats(**common_params, measure_type_detailed_defense=measure_type)
            new_df = stats.get_data_frames()[0]

            # Find new columns to add (excluding keys and common stats like GP, MIN)
            common_cols = set(final_df.columns) & set(new_df.columns)
            cols_to_add = [col for col in new_df.columns if col not in common_cols] + merge_keys

            # Merge new stats in
            final_df = pd.merge(final_df, new_df[cols_to_add], on=merge_keys, how='left')
            time.sleep(0.6)
        except Exception as e:
            print(f"Error fetching '{measure_type}' stats: {e}")

    # --- Removed Team Tracking (PT) stats fetching ---

    print("All data fetched. Renaming columns to match a potential schema...")

    # --- 3. Define a potential column mapping (based on Base and Advanced) ---
    column_mapping = {
        'TEAM_NAME': 'team_name',
        'TEAM_ID': 'team_id',
        'GP': 'gp',
        'W': 'w',
        'L': 'l',
        'MIN': 'min',
        'PTS': 'pts',
        'FGM': 'fgm',
        'FGA': 'fga',
        'FG_PCT': 'fg_pct',
        'FG3M': 'three_pm',
        'FG3A': 'three_pa',
        'FG3_PCT': 'three_p_pct',
        'FTM': 'ftm',
        'FTA': 'fta',
        'FT_PCT': 'ft_pct',
        'OREB': 'oreb',
        'DREB': 'dreb',
        'REB': 'reb',
        'AST': 'ast',
        'TOV': 'tov', # From 'Base'
        'STL': 'stl',
        'BLK': 'blk',
        'PF': 'pf',
        'PLUS_MINUS': 'plus_minus',
        # Advanced
        'OFF_RATING': 'offrtg',
        'DEF_RATING': 'defrtg',
        'NET_RATING': 'netrtg',
        'AST_PCT': 'ast_pct',
        'AST_TO': 'ast_to',
        'AST_RATIO': 'ast_ratio',
        'OREB_PCT': 'oreb_pct',
        'DREB_PCT': 'dreb_pct',
        'REB_PCT': 'reb_pct',
        'TM_TOV_PCT': 'tov_pct', # Team TOV%
        'EFG_PCT': 'efg_pct',
        'TS_PCT': 'ts_pct',
        'PACE': 'pace',
        'PIE': 'pie',
        'POSS': 'poss' # Now in Advanced
    }

    # Rename all columns that are in the fetched dataframe
    final_df = final_df.rename(columns=column_mapping)

    # Add the current_date column
    final_df['current_date'] = datetime.date.today()

    # --- 4. Filter to a potential set of columns (based on Base and Advanced) ---
    potential_schema_columns = [
        'team_name', 'team_id', 'gp', 'w', 'l', 'min', 'pts', 'fgm', 'fga', 'fg_pct',
        'three_pm', 'three_pa', 'three_p_pct', 'ftm', 'fta', 'ft_pct', 'oreb', 'dreb',
        'reb', 'ast', 'tov', 'stl', 'blk', 'pf', 'plus_minus',
        'offrtg', 'defrtg', 'netrtg', 'ast_pct', 'ast_to', 'ast_ratio', 'oreb_pct',
        'dreb_pct', 'reb_pct', 'tov_pct', 'efg_pct', 'ts_pct', 'pace',
        'pie', 'poss', 'current_date'
    ]

    # Filter df to only these columns, in this order
    available_columns = [col for col in potential_schema_columns if col in final_df.columns]
    final_df_filtered = final_df[available_columns]

    print(f"Data processing complete. {len(final_df_filtered.columns)} columns prepared.")

    return final_df_filtered

def load_to_postgres(df, table_name, db_user, db_pass, db_host, db_port, db_name):
    """
    Loads the DataFrame into the specified table in the 'team_data' schema.
    """
    if df is None:
        print("No data to load.")
        return

    try:
        # Create the database connection string
        connection_string = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        engine = create_engine(connection_string)

        print("Connecting to PostgreSQL...")

        # Load the data, replacing the table if it exists
        df.to_sql(
            name=table_name,
            con=engine,
            schema='team_data', # <-- Use the 'team_data' schema
            if_exists='replace',
            index=False
        )

        print(f"Successfully loaded {len(df)} rows into team_data.{table_name}.")

    except Exception as e:
        print(f"An error occurred during database operation: {e}")