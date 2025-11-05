# NBA Sharp - API & Automation Guide

## Overview

The NBA Sharp API provides automated daily updates and admin endpoints for managing projections and analytics.

### Automated Tasks

- **Daily Database Update**: Runs at **12:00 PM EST** every day
- **Game Matchup Calculations**: Runs immediately after database update
- **Player Projections**: Triggered when `daily_proj.csv` is uploaded

### Key Features

✅ **Scheduled automation** - Runs at noon EST daily  
✅ **Manual triggers** - Admin endpoints for on-demand execution  
✅ **File upload** - Upload CSV and optionally auto-run projections  
✅ **Background tasks** - Non-blocking API responses  
✅ **Health monitoring** - Status and scheduler endpoints  

## Quick Start

### 1. Install Dependencies

```bash
# Install new dependencies
uv pip install apscheduler python-multipart python-dotenv

# Or reinstall all
uv sync
```

### 2. Configure Environment

Ensure `.env` file has `DATABASE_URL`:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/nba_sharp
```

### 3. Start the API

```bash
python main.py

# Or with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will start and:
- Schedule the noon EST job automatically
- Display next run time in logs
- Be ready for manual triggers

## API Endpoints

### Health & Status

#### `GET /`
Root endpoint with API information

```bash
curl http://localhost:8000/
```

#### `GET /health`
Health check with system status

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "database_configured": true,
  "scheduler_running": true,
  "daily_csv_exists": false
}
```

### Admin Endpoints

All admin endpoints use **POST** and run tasks in the background.

#### `POST /api/v1/admin/update-database`
Manually trigger database update

```bash
# Update for today
curl -X POST http://localhost:8000/api/v1/admin/update-database \
  -H "Content-Type: application/json" \
  -d '{}'

# Update for specific date
curl -X POST http://localhost:8000/api/v1/admin/update-database \
  -H "Content-Type: application/json" \
  -d '{"date": "2024-11-05"}'
```

Response:
```json
{
  "task": "database_update",
  "status": "started",
  "message": "Database update started for date: today",
  "started_at": "2024-11-05T14:30:00"
}
```

#### `POST /api/v1/admin/calculate-matchups`
Manually trigger game matchup calculations

```bash
curl -X POST http://localhost:8000/api/v1/admin/calculate-matchups \
  -H "Content-Type: application/json" \
  -d '{"date": "2024-11-05"}'
```

#### `POST /api/v1/admin/run-projections`
Manually trigger player projections (requires CSV uploaded first)

```bash
curl -X POST http://localhost:8000/api/v1/admin/run-projections \
  -H "Content-Type: application/json" \
  -d '{"date": "2024-11-05"}'
```

Error if CSV not uploaded:
```json
{
  "detail": "daily_proj.csv not found. Upload it first at /api/v1/admin/upload-daily-csv"
}
```

#### `POST /api/v1/admin/run-full-pipeline`
Run complete pipeline (database + matchups)

This is what runs automatically at noon.

```bash
curl -X POST http://localhost:8000/api/v1/admin/run-full-pipeline \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### `POST /api/v1/admin/upload-daily-csv`
Upload daily projections CSV

```bash
# Simple upload
curl -X POST http://localhost:8000/api/v1/admin/upload-daily-csv \
  -F "file=@/path/to/daily_proj.csv"

# Upload and auto-run projections
curl -X POST http://localhost:8000/api/v1/admin/upload-daily-csv \
  -F "file=@/path/to/daily_proj.csv" \
  -F "auto_run_projections=true"

# Upload with specific date
curl -X POST http://localhost:8000/api/v1/admin/upload-daily-csv \
  -F "file=@/path/to/daily_proj.csv" \
  -F "auto_run_projections=true" \
  -F "date=2024-11-05"
```

Response:
```json
{
  "status": "success",
  "message": "File uploaded successfully",
  "filename": "daily_proj.csv",
  "saved_to": "analysis/daily_player_intake/daily_proj.csv",
  "projections_triggered": true,
  "projections_date": "2024-11-05"
}
```

### Scheduler Endpoints

#### `GET /api/v1/scheduler/status`
Get scheduler status and upcoming jobs

```bash
curl http://localhost:8000/api/v1/scheduler/status
```

Response:
```json
{
  "running": true,
  "jobs": [
    {
      "id": "noon_update",
      "name": "Daily Noon Update (EST)",
      "next_run": "2024-11-06T12:00:00-05:00",
      "trigger": "cron[hour='12', minute='0']"
    }
  ]
}
```

#### `POST /api/v1/scheduler/pause`
Pause the scheduler (stops automatic tasks)

```bash
curl -X POST http://localhost:8000/api/v1/scheduler/pause
```

#### `POST /api/v1/scheduler/resume`
Resume the scheduler

```bash
curl -X POST http://localhost:8000/api/v1/scheduler/resume
```

### Stats Endpoints (existing)

#### `GET /api/v1/stats/teams`
Fetch team stats from NBA API

```bash
curl "http://localhost:8000/api/v1/stats/teams?season=2024-25&last_n_games=10"
```

#### `GET /api/v1/stats/players`
Fetch player stats from NBA API

```bash
curl "http://localhost:8000/api/v1/stats/players?season=2024-25&last_n_games=5"
```

## Automation Workflows

### Daily Automated Workflow

**Time**: 12:00 PM EST every day

1. ✅ Database update (`db.run_daily_update`)
2. ✅ Game matchup calculations (`analysis.game_matchup`)
3. ⏸️ Waits for CSV upload
4. ✅ Player projections (triggered on CSV upload)

