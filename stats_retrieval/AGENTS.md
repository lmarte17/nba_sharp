# NBA Player Stats ETL Script

## 1. Summary

This Python script is an ETL (Extract, Transform, Load) pipeline for NBA player statistics. It uses the `nba_api` library to extract a comprehensive set of player stats from multiple NBA.com API endpoints. It then transforms this data using `pandas` by merging, renaming, and filtering columns to fit a specific schema. Finally, it provides a function to load the resulting DataFrame into a PostgreSQL database using `sqlalchemy`.

The script is modular and designed to be imported by an orchestrator, as its main execution block is commented out.

## 2. Dependencies

* `nba_api`: For extracting data from the NBA.com stats API.
* `pandas`: For data manipulation and transformation (merging, renaming).
* `sqlalchemy`: For creating a database engine to connect to PostgreSQL.
* `psycopg2`: (Implied by `sqlalchemy` connection string) PostgreSQL adapter for Python.
* `time`: For polite API rate-limiting.
* `datetime`: For timestamping the data with `current_date`.

## 3. Core Functions

### `fetch_and_merge_player_stats`

This is the primary data extraction and transformation function.

* **Parameters:**
    * `season` (str): The NBA season to fetch (e.g., '2024-25'). Default: `'2024-25'`.
    * `season_type` (str): The type of season (e.g., 'Regular Season', 'Playoffs'). Default: `'Regular Season'`.
    * `per_mode` (str): The data aggregation mode (e.g., 'PerGame', 'Totals'). Default: `'PerGame'`.
    * `last_n_games` (int): Fetches data for the last N games. `0` fetches all games. Default: `0`.

* **Extraction Process:**
    The function makes **8+ API calls** to build one comprehensive DataFrame.
    1.  **`leaguedashplayerstats(MeasureType='Base')`**: Fetches the main DataFrame with basic box score stats.
    2.  **`leaguedashplayerstats(MeasureType='Advanced')`**: Fetches advanced rating stats (OffRtg, DefRtg, etc.).
    3.  **`leaguedashplayerstats(MeasureType='Usage')`**: Fetches usage-based stats (USG_PCT, TOV_PCT).
    4.  **`leaguedashplayerstats(MeasureType='Misc')`**: Fetches miscellaneous stats (e.g., POSS).
    5.  **`leaguedashptstats(PtMeasureType='Possessions')`**: Fetches player tracking data related to possessions and touches.
    6.  **`leaguedashptstats(PtMeasureType='PostTouch')`**: Fetches player tracking data for post touches.
    7.  **`leaguedashptstats(PtMeasureType='ElbowTouch')`**: Fetches player tracking data for elbow touches.
    8.  **`leaguedashptstats(PtMeasureType='PaintTouch')`**: Fetches player tracking data for paint touches.

* **Transformation Process:**
    1.  **Merge**: All subsequent DataFrames are merged into the initial 'Base' DataFrame using an outer merge on `['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ID', 'TEAM_ABBREVIATION']`.
    2.  **Rename**: A large dictionary (`column_mapping`) is used to rename API columns to standardized schema names (e.g., `FG3M` -> `three_pm`).
    3.  **Timestamp**: A `current_date` column is added with the current date.
    4.  **Filter**: The final DataFrame is filtered to only include columns specified in the `final_schema_columns` list, ensuring a consistent output.

* **Returns:**
    A `pandas.DataFrame` containing the merged, transformed, and filtered player stats, or `None` if the initial fetch fails.

### `load_to_postgres`

This is the data loading function.

* **Parameters:**
    * `df` (pd.DataFrame): The DataFrame to be loaded (from `fetch_and_merge_player_stats`).
    * `table_name` (str): The name of the target SQL table (e.g., 'player_stats_sl', 'player_stats_l10').
    * `db_user` (str): PostgreSQL username.
    * `db_pass` (str): PostgreSQL password.
    * `db_host` (str): PostgreSQL server host.
    * `db_port` (str): PostgreSQL server port.
    * `db_name` (str): PostgreSQL database name.

