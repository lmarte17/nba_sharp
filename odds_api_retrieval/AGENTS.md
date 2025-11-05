# Odds API - Integration Guide for LLMs/Agents

This document provides comprehensive instructions for LLMs and automated agents to interact with the Odds Service API. All endpoints are RESTful and return JSON responses.

## Base URL

The API is hosted at a base URL that should be configured in your environment. All endpoints are prefixed with `/api`.

**Base Path**: `/api`

**Example Base URL**: `https://your-service-domain.com/api` or `http://localhost:8000/api` for local development

## Authentication

Currently, the API does not require authentication headers. The service handles API key management internally.

## Endpoint Overview

| Endpoint | Method | Description | Cost |
|----------|--------|-------------|------|
| `/api/health` | GET | Health check | Free |
| `/api/sports` | GET | List available sports | Free (cached) |
| `/api/{sport}/events` | GET | List events for a sport | 1 |
| `/api/{sport}/odds` | GET | Get featured odds (h2h, spreads, totals) | markets × regions |
| `/api/{sport}/events/{event_id}/odds` | GET | Get odds for specific event (props, period markets) | markets × regions |
| `/api/{sport}/scores` | GET | Get scores for completed/in-progress games | 1 (or 2 if daysFrom provided) |
| `/api/historical/{sport}/events` | GET | Historical events at specific timestamp | 1 |
| `/api/historical/{sport}/odds` | GET | Historical odds snapshot at specific timestamp | markets × regions |
| `/api/historical/{sport}/events/{event_id}/odds` | GET | Historical event odds at specific timestamp | markets × regions |

## Response Format

All endpoints return JSON objects. Most endpoints wrap data in a `data` or `events` or `sports` key:

```json
{
  "data": [...],
  // or
  "events": [...],
  // or
  "sports": [...]
}
```

Historical endpoints include additional metadata:

```json
{
  "timestamp": "2024-11-01T18:00:00Z",
  "previous_timestamp": "2024-11-01T17:00:00Z",
  "next_timestamp": "2024-11-01T19:00:00Z",
  "data": [...]
}
```

## Endpoints

### 1. Health Check

**Endpoint**: `GET /api/health`

**Purpose**: Verify the service is running and healthy.

**Parameters**: None

**Response**:
```json
{
  "status": "ok"
}
```

**Example Request**:
```bash
GET /api/health
```

**Use Case**: Use this endpoint to verify service availability before making other requests.

---

### 2. List Sports

**Endpoint**: `GET /api/sports`

**Purpose**: Retrieve all available sports (in-season or all sports).

**Parameters**: None (all sports are returned by default)

**Response**:
```json
{
  "sports": [
    {
      "key": "americanfootball_nfl",
      "active": true,
      "group": "American Football",
      "description": "US Football",
      "title": "NFL",
      "has_outrights": false
    },
    ...
  ]
}
```

**Example Request**:
```bash
GET /api/sports
```

**Common Sport Keys**:
- `americanfootball_nfl` - NFL
- `basketball_nba` - NBA
- `baseball_mlb` - MLB
- `icehockey_nhl` - NHL
- `soccer_epl` - English Premier League
- `soccer_usa_mls` - MLS

**Use Case**: 
1. First call this to discover available sports
2. Use the `key` field to make subsequent requests
3. Check `active` to see if sport is currently in season

---

### 3. List Events

**Endpoint**: `GET /api/{sport}/events`

**Purpose**: Get a list of events (games/matches) for a specific sport.

**Path Parameters**:
- `sport` (required): Sport key (e.g., `americanfootball_nfl`, `basketball_nba`)

**Query Parameters**:
- `eventIds` (optional): Comma-separated list of specific event IDs to filter
- `commenceTimeFrom` (optional): ISO 8601 timestamp (e.g., `2025-11-03T00:00:00Z`) - filter events starting from this time
- `commenceTimeTo` (optional): ISO 8601 timestamp - filter events starting before this time
- `dateFormat` (optional): Response timestamp format - `iso` (default) or `unix`

