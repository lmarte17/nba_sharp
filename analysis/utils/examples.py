"""
Examples demonstrating usage of utility functions.
This is not meant to be run, just for reference.
"""
import pandas as pd
from analysis.utils import DataUtils, NameMatcher


def example_data_utils():
    """Examples of DataUtils usage."""
    
    # Create sample data
    df = pd.DataFrame({
        'player': ['LeBron James', 'Stephen Curry', 'Kevin Durant', 'Giannis Antetokounmpo'],
        'team': ['LAL', 'GSW', 'PHX', 'MIL'],
        'points': [25.5, 28.3, 27.1, 31.2],
        'minutes': [35.5, 34.2, 36.8, 33.1],
        'salary': [11500, 10800, 10200, 12000],
    })
    
    # Example 1: XLOOKUP - Find a player's points
    lebron_points = DataUtils.xlookup(
        lookup_value='LeBron James',
        lookup_array=df['player'],
        return_array=df['points'],
        if_not_found=0.0
    )
    print(f"LeBron's points: {lebron_points}")  # 25.5
    
    # Example 2: SUMIF - Total points for a team
    lal_total_points = DataUtils.sumif(
        condition_array=df['team'],
        condition_value='LAL',
        sum_array=df['points']
    )
    print(f"LAL total points: {lal_total_points}")  # 25.5
    
    # Example 3: Safe divide - Calculate points per minute
    ppg = DataUtils.safe_divide(25.5, 35.5, default=0.0)
    print(f"Points per minute: {ppg:.2f}")  # 0.72
    
    # Example 4: Safe divide with zero denominator
    result = DataUtils.safe_divide(100, 0, default=0.0)
    print(f"100 / 0 with default: {result}")  # 0.0
    
    # Example 5: Coalesce - Get first non-None value
    value = DataUtils.coalesce(None, None, 42, 100)
    print(f"First non-None: {value}")  # 42
    
    # Example 6: Using with DataFrame apply
    df['points_per_minute'] = df.apply(
        lambda row: DataUtils.safe_divide(row['points'], row['minutes']),
        axis=1
    )
    print("\nPoints per minute for all players:")
    print(df[['player', 'points_per_minute']])
    
    # Example 7: Team salary totals using SUMIF
    df['team_salary'] = df.apply(
        lambda row: DataUtils.sumif(df['team'], row['team'], df['salary']),
        axis=1
    )
    print("\nTeam salary totals:")
    print(df[['player', 'team', 'salary', 'team_salary']])


def example_name_matcher():
    """Examples of NameMatcher usage."""
    
    # Example 1: Normalize names
    name1 = NameMatcher.normalize_name("LeBron  James Jr.")
    name2 = NameMatcher.normalize_name("lebron james jr")
    print(f"Normalized: '{name1}' and '{name2}'")
    print(f"Are equal: {name1 == name2}")  # True
    
    # Example 2: Strip suffixes
    name_without_suffix = NameMatcher.strip_suffix("Martin Luther King Jr.")
    print(f"Without suffix: '{name_without_suffix}'")  # "martin luther king"
    
    # Example 3: Similarity score
    score1 = NameMatcher.similarity_score("LeBron James", "Lebron James")
    score2 = NameMatcher.similarity_score("LeBron James", "Stephen Curry")
    print(f"LeBron vs Lebron similarity: {score1:.2f}")  # ~1.0 (exact match)
    print(f"LeBron vs Curry similarity: {score2:.2f}")   # ~0.3 (different)
    
    # Example 4: Find best match
    database_names = [
        "LeBron James",
        "Stephen Curry", 
        "Kevin Durant",
        "Giannis Antetokounmpo"
    ]
    
    # Trying to match a slightly different name
    match = NameMatcher.find_best_match(
        target_name="Lebron James Jr",
        candidate_names=database_names,
        threshold=0.85
    )
    
    if match:
        matched_name, score = match
        print(f"\nBest match for 'Lebron James Jr': '{matched_name}' (score: {score:.2f})")
    
    # Example 5: Build name mapping between two lists
    csv_names = [
        "Lebron James",
        "Steph Curry",
        "KD",  # Won't match - too different
        "Giannis Antetokounmpo"
    ]
    
    name_map = NameMatcher.build_name_map(
        source_names=csv_names,
        target_names=database_names,
        threshold=0.85
    )
    
    print("\nName mapping:")
    for source, target in name_map.items():
        print(f"  '{source}' -> '{target}'")
    
    # Show unmapped names
    unmapped = [name for name in csv_names if name not in name_map]
    if unmapped:
        print(f"\nUnmapped names: {unmapped}")


