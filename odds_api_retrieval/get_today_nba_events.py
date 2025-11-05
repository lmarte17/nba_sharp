import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


DEFAULT_BASE_API_URL = os.environ.get("ODDS_API_BASE_URL", "http://localhost:8000/api")
SPORT_KEY = "basketball_nba"


def iso_utc_range_for_local_day(local_day: datetime, tz: ZoneInfo) -> Tuple[str, str]:
    """
    Given a local datetime (date component used) and a time zone, return the UTC ISO 8601
    start/end timestamps that cover that local calendar day.
    """
    day_start_local = datetime(
        year=local_day.year,
        month=local_day.month,
        day=local_day.day,
        tzinfo=tz,
    )
    day_end_local = day_start_local + timedelta(days=1) - timedelta(seconds=1)
    day_start_utc = day_start_local.astimezone(timezone.utc)
    day_end_utc = day_end_local.astimezone(timezone.utc)
    return (
        day_start_utc.isoformat().replace("+00:00", "Z"),
        day_end_utc.isoformat().replace("+00:00", "Z"),
    )


def build_events_url(
    base_api_url: str,
    sport_key: str,
    commence_from_iso: str,
    commence_to_iso: str,
    date_format: str = "iso",
    event_ids: Optional[str] = None,
) -> str:
    """
    Build the full URL for GET /api/{sport}/events with date filters.
    """
    base = base_api_url.rstrip("/") + "/"
    path = f"{sport_key}/events"
    endpoint = urljoin(base, path)

    params = {
        "commenceTimeFrom": commence_from_iso,
        "commenceTimeTo": commence_to_iso,
        "dateFormat": date_format,
    }
    if event_ids:
        params["eventIds"] = event_ids

    return f"{endpoint}?{urlencode(params)}"


def fetch_json(url: str, timeout_seconds: int = 20) -> dict:
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=timeout_seconds) as resp:
        content_type = resp.headers.get("Content-Type", "")
        data = resp.read()
        if "application/json" not in content_type:
            # Fallback: attempt to parse regardless
            return json.loads(data.decode("utf-8"))
        return json.loads(data)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Retrieve today's NBA events (interpreting 'today' in a chosen timezone, "
            "default America/New_York), converted to UTC for /api/basketball_nba/events"
        ),
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_API_URL,
        help="Base API URL (default from ODDS_API_BASE_URL or http://localhost:8000/api)",
    )
    parser.add_argument(
        "--tz",
        default="America/New_York",
        help="IANA timezone name to interpret the local day (default: America/New_York)",
    )
    parser.add_argument(
        "--date",
        default=None,
        help=(
            "Local date in YYYY-MM-DD (interpreted in --tz). Defaults to today's date in --tz."
        ),
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    args = parser.parse_args()

    try:
        tz = ZoneInfo(args.tz)
    except Exception as exc:
        raise SystemExit(f"Invalid timezone for --tz: {args.tz} ({exc})")

    if args.date:
        try:
            # Parse the date and attach the provided timezone
            local_day = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=tz)
        except ValueError as exc:
            raise SystemExit(f"Invalid --date format, expected YYYY-MM-DD: {exc}")
    else:
        # Use 'today' in the provided timezone
        local_day = datetime.now(tz)

    start_iso, end_iso = iso_utc_range_for_local_day(local_day, tz)
    url = build_events_url(
        base_api_url=args.base_url,
        sport_key=SPORT_KEY,
        commence_from_iso=start_iso,
        commence_to_iso=end_iso,
        date_format="iso",
    )

    try:
        payload = fetch_json(url)
    except Exception as exc:
        raise SystemExit(f"Request failed: {exc}")

    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=False))
    else:
        print(json.dumps(payload, separators=(",", ":")))


if __name__ == "__main__":
    main()