**Response**:
```json
{
  "events": [
    {
      "id": "abc123def456...",
      "sport_key": "americanfootball_nfl",
      "sport_title": "NFL",
      "commence_time": "2025-11-03T18:00:00Z",
      "home_team": "Kansas City Chiefs",
      "away_team": "Buffalo Bills",
      "completed": false
    },
    ...
  ]
}
```

**Example Requests**:
```bash
# Get all upcoming NFL events
GET /api/americanfootball_nfl/events

# Get events for a specific date range
GET /api/americanfootball_nfl/events?commenceTimeFrom=2025-11-03T00:00:00Z&commenceTimeTo=2025-11-03T23:59:59Z

# Get specific events by ID
GET /api/basketball_nba/events?eventIds=event1,event2,event3
```

**Use Case**:
1. Discover upcoming games for a sport
2. Get event IDs needed for detailed odds requests
3. Filter events by date range for specific time periods

---

### 4. Get Featured Odds

**Endpoint**: `GET /api/{sport}/odds`

**Purpose**: Get odds for featured markets (h2h, spreads, totals, outrights) across multiple events.

**Path Parameters**:
- `sport` (required): Sport key

**Query Parameters**:
- `markets` (optional): Comma-separated market keys (default: `h2h`). Examples: `h2h,spreads,totals`
- `regions` (optional): Comma-separated region codes (default from config). Examples: `us,uk,eu`
- `bookmakers` (optional): Comma-separated bookmaker keys. Overrides regions. Examples: `fanduel,draftkings`
- `eventIds` (optional): Comma-separated event IDs to filter specific events
- `commenceTimeFrom` (optional): ISO 8601 timestamp - filter events starting from this time
- `commenceTimeTo` (optional): ISO 8601 timestamp - filter events starting before this time
- `includeLinks` (optional): Boolean - include deep links to bookmaker sites
- `includeSids` (optional): Boolean - include sportsbook IDs
- `includeBetLimits` (optional): Boolean - include bet limit information

**Available Markets**:
- `h2h` - Moneyline/head-to-head (win/loss)
- `spreads` - Point spreads
- `totals` - Over/under totals
- `outrights` - Futures/tournament outcomes

**Response**:
```json
{
  "data": [
    {
      "id": "abc123...",
      "sport_key": "americanfootball_nfl",
      "commence_time": "2025-11-03T18:00:00Z",
      "home_team": "Kansas City Chiefs",
      "away_team": "Buffalo Bills",
      "bookmakers": [
        {
          "key": "fanduel",
          "title": "FanDuel",
          "markets": [
            {
              "key": "h2h",
              "outcomes": [
                {"name": "Kansas City Chiefs", "price": 1.95},
                {"name": "Buffalo Bills", "price": 1.90}
              ]
            },
            {
              "key": "spreads",
              "outcomes": [
                {"name": "Kansas City Chiefs", "point": -3.5, "price": 1.90},
                {"name": "Buffalo Bills", "point": 3.5, "price": 1.90}
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

**Example Requests**:
```bash
# Get moneyline odds only (default)
GET /api/americanfootball_nfl/odds

# Get multiple markets for US region
GET /api/americanfootball_nfl/odds?markets=h2h,spreads,totals&regions=us

# Get odds for specific events
GET /api/basketball_nba/odds?eventIds=event1,event2&markets=h2h,spreads

