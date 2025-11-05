# Analysis Module - NBA Player Projections & Game Matchups

## Overview

The Analysis module is the analytical layer of the NBA Sharp system that transforms raw statistical data into actionable fantasy projections and game matchups. It consists of two main services:

1. **Game Matchup Calculator** - Computes pace, scoring, and possession projections for each game
2. **Player Projections System** - Generates weighted fantasy point projections by combining daily baselines with historical performance

This module sits between the database layer and the end-user frontend, consuming stored statistics and producing projection outputs.

---

## Module Structure

```
analysis/
├── game_matchup.py          # Game-level projections (pace, points, possessions)
├── player_proj.py           # Player-level fantasy projections
├── verify_setup.py          # Setup verification script
├── utils/
│   ├── data_utils.py        # Excel-like helper functions
│   ├── name_matcher.py      # Fuzzy name matching
│   └── examples.py          # Usage examples
├── daily_player_intake/
│   └── daily_proj.csv       # Input: Daily baseline projections (manual)
└── README.md                # Detailed documentation
```

---

## Service 1: Game Matchup Calculator

### Purpose

Computes game-level projections for each NBA matchup on a given date, including:
- Implied possessions per team
- Expected points scored
- Projected total
- Pace adjustments
- Home court advantage effects

These projections are **prerequisites** for player projections because they provide game context needed for player-level calculations.

### Location

`analysis/game_matchup.py`

### Dependencies

**Database Tables (Read):**
- `game_schedule` - Schedule of games for the target date
- `team_data.team_stats_sl` - Season-long team stats
- `team_data.team_stats_l10` - Last 10 games team stats
- `team_data.team_stats_l5` - Last 5 games team stats
- `team_data.team_stats_l3` - Last 3 games team stats

**Database Tables (Write):**
- `analysis.game_matchup` - Output table with game projections

### Key Inputs

- `game_date` - Date to calculate matchups for (defaults to today)
- Team stats across 4 timeframes (sl, l10, l5, l3)
  - pace: Team pace (possessions per game)
  - offrtg: Offensive rating (points per 100 possessions)
  - defrtg: Defensive rating (points allowed per 100 possessions)

### Calculation Process

For each game and timeframe, the system:

1. **Load Schedule** - Fetch all games for the date
2. **Load Team Stats** - Retrieve stats for home and away teams across all timeframes
3. **Calculate League Baselines** - Compute league-average pace and points per 100 possessions
4. **Apply Home Court Advantage (HCA)**:
   - Home team: +0.3 possessions, +0.5 points per 100
   - Away team: -0.3 possessions, -0.5 points per 100
5. **Compute Implied Possessions**:
   ```
   implied_poss = (home_pace_adj + away_pace_adj) / 2
   ```
6. **Project Points**:
   ```
   exp_pp100 = lg_pp100 + 0.5 * (team_offrtg - lg_pp100) + 0.5 * (lg_pp100 - opp_defrtg)
   proj_pts = exp_pp100 * implied_poss / 100
   ```
7. **Compute Matchup Metrics**:
   - proj_total: Combined projected score
   - matchup: Point differential
   - pts_allowed_pg: Expected points allowed

### Output Schema

Each row in `analysis.game_matchup` represents one team's perspective of a game:

**Identifiers:**
- `game_date_est` - Game date in Eastern Time
- `team_name` - Team name
- `opp_team_name` - Opponent name
- `is_home` - Boolean (home vs away)
- `team_id`, `opp_team_id` - Team IDs

**Metrics (per timeframe: _sl, _l10, _l5, _l3):**
- `pace_{tf}` - Team pace
- `opp_pace_{tf}` - Opponent pace
- `lg_pace_{tf}` - League average pace
- `poss_above_lg_{tf}` - Pace differential vs league
- `implied_poss_{tf}` - **Projected possessions for this game**
- `offrtg_{tf}`, `defrtg_{tf}` - Team ratings
- `opp_offrtg_{tf}`, `opp_defrtg_{tf}` - Opponent ratings
- `lg_pp100_{tf}` - League points per 100 possessions
- `hca_poss_adj_{tf}` - Home court possession adjustment
- `hca_pp100_adj_{tf}` - Home court points adjustment
- `exp_pp100_{tf}` - Expected points per 100 possessions
- `proj_pts_{tf}` - **Projected points**
- `opp_proj_pts_{tf}` - Opponent projected points
- `proj_total_{tf}` - **Projected game total**
- `matchup_{tf}` - **Point differential**
- `pts_allowed_pg_{tf}` - Expected points allowed

