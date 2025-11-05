# Database Module - NBA Sharp Data Layer

## Overview

The Database module is the data persistence and ETL (Extract, Transform, Load) layer of the NBA Sharp system. It manages:

1. **Database Schema** - PostgreSQL tables for player stats, team stats, game schedules, and analysis outputs
2. **Data Ingestion** - ETL pipelines to populate the database from NBA API and Odds API
3. **Data Extraction** - Query helpers to retrieve data for analysis
4. **Daily Updates** - Orchestrated workflow to keep all data current

This module serves as the **single source of truth** for all statistical data used by the analysis and frontend layers.

---

## Module Structure

```
db/
├── database.py              # Database engine and session management
├── models.py                # SQLAlchemy ORM models (table definitions)
├── create_tables.py         # Table creation script
├── run_daily_update.py      # Daily orchestrator script
├── db_insert/
│   ├── ingest_player_stats_to_db.py    # Player stats ETL
│   ├── ingest_team_stats_to_db.py      # Team stats ETL
│   ├── ingest_today_nba_events_to_db.py # Game schedule ETL
│   └── README_PLAYER_PROJECTIONS.md    # Projection ingestion docs
├── db_extract/
│   └── extractors.py        # Query helpers for data retrieval
└── README.md                # Setup documentation
```

---

## Database Architecture

### Technology Stack

- **Database:** PostgreSQL (via Neon serverless)
- **ORM:** SQLAlchemy 2.x
- **Driver:** psycopg (psycopg3)
- **Connection:** SSL required for Neon

### Schema Organization

The database uses **schemas** to organize related tables:

```
nba_sharp (database)
├── public (schema)
│   └── game_schedule           # Game dates and matchups
├── player_data (schema)
│   ├── player_stats_sl         # Season-long player stats
│   ├── player_stats_l10        # Last 10 games player stats
│   ├── player_stats_l5         # Last 5 games player stats
│   └── player_stats_l3         # Last 3 games player stats
├── team_data (schema)
│   ├── team_stats_sl           # Season-long team stats
│   ├── team_stats_l10          # Last 10 games team stats
│   ├── team_stats_l5           # Last 5 games team stats
│   └── team_stats_l3           # Last 3 games team stats
└── analysis (schema)
    ├── game_matchup            # Game-level projections
    └── player_projections      # Player-level projections (optional)
```

---

## Table Schemas

### GameSchedule (`public.game_schedule`)

Stores the schedule of NBA games.

**Columns:**
- `id` (INTEGER, PK) - Auto-incrementing ID
- `game_date_est` (DATE, NOT NULL) - Game date in Eastern Time
- `away_team` (VARCHAR 64, NOT NULL) - Away team full name
- `home_team` (VARCHAR 64, NOT NULL) - Home team full name
- `created_at` (TIMESTAMPTZ) - Record creation timestamp
- `updated_at` (TIMESTAMPTZ) - Record update timestamp

**Constraints:**
- UNIQUE (`game_date_est`, `away_team`, `home_team`)

**Purpose:** Foundation for all game-based analysis. Used by game matchup calculator.

**Source:** Ingested from Odds API via `ingest_today_nba_events_to_db.py`

---

### PlayerStats (`player_data.player_stats_{timeframe}`)

Four tables for player statistics across different time windows: `sl`, `l10`, `l5`, `l3`

**Columns (59 total):**

**Identity:**
- `id` (INTEGER, PK)
- `player_id` (BIGINT) - NBA API player ID
- `player` (VARCHAR 128) - Player full name
- `team` (VARCHAR 64) - Team abbreviation
- `age` (FLOAT)
- `current_date` (DATE) - Data fetch date

**Games & Win/Loss:**
- `gp` (FLOAT) - Games played
- `w` (FLOAT) - Wins
- `l` (FLOAT) - Losses
- `min` (FLOAT) - Minutes played

**Traditional Stats:**
- `pts`, `fgm`, `fga`, `fg_pct` - Scoring
- `three_pm`, `three_pa`, `three_p_pct` - Three-point shooting
- `ftm`, `fta`, `ft_pct` - Free throws
- `oreb`, `dreb`, `reb` - Rebounds
- `ast` - Assists
- `tov` - Turnovers
- `stl` - Steals
- `blk` - Blocks
- `pf` - Personal fouls
- `plus_minus` - Plus/Minus

