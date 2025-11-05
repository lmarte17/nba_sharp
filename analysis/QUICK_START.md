# Player Projections - Quick Start Guide

## Prerequisites Checklist

- [ ] Database is running and populated with stats
- [ ] `daily_proj.csv` downloaded and placed in `analysis/daily_player_intake/`
- [ ] Game matchup data exists for target date

## Verify Setup

```bash
python -m analysis.verify_setup
```

This checks:
- ✓ Database connection
- ✓ Player/team stats available
- ✓ CSV file exists
- ✓ Utility functions work

## Basic Workflow

### 1. Update Database (Daily)

```bash
# Updates all stats and generates matchup data
python -m db.run_daily_update
```

### 2. Download Daily Projections

1. Download `daily_proj.csv` from your source
2. Place in `analysis/daily_player_intake/daily_proj.csv`

### 3. Run Projections

```bash
# For today
python -m analysis.player_proj

# For specific date
python -m analysis.player_proj --date 2024-11-10
```

### 4. View Results

Output saved to: `analysis/daily_player_intake/player_projections_{date}.csv`

## Command Reference

### Run Projections

```bash
# Basic
python -m analysis.player_proj

# With options
python -m analysis.player_proj \
  --date 2024-11-10 \
  --csv /path/to/daily_proj.csv \
  --output /path/to/output.csv \
  --database-url postgresql://user:pass@localhost/nba
```

### Update Database

```bash
# Full update
python -m db.run_daily_update

# Just matchup data
python -m analysis.game_matchup --date 2024-11-10
```

### Verify Setup

```bash
python -m analysis.verify_setup
```

### Run Examples

```bash
python -m analysis.utils.examples
```

## Output Columns

Key columns in output CSV:

| Column | Description |
|--------|-------------|
| `player` | Player name |
| `team` | Team abbreviation |
| `opp` | Opponent abbreviation |
| `salary` | FanDuel salary |
| `proj_mins` | Projected minutes |
| `ownership` | Projected ownership % |
| `fp_proj` | **Final fantasy point projection** |
| `projected_value` | **Points per $1000 salary** |
| `fp_proj_it_l5` | Last 5 games IT method projection |
| `fp_proj_tpm_l5` | Last 5 games TPM method projection |

Sort by `fp_proj` for highest projected points or `projected_value` for best value plays.

## Common Issues

### "No matchup data found"

**Solution**: Run matchup calculations first
```bash
python -m analysis.game_matchup --date 2024-11-10
```

### "X players could not be matched"

**Cause**: Player names in CSV don't match database

**Solutions**:
- Check name spelling in CSV vs database
- Player may be new with no stats yet
- Check suffixes (Jr., Sr., II, etc.)

### "Database connection error"

**Solutions**:
- Ensure database is running
- Check `DATABASE_URL` environment variable
- Verify credentials

### "CSV file not found"

**Solution**: Place `daily_proj.csv` in `analysis/daily_player_intake/`

## Tips

### Best Practices

1. **Update database daily** before running projections
2. **Run matchup first** to ensure implied possessions are calculated
3. **Check unmapped names** in output warnings
4. **Validate results** against domain knowledge before using

### Customization

#### Adjust Projection Weights

Edit `TPM_WEIGHTS` and `IT_WEIGHTS` in `player_proj.py`:

```python
TPM_WEIGHTS = {
    'sl': 1,
    'l10': 4,
    'l5': 8,  # Higher = more weight
    'l3': 4,
}
```

#### Change Fuzzy Matching Threshold

In `player_proj.py`, adjust threshold in `build_name_mapping()`:

```python
name_map = NameMatcher.build_name_map(
    proj_players, 
    db_players, 
    threshold=0.85  # Lower = more lenient matching
)
```

#### Add Output Columns

Edit `output_cols` in `save_projections()` function.

## Programmatic Usage

```python
from pathlib import Path
import datetime
from analysis.player_proj import build_projections

# Build projections
df = build_projections(
    daily_proj_path=Path("analysis/daily_player_intake/daily_proj.csv"),
    game_date=datetime.date(2024, 11, 5)
)

# Filter and analyze
top_value = df.nlargest(20, 'projected_value')
high_ownership = df[df['ownership'] > 20]
cheap_plays = df[df['salary'] < 6000].nlargest(10, 'projected_value')

# Export
df.to_csv("my_projections.csv", index=False)
```

## Getting Help

1. **Read the docs**: `analysis/README.md` - Complete documentation
2. **Check examples**: `analysis/utils/examples.py` - Utility function examples
3. **Verify setup**: `python -m analysis.verify_setup` - Diagnose issues
4. **Check spec**: `analysis/player_proj.md` - Original specification
5. **Review summary**: `analysis/IMPLEMENTATION_SUMMARY.md` - Implementation details

## Quick Debug

```python
# Check if player exists in database
from db.database import get_engine, get_session_maker
from db.db_extract import load_player_stats_dataframe

engine = get_engine()
session = next(get_session_maker(engine)())
df = load_player_stats_dataframe(session, 'season_long')

# Search for player
player_name = "LeBron James"
matches = df[df['player'].str.contains(player_name, case=False)]
print(matches[['player', 'team', 'fp', 'touches']])

session.close()
```

```python
# Test name matching
from analysis.utils import NameMatcher

csv_name = "Lebron James Jr"
db_names = ["LeBron James", "LeBron James Jr.", "Lebron James"]

for db_name in db_names:
    score = NameMatcher.similarity_score(csv_name, db_name)
    print(f"{csv_name} vs {db_name}: {score:.2f}")
```

## Workflow Diagram

```
┌─────────────────────────────────────────────────────┐
│  1. Update Database                                  │
│     python -m db.run_daily_update                    │
│     • Fetches latest player/team stats               │
│     • Calculates game matchups                       │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  2. Place daily_proj.csv                             │
│     • Download from source                           │
│     • Save to: analysis/daily_player_intake/         │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  3. Run Projections                                  │
│     python -m analysis.player_proj                   │
│     • Loads CSV + database stats                     │
│     • Matches player names (fuzzy)                   │
│     • Calculates metrics (8 methods)                 │
│     • Generates weighted projections                 │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  4. Use Projections                                  │
│     • Review: player_projections_{date}.csv          │
│     • Sort by: fp_proj or projected_value            │
│     • Build lineups                                  │
└─────────────────────────────────────────────────────┘
```

## File Locations

```
analysis/
├── player_proj.py              # Run this
├── daily_player_intake/
│   ├── daily_proj.csv         # Place input here
│   └── player_projections_*.csv  # Output here
├── README.md                   # Full docs
├── QUICK_START.md             # This file
└── verify_setup.py            # Diagnostics
```

---

**Ready to Go?**

```bash
python -m analysis.verify_setup  # Check setup
python -m analysis.player_proj   # Run projections
```