### Usage

**Command Line:**
```bash
# Calculate matchups for today
python -m analysis.game_matchup

# Calculate for specific date
python -m analysis.game_matchup --date 2024-11-05

# Custom database
python -m analysis.game_matchup --date 2024-11-05 --database-url $DATABASE_URL
```

**Programmatic:**
```python
from analysis.game_matchup import run
import datetime

# Compute matchups
count = run(
    game_date=datetime.date(2024, 11, 5),
    database_url=None  # Uses DATABASE_URL env var
)
print(f"Computed matchups for {count} team perspectives")
```

### Integration Notes

1. **Must run AFTER** `db.run_daily_update` to ensure team stats are current
2. **Must run BEFORE** `analysis.player_proj` because player projections need `implied_poss_{tf}`
3. Upserts data (safe to re-run for same date)
4. Handles team name aliases (e.g., "Los Angeles Lakers" = "LA Lakers" = "L.A. Lakers")

---

## Service 2: Player Projections System

### Purpose

Generates comprehensive fantasy point projections for NBA players by:
1. Loading daily baseline projections (salary, minutes, ownership)
2. Merging historical performance across multiple timeframes
3. Computing rate-based metrics (points per minute, per touch, per possession)
4. Generating weighted projections using multiple methods
5. Calculating value metrics (points per $1000 of salary)

### Location

`analysis/player_proj.py`

### Dependencies

**Database Tables (Read):**
- `player_data.player_stats_sl` - Season-long player stats
- `player_data.player_stats_l10` - Last 10 games player stats
- `player_data.player_stats_l5` - Last 5 games player stats
- `player_data.player_stats_l3` - Last 3 games player stats
- `team_data.team_stats_{timeframe}` - Team context stats
- `analysis.game_matchup` - Game projections (from game_matchup.py)

**Database Tables (Write):**
- `analysis.player_projections` - (Optional) Output projections to DB

**File Inputs:**
- `analysis/daily_player_intake/daily_proj.csv` - Daily baseline projections (manually sourced)

**File Outputs:**
- `analysis/daily_player_intake/player_projections_{date}.csv` - Final projections

### Daily Projections CSV Format

**Required Columns:**
- `Name` - Player name
- `Pos` - Position
- `Team` - Team abbreviation (e.g., LAL, BOS)
- `Opp` - Opponent abbreviation
- `Salary` - DFS salary
- `Min` - Projected minutes
- `Adj Own` - Projected ownership percentage

**Optional Columns:**
- `Status` - Injury status
- `gameInfo` - Game context information

### Calculation Pipeline

The system executes the following pipeline for each player:

#### 1. Data Loading & Name Matching

- Load daily CSV projections
- Filter players with < 15 projected minutes or no salary
- Map team abbreviations to full names
- Use fuzzy matching (85% threshold) to map player names to database
- Handle missing recent data by falling back to longer timeframes

#### 2. Historical Stats Merge

For each timeframe (sl, l10, l5, l3), extract:
- `gp` - Games played
- `usg_pct` - Usage percentage
- `fp` - Fantasy points
- `touches` - Ball touches
- `min` - Minutes played
- `poss` - Possessions

#### 3. Rate-Based Metrics

Calculate efficiency metrics for each timeframe:

- **fppm** (Fantasy Points Per Minute):
  ```
  fppm = fp / min
  ```

- **fppt** (Fantasy Points Per Touch):
  ```
  fppt = fp / touches
  ```

- **fppp** (Fantasy Points Per Possession):
  ```
  fppp = fp / (poss / gp)
  ```

- **tpm** (Touches Per Minute):
  ```
  tpm = touches / min
  ```

- **tpp** (Touches Per Possession):
  ```
  tpp = touches / (poss / gp)
  ```

#### 4. Team Context

- **poss_pct** - Player's share of team possessions:
  ```
  poss_pct = (player_poss / team_poss) * 100
  ```

#### 5. Touch Projections (Two Methods)

**Method 1: Implied Possessions (IP)**
```
touches_ip = (poss_pct / 100) * tpp * implied_poss
```
Uses game's projected possessions from matchup data.

**Method 2: Touches Per Minute (TPM)**
```
touches_tpm = tpm * proj_mins
```
Uses projected playing time.

#### 6. Fantasy Point Projections

**Method 1: IT (Implied Touches)**
```
fp_proj_it = fppt * touches_ip
```

**Method 2: TPM (Touches Per Minute)**
```
fp_proj_tpm = fppt * touches_tpm
```