**Fantasy:**
- `fp` (FLOAT) - Fantasy points
- `dd2` (FLOAT) - Double-doubles
- `tdthree_` (FLOAT) - Triple-doubles

**Advanced Metrics:**
- `offrtg`, `defrtg`, `netrtg` - Ratings
- `ast_pct`, `ast_to`, `ast_ratio` - Assist metrics
- `oreb_pct`, `dreb_pct`, `reb_pct` - Rebounding %
- `tov_pct` - Turnover %
- `efg_pct`, `ts_pct` - Shooting efficiency
- `usg_pct` - Usage %
- `pace` - Pace
- `pie` - Player Impact Estimate
- `poss` - Possessions

**Tracking Stats:**
- `touches` - Ball touches
- `front_ct_touches` - Front court touches
- `time_of_poss` - Time of possession
- `avg_sec_per_touch` - Seconds per touch
- `avg_drib_per_touch` - Dribbles per touch
- `pts_per_touch` - Points per touch
- `elbow_touches` - Elbow area touches
- `post_ups` - Post touches
- `paint_touches` - Paint area touches
- `pts_per_elbow_touch` - Points per elbow touch
- `pts_per_post_touch` - Points per post touch
- `pts_per_paint_touch` - Points per paint touch

**Timestamps:**
- `created_at`, `updated_at` (TIMESTAMPTZ)

**Purpose:** Core statistical data for player projections. Provides historical performance across multiple timeframes.

**Source:** Ingested from NBA API via `ingest_player_stats_to_db.py`

---

### TeamStats (`team_data.team_stats_{timeframe}`)

Four tables for team statistics across different time windows: `sl`, `l10`, `l5`, `l3`

**Columns (36 total):**

**Identity:**
- `id` (INTEGER, PK)
- `team_id` (BIGINT) - NBA API team ID
- `team_name` (VARCHAR 128) - Full team name
- `current_date` (DATE) - Data fetch date

**Games & Win/Loss:**
- `gp`, `w`, `l` (FLOAT)
- `min` (FLOAT)

**Traditional Stats:**
- `pts`, `fgm`, `fga`, `fg_pct`
- `three_pm`, `three_pa`, `three_p_pct`
- `ftm`, `fta`, `ft_pct`
- `oreb`, `dreb`, `reb`
- `ast`, `tov`, `stl`, `blk`, `pf`
- `plus_minus`

**Advanced Metrics:**
- `offrtg`, `defrtg`, `netrtg`
- `ast_pct`, `ast_to`, `ast_ratio`
- `oreb_pct`, `dreb_pct`, `reb_pct`
- `tov_pct` - Team turnover %
- `efg_pct`, `ts_pct`
- `pace` - **Critical for matchup calculations**
- `pie`
- `poss` - **Critical for matchup calculations**

**Timestamps:**
- `created_at`, `updated_at`

**Purpose:** Team-level aggregates for game matchup calculations and player context.

**Source:** Ingested from NBA API via `ingest_team_stats_to_db.py`

---

### GameMatchup (`analysis.game_matchup`)

Game-level projections for pace, scoring, and possessions.

**Columns (80+ total):**

**Identity:**
- `id` (INTEGER, PK)
- `game_date_est` (DATE)
- `team_name` (VARCHAR 128)
- `opp_team_name` (VARCHAR 128)
- `is_home` (BOOLEAN)
- `team_id`, `opp_team_id` (BIGINT)
- `calc_version` (VARCHAR 16) - Calculation version

**Per Timeframe (_sl, _l10, _l5, _l3):**

Each timeframe has 19 metrics:
- `pace_{tf}` - Team pace
- `opp_pace_{tf}` - Opponent pace
- `lg_pace_{tf}` - League average pace
- `poss_above_lg_{tf}` - Pace differential
- `implied_poss_{tf}` - **Projected possessions** ⭐
- `offrtg_{tf}`, `defrtg_{tf}` - Team ratings
- `opp_offrtg_{tf}`, `opp_defrtg_{tf}` - Opponent ratings
- `lg_pp100_{tf}` - League points per 100
- `hca_poss_adj_{tf}` - Home court possession adjustment
- `hca_pp100_adj_{tf}` - Home court points adjustment
- `exp_pp100_{tf}` - Expected points per 100
- `opp_exp_pp100_{tf}` - Opponent expected points per 100
- `proj_pts_{tf}` - Projected team points
- `opp_proj_pts_{tf}` - Projected opponent points
- `proj_total_{tf}` - Projected game total
- `matchup_{tf}` - Point differential
- `pts_allowed_pg_{tf}` - Expected points allowed

