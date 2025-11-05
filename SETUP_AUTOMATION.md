# NBA Sharp - Automation Setup Guide

## Quick Setup

### 1. Install New Dependencies

```bash
uv sync
```

This installs the new packages:
- `apscheduler` - Job scheduling
- `python-multipart` - File uploads
- `python-dotenv` - Environment variables

### 2. Verify Environment Variables

Ensure `.env` contains:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/nba_sharp
```

### 3. Start the API

```bash
python main.py
```

You should see:

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Scheduler started. Noon EST job configured.
INFO:     Next scheduled run: 2024-11-06T12:00:00-05:00
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## What Was Automated

### ✅ Automatic (Scheduled at Noon EST)

These run automatically every day at 12:00 PM EST:

1. **Database Update**
   ```bash
   python -m db.run_daily_update --database-url $DATABASE_URL
   ```

2. **Game Matchup Calculations**
   ```bash
   python -m analysis.game_matchup --database-url $DATABASE_URL
   ```

### 🔄 Triggered on CSV Upload

This runs when you upload `daily_proj.csv`:

3. **Player Projections**
   ```bash
   python -m analysis.player_proj --save-to-db --database-url $DATABASE_URL
   ```

## How to Use

### Option 1: Let It Run Automatically

Just start the API and it will:
- Run database updates + matchups at noon EST daily
- Wait for you to upload the CSV
- Process projections when CSV is uploaded

### Option 2: Manual Triggers

Use the API endpoints to run tasks on demand:

```bash
# Run full pipeline (DB + matchups)
curl -X POST http://localhost:8000/api/v1/admin/run-full-pipeline \
  -H "Content-Type: application/json" \
  -d '{"date": "2024-11-05"}'

# Upload CSV and auto-run projections
curl -X POST http://localhost:8000/api/v1/admin/upload-daily-csv \
  -F "file=@daily_proj.csv" \
  -F "auto_run_projections=true"
```

### Option 3: Test Script

```bash
chmod +x test_api.sh
./test_api.sh
```

## API Endpoints Summary

### Admin Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/admin/update-database` | POST | Run database update |
| `/api/v1/admin/calculate-matchups` | POST | Run matchup calculations |
| `/api/v1/admin/run-projections` | POST | Run player projections |
| `/api/v1/admin/run-full-pipeline` | POST | Run DB update + matchups |
| `/api/v1/admin/upload-daily-csv` | POST | Upload CSV file |

### Scheduler Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/scheduler/status` | GET | View scheduled jobs |
| `/api/v1/scheduler/pause` | POST | Pause automation |
| `/api/v1/scheduler/resume` | POST | Resume automation |

### Monitoring

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | System health check |
| `/` | GET | API info |

## Workflow Examples

### Daily Workflow (Automated)

```
12:00 PM EST
  ↓
Database Update (automatic)
  ↓
Matchup Calculations (automatic)
  ↓
[Wait for CSV upload]
  ↓
You upload CSV via API/frontend
  ↓
Player Projections (triggered)
  ↓
Done!
```

### Manual Workflow

```bash
# Morning: Get latest data
curl -X POST http://localhost:8000/api/v1/admin/run-full-pipeline \
  -H "Content-Type: application/json" \
  -d '{}'

# Afternoon: Upload new CSV with updated minutes
curl -X POST http://localhost:8000/api/v1/admin/upload-daily-csv \
  -F "file=@daily_proj_v2.csv" \
  -F "auto_run_projections=true"

# Done! Projections updated in database
```

## Frontend Integration

When building your admin dashboard, you'll call these endpoints:

### Dashboard Components

1. **Status Card**
   ```javascript
   // Check if system is healthy
   fetch('/health')
   
   // Check next scheduled run
   fetch('/api/v1/scheduler/status')
   ```

2. **Manual Trigger Buttons**
   ```javascript
   // Run database update
   fetch('/api/v1/admin/update-database', {
     method: 'POST',
     headers: {'Content-Type': 'application/json'},
     body: JSON.stringify({date: '2024-11-05'})
   })
   ```

3. **CSV Upload Widget**
   ```javascript
   const formData = new FormData();
   formData.append('file', fileInput.files[0]);
   formData.append('auto_run_projections', 'true');
   
   fetch('/api/v1/admin/upload-daily-csv', {
     method: 'POST',
     body: formData
   })
   ```

## Monitoring

### Check Scheduler Status

```bash
curl http://localhost:8000/api/v1/scheduler/status
```

Output:
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

### View Logs

The API logs all task executions:

```
2024-11-05 12:00:00 - __main__ - INFO - Running scheduled noon update
2024-11-05 12:00:01 - __main__ - INFO - Starting daily update for date: None
2024-11-05 12:05:23 - __main__ - INFO - Daily update completed successfully
```

### Pause/Resume Automation

```bash
# Pause scheduled tasks
curl -X POST http://localhost:8000/api/v1/scheduler/pause

# Resume
curl -X POST http://localhost:8000/api/v1/scheduler/resume
```

## Production Deployment

### Using PM2 (Node.js Process Manager)

```bash
# Install PM2
npm install -g pm2

# Start API
pm2 start main.py --name nba-sharp --interpreter python3

# Auto-restart on reboot
pm2 startup
pm2 save
```

### Using Systemd (Linux)

```bash
# Create service file
sudo nano /etc/systemd/system/nba-sharp.service

# Enable and start
sudo systemctl enable nba-sharp
sudo systemctl start nba-sharp

# View logs
sudo journalctl -u nba-sharp -f
```

See `API_AUTOMATION.md` for detailed deployment instructions.

## Troubleshooting

### API doesn't start

```bash
# Check dependencies
uv sync

# Check environment
cat .env

# Run with verbose logging
uvicorn main:app --log-level debug
```

### Scheduled task doesn't run

```bash
# Check scheduler status
curl http://localhost:8000/api/v1/scheduler/status

# Check if paused
# Resume if needed
curl -X POST http://localhost:8000/api/v1/scheduler/resume
```

### CSV upload fails

Ensure directory exists:
```bash
mkdir -p analysis/daily_player_intake
```

### Database errors

Check connection:
```bash
# Verify DATABASE_URL
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1;"
```

## Next Steps

1. ✅ **Test the automation**
   ```bash
   ./test_api.sh
   ```

2. ✅ **Verify scheduled job**
   ```bash
   curl http://localhost:8000/api/v1/scheduler/status
   ```

3. 🔜 **Build frontend admin dashboard**
   - Use endpoints from `API_AUTOMATION.md`
   - Implement file upload widget
   - Add task status monitoring

4. 🔜 **Add authentication**
   - Secure admin endpoints
   - Add user management
   - Implement API keys

5. 🔜 **Add notifications**
   - Email on task completion
   - Slack/Discord webhooks
   - Push notifications

## Files Reference

- `main.py` - FastAPI application with automation
- `API_AUTOMATION.md` - Complete API documentation
- `test_api.sh` - Test script for all endpoints
- `pyproject.toml` - Updated dependencies
- `.env` - Environment variables (DATABASE_URL)

## Summary

You now have:

✅ **Automated noon EST updates** - Database + matchups run daily  
✅ **CSV upload endpoint** - Upload file via API  
✅ **Auto-trigger projections** - Optionally run on upload  
✅ **Manual triggers** - Run any task on demand  
✅ **Scheduler control** - Pause/resume automation  
✅ **Health monitoring** - Status endpoints  
✅ **Background tasks** - Non-blocking execution  
✅ **Complete logging** - Track all operations  
✅ **Production ready** - Deployment guides included  

The system is ready for your admin dashboard frontend!