#### 7. Team Aggregates

Calculate team-level context:
- `team_salary` - Sum of team salaries
- `salary_share` - Player's % of team salary
- `team_ownership` - Sum of team ownership
- `team_minutes` - Total projected minutes
- `minutes_avail` - Available minutes (240 - team_minutes)

#### 8. Final Weighted Projection

Combine all 8 projections (4 timeframes × 2 methods):

**Weights for TPM Method:**
- sl: 1
- l10: 4
- l5: 8 (highest - most recent form)
- l3: 4

**Weights for IT Method:**
- sl: 1
- l10: 3
- l5: 6
- l3: 3

**Final Calculation:**
```
fp_proj = Σ(projection * weight) / Σ(weights)
projected_value = fp_proj / (salary / 1000)
```

### Output Schema

**Core Projection Columns:**
- `player` - Player name
- `pos` - Position
- `team` - Team abbreviation
- `opp` - Opponent abbreviation
- `salary` - DFS salary
- `proj_mins` - Projected minutes
- `ownership` - Projected ownership %
- `fp_proj` - **Final weighted fantasy point projection**
- `projected_value` - **Points per $1000 of salary**

**Context Columns:**
- `salary_share` - % of team salary
- `team_minutes` - Total team minutes
- `minutes_avail` - Available minutes
- `game_date` - Game date

**Historical Performance (per timeframe):**
- `fp_{tf}` - Historical fantasy points
- `fppm_{tf}` - Fantasy points per minute
- `usg_pct_{tf}` - Usage percentage
- `touches_{tf}` - Touches
- `fp_proj_it_{tf}` - IT method projection
- `fp_proj_tpm_{tf}` - TPM method projection

Output is sorted by `fp_proj` descending.

### Usage

**Command Line:**
```bash
# Run projections for today
python -m analysis.player_proj

# Specific date
python -m analysis.player_proj --date 2024-11-05

# Custom CSV path
python -m analysis.player_proj --csv ~/Downloads/daily_proj.csv

# Custom output path
python -m analysis.player_proj --output ~/my_projections.csv

# Save to database (in addition to CSV)
python -m analysis.player_proj --save-to-db

# Full example with all options
python -m analysis.player_proj \
  --date 2024-11-05 \
  --csv analysis/daily_player_intake/daily_proj.csv \
  --output analysis/daily_player_intake/player_projections_2024-11-05.csv \
  --database-url $DATABASE_URL
```

**Programmatic:**
```python
from pathlib import Path
import datetime
from analysis.player_proj import build_projections, save_projections

# Build projections
df = build_projections(
    daily_proj_path=Path("analysis/daily_player_intake/daily_proj.csv"),
    game_date=datetime.date(2024, 11, 5),
    database_url=None,  # Uses DATABASE_URL env var
    save_to_db=False
)

# Access top projections
top_10 = df.nlargest(10, 'fp_proj')[['player', 'team', 'salary', 'fp_proj', 'projected_value']]
print(top_10)

# Get high value plays
value_plays = df.nlargest(10, 'projected_value')

# Save to CSV
save_projections(df, Path("my_projections.csv"))
```

### Integration Notes

1. **Prerequisites:**
   - Database must have current player and team stats (run `db.run_daily_update`)
   - Game matchup data must exist (run `analysis.game_matchup`)
   - `daily_proj.csv` must be manually placed in `analysis/daily_player_intake/`

2. **Execution Order:**
   ```bash
   # 1. Update database stats
   python -m db.run_daily_update
   
   # 2. Calculate game matchups
   python -m analysis.game_matchup --date 2024-11-05
   
   # 3. Place daily_proj.csv in analysis/daily_player_intake/
   
   # 4. Run player projections
   python -m analysis.player_proj --date 2024-11-05
   ```

3. **Name Matching:**
   - Uses fuzzy matching (threshold: 0.85) to map CSV names to database names
   - Handles suffixes (Jr., Sr., II, III)
   - Reports unmatched names for manual review

4. **Missing Data Handling:**
   - If l3 stats are zero, copies from l5
   - If l5 is zero, copies from l10
   - If l10 is zero, copies from sl
   - Drops players with no data across all timeframes

---

## Utility Modules

### DataUtils (`utils/data_utils.py`)

Excel-like helper functions for data manipulation:

**Functions:**
- `xlookup(lookup_value, lookup_array, return_array, if_not_found)` - Excel XLOOKUP equivalent
- `sumif(range_array, criteria, sum_array)` - Excel SUMIF equivalent
- `safe_divide(numerator, denominator, default)` - Division with zero/null handling
- `coalesce(*values)` - Return first non-null value

**Example:**
```python
from analysis.utils import DataUtils

# Lookup player stat
pts = DataUtils.xlookup(
    "LeBron James",
    df['player'],
    df['pts'],
    if_not_found=0.0
)

# Sum team salary
team_total = DataUtils.sumif(
    df['team'],
    'LAL',
    df['salary']
)

# Safe division
ppg = DataUtils.safe_divide(total_pts, games_played, default=0.0)
```

### NameMatcher (`utils/name_matcher.py`)

Fuzzy name matching for handling name variations:

**Functions:**
- `normalize_name(name)` - Standardize name format
- `strip_suffix(name)` - Remove Jr., Sr., II, III suffixes
- `similarity_score(name1, name2)` - Calculate 0-1 similarity
- `find_best_match(target, candidates, threshold)` - Find best match
- `build_name_map(source_names, target_names, threshold)` - Build name mapping

**Example:**
```python
from analysis.utils import NameMatcher

# Build mapping between CSV names and DB names
name_map = NameMatcher.build_name_map(
    csv_players,
    db_players,
    threshold=0.85
)

# Find best match for a name
db_name = NameMatcher.find_best_match(
    "LeBron James Jr.",
    db_players,
    threshold=0.80
)
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     ANALYSIS MODULE                          │
└─────────────────────────────────────────────────────────────┘

INPUT (from DB):
├── game_schedule (game dates, teams)
├── team_data.team_stats_* (pace, ratings)
└── player_data.player_stats_* (performance stats)

INPUT (manual):
└── daily_proj.csv (salary, minutes, ownership)

PROCESSING:
├── game_matchup.py
│   ├── Load team stats across timeframes
│   ├── Calculate league baselines
│   ├── Apply HCA adjustments
│   ├── Compute implied possessions
│   └── Project points and totals
│
└── player_proj.py
    ├── Load daily baseline projections
    ├── Fuzzy match player names
    ├── Merge historical stats
    ├── Calculate rate metrics
    ├── Project touches (2 methods)
    ├── Project fantasy points (2 methods)
    ├── Weight projections across timeframes
    └── Calculate value metrics

OUTPUT:
├── analysis.game_matchup (DB table)
│   └── Game-level projections
│
└── player_projections_{date}.csv (file)
    └── Player-level fantasy projections
```

---

## Environment Variables

```bash
# Required
export DATABASE_URL="postgresql+psycopg://user:pass@host/db?sslmode=require"

# Optional
export ANALYSIS_DEBUG="1"  # Enable debug logging
```

---

## Typical Workflow

### Daily Update Workflow

```bash
# Morning: Update all stats in database
python -m db.run_daily_update --season 2024-25

# Calculate game matchups for today
python -m analysis.game_matchup

# Download daily_proj.csv and place in analysis/daily_player_intake/

# Generate player projections
python -m analysis.player_proj

# Output: analysis/daily_player_intake/player_projections_{today}.csv
```

### Historical Analysis Workflow

```bash
# Analyze specific past date
DATE="2024-11-01"

# Calculate matchups
python -m analysis.game_matchup --date $DATE

# Generate projections (if you have historical daily_proj.csv)
python -m analysis.player_proj \
  --date $DATE \
  --csv analysis/daily_player_intake/daily_proj_$DATE.csv \
  --output analysis/historical/projections_$DATE.csv
```

---

## Troubleshooting

### "No matchup data found for {date}"

**Cause:** Game matchup calculations haven't been run for this date.

**Solution:**
```bash
python -m analysis.game_matchup --date {date}
```

### "X players could not be matched to database"

**Cause:** Player names in CSV don't match database names.

**Solutions:**
1. Check name spelling/formatting
2. Ensure database has stats for these players
3. Adjust fuzzy matching threshold in code (default: 0.85)
4. Manually verify unmapped names are intentional (rookies, inactive players)

### "Dropping X players with no historical data"

**Cause:** Players have no stats in database for any timeframe.

**Reasons:**
- New players with 0 games played
- Inactive players not in current season
- Name mismatches preventing data lookup

**Solution:** This is expected for players without game history. They're filtered out.

### "File not found: daily_proj.csv"

**Cause:** Daily projections CSV is missing.

**Solution:**
1. Download daily projections from source
2. Save as `analysis/daily_player_intake/daily_proj.csv`
3. Or specify custom path: `--csv /path/to/file.csv`