**Constraints:**
- UNIQUE (`game_date_est`, `team_name`, `opp_team_name`)

**Purpose:** Provides game context for player projections. Critical for calculating implied touches.

**Source:** Generated by `analysis/game_matchup.py`

---

### PlayerProjections (`analysis.player_projections`)

*Optional table for storing player projection outputs*

**Columns:**
- `id` (INTEGER, PK)
- `game_date` (DATE)
- `player` (VARCHAR 128)
- `team`, `opp` (VARCHAR 64)
- `salary` (FLOAT)
- `proj_mins` (FLOAT)
- `ownership` (FLOAT)
- `fp_proj` (FLOAT) - Final fantasy projection
- `projected_value` (FLOAT) - Value metric
- Additional columns for intermediate calculations
- `created_at`, `updated_at`

**Purpose:** Optional storage of projection outputs for historical tracking.

**Source:** Generated by `analysis/player_proj.py` with `--save-to-db` flag

---

## Data Ingestion (ETL)

### Daily Update Orchestrator

**Script:** `db/run_daily_update.py`

**Purpose:** Runs complete daily ETL pipeline to update all tables.

**Process:**
1. Create/verify database schemas and tables
2. Fetch and upsert today's game schedule from Odds API
3. Ingest team stats across all timeframes (sl, l10, l5, l3)
4. Ingest player stats across all timeframes
5. Optional: Run game matchup calculations (external to db module)

**Usage:**

```bash
# Basic usage (uses DATABASE_URL env var)
python -m db.run_daily_update

# Full options
python -m db.run_daily_update \
  --database-url $DATABASE_URL \
  --season 2024-25 \
  --season-type "Regular Season" \
  --per-mode PerGame \
  --events-base-url http://localhost:8000/api \
  --tz America/New_York \
  --date 2024-11-05
```

**Parameters:**
- `--database-url` - PostgreSQL connection string (or use DATABASE_URL env var)
- `--season` - NBA season (e.g., "2024-25")
- `--season-type` - "Regular Season" or "Playoffs"
- `--per-mode` - "PerGame" or "Per100Possessions"
- `--events-base-url` - Odds API base URL
- `--tz` - Timezone for event date interpretation
- `--date` - Specific date (YYYY-MM-DD) or today

**Output:**
```
Ensuring database schemas and tables exist...
Updating game_schedule for the requested day...
Upserted 12 rows into game_schedule (conflicts ignored)
Ingesting team stats across timeframes...
  Fetching season_long team stats...
  Loaded 30 teams to team_data.team_stats_sl
  Fetching last_10 team stats...
  Loaded 30 teams to team_data.team_stats_l10
  ...
Ingesting player stats across timeframes...
  Fetching season_long player stats...
  Loaded 458 players to player_data.player_stats_sl
  ...
Daily update completed.
```

---

### Player Stats Ingestion

**Script:** `db/db_insert/ingest_player_stats_to_db.py`

**Purpose:** Extract player statistics from NBA API and load into database.

**Data Source:** NBA.com API via `nba_api` Python library

**API Calls (per timeframe):**
1. `leaguedashplayerstats(MeasureType='Base')` - Basic box score stats
2. `leaguedashplayerstats(MeasureType='Advanced')` - Advanced ratings
3. `leaguedashplayerstats(MeasureType='Usage')` - Usage stats
4. `leaguedashplayerstats(MeasureType='Misc')` - Miscellaneous stats
5. `leaguedashptstats(PtMeasureType='Possessions')` - Tracking: possessions
6. `leaguedashptstats(PtMeasureType='PostTouch')` - Tracking: post touches
7. `leaguedashptstats(PtMeasureType='ElbowTouch')` - Tracking: elbow touches
8. `leaguedashptstats(PtMeasureType='PaintTouch')` - Tracking: paint touches

**Process:**
1. Fetch data from 8 NBA API endpoints
2. Merge all DataFrames on `['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ID', 'TEAM_ABBREVIATION']`
3. Rename columns to match database schema
4. Add `current_date` timestamp
5. Filter to final schema columns
6. Load to PostgreSQL with `if_exists='replace'` (truncate and replace)

