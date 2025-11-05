# NBA Sharp - Database Setup (Neon)

## Neon Postgres Setup

1. Create a Neon project and database.
   - In the Neon console, create a new project and note the connection details.
   - Create a database (e.g., `nbasharp`).
2. Get your connection string.
   - Choose the `psql` or `SQLAlchemy` style URL with SSL required.
   - Format (SQLAlchemy):
     - `postgresql+psycopg://<user>:<password>@<host>/<database>?sslmode=require`
3. Set the environment variable locally:
   - macOS/Linux (zsh):
     ```bash
     export DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST/DBNAME?sslmode=require"
     ```
   - Or pass `--database-url` directly to the creation script.

## Install Dependencies

```bash
uv sync
```

## Create Tables

This project includes a `game_schedule` table with `game_date_est` (DATE), `away_team`, `home_team`, plus timestamps and a uniqueness constraint on `(game_date_est, away_team, home_team)`.

Run the creation script (no-op if tables already exist):

```bash
python /Users/lmarte/Documents/Projects/sharp/nba_sharp/db/create_tables.py --database-url "$DATABASE_URL"
```

Alternatively, rely on the environment variable:

```bash
export DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST/DBNAME?sslmode=require"
python /Users/lmarte/Documents/Projects/sharp/nba_sharp/db/create_tables.py
```

## Model: GameSchedule

- game_date_est: DATE (represents the calendar date in America/New_York)
- away_team: VARCHAR(64)
- home_team: VARCHAR(64)
- created_at, updated_at: timestamptz with defaults
- Unique: `(game_date_est, away_team, home_team)`

Note: We intentionally store the local game date as a DATE in EST. If you later need exact tipoff times in UTC, we can add a `game_datetime_utc TIMESTAMPTZ` plus a stored generated `game_date_est` column for consistency.

## Ingest Today's NBA Events into game_schedule

Fetch events from the Odds API and upsert into `game_schedule` (EST calendar date):

```bash
export DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST/DBNAME?sslmode=require"

# Default: interpret 'today' in Eastern Time, query Odds API, upsert rows
python /Users/lmarte/Documents/Projects/sharp/nba_sharp/db/db_insert/ingest_today_nba_events_to_db.py

# Specify a custom base URL and date/timezone if needed
python /Users/lmarte/Documents/Projects/sharp/nba_sharp/db/db_insert/ingest_today_nba_events_to_db.py \
  --base-url https://dummy-odds.example.com/api \
  --date 2025-11-03 \
  --tz America/New_York

# Dry-run (no DB writes)
python /Users/lmarte/Documents/Projects/sharp/nba_sharp/db/db_insert/ingest_today_nba_events_to_db.py --dry-run
```

