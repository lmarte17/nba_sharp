"""
NBA Sharp API

FastAPI application with scheduled tasks and admin endpoints for:
- Daily database updates
- Game matchup calculations
- Player projections
"""
import os
import asyncio
import datetime
import shutil
from pathlib import Path
from typing import Optional
import logging

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
import json

from stats_retrieval.fetch_and_merge_player_stats import fetch_and_merge_player_stats
from stats_retrieval.fetch_and_merge_team_stats import fetch_and_merge_team_stats

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="NBA Sharp API",
    version="0.1.0",
    description="NBA analytics and projections API with automated daily updates"
)

# Scheduler for automated tasks
scheduler = AsyncIOScheduler()

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Paths
DAILY_PROJ_DIR = Path("analysis/daily_player_intake")
DAILY_PROJ_PATH = DAILY_PROJ_DIR / "daily_proj.csv"


# ============================================================================
# Pydantic Models
# ============================================================================

class TaskStatus(BaseModel):
    """Status response for async tasks"""
    task: str
    status: str
    message: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class DateParam(BaseModel):
    """Date parameter for endpoints"""
    date: Optional[str] = None  # YYYY-MM-DD format


# ============================================================================
# Background Task Functions
# ============================================================================

async def run_daily_update(date_str: Optional[str] = None):
    """Run the daily database update"""
    try:
        logger.info(f"Starting daily update for date: {date_str or 'today'}")
        
        # Import here to avoid circular imports
        from db.run_daily_update import main as run_update
        
        # Build command args
        import sys
        original_argv = sys.argv.copy()
        
        args = ["run_daily_update"]
        if date_str:
            args.extend(["--date", date_str])
        if DATABASE_URL:
            args.extend(["--database-url", DATABASE_URL])
        
        sys.argv = args
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, run_update)
        
        sys.argv = original_argv
        logger.info("Daily update completed successfully")
        
    except Exception as e:
        logger.error(f"Daily update failed: {e}", exc_info=True)
        raise


async def run_game_matchup(date_str: Optional[str] = None):
    """Run game matchup calculations"""
    try:
        logger.info(f"Starting game matchup calculations for date: {date_str or 'today'}")
        
        from analysis.game_matchup import main as run_matchup
        
        # Build command args
        import sys
        original_argv = sys.argv.copy()
        
        args = ["game_matchup"]
        if date_str:
            args.extend(["--date", date_str])
        if DATABASE_URL:
            args.extend(["--database-url", DATABASE_URL])
        
        sys.argv = args
        
        # Run in executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, run_matchup)
        
        sys.argv = original_argv
        logger.info("Game matchup calculations completed successfully")
        
    except Exception as e:
        logger.error(f"Game matchup calculation failed: {e}", exc_info=True)
        raise


async def run_player_projections(date_str: Optional[str] = None):
    """Run player projections"""
    try:
        logger.info(f"Starting player projections for date: {date_str or 'today'}")
        
        if not DAILY_PROJ_PATH.exists():
            raise FileNotFoundError(f"Daily projections CSV not found at {DAILY_PROJ_PATH}")
        
        from analysis.player_proj import build_projections, save_projections
        
        # Determine date
        if date_str:
            game_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            game_date = datetime.date.today()
        
        # Build projections
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None,
            build_projections,
            DAILY_PROJ_PATH,
            game_date,
            DATABASE_URL,
            True  # save_to_db=True
        )
        
        # Save to CSV
        output_path = DAILY_PROJ_DIR / f"player_projections_{game_date}.csv"
        await loop.run_in_executor(None, save_projections, df, output_path)
        
        logger.info(f"Player projections completed successfully. Processed {len(df)} players")
        
    except Exception as e:
        logger.error(f"Player projections failed: {e}", exc_info=True)
        raise