**Usage:**

```bash
# Run for all timeframes
python -m db.db_insert.ingest_player_stats_to_db \
  --database-url $DATABASE_URL \
  --season 2024-25

# Specific timeframe
python -m db.db_insert.ingest_player_stats_to_db \
  --season 2024-25 \
  --last-n-games 5  # For L5 only
```

**Programmatic:**
```python
from db.db_insert.ingest_player_stats_to_db import run

run(
    season="2024-25",
    season_type="Regular Season",
    per_mode="PerGame",
    database_url=None  # Uses DATABASE_URL env var
)
```

**Output:** Replaces all 4 player stats tables (sl, l10, l5, l3)

**Performance:** ~30-60 seconds (8 API calls × 4 timeframes = 32 total API calls)

---

### Team Stats Ingestion

**Script:** `db/db_insert/ingest_team_stats_to_db.py`

**Purpose:** Extract team statistics from NBA API and load into database.

**Data Source:** NBA.com API via `nba_api` library

**API Calls (per timeframe):**
1. `leaguedashteamstats(MeasureType='Base')` - Basic box score stats
2. `leaguedashteamstats(MeasureType='Advanced')` - Advanced ratings

**Process:**
1. Fetch data from 2 NBA API endpoints
2. Merge DataFrames on `['TEAM_ID', 'TEAM_NAME']`
3. Rename columns to match database schema
4. Add `current_date` timestamp
5. Filter to final schema columns
6. Load to PostgreSQL with `if_exists='replace'`

**Usage:**

```bash
# Run for all timeframes
python -m db.db_insert.ingest_team_stats_to_db \
  --database-url $DATABASE_URL \
  --season 2024-25
```

**Programmatic:**
```python
from db.db_insert.ingest_team_stats_to_db import run

run(
    season="2024-25",
    season_type="Regular Season",
    per_mode="PerGame",
    database_url=None
)
```

**Output:** Replaces all 4 team stats tables (sl, l10, l5, l3)

**Performance:** ~10-15 seconds (2 API calls × 4 timeframes = 8 total API calls)

---

### Game Schedule Ingestion

**Script:** `db/db_insert/ingest_today_nba_events_to_db.py`

**Purpose:** Fetch today's NBA games from Odds API and upsert into `game_schedule`.

**Data Source:** Odds API (via `odds_api_retrieval/get_today_nba_events.py`)

**Process:**
1. Determine target date in specified timezone (default: America/New_York)
2. Convert date to UTC range (start of day to end of day)
3. Query Odds API `/api/basketball_nba/events?commenceTimeFrom=...&commenceTimeTo=...`
4. Parse response for `home_team`, `away_team`, `commence_time`
5. Convert `commence_time` to EST date
6. Upsert into `game_schedule` (ON CONFLICT DO NOTHING)

**Usage:**

```bash
# Ingest today's games
python -m db.db_insert.ingest_today_nba_events_to_db

# Specific date
python -m db.db_insert.ingest_today_nba_events_to_db --date 2024-11-05

# Dry run (no DB writes)
python -m db.db_insert.ingest_today_nba_events_to_db --dry-run

# Custom Odds API URL
python -m db.db_insert.ingest_today_nba_events_to_db \
  --base-url https://your-odds-api.com/api
```

**Programmatic:**
```python
from db.db_insert.ingest_today_nba_events_to_db import upsert_game_schedule, parse_events
from odds_api_retrieval.get_today_nba_events import fetch_json

# Fetch events
url = "http://localhost:8000/api/basketball_nba/events?..."
payload = fetch_json(url)
events = parse_events(payload)

# Upsert to DB
rows = [...]  # Format: [{"game_date_est": date, "away_team": str, "home_team": str}]
count = upsert_game_schedule(session, rows)
```

**Output:** Inserts new games, ignores conflicts for existing games

**Performance:** < 1 second (1 API call)

---

## Data Extraction (Queries)

### Query Helpers

**Module:** `db/db_extract/extractors.py`

Provides utility functions to extract data from the database for analysis.

#### Team Name Resolution

**Function:** `resolve_team_record(stats_map, schedule_name)`

Handles team name aliasing (e.g., "Los Angeles Lakers" = "LA Lakers" = "L.A. Lakers")