### Projections seem off

**Checklist:**
1. Database stats are current: `python -m db.run_daily_update`
2. Game matchups are calculated: `python -m analysis.game_matchup`
3. Daily CSV is for correct date
4. Team abbreviations match between CSV and database
5. Check projection weights if recent form should be valued more/less

---

## Performance Notes

- **game_matchup.py**: Fast (< 1 second for typical slate)
- **player_proj.py**: Moderate (5-10 seconds for 150-200 players)
- Name matching is the slowest operation
- Database queries are optimized with proper indexes

---

## Frontend Integration

When building a frontend to consume this module:

### For Game Matchups

**Query:**
```sql
SELECT 
    game_date_est,
    team_name,
    opp_team_name,
    is_home,
    implied_poss_sl,
    implied_poss_l5,
    proj_pts_sl,
    proj_pts_l5,
    proj_total_sl,
    matchup_sl
FROM analysis.game_matchup
WHERE game_date_est = '2024-11-05'
ORDER BY team_name;
```

**Use Cases:**
- Display game pace and total projections
- Show matchup quality for each team
- Identify pace-up/pace-down spots

### For Player Projections

**Read CSV:**
```python
import pandas as pd

df = pd.read_csv("analysis/daily_player_intake/player_projections_2024-11-05.csv")

# Sort by value
top_values = df.nlargest(20, 'projected_value')

# Filter by position
guards = df[df['pos'].str.contains('PG|SG', regex=True)]

# Filter by salary range
mid_salary = df[(df['salary'] >= 6000) & (df['salary'] <= 8000)]
```

**Or Query Database:**
```sql
SELECT 
    player,
    pos,
    team,
    opp,
    salary,
    proj_mins,
    ownership,
    fp_proj,
    projected_value
FROM analysis.player_projections
WHERE game_date = '2024-11-05'
ORDER BY projected_value DESC
LIMIT 20;
```

### REST API Recommendations

If building an API layer:

```
GET /api/matchups?date=2024-11-05
GET /api/projections?date=2024-11-05
GET /api/projections?date=2024-11-05&position=PG
GET /api/projections?date=2024-11-05&min_value=5.0
GET /api/projections/player/{player_name}?date=2024-11-05
```

---

## Key Metrics Reference

### Game Matchup Metrics

| Metric | Description | Use Case |
|--------|-------------|----------|
| `implied_poss_{tf}` | Projected possessions | Core metric for player projections |
| `proj_pts_{tf}` | Projected team points | Scoring environment assessment |
| `proj_total_{tf}` | Total game points | Pace/scoring environment |
| `matchup_{tf}` | Point differential | Win probability indicator |
| `pace_{tf}` | Team pace | Tempo preference |

### Player Projection Metrics

| Metric | Description | Use Case |
|--------|-------------|----------|
| `fp_proj` | Final fantasy projection | Primary DFS metric |
| `projected_value` | Points per $1000 | Value identification |
| `fppm_{tf}` | Fantasy points per minute | Efficiency metric |
| `usg_pct_{tf}` | Usage percentage | Opportunity share |
| `salary_share` | % of team salary | Pricing analysis |

---

## Notes for LLM/Agent Implementation

1. **Execution Order Matters:** Always run in sequence:
   - `db.run_daily_update` → `game_matchup.py` → `player_proj.py`

2. **Manual Step Required:** `daily_proj.csv` must be provided manually (not automated)

3. **Name Matching:** Expect ~5-10% of players to have name matching issues. This is normal.

4. **Timeframe Importance:** Recent timeframes (l5, l3) are weighted heaviest. Adjust if needed.

5. **Database Connection:** All modules use same DATABASE_URL env var or `--database-url` arg

6. **Error Handling:** Both modules are safe to re-run (upsert behavior)

7. **Validation:** Always check output makes sense:
   - Projected minutes should match input
   - High salaries should have high projections (usually)
   - Value plays should be identifiable

8. **Extensions:** Easy to add new metrics by following existing calculation patterns

---

## Version History

- **v1.0** - Initial implementation with dual-method projections
- **v1.1** - Added team context aggregates
- **v1.2** - Improved name matching with fuzzy logic
- **v1.3** - Added database save option for projections

---

## References

- See `analysis/README.md` for detailed documentation
- See `analysis/QUICK_START.md` for setup instructions
- See `analysis/IMPLEMENTATION_SUMMARY.md` for technical details
- See `db/AGENTS.md` for database layer documentation

