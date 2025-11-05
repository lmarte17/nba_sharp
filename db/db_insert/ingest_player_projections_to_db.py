"""
Ingest player projections into the database.
"""
import argparse
from typing import Optional
import pandas as pd
from sqlalchemy.dialects.postgresql import insert as pg_insert

try:
    from db.database import get_engine, get_session_maker
    from db.models import PlayerProjection
except ImportError:
    import sys
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from db.database import get_engine, get_session_maker  # type: ignore
    from db.models import PlayerProjection  # type: ignore


def upsert_projections(df: pd.DataFrame, database_url: Optional[str] = None) -> int:
    """
    Save player projections DataFrame to database.
    
    For each unique game_date in the DataFrame:
    - Deletes all existing projections for that date
    - Inserts the new projections
    
    This ensures clean replacement when re-running projections for the same date
    (e.g., due to injury updates, minutes changes, etc.)
    
    Args:
        df: DataFrame with player projections (from player_proj.build_projections)
        database_url: Optional database URL
        
    Returns:
        Number of rows inserted
    """
    engine = get_engine(database_url)
    SessionLocal = get_session_maker(engine)
    
    # Ensure table exists
    PlayerProjection.__table__.create(bind=engine, checkfirst=True)
    
    # Convert DataFrame to list of dicts
    # Only include columns that exist in the model
    model_columns = [col.name for col in PlayerProjection.__table__.columns if col.name not in ('id', 'created_at', 'updated_at')]
    
    # Filter DataFrame to only include columns that exist in the model
    available_cols = [col for col in model_columns if col in df.columns]
    df_filtered = df[available_cols].copy()
    
    # Convert to records
    records = df_filtered.to_dict('records')
    
    if not records:
        print("No records to insert")
        return 0
    
    # Add calc_version to all records
    for record in records:
        record['calc_version'] = 'v1'
    
    # Get unique game dates from the data
    unique_dates = df['game_date'].unique()
    
    with SessionLocal() as session:
        # Delete existing projections for these dates
        for game_date in unique_dates:
            deleted = session.query(PlayerProjection).filter(
                PlayerProjection.game_date == game_date
            ).delete()
            if deleted > 0:
                print(f"Deleted {deleted} existing projections for {game_date}")
        
        # Insert new projections
        stmt = pg_insert(PlayerProjection.__table__).values(records)
        result = session.execute(stmt)
        session.commit()
        
        row_count = getattr(result, 'rowcount', 0) or 0
        return row_count


def main() -> None:
    """CLI entry point for testing."""
    parser = argparse.ArgumentParser(
        description="Ingest player projections from CSV to database"
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="Path to projections CSV file",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database URL (default: from DATABASE_URL env var)",
    )
    
    args = parser.parse_args()
    
    # Load CSV
    print(f"Loading projections from {args.csv}...")
    df = pd.read_csv(args.csv)
    print(f"Loaded {len(df)} projections")
    
    # Save to database (replaces existing for same dates)
    print("Saving to database...")
    count = upsert_projections(df, args.database_url)
    print(f"Saved {count} player projections")


if __name__ == "__main__":
    main()