**Example:**
```python
from db.db_extract import load_team_stats_map, resolve_team_record

# Load team stats
stats_map = load_team_stats_map(session, "season_long")

# Resolve "LA Lakers" to database record
record, matched_key = resolve_team_record(stats_map, "LA Lakers")
# Returns: {"team_id": 1610612747, "team_name": "Los Angeles Lakers", ...}
```

#### Schedule Queries

**Function:** `fetch_schedule_for_date(session, game_date_est)`

Returns list of games for a date.

**Example:**
```python
from db.db_extract import fetch_schedule_for_date
import datetime

games = fetch_schedule_for_date(session, datetime.date(2024, 11, 5))
# Returns: [{"game_date_est": date, "home_team": str, "away_team": str}, ...]
```

#### Team Stats Queries

**Function:** `load_team_stats_dataframe(session, timeframe)`

Returns DataFrame with team stats.

**Parameters:**
- `timeframe` - One of: "season_long", "last_10", "last_5", "last_3"

**Example:**
```python
from db.db_extract import load_team_stats_dataframe

df = load_team_stats_dataframe(session, "last_5")
# Returns: DataFrame with all team stats for L5 period
```

#### Player Stats Queries

**Function:** `load_player_stats_dataframe(session, timeframe)`

Returns DataFrame with player stats.

**Example:**
```python
from db.db_extract import load_player_stats_dataframe

df = load_player_stats_dataframe(session, "season_long")
# Returns: DataFrame with all player stats for season
```

#### Game Matchup Queries

**Function:** `load_game_matchup_dataframe(session, game_date_est)`

Returns DataFrame with matchup data for a specific date.

**Example:**
```python
from db.db_extract import load_game_matchup_dataframe
import datetime

df = load_game_matchup_dataframe(session, datetime.date(2024, 11, 5))
# Returns: DataFrame with all matchup metrics for all teams on 2024-11-05
```

#### League Baselines

**Function:** `compute_league_baselines(session, timeframe)`

Returns tuple of (league_avg_pace, league_avg_pp100).

**Example:**
```python
from db.db_extract import compute_league_baselines

lg_pace, lg_pp100 = compute_league_baselines(session, "last_10")
# Returns: (100.5, 114.2)
```

---

## Database Connection

### Environment Variable

```bash
export DATABASE_URL="postgresql+psycopg://user:password@host:5432/dbname?sslmode=require"
```

**Format Components:**
- `postgresql+psycopg` - SQLAlchemy dialect + driver
- `user:password` - Database credentials
- `host:5432` - Database host and port
- `dbname` - Database name
- `?sslmode=require` - SSL required (for Neon)

### Connection Management

**Module:** `db/database.py`

**Functions:**

```python
from db.database import get_engine, get_session_maker

# Get SQLAlchemy engine
engine = get_engine(database_url=None)  # Uses DATABASE_URL env var

# Get session maker
SessionLocal = get_session_maker(engine)

# Use session
with SessionLocal() as session:
    # Perform queries
    result = session.execute(text("SELECT * FROM game_schedule"))
```

**Parameters:**
- `database_url` (Optional[str]) - Connection string. If None, uses DATABASE_URL env var.

---

## Table Creation

### Manual Creation

**Script:** `db/create_tables.py`

**Purpose:** Create all database schemas and tables.

**Usage:**

```bash
# Create tables (uses DATABASE_URL env var)
python -m db.create_tables

# Specify database URL
python -m db.create_tables --database-url $DATABASE_URL
```

**Process:**
1. Create schemas: `player_data`, `team_data`, `analysis`
2. Create all tables using SQLAlchemy models
3. Uses `checkfirst=True` - safe to run multiple times (idempotent)

**Programmatic:**
```python
from db.create_tables import create_all

create_all(database_url=None)  # Uses DATABASE_URL env var
```

### Automatic Creation

Tables are automatically created (if not exist) when running:
- `db.run_daily_update`
- Any ingestion script

---

## Data Flows

### Initial Setup Flow

```
1. Create Neon PostgreSQL database
2. Set DATABASE_URL environment variable
3. Run: python -m db.create_tables
4. Run: python -m db.run_daily_update
   ├── Creates/verifies schemas and tables
   ├── Fetches game schedule from Odds API
   ├── Fetches team stats from NBA API (4 timeframes)
   └── Fetches player stats from NBA API (4 timeframes)
5. Database is ready for analysis module
```

