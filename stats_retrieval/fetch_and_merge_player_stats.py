import pandas as pd
import time
import datetime
from sqlalchemy import create_engine
from nba_api.stats.endpoints import leaguedashplayerstats, leaguedashptstats

def fetch_and_merge_player_stats(season='2024-25', season_type='Regular Season', per_mode='PerGame', last_n_games=0):
    """
    Fetches all player stats from multiple endpoints and merges them to fit the schema.
    
    This is complex because the schema combines:
    1. leaguedashplayerstats (MeasureType='Base')
    2. leaguedashplayerstats (MeasureType='Advanced')
    3. leaguedashplayerstats (MeasureType='Usage')
    4. leaguedashplayerstats (MeasureType='Misc')
    5. leaguedashptstats (PtMeasureType='Possessions')
    6. leaguedashptstats (PtMeasureType='PostTouch')
    7. leaguedashptstats (PtMeasureType='ElbowTouch')
    8. leaguedashptstats (PtMeasureType='PaintTouch')
    """
    
    print(f"Starting to fetch all player stats for {season} (Last {last_n_games} Games)...")
    
    # Define common parameters
    common_params = {
        'season': season,
        'season_type_all_star': season_type,
        'per_mode_detailed': per_mode,
        'league_id_nullable': '00',
        'last_n_games': last_n_games  # <-- ADDED THIS
    }
    
    # --- 1. Fetch 'Base' stats (our main dataframe) ---
    print("Fetching 'Base' stats...")
    try:
        stats = leaguedashplayerstats.LeagueDashPlayerStats(**common_params, measure_type_detailed_defense='Base')
        final_df = stats.get_data_frames()[0]
        # These are the columns we will merge on
        merge_keys = ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ID', 'TEAM_ABBREVIATION']
        time.sleep(0.6) # Be polite to the API
    except Exception as e:
        print(f"Error fetching 'Base' stats: {e}")
        return None

    # --- 2. Fetch other MeasureTypes from leaguedashplayerstats ---
    measure_types = ['Advanced', 'Usage', 'Misc']
    
    for measure_type in measure_types:
        print(f"Fetching '{measure_type}' stats...")
        try:
            stats = leaguedashplayerstats.LeagueDashPlayerStats(**common_params, measure_type_detailed_defense=measure_type)
            new_df = stats.get_data_frames()[0]
            
            # Find new columns to add (excluding keys and common stats like GP, MIN)
            common_cols = set(final_df.columns) & set(new_df.columns)
            cols_to_add = [col for col in new_df.columns if col not in common_cols] + merge_keys
            
            # Merge new stats in
            final_df = pd.merge(final_df, new_df[cols_to_add], on=merge_keys, how='left')
            time.sleep(0.6)
        except Exception as e:
            print(f"Error fetching '{measure_type}' stats: {e}")

    # --- 3. Fetch Player Tracking (PT) stats from leaguedashptstats ---
    # These have different parameters and PtMeasureType
    pt_params = {
        'season': season,
        'season_type_all_star': season_type,
        'per_mode_simple': per_mode,
        'league_id_nullable': '00',
        'player_or_team': 'Player',
        'last_n_games': last_n_games  # <-- ADDED THIS
    }
    
    # We need to call this endpoint for each type of tracking stat in your schema
    pt_measure_types = ['Possessions', 'PostTouch', 'ElbowTouch', 'PaintTouch']
    
    for pt_measure in pt_measure_types:
        print(f"Fetching Tracking '{pt_measure}' stats...")
        try:
            pt_stats = leaguedashptstats.LeagueDashPtStats(**pt_params, pt_measure_type=pt_measure)
            new_df = pt_stats.get_data_frames()[0]

            # Find new columns to add
            common_cols = set(final_df.columns) & set(new_df.columns)
            cols_to_add = [col for col in new_df.columns if col not in common_cols] + merge_keys
            
            final_df = pd.merge(final_df, new_df[cols_to_add], on=merge_keys, how='left')
            time.sleep(0.6)
        except Exception as e:
            print(f"Error fetching '{pt_measure}' stats: {e}")

    print("All data fetched. Renaming columns to match schema...")

    # --- 4. Define the massive column mapping ---
    # Maps API column names to your exact SQL schema names
    column_mapping = {
        'PLAYER_NAME': 'player',
        'PLAYER_ID': 'player_id',
        'TEAM_ABBREVIATION': 'team',
        'AGE': 'age',
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
        'NBA_FANTASY_PTS': 'fp',
        'DD2': 'dd2',
        'TD3': 'tdthree_', # Match schema typo
        'PLUS_MINUS': 'plus_minus',
        # From 'Advanced'
        'OFF_RATING': 'offrtg',
        'DEF_RATING': 'defrtg',
        'NET_RATING': 'netrtg',
        'AST_PCT': 'ast_pct',
        'AST_TO': 'ast_to',
        'AST_RATIO': 'ast_ratio',
        'OREB_PCT': 'oreb_pct',
        'DREB_PCT': 'dreb_pct',
        'REB_PCT': 'reb_pct',
        'TM_TOV_PCT': 'tov_pct', # This is 'team' TOV%. We'll replace it.
        'EFG_PCT': 'efg_pct',
        'TS_PCT': 'ts_pct',
        'PACE': 'pace',
        'PIE': 'pie',
        # From 'Usage'
        'USG_PCT': 'usg_pct',
        'TOV_PCT': 'tov_pct', # From 'Usage' - this is PLAYER TOV%, overwrites team one.
        # From 'Misc'
        'POSS': 'poss',
        # From 'leaguedashptstats' (Tracking)
        'TOUCHES': 'touches',
        'FRONT_CT_TOUCHES': 'front_ct_touches',
        'TIME_OF_POSS': 'time_of_poss',
        'AVG_SEC_PER_TOUCH': 'avg_sec_per_touch',
        'AVG_DRIB_PER_TOUCH': 'avg_drib_per_touch',
        'PTS_PER_TOUCH': 'pts_per_touch',
        'ELBOW_TOUCHES': 'elbow_touches',
        'POST_TOUCHES': 'post_ups', # API is POST_TOUCHES
        'PAINT_TOUCHES': 'paint_touches',
        'PTS_PER_ELBOW_TOUCH': 'pts_per_elbow_touch',
        'PTS_PER_POST_TOUCH': 'pts_per_post_touch',
        'PTS_PER_PAINT_TOUCH': 'pts_per_paint_touch'
    }
    
    # Rename all columns
    final_df = final_df.rename(columns=column_mapping)
    
    # Add the current_date column
    final_df['current_date'] = datetime.date.today()
    
    # --- 5. Filter to *only* columns in your schema ---
    final_schema_columns = [
        'player', 'player_id', 'team', 'age', 'gp', 'w', 'l', 'min', 'pts', 'fgm', 'fga', 'fg_pct',
        'three_pm', 'three_pa', 'three_p_pct', 'ftm', 'fta', 'ft_pct', 'oreb', 'dreb',
        'reb', 'ast', 'tov', 'stl', 'blk', 'pf', 'fp', 'dd2', 'tdthree_', 'plus_minus',
        'offrtg', 'defrtg', 'netrtg', 'ast_pct', 'ast_to', 'ast_ratio', 'oreb_pct',
        'dreb_pct', 'reb_pct', 'tov_pct', 'efg_pct', 'ts_pct', 'usg_pct', 'pace',
        'pie', 'poss', 'touches', 'front_ct_touches', 'time_of_poss', 'avg_sec_per_touch',
        'avg_drib_per_touch', 'pts_per_touch', 'elbow_touches', 'post_ups', 'paint_touches',
        'pts_per_elbow_touch', 'pts_per_post_touch', 'pts_per_paint_touch', 'current_date'
    ]
    
    # Filter df to only these columns, in this order
    # We check which columns we successfully fetched that are in the final list
    available_columns = [col for col in final_schema_columns if col in final_df.columns]
    final_df_filtered = final_df[available_columns]
    
    print(f"Data processing complete. {len(final_df_filtered.columns)} columns prepared for SQL.")
    
    return final_df_filtered

def load_to_postgres(df, table_name, db_user, db_pass, db_host, db_port, db_name):
    """
    Loads the DataFrame into the specified table and schema.
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
            name=table_name,  # <-- CHANGED
            con=engine,
            schema='player_data',
            if_exists='replace',
            index=False
        )
        
        print(f"Successfully loaded {len(df)} rows into player_data.{table_name}.")
        
    except Exception as e:
        print(f"An error occurred during database operation: {e}")