* **Process:**
    1.  Creates a `sqlalchemy` engine using a `postgresql+psycopg2` connection string.
    2.  Calls `df.to_sql()` to load the data.
    3.  **Target Schema**: `player_data`
    4.  **Write Behavior**: `if_exists='replace'` (truncates and replaces the table).
    5.  **Index**: `index=False` (does not write the pandas index).

## 4. Final Data Schema

The `fetch_and_merge_player_stats` function returns a DataFrame that adheres to the following schema.

| Column Name | API Source | Description |
| :--- | :--- | :--- |
| `player` | `PLAYER_NAME` (Base) | Player's full name. |
| `player_id` | `PLAYER_ID` (Base) | Unique identifier for the player. |
| `team` | `TEAM_ABBREVIATION` (Base) | Abbreviated name of the player's team. |
| `age` | `AGE` (Base) | Player's age. |
| `gp` | `GP` (Base) | Games played. |
| `w` | `W` (Base) | Wins. |
| `l` | `L` (Base) | Losses. |
| `min` | `MIN` (Base) | Minutes played. |
| `pts` | `PTS` (Base) | Points scored. |
| `fgm` | `FGM` (Base) | Field goals made. |
| `fga` | `FGA` (Base) | Field goals attempted. |
| `fg_pct` | `FG_PCT` (Base) | Field goal percentage. |
| `three_pm` | `FG3M` (Base) | Three-point field goals made. |
| `three_pa` | `FG3A` (Base) | Three-point field goals attempted. |
| `three_p_pct` | `FG3_PCT` (Base) | Three-point field goal percentage. |
| `ftm` | `FTM` (Base) | Free throws made. |
| `fta` | `FTA` (Base) | Free throws attempted. |
| `ft_pct` | `FT_PCT` (Base) | Free throw percentage. |
| `oreb` | `OREB` (Base) | Offensive rebounds. |
| `dreb` | `DREB` (Base) | Defensive rebounds. |
| `reb` | `REB` (Base) | Total rebounds. |
| `ast` | `AST` (Base) | Assists. |
| `tov` | `TOV` (Usage) | Turnovers (Player). |
| `stl` | `STL` (Base) | Steals. |
| `blk` | `BLK` (Base) | Blocks. |
| `pf` | `PF` (Base) | Personal fouls. |
| `fp` | `NBA_FANTASY_PTS` (Base) | NBA fantasy points. |
| `dd2` | `DD2` (Base) | Double-doubles. |
| `tdthree_` | `TD3` (Base) | Triple-doubles. (Note: Matches schema typo) |
| `plus_minus` | `PLUS_MINUS` (Base) | Plus/Minus rating. |
| `offrtg` | `OFF_RATING` (Advanced) | Offensive rating. |
| `defrtg` | `DEF_RATING` (Advanced) | Defensive rating. |
| `netrtg` | `NET_RATING` (Advanced) | Net rating. |
| `ast_pct` | `AST_PCT` (Advanced) | Assist percentage. |
| `ast_to` | `AST_TO` (Advanced) | Assist to turnover ratio. |
| `ast_ratio` | `AST_RATIO` (Advanced) | Assist ratio. |
| `oreb_pct` | `OREB_PCT` (Advanced) | Offensive rebound percentage. |
| `dreb_pct` | `DREB_PCT` (Advanced) | Defensive rebound percentage. |
| `reb_pct` | `REB_PCT` (Advanced) | Total rebound percentage. |
| `tov_pct` | `TOV_PCT` (Usage) | Turnover percentage (Player). |
| `efg_pct` | `EFG_PCT` (Advanced) | Effective field goal percentage. |
| `ts_pct` | `TS_PCT` (Advanced) | True shooting percentage. |
| `usg_pct` | `USG_PCT` (Usage) | Usage percentage. |
| `pace` | `PACE` (Advanced) | Pace. |
| `pie` | `PIE` (Advanced) | Player Impact Estimate. |
| `poss` | `POSS` (Misc) | Possessions played. |
| `touches` | `TOUCHES` (Possessions) | Number of touches. |
| `front_ct_touches` | `FRONT_CT_TOUCHES` (Possessions) | Front court touches. |
| `time_of_poss` | `TIME_OF_POSS` (Possessions) | Time of possession. |
| `avg_sec_per_touch` | `AVG_SEC_PER_TOUCH` (Possessions) | Average seconds per touch. |
| `avg_drib_per_touch` | `AVG_DRIB_PER_TOUCH` (Possessions) | Average dribbles per touch. |
| `pts_per_touch` | `PTS_PER_TOUCH` (Possessions) | Points per touch. |
Setting up the environment...
* Checking for `nba_api`...
* Checking for `pandas`...
* Checking for `sqlalchemy`...
* Checking for `psycopg2-binary`...

