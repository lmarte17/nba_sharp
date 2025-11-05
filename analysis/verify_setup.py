#!/usr/bin/env python3
"""
Quick verification script to check if the projection system setup is correct.
"""
import sys
from pathlib import Path

# Add parent to path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.database import get_engine, get_session_maker
from db.db_extract import load_player_stats_dataframe, load_team_stats_dataframe
from analysis.utils import DataUtils, NameMatcher


def check_database():
    """Check if database has required data."""
    print("=" * 60)
    print("Checking Database Connection and Data")
    print("=" * 60)
    
    try:
        engine = get_engine()
        SessionLocal = get_session_maker(engine)
        
        with SessionLocal() as session:
            # Check player stats
            for period in ['season_long', 'last_10', 'last_5', 'last_3']:
                df = load_player_stats_dataframe(session, period)
                print(f"✓ Player stats ({period:12s}): {len(df):4d} players")
            
            print()
            
            # Check team stats
            for period in ['season_long', 'last_10', 'last_5', 'last_3']:
                df = load_team_stats_dataframe(session, period)
                print(f"✓ Team stats  ({period:12s}): {len(df):4d} teams")
            
        print("\n✅ Database connection successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Database error: {e}")
        print("\nMake sure:")
        print("  1. Database is running")
        print("  2. DATABASE_URL environment variable is set")
        print("  3. Database has been populated with stats")
        print("  4. Run: python -m db.run_daily_update")
        return False


def check_csv():
    """Check if daily projections CSV exists."""
    print("\n" + "=" * 60)
    print("Checking Daily Projections CSV")
    print("=" * 60)
    
    csv_path = Path(__file__).parent / "daily_player_intake" / "daily_proj.csv"
    
    if csv_path.exists():
        import pandas as pd
        df = pd.read_csv(csv_path)
        print(f"✓ CSV found at: {csv_path}")
        print(f"✓ Contains {len(df)} players")
        print(f"✓ Columns: {', '.join(df.columns[:8])}...")
        print("\n✅ CSV file ready!")
        return True
    else:
        print(f"❌ CSV not found at: {csv_path}")
        print("\nPlease:")
        print("  1. Download daily_proj.csv")
        print("  2. Place it at: analysis/daily_player_intake/daily_proj.csv")
        return False


def check_utilities():
    """Verify utility functions work."""
    print("\n" + "=" * 60)
    print("Testing Utility Functions")
    print("=" * 60)
    
    try:
        import pandas as pd
        
        # Test DataUtils
        df = pd.DataFrame({
            'name': ['Player A', 'Player B', 'Player C'],
            'points': [25, 30, 20],
            'team': ['LAL', 'GSW', 'LAL']
        })
        
        result = DataUtils.xlookup('Player B', df['name'], df['points'], 0)
        assert result == 30, f"xlookup failed: expected 30, got {result}"
        print("✓ DataUtils.xlookup works")
        
        result = DataUtils.sumif(df['team'], 'LAL', df['points'])
        assert result == 45, f"sumif failed: expected 45, got {result}"
        print("✓ DataUtils.sumif works")
        
        result = DataUtils.safe_divide(100, 4)
        assert result == 25, f"safe_divide failed: expected 25, got {result}"
        print("✓ DataUtils.safe_divide works")
        
        # Test NameMatcher
        score = NameMatcher.similarity_score("LeBron James", "Lebron James")
        assert score >= 0.95, f"similarity_score failed: expected >= 0.95, got {score}"
        print("✓ NameMatcher.similarity_score works")
        
        match = NameMatcher.find_best_match(
            "Lebron James Jr",
            ["LeBron James", "Stephen Curry"],
            threshold=0.85
        )
        assert match is not None, "find_best_match failed"
        assert match[0] == "LeBron James", f"find_best_match wrong: got {match[0]}"
        print("✓ NameMatcher.find_best_match works")
        
        print("\n✅ All utility functions working!")
        return True
        
    except Exception as e:
        print(f"\n❌ Utility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all checks."""
    print("\n" + "=" * 60)
    print("PLAYER PROJECTION SYSTEM - SETUP VERIFICATION")
    print("=" * 60 + "\n")
    
    checks = []
    
    # Run checks
    checks.append(("Utilities", check_utilities()))
    checks.append(("Database", check_database()))
    checks.append(("CSV File", check_csv()))
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    all_passed = all(passed for _, passed in checks)
    
    for name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("✅ ALL CHECKS PASSED!")
        print("\nYou're ready to run projections:")
        print("  python -m analysis.player_proj")
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nPlease fix the issues above before running projections.")
        sys.exit(1)
    
    print("=" * 60)


if __name__ == "__main__":
    main()