# Get odds from specific bookmakers
GET /api/americanfootball_nfl/odds?bookmakers=fanduel,draftkings&markets=h2h
```

**Cost**: `markets × regions` (e.g., 3 markets × 1 region = 3 requests)

**Use Case**:
1. Get betting odds for multiple games at once
2. Compare odds across different bookmakers
3. Monitor line movements for featured markets

---

### 5. Get Event-Specific Odds

**Endpoint**: `GET /api/{sport}/events/{event_id}/odds`

**Purpose**: Get detailed odds for a specific event, including player props, period markets, and alternate lines.

**Path Parameters**:
- `sport` (required): Sport key
- `event_id` (required): 32-character event ID

**Query Parameters**:
- `markets` (optional): Comma-separated market keys. Supports player props, period markets, etc.
- `regions` (optional): Comma-separated region codes
- `bookmakers` (optional): Comma-separated bookmaker keys
- `includeLinks` (optional): Boolean
- `includeSids` (optional): Boolean
- `includeBetLimits` (optional): Boolean

**Available Markets** (examples - many more available):
- Player props: `player_points`, `player_rebounds`, `player_assists`, `player_pass_tds`, `player_reception_yards`, etc.
- Period markets: `h2h_q1`, `h2h_q2`, `h2h_h1`, `h2h_h2`, `spreads_q1`, `totals_q1`, etc.
- Alternate lines: `alternate_spreads`, `alternate_totals`
- Sport-specific: `btts` (both teams to score - soccer), `draw_no_bet` (soccer)

**Response**: Same structure as featured odds, but may include additional market types.

**Example Requests**:
```bash
# Get player props for an NBA game
GET /api/basketball_nba/events/abc123.../odds?markets=player_points,player_rebounds&regions=us

# Get quarter-by-quarter markets
GET /api/basketball_nba/events/abc123.../odds?markets=h2h_q1,h2h_q2,h2h_q3,h2h_q4&regions=us

# Get all available markets for an event
GET /api/americanfootball_nfl/events/abc123.../odds?regions=us
```

**Cost**: `markets × regions`

**Use Case**:
1. Get detailed betting options for a specific game
2. Retrieve player prop bets
3. Access period-specific markets (quarters, halves, periods)

---

### 6. Get Scores

**Endpoint**: `GET /api/{sport}/scores`

**Purpose**: Get scores for completed or in-progress games.

**Path Parameters**:
- `sport` (required): Sport key

**Query Parameters**:
- `daysFrom` (optional): Integer 1-3. Number of days back to retrieve scores. Cost is 2 if provided, 1 if omitted.
- `dateFormat` (optional): `iso` (default) or `unix`
- `eventIds` (optional): Comma-separated event IDs to filter
- `date` (optional): ISO 8601 date string (YYYY-MM-DD format)

**Response**:
```json
{
  "data": [
    {
      "id": "abc123...",
      "sport_key": "basketball_nba",
      "commence_time": "2025-11-03T18:00:00Z",
      "home_team": "Lakers",
      "away_team": "Warriors",
      "completed": true,
      "scores": [
        {"name": "Lakers", "score": 112},
        {"name": "Warriors", "score": 108}
      ]
    },
    ...
  ]
}
```

**Example Requests**:
```bash
# Get recent scores (last day)
GET /api/basketball_nba/scores?daysFrom=1

# Get scores for specific events
GET /api/americanfootball_nfl/scores?eventIds=event1,event2