### Daily Update Flow

```
python -m db.run_daily_update
    │
    ├─→ Create/verify schemas and tables
    │
    ├─→ Fetch today's games
    │   └─→ Odds API → game_schedule table
    │
    ├─→ Fetch team stats (sl, l10, l5, l3)
    │   └─→ NBA API → team_data.team_stats_* tables (REPLACE)
    │
    └─→ Fetch player stats (sl, l10, l5, l3)
        └─→ NBA API → player_data.player_stats_* tables (REPLACE)
```

### Analysis Flow

```
Analysis Module (external)
    │
    ├─→ Read: game_schedule
    ├─→ Read: team_data.team_stats_*
    ├─→ Read: player_data.player_stats_*
    │
    ├─→ Compute game matchups
    │   └─→ Write: analysis.game_matchup (UPSERT)
    │
    └─→ Compute player projections
        └─→ Write: CSV file (or optionally analysis.player_projections)
```

---

## Typical Workflows

### Daily Production Workflow

```bash
# Morning: Update all data
python -m db.run_daily_update --season 2024-25

# Verify data loaded
psql $DATABASE_URL -c "SELECT COUNT(*) FROM player_data.player_stats_sl"
psql $DATABASE_URL -c "SELECT * FROM game_schedule WHERE game_date_est = CURRENT_DATE"

# Run analysis (external to db module)
python -m analysis.game_matchup
python -m analysis.player_proj
```

### Historical Data Backfill

```bash
# Load stats for specific past season
python -m db.db_insert.ingest_team_stats_to_db \
  --season 2023-24 \
  --season-type "Regular Season"

python -m db.db_insert.ingest_player_stats_to_db \
  --season 2023-24 \
  --season-type "Regular Season"
```

### Verify Database State

```bash
# Check row counts
psql $DATABASE_URL -c "
SELECT 
  'player_stats_sl' as table_name, COUNT(*) as rows FROM player_data.player_stats_sl
UNION ALL
SELECT 'player_stats_l10', COUNT(*) FROM player_data.player_stats_l10
UNION ALL
SELECT 'team_stats_sl', COUNT(*) FROM team_data.team_stats_sl
UNION ALL
SELECT 'game_schedule', COUNT(*) FROM game_schedule
UNION ALL
SELECT 'game_matchup', COUNT(*) FROM analysis.game_matchup
"

# Check latest data dates
psql $DATABASE_URL -c "
SELECT MAX(current_date) as latest_player_data 
FROM player_data.player_stats_sl
"
```

---

## Environment Variables

```bash
# Required
export DATABASE_URL="postgresql+psycopg://user:pass@host/db?sslmode=require"

# Optional (for Odds API)
export ODDS_API_BASE_URL="http://localhost:8000/api"

# Optional (for debugging)
export DB_ECHO="1"  # Echo SQL queries
```

---

## Troubleshooting

### "Connection refused" or "Could not connect to server"

**Cause:** Database URL is incorrect or database is not accessible.

**Solutions:**
1. Verify DATABASE_URL is set: `echo $DATABASE_URL`
2. Test connection: `psql $DATABASE_URL -c "SELECT 1"`
3. Check Neon console for database status
4. Verify SSL mode is included: `?sslmode=require`

### "relation does not exist"

**Cause:** Tables haven't been created.

**Solution:**
```bash
python -m db.create_tables
```

### "nba_api" rate limit errors

**Cause:** NBA API rate limiting.

**Solutions:**
1. Wait 60 seconds between runs
2. The scripts include sleep delays between requests
3. Don't run multiple ingestion scripts simultaneously

### Stale data in tables

**Cause:** Stats tables use `if_exists='replace'` - entire table is replaced each run.

**Solutions:**
1. Check `current_date` column to verify data freshness
2. Re-run ingestion: `python -m db.run_daily_update`

### Team name mismatches

**Cause:** Different sources use different team name formats.

**Solution:**
- Use `resolve_team_record()` helper function
- Handles common aliases automatically
- See `db/db_extract/extractors.py` for alias mappings

### "SSL SYSCALL error: EOF detected"

**Cause:** Neon connection dropped (serverless timeout).

**Solution:**
- Sessions should be short-lived
- Use context managers: `with SessionLocal() as session:`
- Don't hold connections open for extended periods

---

## Performance Considerations

### Ingestion Performance

