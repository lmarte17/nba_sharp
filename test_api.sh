#!/bin/bash
# Test script for NBA Sharp API endpoints

BASE_URL="http://localhost:8000"
DATE="2024-11-05"

echo "=== NBA Sharp API Test Script ==="
echo ""

# Health check
echo "1. Health Check"
curl -s "$BASE_URL/health" | python -m json.tool
echo ""
echo ""

# Scheduler status
echo "2. Scheduler Status"
curl -s "$BASE_URL/api/v1/scheduler/status" | python -m json.tool
echo ""
echo ""

# Trigger database update (with date)
echo "3. Trigger Database Update (with specific date)"
curl -s -X POST "$BASE_URL/api/v1/admin/update-database" \
  -H "Content-Type: application/json" \
  -d "{\"date\": \"$DATE\"}" | python -m json.tool
echo ""
echo ""

# Trigger database update (for today)
echo "3b. Trigger Database Update (for today)"
curl -s -X POST "$BASE_URL/api/v1/admin/update-database" \
  -H "Content-Type: application/json" \
  -d "{}" | python -m json.tool
echo ""
echo ""

# Trigger matchup calculation
echo "4. Trigger Matchup Calculation"
curl -s -X POST "$BASE_URL/api/v1/admin/calculate-matchups" \
  -H "Content-Type: application/json" \
  -d "{\"date\": \"$DATE\"}" | python -m json.tool
echo ""
echo ""

# Upload CSV (if file exists)
if [ -f "analysis/daily_player_intake/daily_proj.csv" ]; then
  echo "5. Upload Daily CSV"
  curl -s -X POST "$BASE_URL/api/v1/admin/upload-daily-csv" \
    -F "file=@analysis/daily_player_intake/daily_proj.csv" | python -m json.tool
  echo ""
  echo ""
  
  # Trigger projections
  echo "6. Trigger Player Projections"
  curl -s -X POST "$BASE_URL/api/v1/admin/run-projections" \
    -H "Content-Type: application/json" \
    -d "{\"date\": \"$DATE\"}" | python -m json.tool
  echo ""
  echo ""
else
  echo "5. Skipping CSV upload (file not found)"
  echo ""
fi

echo "=== Test Complete ==="