def example_projection_workflow():
    """Example showing how utilities work together in projection workflow."""
    
    # Simulated daily projections
    daily_df = pd.DataFrame({
        'player': ['Lebron James', 'Stephen Curry', 'Kevin Durant'],
        'team': ['LAL', 'GSW', 'PHX'],
        'salary': [11500, 10800, 10200],
        'proj_mins': [35, 34, 36],
    })
    
    # Simulated historical stats from database
    historical_df = pd.DataFrame({
        'player': ['LeBron James', 'Stephen Curry', 'Kevin Durant'],
        'team': ['LAL', 'GSW', 'PHX'],
        'fp': [48.5, 45.2, 42.8],
        'touches': [78, 72, 68],
        'minutes': [35.5, 34.2, 36.8],
    })
    
    print("=== Projection Workflow Example ===\n")
    
    # Step 1: Match names using fuzzy matching
    db_names = historical_df['player'].tolist()
    csv_names = daily_df['player'].tolist()
    
    name_map = NameMatcher.build_name_map(csv_names, db_names, threshold=0.85)
    daily_df['db_player'] = daily_df['player'].map(name_map)
    
    print("1. Name mapping:")
    print(daily_df[['player', 'db_player']])
    
    # Step 2: Lookup historical stats
    daily_df['hist_fp'] = daily_df['db_player'].apply(
        lambda x: DataUtils.xlookup(x, historical_df['player'], historical_df['fp'], 0.0)
    )
    
    daily_df['hist_touches'] = daily_df['db_player'].apply(
        lambda x: DataUtils.xlookup(x, historical_df['player'], historical_df['touches'], 0.0)
    )
    
    daily_df['hist_minutes'] = daily_df['db_player'].apply(
        lambda x: DataUtils.xlookup(x, historical_df['player'], historical_df['minutes'], 1.0)
    )
    
    print("\n2. Historical stats merged:")
    print(daily_df[['player', 'hist_fp', 'hist_touches', 'hist_minutes']])
    
    # Step 3: Calculate rate stats
    daily_df['fppm'] = daily_df.apply(
        lambda row: DataUtils.safe_divide(row['hist_fp'], row['hist_minutes']),
        axis=1
    )
    
    daily_df['tpm'] = daily_df.apply(
        lambda row: DataUtils.safe_divide(row['hist_touches'], row['hist_minutes']),
        axis=1
    )
    
    print("\n3. Rate stats calculated:")
    print(daily_df[['player', 'fppm', 'tpm']])
    
    # Step 4: Project based on today's minutes
    daily_df['proj_touches'] = daily_df['tpm'] * daily_df['proj_mins']
    daily_df['proj_fp'] = daily_df['fppm'] * daily_df['proj_mins']
    
    print("\n4. Projections:")
    print(daily_df[['player', 'proj_mins', 'proj_touches', 'proj_fp']])
    
    # Step 5: Calculate value (points per $1k)
    daily_df['value'] = daily_df.apply(
        lambda row: DataUtils.safe_divide(row['proj_fp'], row['salary'] / 1000),
        axis=1
    )
    
    print("\n5. Value calculation:")
    print(daily_df[['player', 'salary', 'proj_fp', 'value']])
    
    # Step 6: Team aggregations
    daily_df['team_salary'] = daily_df.apply(
        lambda row: DataUtils.sumif(daily_df['team'], row['team'], daily_df['salary']),
        axis=1
    )
    
    print("\n6. Team aggregations:")
    print(daily_df[['player', 'team', 'salary', 'team_salary']])


if __name__ == "__main__":
    print("=" * 60)
    print("DataUtils Examples")
    print("=" * 60)
    example_data_utils()
    
    print("\n" + "=" * 60)
    print("NameMatcher Examples")
    print("=" * 60)
    example_name_matcher()
    
    print("\n" + "=" * 60)
    print("Projection Workflow Example")
    print("=" * 60)
    example_projection_workflow()

