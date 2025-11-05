# NBA Player Projections System

This module provides a comprehensive player fantasy projection system that combines daily baseline projections with historical statistics to generate weighted fantasy point projections.

## Overview

The projection system:
1. Loads daily projections CSV with baseline data (salary, projected minutes, ownership, etc.)
2. Extracts historical player stats across multiple time periods (season-long, last 10, 5, 3 games)
3. Extracts team stats for context
4. Computes advanced metrics and rate-based stats
5. Generates final weighted projections using multiple methods

## Files Structure

```
analysis/
├── player_proj.py          # Main projection script
├── game_matchup.py         # Game matchup calculations (prerequisite)
├── utils/
│   ├── __init__.py
│   ├── data_utils.py       # Excel-like helper functions (xlookup, sumif, etc.)
│   └── name_matcher.py     # Fuzzy name matching for player names
└── daily_player_intake/
    ├── daily_proj.csv      # Input: Daily projections (manually downloaded)
    └── player_projections_{date}.csv  # Output: Final projections
```

## Setup

### Prerequisites

1. Database must be populated with:
   - Player stats (season_long, last_10, last_5, last_3)
   - Team stats (season_long, last_10, last_5, last_3)
   - Game schedule
   
2. Run game matchup calculations first:
   ```bash
   python -m db.run_daily_update
   # or
   python -m analysis.game_matchup --date 2024-11-05
   ```

3. Manually download and place `daily_proj.csv` in `analysis/daily_player_intake/`

## Usage

### Basic Usage

Run projections for today:

```bash
python -m analysis.player_proj
```

### Advanced Options

```bash
# Specify a date
python -m analysis.player_proj --date 2024-11-05

# Specify custom CSV path
python -m analysis.player_proj --csv /path/to/daily_proj.csv

# Specify custom output path
python -m analysis.player_proj --output /path/to/output.csv

# Use custom database URL
python -m analysis.player_proj --database-url postgresql://user:pass@host/db
```

### Full Example

```bash
# 1. Update database with latest stats
python -m db.run_daily_update

# 2. Place daily_proj.csv in analysis/daily_player_intake/

# 3. Run projections
python -m analysis.player_proj --date 2024-11-05

# Output will be saved to:
# analysis/daily_player_intake/player_projections_2024-11-05.csv
```

## How It Works

### 1. Data Loading

The system loads:
- **Daily Projections CSV**: Contains baseline projections with columns:
  - Name, Pos, Team, Opp, Status, Salary
  - Min (projected minutes), Adj Own (ownership %)
  - gameInfo

- **Historical Player Stats**: From database for 4 periods (sl, l10, l5, l3):
  - Base stats: gp, usg_pct, fp, touches, min, poss
  - Advanced stats: All available metrics

- **Team Stats**: Team-level aggregates for context

- **Game Matchup Data**: Implied possessions and pace projections

### 2. Name Matching

Player names from the CSV may not exactly match database names (different suffixes, spelling variations). The system uses fuzzy matching to map names with 85%+ similarity.

### 3. Data Validation

- If a player's recent stats (l3) are missing/zero, the system falls back to l5, then l10, then season-long
- Players with no data across all periods are dropped

### 4. Calculations

For each time period (sl, l10, l5, l3), the system calculates:

#### Rate-Based Stats
- **fppm**: Fantasy Points Per Minute = fp / min
- **fppt**: Fantasy Points Per Touch = fp / touches
- **fppp**: Fantasy Points Per Possession = fp / (poss / gp)
- **tpm**: Touches Per Minute = touches / min
- **tpp**: Touches Per Possession = touches / (poss / gp)

#### Team Context
- **poss_pct**: Player's possession % of team total

#### Touch Projections (2 methods)
1. **touches_ip** (Implied Possessions method):
   - Uses game's implied possessions from matchup data
   - `touches_ip = (poss_pct / 100) * tpp * implied_poss`

2. **touches_tpm** (Touches Per Minute method):
   - `touches_tpm = tpm * proj_mins`

#### Fantasy Point Projections (2 methods)
1. **fp_proj_it**: `fppt * touches_ip`
2. **fp_proj_tpm**: `fppt * touches_tpm`

#### Team Fantasy Context
- **team_fp**: Total team fantasy points
- **fp_per**: Player's % of team fantasy points