All required packages are installed.
| `elbow_touches` | `ELBOW_TOUCHES` (ElbowTouch) | Elbow touches. |
| `post_ups` | `POST_TOUCHES` (PostTouch) | Post touches (API is POST_TOUCHES). |
| `paint_touches` | `PAINT_TOUCHES` (PaintTouch) | Paint touches. |
| `pts_per_elbow_touch` | `PTS_PER_ELBOW_TOUCH` (ElbowTouch) | Points per elbow touch. |
| `pts_per_post_touch` | `PTS_PER_POST_TOUCH` (PostTouch) | Points per post touch. |
| `pts_per_paint_touch` | `PTS_PER_PAINT_TOUCH` (PaintTouch) | Points per paint touch. |
| `current_date` | Derived | The date the data was fetched. |



# NBA Team Stats ETL Script

## 1. Summary

This Python script is an ETL (Extract, Transform, Load) pipeline for NBA team statistics. It uses the `nba_api` library to extract team stats from the `leaguedashteamstats` endpoint. Unlike the more complex player stats script, this one only queries for 'Base' and 'Advanced' metrics and does *not* query the `leaguedashptstats` (tracking) endpoint.

The script transforms the data using `pandas` by merging the two data sets, renaming columns to a standardized schema, and adding a timestamp. Finally, it provides a function to load the resulting DataFrame into a PostgreSQL database within the `team_data` schema.

## 2. Dependencies

* `nba_api` (specifically `leaguedashteamstats`): For extracting data from the NBA.com stats API.
* `pandas`: For data manipulation and transformation (merging, renaming).
* `sqlalchemy`: For creating a database engine to connect to PostgreSQL.
* `psycopg2`: (Implied by `sqlalchemy` connection string) PostgreSQL adapter for Python.
* `time`: For polite API rate-limiting.
* `datetime`: For timestamping the data with `current_date`.

## 3. Core Functions

### `fetch_and_merge_team_stats`

This is the primary data extraction and transformation function.

* **Parameters:**
    * `season` (str): The NBA season to fetch (e.g., '2024-25'). Default: `'2024-25'`.
    * `season_type` (str): The type of season (e.g., 'Regular Season', 'Playoffs'). Default: `'Regular Season'`.
    * `per_mode` (str): The data aggregation mode (e.g., 'PerGame', 'Totals'). Default: `'PerGame'`.
    * `last_n_games` (int): Fetches data for the last N games. `0` fetches all games. Default: `0`.

* **Extraction Process:**
    The function makes **2 API calls** to build one comprehensive DataFrame:
    1.  **`leaguedashteamstats(MeasureType='Base')`**: Fetches the main DataFrame with basic box score stats.
    2.  **`leaguedashteamstats(MeasureType='Advanced')`**: Fetches advanced rating stats (OffRtg, DefRtg, Pace, etc.).

* **Transformation Process:**
    1.  **Merge**: The 'Advanced' DataFrame is merged into the 'Base' DataFrame using an outer merge on `['TEAM_ID', 'TEAM_NAME']`.
    2.  **Rename**: A dictionary (`column_mapping`) is used to rename API columns to standardized schema names (e.g., `TEAM_NAME` -> `team_name`, `OFF_RATING` -> `offrtg`).
    3.  **Timestamp**: A `current_date` column is added with the current date.
    4.  **Filter**: The final DataFrame is filtered to only include columns specified in the `potential_schema_columns` list.

* **Returns:**
    A `pandas.DataFrame` containing the merged, transformed, and filtered team stats, or `None` if the initial fetch fails.

### `load_to_postgres`

This is the data loading function.