# Get scores for a specific date
GET /api/basketball_nba/scores?date=2025-11-03
```

**Cost**: 1 (or 2 if `daysFrom` is provided)

**Use Case**:
1. Check game results
2. Track live scores
3. Historical score lookup

---

### 7. Get Historical Events

**Endpoint**: `GET /api/historical/{sport}/events`

**Purpose**: Get a snapshot of events as they existed at a specific point in time.

**Path Parameters**:
- `sport` (required): Sport key

**Query Parameters**:
- `date` (required): ISO 8601 timestamp of the snapshot (e.g., `2024-11-01T18:00:00Z`)
- `dateFormat` (optional): Response format - `iso` (default) or `unix`
- `eventIds` (optional): Comma-separated event IDs to filter
- `commenceTimeFrom` (optional): ISO 8601 timestamp filter
- `commenceTimeTo` (optional): ISO 8601 timestamp filter

**Response**:
```json
{
  "timestamp": "2024-11-01T18:00:00Z",
  "previous_timestamp": "2024-11-01T17:00:00Z",
  "next_timestamp": "2024-11-01T19:00:00Z",
  "data": [
    {
      "id": "abc123...",
      "sport_key": "basketball_nba",
      "commence_time": "2024-11-01T20:00:00Z",
      "home_team": "Lakers",
      "away_team": "Warriors",
      "completed": false
    },
    ...
  ]
}
```

**Example Request**:
```bash
GET /api/historical/basketball_nba/events?date=2024-11-01T18:00:00Z
```

**Use Case**:
1. See what events were scheduled at a past point in time
2. Historical analysis of event schedules
3. Audit trail of event changes

---

### 8. Get Historical Odds

**Endpoint**: `GET /api/historical/{sport}/odds`

**Purpose**: Get a snapshot of odds as they existed at a specific point in time across multiple events.

**Path Parameters**:
- `sport` (required): Sport key

**Query Parameters**:
- `regions` (required): Comma-separated region codes (at least one required)
- `date` (required): ISO 8601 timestamp of the snapshot
- `markets` (optional): Comma-separated market keys
- `oddsFormat` (optional): `american` (default) or `decimal`
- `dateFormat` (optional): `iso` (default) or `unix`

**Response**: Same structure as featured odds, but includes timestamp metadata:

```json
{
  "timestamp": "2024-09-15T18:00:00Z",
  "previous_timestamp": "2024-09-15T17:00:00Z",
  "next_timestamp": "2024-09-15T19:00:00Z",
  "data": [
    {
      "id": "abc123...",
      "bookmakers": [...],
      ...
    }
  ]
}
```

**Example Request**:
```bash
GET /api/historical/americanfootball_nfl/odds?date=2024-09-15T18:00:00Z&markets=h2h&regions=us
```

**Cost**: `markets × regions`

**Use Case**:
1. Analyze how odds changed over time
2. Backtest betting strategies
3. Research historical line movements

---

### 9. Get Historical Event Odds

**Endpoint**: `GET /api/historical/{sport}/events/{event_id}/odds`

**Purpose**: Get a snapshot of odds for a specific event at a specific point in time.

**Path Parameters**:
- `sport` (required): Sport key
- `event_id` (required): 32-character event ID

**Query Parameters**:
- `regions` (required): Comma-separated region codes (at least one required)
- `date` (required): ISO 8601 timestamp of the snapshot
- `markets` (optional): Comma-separated market keys
- `oddsFormat` (optional): `american` (default) or `decimal`
- `dateFormat` (optional): `iso` (default) or `unix`

**Response**: Single event object with timestamp metadata:

```json
{
  "timestamp": "2024-11-01T22:00:00Z",
  "previous_timestamp": "2024-11-01T21:00:00Z",
  "next_timestamp": "2024-11-01T23:00:00Z",
  "data": {
    "id": "abc123...",
    "bookmakers": [...],
    ...
  }
}
```

**Example Request**:
```bash
GET /api/historical/basketball_nba/events/abc123.../odds?date=2024-11-01T22:00:00Z&markets=h2h,spreads&regions=us
```

**Cost**: `markets × regions`

**Use Case**:
1. Track how odds for a specific game changed over time
2. Analyze line movement for a particular event
3. Historical research on specific games

---

## Common Patterns and Best Practices

### 1. Discovering Available Data

**Workflow**:
1. Call `/api/sports` to get available sports
2. Use a sport key to call `/api/{sport}/events` to see upcoming games
3. Use event IDs to get detailed odds via `/api/{sport}/events/{event_id}/odds`

### 2. Filtering by Date

Use ISO 8601 timestamps (UTC recommended):
- Format: `YYYY-MM-DDTHH:MM:SSZ` or `YYYY-MM-DDTHH:MM:SS+00:00`
- Examples: `2025-11-03T00:00:00Z`, `2025-11-03T18:30:00Z`

### 3. Comma-Separated Parameters

Many parameters accept comma-separated values. You can also pass them as repeated query parameters:
- `?markets=h2h,spreads,totals` OR `?markets=h2h&markets=spreads&markets=totals`
- `?regions=us,uk` OR `?regions=us&regions=uk`

### 4. Cost Optimization

- Start with `/api/sports` (free, cached)
- Use `/api/{sport}/events` (cost: 1) to discover events before requesting odds
- Request only needed markets to minimize costs
- Use specific `eventIds` to filter data instead of fetching all events
- Consider caching responses for frequently accessed data

### 5. Error Handling

The API uses standard HTTP status codes:
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `404` - Not Found (invalid sport/event)
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error
- `503` - Service Unavailable (configuration error)

Always check response status codes and handle errors appropriately.

### 6. Rate Limits

The service enforces rate limits (30 requests/second). If you receive a `429` response:
- Wait before retrying
- Implement exponential backoff
- Consider batching requests when possible

### 7. Response Headers

Check these headers for quota information:
- `x-requests-used`: Requests used since last reset
- `x-requests-remaining`: Requests remaining before quota reset
- `x-requests-last`: Cost of the last API call

---

## Example Workflows

### Workflow 1: Get Current NFL Odds

```bash
# 1. Get NFL events for today
GET /api/americanfootball_nfl/events?commenceTimeFrom=2025-11-03T00:00:00Z&commenceTimeTo=2025-11-03T23:59:59Z