- **Player Stats:** ~30-60 seconds (32 API calls)
- **Team Stats:** ~10-15 seconds (8 API calls)
- **Game Schedule:** < 1 second (1 API call)
- **Total Daily Update:** ~45-75 seconds

### Query Performance

- All tables have primary keys for fast lookups
- Consider adding indexes on frequently queried columns:
  ```sql
  CREATE INDEX idx_player_stats_sl_player ON player_data.player_stats_sl(player);
  CREATE INDEX idx_team_stats_sl_team ON team_data.team_stats_sl(team_name);
  CREATE INDEX idx_game_schedule_date ON game_schedule(game_date_est);
  ```

### Database Size

Approximate sizes:
- `player_stats_*` (4 tables): ~2-3 MB each (~450 players × 59 columns)
- `team_stats_*` (4 tables): ~50 KB each (30 teams × 36 columns)
- `game_schedule`: ~10 KB (season schedule)
- `game_matchup`: ~50 KB per date (12 games × 2 teams × 80 columns)
- **Total:** ~15-20 MB for current season data

---

## Frontend Integration

### REST API Recommendations

When building an API layer to expose database data:

```
GET /api/schedule?date=2024-11-05
  → Query: game_schedule WHERE game_date_est = '2024-11-05'

GET /api/players/stats?timeframe=last_5
  → Query: player_data.player_stats_l5

GET /api/teams/stats?timeframe=season_long
  → Query: team_data.team_stats_sl

GET /api/matchups?date=2024-11-05
  → Query: analysis.game_matchup WHERE game_date_est = '2024-11-05'

GET /api/players/{player_name}/stats
  → Query: player_data.player_stats_* WHERE player = {player_name}

GET /api/teams/{team_name}/stats
  → Query: team_data.team_stats_* WHERE team_name = {team_name}
```

### Direct Database Access

For frontend apps with direct database access:

```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine(DATABASE_URL)

# Load player stats
df = pd.read_sql(
    "SELECT * FROM player_data.player_stats_l5 WHERE team = 'LAL'",
    engine
)

# Load today's games
games = pd.read_sql(
    "SELECT * FROM game_schedule WHERE game_date_est = CURRENT_DATE",
    engine
)

# Load matchup data
matchups = pd.read_sql(
    "SELECT * FROM analysis.game_matchup WHERE game_date_est = '2024-11-05'",
    engine
)
```

### GraphQL Schema Recommendations

```graphql
type Player {
  id: ID!
  player: String!
  team: String!
  stats: PlayerStats!
}

type PlayerStats {
  seasonLong: StatLine!
  last10: StatLine!
  last5: StatLine!
  last3: StatLine!
}

type StatLine {
  gp: Float
  min: Float
  pts: Float
  reb: Float
  ast: Float
  # ... all other stats
}

type Query {
  players(team: String, timeframe: String): [Player!]!
  player(name: String!): Player
  teams(timeframe: String): [Team!]!
  schedule(date: Date!): [Game!]!
  matchups(date: Date!): [GameMatchup!]!
}
```

---

## Schema Evolution

### Adding Columns

To add new columns to existing tables:

1. Update model in `db/models.py`
2. Run migration (using Alembic or manual ALTER TABLE)
3. Update ingestion scripts to populate new columns
4. Update extraction helpers if needed

**Example:**
```python
# In models.py
class PlayerStatsSL(Base):
    # ... existing columns ...
    new_metric = Column(Float, nullable=True)

# Migration SQL
ALTER TABLE player_data.player_stats_sl 
ADD COLUMN new_metric FLOAT;
```

### Versioning

- `game_matchup` table includes `calc_version` field for tracking calculation changes
- Consider adding `schema_version` to other tables for major schema changes
- Use `current_date` to track data freshness

---

## Backup and Recovery

### Neon Automatic Backups

Neon provides automatic backups. Check Neon console for:
- Point-in-time recovery
- Branch creation for testing

### Manual Backups

```bash
# Backup entire database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Backup specific schema
pg_dump $DATABASE_URL -n player_data > backup_player_data.sql

# Restore
psql $DATABASE_URL < backup_20241105.sql
```

### Re-ingestion

Since all data comes from external APIs, you can always re-ingest:

```bash
# Re-populate entire database
python -m db.run_daily_update --season 2024-25
```

---

## Security

### Connection Security