* **Parameters:**
    * `df` (pd.DataFrame): The DataFrame to be loaded (from `fetch_and_merge_team_stats`).
    * `table_name` (str): The name of the target SQL table (e.g., 'team_stats_sl', 'team_stats_l10').
    * `db_user` (str): PostgreSQL username.
    * `db_pass` (str): PostgreSQL password.
    * `db_host` (str): PostgreSQL server host.
    * `db_port` (str): PostgreSQL server port.
    * `db_name` (str): PostgreSQL database name.

* **Process:**
    1.  Creates a `sqlalchemy` engine using a `postgresql+psycopg2` connection string.
    2.  Calls `df.to_sql()` to load the data.
    3.  **Target Schema**: `team_data`
    4.  **Write Behavior**: `if_exists='replace'` (truncates and replaces the table).
    5.  **Index**: `index=False` (does not write the pandas index).

## 4. Final Data Schema

The `fetch_and_merge_team_stats` function returns a DataFrame that adheres to the following schema.

| Column Name | API Source | Description |
| :--- | :--- | :--- |
| `team_name` | `TEAM_NAME` (Base) | Full name of the team. |
| `team_id` | `TEAM_ID` (Base) | Unique identifier for the team. |
| `gp` | `GP` (Base) | Games played. |
| `w` | `W` (Base) | Wins. |
| `l` | `L` (Base) | Losses. |
| `min` | `MIN` (Base) | Minutes played. |
| `pts` | `PTS` (Base) | Points scored. |
| `fgm` | `FGM` (Base) | Field goals made. |
| `fga` | `FGA` (Base) | Field goals attempted. |
| `fg_pct` | `FG_PCT` (Base) | Field goal percentage. |
| `three_pm` | `FG3M` (Base) | Three-point field goals made. |
| `three_pa` | `FG3A` (Base) | Three-point field goals attempted. |
| `three_p_pct` | `FG3_PCT` (Base) | Three-point field goal percentage. |
| `ftm` | `FTM` (Base) | Free throws made. |
| `fta` | `FTA` (Base) | Free throws attempted. |
| `ft_pct` | `FT_PCT` (Base) | Free throw percentage. |
| `oreb` | `OREB` (Base) | Offensive rebounds. |
| `dreb` | `DREB` (Base) | Defensive rebounds. |
| `reb` | `REB` (Base) | Total rebounds. |
| `ast` | `AST` (Base) | Assists. |
| `tov` | `TOV` (Base) | Turnovers. |
| `stl` | `STL` (Base) | Steals. |
| `blk` | `BLK` (Base) | Blocks. |
| `pf` | `PF` (Base) | Personal fouls. |
| `plus_minus` | `PLUS_MINUS` (Base) | Plus/Minus rating. |
| `offrtg` | `OFF_RATING` (Advanced) | Offensive rating. |
| `defrtg` | `DEF_RATING` (Advanced) | Defensive rating. |
| `netrtg` | `NET_RATING` (Advanced) | Net rating. |
| `ast_pct` | `AST_PCT` (Advanced) | Assist percentage. |
| `ast_to` | `AST_TO` (Advanced) | Assist to turnover ratio. |
| `ast_ratio` | `AST_RATIO` (Advanced) | Assist ratio. |
| `oreb_pct` | `OREB_PCT` (Advanced) | Offensive rebound percentage. |
| `dreb_pct` | `DREB_PCT` (Advanced) | Defensive rebound percentage. |
| `reb_pct` | `REB_PCT` (Advanced) | Total rebound percentage. |
| `tov_pct` | `TM_TOV_PCT` (Advanced) | Turnover percentage (Team). |
| `efg_pct` | `EFG_PCT` (Advanced) | Effective field goal percentage. |
| `ts_pct` | `TS_PCT` (Advanced) | True shooting percentage. |
| `pace` | `PACE` (Advanced) | Pace. |
| `pie` | `PIE` (Advanced) | Player Impact Estimate. |
| `poss` | `POSS` (Advanced) | Possessions played. |
Setting up the environment...
* Checking for `nba_api`...
* Checking for `pandas`...
* Checking for `sqlalchemy`...
* Checking for `psycopg2-binary`...

All required packages are installed.
| `current_date` | Derived | The date the data was fetched. |