# 2. Get odds for those events
GET /api/americanfootball_nfl/odds?markets=h2h,spreads,totals&regions=us&commenceTimeFrom=2025-11-03T00:00:00Z&commenceTimeTo=2025-11-03T23:59:59Z
```

### Workflow 2: Get Player Props for a Specific Game

```bash
# 1. Get event ID
GET /api/basketball_nba/events?commenceTimeFrom=2025-11-03T18:00:00Z&commenceTimeTo=2025-11-03T23:59:59Z

# 2. Use event ID to get player props
GET /api/basketball_nba/events/{event_id}/odds?markets=player_points,player_rebounds,player_assists&regions=us
```

### Workflow 3: Historical Analysis

```bash
# 1. Get historical odds snapshot
GET /api/historical/americanfootball_nfl/odds?date=2024-09-15T18:00:00Z&markets=h2h&regions=us

# 2. Get next snapshot to compare
# Use next_timestamp from previous response
GET /api/historical/americanfootball_nfl/odds?date={next_timestamp}&markets=h2h&regions=us
```

---

## Notes for LLM/Agent Implementation

1. **Always validate parameters**: Check that sport keys, event IDs, and timestamps are valid before making requests.

2. **Handle pagination**: The API doesn't paginate, but responses may be large. Consider filtering by date ranges or event IDs.

3. **Cache sports list**: The `/api/sports` endpoint is free and cached. Store the result and reuse it.

4. **Event IDs are 32 characters**: Validate event ID length before using in path parameters.

5. **ISO 8601 timestamps**: Always use UTC timezone (Z suffix) for consistency.

6. **Cost awareness**: Track costs by monitoring response headers and minimizing unnecessary requests.

7. **Error recovery**: Implement retry logic with backoff for transient errors (429, 500, 503).

8. **Type safety**: All responses are JSON. Validate structure before accessing nested fields.

---

## Quick Reference

| Operation | Endpoint Pattern | Key Parameters |
|-----------|-----------------|----------------|
| Health check | `GET /api/health` | None |
| List sports | `GET /api/sports` | None |
| List events | `GET /api/{sport}/events` | `commenceTimeFrom`, `commenceTimeTo`, `eventIds` |
| Get featured odds | `GET /api/{sport}/odds` | `markets`, `regions`, `bookmakers`, `eventIds` |
| Get event odds | `GET /api/{sport}/events/{event_id}/odds` | `markets`, `regions`, `bookmakers` |
| Get scores | `GET /api/{sport}/scores` | `daysFrom`, `date`, `eventIds` |
| Historical events | `GET /api/historical/{sport}/events` | `date` (required) |
| Historical odds | `GET /api/historical/{sport}/odds` | `date` (required), `regions` (required) |
| Historical event odds | `GET /api/historical/{sport}/events/{event_id}/odds` | `date` (required), `regions` (required) |