- Always use SSL: `?sslmode=require`
- Use environment variables for credentials, never hardcode
- Neon provides automatic connection pooling and security

### Access Control

Consider creating read-only database users for frontend access:

```sql
-- Create read-only user
CREATE USER frontend_readonly WITH PASSWORD 'secure_password';

-- Grant read access to schemas
GRANT USAGE ON SCHEMA player_data TO frontend_readonly;
GRANT USAGE ON SCHEMA team_data TO frontend_readonly;
GRANT USAGE ON SCHEMA analysis TO frontend_readonly;

-- Grant SELECT on tables
GRANT SELECT ON ALL TABLES IN SCHEMA player_data TO frontend_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA team_data TO frontend_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA analysis TO frontend_readonly;
```

---

## Dependencies

### Python Packages

```toml
# From pyproject.toml
[project]
dependencies = [
    "sqlalchemy>=2.0.0",      # ORM
    "psycopg>=3.0.0",         # PostgreSQL driver
    "nba_api>=1.0.0",         # NBA.com API client
    "pandas>=2.0.0",          # Data manipulation
]
```

### External Services

- **Neon PostgreSQL** - Database hosting
- **NBA.com API** - Player and team statistics (via nba_api)
- **Odds API** - Game schedule (via odds_api_retrieval module)

---

## API Rate Limits

### NBA API

- No official rate limit, but recommended: 1 request per second
- Scripts include `time.sleep(1)` between requests
- ~40 requests per daily update (player + team stats)

### Odds API

- Rate limits depend on your Odds API plan
- Daily update makes 1 request for schedule
- See `odds_api_retrieval/AGENTS.md` for details

---

## Monitoring and Logging

### Check Data Freshness

```sql
-- Check when data was last updated
SELECT 
    'player_stats_sl' as table_name,
    MAX(current_date) as latest_data,
    COUNT(*) as row_count
FROM player_data.player_stats_sl
UNION ALL
SELECT 
    'team_stats_sl',
    MAX(current_date),
    COUNT(*)
FROM team_data.team_stats_sl;
```

### Check for Missing Data

```sql
-- Find teams without stats
SELECT DISTINCT team FROM player_data.player_stats_sl
WHERE team NOT IN (SELECT team_name FROM team_data.team_stats_sl);

-- Find dates without schedule
SELECT game_date_est, COUNT(*) as games
FROM game_schedule
GROUP BY game_date_est
ORDER BY game_date_est DESC
LIMIT 30;
```

---

## Notes for LLM/Agent Implementation

1. **Idempotent Operations:** All ingestion scripts are safe to re-run
   - Stats ingestion uses `if_exists='replace'`
   - Schedule ingestion uses `ON CONFLICT DO NOTHING`
   - Matchup calculation uses upsert

2. **Execution Order:** For daily updates, order doesn't matter between team and player stats, but both should run before analysis

3. **Error Handling:** Scripts will raise exceptions on failure. Wrap in try/except for production:
   ```python
   try:
       run_daily_update()
   except Exception as e:
       logger.error(f"Daily update failed: {e}")
       send_alert()
   ```

4. **Database Sessions:** Always use context managers:
   ```python
   with SessionLocal() as session:
       # Do work
       pass
   # Session automatically closed
   ```

5. **Timeframe Consistency:** Always use timeframe names: "season_long", "last_10", "last_5", "last_3" (not sl, l10, etc.)

6. **Team Name Handling:** Use `resolve_team_record()` for all team name lookups to handle aliases

7. **Data Validation:** After ingestion, verify row counts are reasonable:
   - Player stats: 400-500 players
   - Team stats: 30 teams
   - Game schedule: 10-15 games per day

8. **Connection Pooling:** Neon handles this automatically, no need to implement

---

## Version History

- **v1.0** - Initial schema with player_data and team_data
- **v1.1** - Added analysis schema for game_matchup
- **v1.2** - Added player_projections table (optional)
- **v1.3** - Enhanced team name aliasing

---

## References

- **SQLAlchemy 2.0 Docs:** https://docs.sqlalchemy.org/
- **nba_api Documentation:** https://github.com/swar/nba_api
- **Neon PostgreSQL:** https://neon.tech/docs
- See `db/README.md` for setup instructions
- See `stats_retrieval/AGENTS.md` for NBA API details
- See `odds_api_retrieval/AGENTS.md` for Odds API details