async def run_full_pipeline(date_str: Optional[str] = None):
    """Run the complete pipeline: update DB, calculate matchups"""
    try:
        logger.info("Starting full pipeline")
        
        # Step 1: Daily update
        await run_daily_update(date_str)
        
        # Step 2: Game matchups
        await run_game_matchup(date_str)
        
        logger.info("Full pipeline completed successfully")
        
    except Exception as e:
        logger.error(f"Full pipeline failed: {e}", exc_info=True)
        raise


# ============================================================================
# Scheduled Tasks (Noon EST)
# ============================================================================

async def scheduled_noon_update():
    """Scheduled task that runs at noon EST"""
    try:
        logger.info("Running scheduled noon update")
        await run_full_pipeline()
        logger.info("Scheduled noon update completed")
    except Exception as e:
        logger.error(f"Scheduled noon update failed: {e}", exc_info=True)


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "status": "ok",
        "service": "nba-sharp",
        "version": "0.1.0",
        "endpoints": {
            "stats": "/api/v1/stats/*",
            "admin": "/api/v1/admin/*",
            "scheduler": "/api/v1/scheduler/*"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database_configured": DATABASE_URL is not None,
        "scheduler_running": scheduler.running,
        "daily_csv_exists": DAILY_PROJ_PATH.exists()
    }


# ============================================================================
# Stats Endpoints (existing)
# ============================================================================

@app.get("/api/v1/stats/teams")
async def get_team_stats(
    season: str = "2025-26",
    season_type: str = "Regular Season",
    per_mode: str = "PerGame",
    last_n_games: int = 0,
):
    """Fetch team stats from NBA API"""
    try:
        df = fetch_and_merge_team_stats(
            season=season,
            season_type=season_type,
            per_mode=per_mode,
            last_n_games=last_n_games,
        )
        if df is None:
            raise HTTPException(status_code=502, detail="Failed to fetch team stats")

        data = json.loads(df.to_json(orient="records"))
        return JSONResponse(content=data)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}")


@app.get("/api/v1/stats/players")
async def get_player_stats(
    season: str = "2025-26",
    season_type: str = "Regular Season",
    per_mode: str = "PerGame",
    last_n_games: int = 0,
):
    """Fetch player stats from NBA API"""
    try:
        df = fetch_and_merge_player_stats(
            season=season,
            season_type=season_type,
            per_mode=per_mode,
            last_n_games=last_n_games,
        )
        if df is None:
            raise HTTPException(status_code=502, detail="Failed to fetch player stats")

        data = json.loads(df.to_json(orient="records"))
        return JSONResponse(content=data)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}")


# ============================================================================
# Admin Endpoints - Manual Triggers
# ============================================================================

@app.post("/api/v1/admin/update-database", response_model=TaskStatus)
async def trigger_database_update(
    background_tasks: BackgroundTasks,
    params: DateParam
):
    """
    Manually trigger database update.
    
    Runs: python -m db.run_daily_update
    """
    background_tasks.add_task(run_daily_update, params.date)
    
    return TaskStatus(
        task="database_update",
        status="started",
        message=f"Database update started for date: {params.date or 'today'}",
        started_at=datetime.datetime.now().isoformat()
    )


@app.post("/api/v1/admin/calculate-matchups", response_model=TaskStatus)
async def trigger_matchup_calculation(
    background_tasks: BackgroundTasks,
    params: DateParam
):
    """
    Manually trigger game matchup calculations.
    
    Runs: python -m analysis.game_matchup
    """
    background_tasks.add_task(run_game_matchup, params.date)
    
    return TaskStatus(
        task="matchup_calculation",
        status="started",
        message=f"Matchup calculation started for date: {params.date or 'today'}",
        started_at=datetime.datetime.now().isoformat()
    )


