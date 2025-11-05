# Player Projections Database Integration

## Overview

Player projections can now be saved to the database in addition to CSV export. This provides historical tracking and enables programmatic access to projection data.

## Database Schema

### Table: `analysis.player_projection`

**Location**: Stored in the `analysis` schema alongside `game_matchup`

**Primary Key**: Auto-incrementing `id`

**Unique Constraint**: `(game_date, player, team)` - One projection per player per team per date

### Columns

#### Identity Columns
- `game_date` (Date): The date of the game
- `player` (String): Player name from CSV
- `db_player` (String): Matched database player name (from fuzzy matching)
- `pos` (String): Position
- `team` (String): Team abbreviation (e.g., 'MIL', 'LAL')
- `team_full_name` (String): Full team name (e.g., 'Milwaukee Bucks')
- `opp` (String): Opponent abbreviation
- `opp_full_name` (String): Full opponent name
- `status` (String): Player status (P, Q, etc.)
- `game_info` (String): Game information

#### Base Projections
- `salary` (Float): FanDuel salary
- `proj_mins` (Float): Projected minutes
- `ownership` (Float): Projected ownership percentage

#### Key Outputs
- `fp_proj` (Float): **Final weighted fantasy point projection**
- `projected_value` (Float): **Points per $1000 of salary**

#### Team Aggregates
- `team_salary`: Total team salary
- `salary_share`: Player's % of team salary
- `team_ownership`: Total team ownership
- `team_minutes`: Total projected team minutes
- `minutes_avail`: Available minutes (240 - team_minutes)

#### Period-Specific Metrics

For each period (sl, l10, l5, l3), the following metrics are stored:

**Base Stats**:
- `gp_{period}`: Games played
- `usg_pct_{period}`: Usage percentage
- `fp_{period}`: Fantasy points
- `touches_{period}`: Total touches
- `min_{period}`: Minutes
- `poss_{period}`: Possessions

**Rate Stats**:
- `fppm_{period}`: Fantasy points per minute
- `fppt_{period}`: Fantasy points per touch
- `fppp_{period}`: Fantasy points per possession
- `tpm_{period}`: Touches per minute
- `tpp_{period}`: Touches per possession

**Team Context**:
- `team_poss_{period}`: Team total possessions
- `poss_pct_{period}`: Player's % of team possessions

**Touch Projections**:
- `implied_poss_{period}`: Implied possessions from matchup
- `touches_ip_{period}`: Implied touches (from possessions)
- `touches_tpm_{period}`: Implied touches (from TPM rate)

**Fantasy Projections**:
- `fp_proj_it_{period}`: Fantasy points (Implied Touches method)
- `fp_proj_tpm_{period}`: Fantasy points (TPM method)

**Team Fantasy Context**:
- `team_fp_{period}`: Team total fantasy points
- `fp_per_{period}`: Player's % of team fantasy points

#### Metadata
- `calc_version` (String): Version of calculation algorithm (e.g., 'v1')
- `created_at` (DateTime): When record was created
- `updated_at` (DateTime): When record was last updated

## Usage

### Creating the Table

Run once to create the table:

```bash
python -m db.create_tables
```

This creates the `analysis.player_projection` table along with all other tables.

### Running Projections with Database Save

#### Command Line

```bash
# Save to both CSV and database
python -m analysis.player_proj --save-to-db

# With specific date
python -m analysis.player_proj --date 2024-11-10 --save-to-db

# With custom database URL
python -m analysis.player_proj --save-to-db --database-url postgresql://user:pass@localhost/nba
```

#### Programmatic Usage

```python
from pathlib import Path
import datetime
from analysis.player_proj import build_projections

# Build and save to database
df = build_projections(
    daily_proj_path=Path("analysis/daily_player_intake/daily_proj.csv"),
    game_date=datetime.date(2024, 11, 5),
    database_url=None,  # Uses DATABASE_URL env var
    save_to_db=True  # Enable database save
)
```

### Manually Ingesting Existing CSV

If you have existing projection CSVs you want to add to the database:

```bash
python -m db.db_insert.ingest_player_projections_to_db \
  --csv analysis/daily_player_intake/player_projections_2024-11-05.csv
```

## Data Behavior

### Replace Logic

The system uses a **delete-then-insert** approach for each date:

1. **Delete**: Removes all existing projections for the game_date(s) in the DataFrame
2. **Insert**: Adds all new projection records

**Why this approach?**
- Handles changes in player availability (injuries, rest, etc.)
- Handles changes in minutes projections throughout the day
- Ensures no stale data if a player is removed from projections
- Clean slate for each date when re-running

