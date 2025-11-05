from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import json

from stats_retrieval.fetch_and_merge_player_stats import fetch_and_merge_player_stats
from stats_retrieval.fetch_and_merge_team_stats import fetch_and_merge_team_stats


app = FastAPI(title="NBA Sharp API", version="0.1.0")


@app.get("/")
async def root():
    return {"status": "ok", "service": "nba-sharp"}


@app.get("/api/v1/stats/teams")
async def get_team_stats(
    season: str = "2025-26",
    season_type: str = "Regular Season",
    per_mode: str = "PerGame",
    last_n_games: int = 0,
):
    try:
        df = fetch_and_merge_team_stats(
            season=season,
            season_type=season_type,
            per_mode=per_mode,
            last_n_games=last_n_games,
        )
        if df is None:
            raise HTTPException(status_code=502, detail="Failed to fetch team stats")

        # Use DataFrame JSON round-trip to ensure numpy types serialize cleanly
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
