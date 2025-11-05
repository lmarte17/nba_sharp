Now I'd like to build the players analysis and projections table

**IMPLEMENTATION STATUS: COMPLETE**
- Main script: `analysis/player_proj.py`
- Utilities: `analysis/utils/`
- Documentation: `analysis/README.md`
- Run: `python -m analysis.player_proj`

---

## Original Specification

We'll start with a daily projections csv file that houses fantasy-related information:
Name - player name (One thing about this is that there may be some dissimilarities between the names here and the names in our DB, like suffixes and slight spelling differences. We'll need an approach to figure this out. Could be an opportunity to use fuzzy or maybe a small LLM)
Pos - Position
team - Team name
Opp - Opponent's team name
Status - Status for the game. This field could be embty, P for probable, Q for questionable, etc
gameInfo: team a @ team b
salary - Salary on fanduel

The columns below are projections, some of which we'll need for our analysis
value: projected fantasy points for every $1000
Adj Own - projected ownership
Min: projected minutes

There are other columns, but we don't really have to worry about them

I'll manually download the daily_proj.csv and place it in the daily_player_intake directory. After this, we can start retrieving the stats from the DB and starting our calculations and building our calculations table.

First we'll retrieve the information we need from the daily_proj.csv file and create these columns:
Name (we can change to player to match our DB)
Pos
Team
Opp
Salary
Mins (We can change to Proj Mins)
Adj Own - We can change to Own

This is the most complex function and the core of the projection system.

- **Purpose:** To merge all the data (initial projections, player stats, team stats) and calculate a wide range of advanced metrics and final fantasy point projections.
    
- **Process & Column Breakdown:**
    
    1. **Initial Stat Merging:**
        
        - It loops through each period (`sl`, `l10`, `l5`, `l3`) and each base stat (`gp`, `usg_pct`, `fp`, `touches`, `min`, `poss`).
            
        - It creates new columns for each combination (e.g., `usg_pct_sl`, `usg_pct_l10`, etc.).
            
        - It populates these columns by looking up each player's name in the corresponding historical DataFrame (e.g., `player_dfs['l10']`) using `DataUtils.xlookup`.
            
    2. **Data Validation (Handling Zeros):**
        
        - This section is crucial for handling players who may have missed recent games (e.g., their "Last 3" stats are all zero).
            
        - It loops _backwards_ from `l3` up to `l10`.
            
        - If it finds that all stats for a player in a given period (e.g., `l3`) are zero, it _copies the stats from the next largest period_ (e.g., `l5`) into the `l3` columns. This ensures the most recent _available_ data is used.
            
        - If _all_ periods are zero for a player, that player is dropped from the DataFrame.
            
    3. **Period-by-Period Calculations:**
        
        - The code now iterates through each period (`sl`, `l10`, `l5`, `l3`) again to calculate rate-based stats.
            
        - `fppm_{period}`: **Fantasy Points Per Minute** (`fp_{period}` / `min_{period}`).
            
        - `fppt_{period}`: **Fantasy Points Per Touch** (`fp_{period}` / `touches_{period}`).
            
        - `fppp_{period}`: **Fantasy Points Per Possession** (`fp_{period}` / (`poss_{period}` / `gp_{period}`)).
            
        - `tpm_{period}`: **Touches Per Minute** (`touches_{period}` / `min_{period}`).
            
        - `tpp_{period}`: **Touches Per Possession** (`touches_{period}` / (`poss_{period}` / `gp_{period}`)).
            
        - `poss_pct_{period}`: **Player's Possession Percentage**. Looks up the player's team's total possessions (`team_dfs[period]['poss']`) and calculates the player's share: `(player_poss / team_poss) * 100`.
            
        - `touches_ip_{period}`: **Implied Touches (from Implied Possessions)**. This is a complex projection. It uses the `matchup_df` to find the _game's_ total implied possessions for that period. It then multiplies this by the player's possession percentage (`poss_pct_{period}`) and their touches-per-possession rate (`tpp_{period}`). This estimates touches based on the specific game's pace.
            
        - `touches_tpm_{period}`: **Implied Touches (from Touches Per Minute)**. A simpler projection. It multiplies the player's touches-per-minute rate (`tpm_{period}`) by their `projected_minutes` for the day.
            
        - `team_fp_{period}`: **Team Total Fantasy Points**. Uses `DataUtils.sumif` to add up the fantasy points (`fp_{period}`) of all players on the same team.
            
        - `fp_per_{period}`: **Fantasy Point Percentage**. The player's share of their team's total fantasy points: `(fp_{period} / team_fp_{period}) * 100`.
            
        - `fp_proj_it_{period}`: **Fantasy Point Projection (Implied Touches method)**. `fppt_{period}` * `touches_ip_{period}`. (Projects fantasy points based on their pace-adjusted touch projection).
            
        - `fp_proj_tpm_{period}`: **Fantasy Point Projection (Touches Per Minute method)**. `fppt_{period}` * `touches_tpm_{period}`. (Projects fantasy points based on their minutes-based touch projection).
            
    4. **Team-Level Summary Calculations:**
        
        - `team_salary`: Total combined `salary` of all players on the team in today's `df`.
            
        - `salary_share`: The player's `salary` as a percentage of the `team_salary`.
            
        - `team_ownership`: Total combined `ownership` of all players on the team.
            
        - `team_minutes`: Total `projected_minutes` for all players on the team.
            
        - `minutes_avail`: **Available Minutes**. Calculated as `240` (total minutes in a regulation game) minus `team_minutes`. This shows how many minutes are unaccounted for, which could indicate an opportunity or a flawed projection.
            
    5. **Final Weighted Projection:**
        
        - `fp_proj`: This is the **final, single fantasy point projection**.
            
        - It is a **weighted average** of all 8 projection methods calculated earlier (4 periods x 2 methods: `fp_proj_it_sl`...`fp_proj_tpm_l3`).
            
        - The weights (`it_weights`, `tpm_weights`) give more importance to certain methods. For example, `fp_proj_tpm_l5` (Last 5 games, TPM method) is given the highest weight of `8`, while `fp_proj_it_sl` (Season Long, IT method) is given a weight of only `1`.
            
        - The calculation sums all (projection * weight) and divides by the total sum of all weights.
            
    6. **Final Value Calculation:**
        
        - `projected_value`: A common fantasy sports metric. It's the player's `fp_proj` divided by their salary in thousands (e.g., `salary` / 1000). This shows "points per dollar."