@app.post("/api/v1/admin/run-projections", response_model=TaskStatus)
async def trigger_player_projections(
    background_tasks: BackgroundTasks,
    params: DateParam
):
    """
    Manually trigger player projections.
    
    Runs: python -m analysis.player_proj --save-to-db
    
    Requires daily_proj.csv to be uploaded first.
    """
    if not DAILY_PROJ_PATH.exists():
        raise HTTPException(
            status_code=400,
            detail=f"daily_proj.csv not found. Upload it first at /api/v1/admin/upload-daily-csv"
        )
    
    background_tasks.add_task(run_player_projections, params.date)
    
    return TaskStatus(
        task="player_projections",
        status="started",
        message=f"Player projections started for date: {params.date or 'today'}",
        started_at=datetime.datetime.now().isoformat()
    )


@app.post("/api/v1/admin/run-full-pipeline", response_model=TaskStatus)
async def trigger_full_pipeline(
    background_tasks: BackgroundTasks,
    params: DateParam
):
    """
    Run the complete pipeline: database update + matchup calculations.
    
    This is what runs automatically at noon EST.
    """
    background_tasks.add_task(run_full_pipeline, params.date)
    
    return TaskStatus(
        task="full_pipeline",
        status="started",
        message=f"Full pipeline started for date: {params.date or 'today'}",
        started_at=datetime.datetime.now().isoformat()
    )


@app.post("/api/v1/admin/upload-daily-csv")
async def upload_daily_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auto_run_projections: bool = False,
    date: Optional[str] = None
):
    """
    Upload daily_proj.csv file.
    
    Args:
        file: CSV file upload
        auto_run_projections: If True, automatically runs projections after upload
        date: Optional date for projections (YYYY-MM-DD)
    
    This endpoint:
    1. Saves the uploaded file to analysis/daily_player_intake/daily_proj.csv
    2. Optionally triggers player projections
    """
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        
        # Ensure directory exists
        DAILY_PROJ_DIR.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded file
        with DAILY_PROJ_PATH.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"Uploaded daily_proj.csv ({file.filename})")
        
        response = {
            "status": "success",
            "message": "File uploaded successfully",
            "filename": file.filename,
            "saved_to": str(DAILY_PROJ_PATH)
        }
        
        # Optionally trigger projections
        if auto_run_projections:
            background_tasks.add_task(run_player_projections, date)
            response["projections_triggered"] = True
            response["projections_date"] = date or "today"
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ============================================================================
# Scheduler Endpoints
# ============================================================================

@app.get("/api/v1/scheduler/status")
async def get_scheduler_status():
    """Get scheduler status and upcoming jobs"""
    jobs = scheduler.get_jobs()
    
    return {
        "running": scheduler.running,
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
            for job in jobs
        ]
    }


@app.post("/api/v1/scheduler/pause")
async def pause_scheduler():
    """Pause the scheduler (stops automatic tasks)"""
    scheduler.pause()
    return {"status": "paused", "message": "Scheduler paused. Automatic tasks will not run."}


@app.post("/api/v1/scheduler/resume")
async def resume_scheduler():
    """Resume the scheduler"""
    scheduler.resume()
    return {"status": "running", "message": "Scheduler resumed. Automatic tasks enabled."}


# ============================================================================
# Application Lifecycle
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize scheduler on startup"""
    logger.info("Starting NBA Sharp API...")
    
    # Add scheduled job for noon EST (12:00 PM Eastern)
    scheduler.add_job(
        scheduled_noon_update,
        trigger=CronTrigger(hour=12, minute=0, timezone='America/New_York'),
        id='noon_update',
        name='Daily Noon Update (EST)',
        replace_existing=True
    )
    
    # Start scheduler
    scheduler.start()
    logger.info("Scheduler started. Noon EST job configured.")
    logger.info(f"Database URL configured: {DATABASE_URL is not None}")
    
    # Log next run time
    jobs = scheduler.get_jobs()
    for job in jobs:
        if job.next_run_time:
            logger.info(f"Next scheduled run: {job.next_run_time.isoformat()}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down...")
    scheduler.shutdown()
    logger.info("Scheduler stopped")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