### 5. Team Aggregates

From today's projections:
- **team_salary**: Total team salary
- **salary_share**: Player's % of team salary
- **team_ownership**: Total team ownership
- **team_minutes**: Total projected minutes
- **minutes_avail**: Available minutes (240 - team_minutes)

### 6. Final Weighted Projection

Combines all 8 projection methods (4 periods × 2 methods) using weights:

**TPM Method Weights:**
- sl: 1
- l10: 4
- l5: 8 (highest - most recent form)
- l3: 4

**IT Method Weights:**
- sl: 1
- l10: 3
- l5: 6
- l3: 3

Final projection is weighted average: `fp_proj = Σ(projection * weight) / Σ(weights)`

**Projected Value**: `fp_proj / (salary / 1000)` - points per $1000 of salary

## Output

The output CSV includes:

### Core Columns
- player, pos, team, opp, status
- salary, proj_mins, ownership
- **fp_proj**: Final weighted fantasy point projection
- **projected_value**: Points per $1000 of salary

### Context Columns
- salary_share, minutes_avail

### Recent Performance (l5, l3)
- fp_{period}: Historical fantasy points
- fppm_{period}: Fantasy points per minute
- usg_pct_{period}: Usage percentage
- fp_proj_it_{period}: IT method projection
- fp_proj_tpm_{period}: TPM method projection

Output is sorted by `fp_proj` descending (highest projected points first).

## Utility Functions

### DataUtils

Excel-like helper functions in `analysis/utils/data_utils.py`:

- **xlookup**: Lookup values like Excel's XLOOKUP
- **sumif**: Conditional sum like Excel's SUMIF
- **safe_divide**: Division with fallback for zero/null
- **coalesce**: Return first non-null value

### NameMatcher

Fuzzy name matching in `analysis/utils/name_matcher.py`:

- **normalize_name**: Standardize name format
- **strip_suffix**: Remove Jr., Sr., II, III, etc.
- **similarity_score**: Calculate 0-1 similarity between names
- **find_best_match**: Find best match from candidates
- **build_name_map**: Build mapping between two name lists

## Troubleshooting

### "No matchup data found"
Run `game_matchup.py` first to generate matchup data for the date.

### "X players could not be matched to database"
Some player names in the CSV don't match database names. Check:
- Name spelling differences
- Suffixes (Jr., Sr., II, etc.)
- Database has stats for these players

Adjust fuzzy matching threshold in code if needed (default 0.85).

### "Dropping X players with no historical data"
Players in CSV don't have stats in database. They may be:
- New players with no games played
- Inactive players
- Name mismatches

### Missing projected values
Ensure:
1. Database has player stats for all periods
2. Game matchup data exists for the date
3. Team names in CSV match team names in database

## Development

### Adding New Metrics

To add new calculated metrics:

1. Add calculation in appropriate function (e.g., `calculate_rate_stats`)
2. Add column name to output in `save_projections`
3. Update documentation

### Adjusting Weights

Modify `TPM_WEIGHTS` and `IT_WEIGHTS` dictionaries in `player_proj.py` to change projection method importance.

### Customizing Output

Edit `output_cols` list in `save_projections` function to include/exclude columns.

## Examples

### Command Line

```bash
# Today's projections
python -m analysis.player_proj

# Specific date
python -m analysis.player_proj --date 2024-11-10

# Custom paths
python -m analysis.player_proj \
  --csv ~/Downloads/daily_proj.csv \
  --output ~/projections.csv
```

### Programmatic Usage

```python
from pathlib import Path
import datetime
from analysis.player_proj import build_projections, save_projections

# Build projections
df = build_projections(
    daily_proj_path=Path("analysis/daily_player_intake/daily_proj.csv"),
    game_date=datetime.date(2024, 11, 5),
    database_url=None  # Uses DATABASE_URL env var
)

# Access projections
top_players = df.nlargest(10, 'fp_proj')
high_value = df.nlargest(10, 'projected_value')

# Save
save_projections(df, Path("my_projections.csv"))
```

## Notes

- Projections are point-in-time based on current database stats
- Update database regularly for accurate projections
- Recent form (l5) is weighted highest in projections
- System handles players returning from injury (uses longer periods if recent data missing)
- Fuzzy matching helps with name variations but isn't perfect
- Always validate output against domain knowledge