**Examples:**
- Run projections for Nov 5 → Inserts 180 players
- Update and re-run for Nov 5 → Deletes 180 old records, inserts 175 new (5 players now injured)
- Run projections for Nov 6 → Nov 5 data unchanged, Nov 6 inserted as new date

### What Gets Saved

All calculated columns from the projection DataFrame are saved, including:
- All identity and base projection columns
- All period-specific metrics (sl, l10, l5, l3)
- All calculated rates and projections
- Team aggregates
- Final weighted projections

## Querying Projections

### SQL Examples

```sql
-- Get latest projections for a date
SELECT game_date, player, team, salary, proj_mins, fp_proj, projected_value
FROM analysis.player_projection
WHERE game_date = '2024-11-05'
ORDER BY fp_proj DESC
LIMIT 10;

-- Get high-value plays (salary < $6000)
SELECT player, team, salary, fp_proj, projected_value
FROM analysis.player_projection
WHERE game_date = '2024-11-05'
  AND salary < 6000
ORDER BY projected_value DESC
LIMIT 20;

-- Compare projection methods for a player
SELECT 
    player,
    team,
    fp_proj_it_l5,
    fp_proj_tpm_l5,
    fp_proj_it_l3,
    fp_proj_tpm_l3,
    fp_proj
FROM analysis.player_projection
WHERE game_date = '2024-11-05'
  AND player = 'Giannis Antetokounmpo';

-- Track projection accuracy over time (requires actual results)
SELECT 
    game_date,
    player,
    fp_proj,
    -- Add actual_fp from results table when available
    -- actual_fp - fp_proj AS projection_error
FROM analysis.player_projection
WHERE player = 'LeBron James'
ORDER BY game_date DESC
LIMIT 10;

-- Team-level analysis
SELECT 
    game_date,
    team,
    COUNT(*) as players,
    AVG(fp_proj) as avg_proj,
    SUM(fp_proj) as total_proj,
    AVG(projected_value) as avg_value
FROM analysis.player_projection
WHERE game_date = '2024-11-05'
GROUP BY game_date, team
ORDER BY total_proj DESC;
```

### Python Examples

```python
from db.database import get_engine, get_session_maker
from sqlalchemy import text
import pandas as pd

engine = get_engine()

# Get projections for a date
query = """
    SELECT *
    FROM analysis.player_projection
    WHERE game_date = :date
    ORDER BY fp_proj DESC
"""
df = pd.read_sql(text(query), engine, params={"date": "2024-11-05"})

# Get top value plays
query = """
    SELECT player, team, salary, fp_proj, projected_value
    FROM analysis.player_projection
    WHERE game_date = :date AND salary < 6000
    ORDER BY projected_value DESC
    LIMIT 20
"""
value_plays = pd.read_sql(text(query), engine, params={"date": "2024-11-05"})

# Historical projections for a player
query = """
    SELECT game_date, opp, fp_proj, projected_value, salary
    FROM analysis.player_projection
    WHERE player = :player
    ORDER BY game_date DESC
"""
history = pd.read_sql(text(query), engine, params={"player": "LeBron James"})
```

## Benefits of Database Storage

1. **Historical Tracking**: Keep all past projections for analysis
2. **Programmatic Access**: Query projections from other scripts
3. **Comparison**: Compare different projection dates or methods
4. **Integration**: Join with other tables (matchups, actual results)
5. **Backup**: Database backup includes projection history
6. **Audit Trail**: `created_at` and `updated_at` track changes

## Notes

- Database save is **optional** (use `--save-to-db` flag)
- CSV export still happens regardless of database setting
- Database save is non-blocking - errors won't stop CSV export
- Table automatically created if it doesn't exist
- Safe to run multiple times - deletes old data for the date, then inserts new
- Different dates append to database (only matching dates are replaced)

## Troubleshooting

### "Table doesn't exist"

```bash
python -m db.create_tables
```

### "Too many columns" or "Column not found"

The ingest script automatically filters to only columns that exist in the model. If you add new columns to the DataFrame, you may need to add them to the `PlayerProjection` model.

### Performance

- Initial insert of ~200 players: < 1 second
- Includes automatic indexing on unique constraint
- No performance impact on CSV-only workflow

## Future Enhancements

Potential additions:
- Store actual results and calculate accuracy metrics
- Add indexes for common query patterns
- Materialized views for aggregations
- Historical comparison queries
- API endpoints for projection data