### Manual Workflow

#### Option 1: Full Pipeline + Projections

```bash
# Step 1: Run database + matchups
curl -X POST http://localhost:8000/api/v1/admin/run-full-pipeline \
  -H "Content-Type: application/json" \
  -d '{"date": "2024-11-05"}'

# Step 2: Upload CSV and auto-run projections
curl -X POST http://localhost:8000/api/v1/admin/upload-daily-csv \
  -F "file=@daily_proj.csv" \
  -F "auto_run_projections=true" \
  -F "date=2024-11-05"
```

#### Option 2: Individual Steps

```bash
# Step 1: Update database
curl -X POST http://localhost:8000/api/v1/admin/update-database \
  -H "Content-Type: application/json" \
  -d '{"date": "2024-11-05"}'

# Step 2: Calculate matchups
curl -X POST http://localhost:8000/api/v1/admin/calculate-matchups \
  -H "Content-Type: application/json" \
  -d '{"date": "2024-11-05"}'

# Step 3: Upload CSV
curl -X POST http://localhost:8000/api/v1/admin/upload-daily-csv \
  -F "file=@daily_proj.csv"

# Step 4: Run projections
curl -X POST http://localhost:8000/api/v1/admin/run-projections \
  -H "Content-Type: application/json" \
  -d '{"date": "2024-11-05"}'
```

## Frontend Integration

### React/Vue Example

```javascript
// Upload CSV and trigger projections
async function uploadAndRunProjections(file, date) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('auto_run_projections', 'true');
  formData.append('date', date);
  
  const response = await fetch('http://localhost:8000/api/v1/admin/upload-daily-csv', {
    method: 'POST',
    body: formData
  });
  
  return await response.json();
}

// Check scheduler status
async function getSchedulerStatus() {
  const response = await fetch('http://localhost:8000/api/v1/scheduler/status');
  return await response.json();
}

// Trigger full pipeline
async function runFullPipeline(date = null) {
  const response = await fetch('http://localhost:8000/api/v1/admin/run-full-pipeline', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ date })
  });
  
  return await response.json();
}
```

### Admin Dashboard Components

**Components to build:**

1. **Scheduler Status Card**
   - Show if scheduler is running
   - Display next scheduled run time
   - Pause/Resume buttons

2. **Manual Triggers Panel**
   - Buttons for each task
   - Date picker for custom dates
   - Task status indicators

3. **CSV Upload Widget**
   - File upload with drag & drop
   - Auto-run projections checkbox
   - Upload progress indicator

4. **Task History**
   - Recent task executions
   - Success/failure status
   - Execution logs

5. **System Health**
   - Database connection status
   - CSV file status
   - API health

## Monitoring & Logs

### View Logs

```bash
# When running with uvicorn
python main.py

# Logs will show:
# - Scheduled job triggers
# - Task starts and completions
# - Errors and warnings
```

Example log output:
```
2024-11-05 12:00:00 - __main__ - INFO - Running scheduled noon update
2024-11-05 12:00:01 - __main__ - INFO - Starting daily update for date: None
2024-11-05 12:05:23 - __main__ - INFO - Daily update completed successfully
2024-11-05 12:05:24 - __main__ - INFO - Starting game matchup calculations
2024-11-05 12:06:10 - __main__ - INFO - Game matchup calculations completed successfully
2024-11-05 12:06:10 - __main__ - INFO - Scheduled noon update completed
```

### Error Handling

All background tasks have try/catch error handling:
- Errors are logged but don't crash the API
- Failed tasks can be retried via manual triggers
- Scheduler continues running on task failures

## Production Deployment

### Using Systemd (Linux)

Create `/etc/systemd/system/nba-sharp.service`:

```ini
[Unit]
Description=NBA Sharp API
After=network.target postgresql.service

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/nba_sharp
Environment="DATABASE_URL=postgresql://..."
ExecStart=/path/to/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Start service:
```bash
sudo systemctl start nba-sharp
sudo systemctl enable nba-sharp  # Auto-start on boot
```

### Using Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install -e .

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Run:
```bash
docker build -t nba-sharp .
docker run -d -p 8000:8000 --env-file .env nba-sharp
```

### Environment Variables

Required:
- `DATABASE_URL`: PostgreSQL connection string

Optional:
- `PORT`: API port (default: 8000)
- `LOG_LEVEL`: Logging level (default: INFO)

## Troubleshooting

### Scheduler not running

Check status:
```bash
curl http://localhost:8000/api/v1/scheduler/status
```

If paused, resume:
```bash
curl -X POST http://localhost:8000/api/v1/scheduler/resume
```

### Task fails silently

Check server logs for error details. Tasks run in background, so HTTP response is immediate.

### CSV upload fails

Ensure:
1. File is `.csv` format
2. Directory `analysis/daily_player_intake/` exists
3. Server has write permissions

### Database connection fails

Verify:
1. `DATABASE_URL` in `.env` is correct
2. PostgreSQL is running
3. Database exists and is accessible

## Next Steps

For frontend development:
1. Use these endpoints to build admin dashboard
2. Implement real-time task status tracking (consider WebSockets)
3. Add user authentication
4. Build historical projection viewer
5. Add notification system for task completion

## Security Notes

**Important**: These are admin endpoints with no authentication!

For production:
1. Add authentication middleware (OAuth2, JWT)
2. Restrict admin endpoints to authenticated users
3. Add rate limiting
4. Use HTTPS
5. Implement CORS properly
6. Add API keys for external access

