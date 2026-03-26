#!/usr/bin/env python3
"""
Generate a stable, analysis-friendly CSV from the local activity JSON archive.

Inputs:
  archive/activities/<activity_id>.json

Outputs:
  derived/activities.csv

Design:
- JSON-first: NO Strava API calls.
- Deterministic: always rebuild the full CSV from local JSON files.
- Works even if some fields are missing/null.
"""

from __future__ import annotations

import csv
from datetime import datetime

from typing import Any, Dict, List, Optional

from activity_archive.archive import count_json_files, iter_activity_dicts
from activity_archive.activity import activity_type, parse_iso_datetime, is_run
from activity_archive.units import (
    meters_to_feet,
    meters_to_miles,
    mps_to_mph,
    pace_mmss,
    safe_float,
    safe_int,
)

from activity_archive.paths import ACTIVITIES_DIR, ACTIVITIES_CSV_PATH


DISTANCE_MI_DECIMALS = 2
MOVING_MIN_DECIMALS = 2
PACE_DECIMALS = 2
SPEED_MPH_DECIMALS = 2
ELAPSED_MIN_DECIMALS = 2
ELEV_FT_DECIMALS = 0

FIELDNAMES = [
    "id",
    "date_local",
    "start_time_local",
    "type",
    "distance_mi",
    "moving_time_min",
    "elapsed_time_min",
    "total_elev_gain_ft",
    "avg_speed_mph",
    "pace_mmss",
    "pace_min_per_mi",
    "name",
]


def hhmmss(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    return dt.strftime("%H:%M:%S")


def activity_to_row(a: dict[str, Any]) -> Dict[str, Any]:
    activity_id = str(a.get("id") or "")

    typ = activity_type(a)

    start_local = parse_iso_datetime(a.get("start_date_local")) or parse_iso_datetime(
        a.get("start_date")
    )
    date_local = start_local.date().isoformat() if start_local else ""
    time_local = hhmmss(start_local)

    distance_m = safe_float(a.get("distance")) or 0.0
    distance_mi = meters_to_miles(distance_m)

    moving_seconds = safe_int(a.get("moving_time"), default=0)
    elapsed_seconds = safe_int(a.get("elapsed_time"), default=0)

    moving_min = (moving_seconds / 60.0) if moving_seconds else 0.0
    elapsed_min = (elapsed_seconds / 60.0) if elapsed_seconds else 0.0

    elev_gain_m = safe_float(a.get("total_elevation_gain"), default=0.0)
    elev_ft = meters_to_feet(elev_gain_m)

    avg_speed_mps = safe_float(a.get("average_speed"), default=0.0)
    avg_speed_mph = mps_to_mph(avg_speed_mps)

    pace_str = ""
    pace_min_per_mi = ""

    if is_run(a) and distance_mi > 0 and moving_seconds > 0:
        pace_str = pace_mmss(distance_mi, moving_seconds)
        pace_min_per_mi = round(
            (moving_seconds / distance_mi) / 60.0,
            PACE_DECIMALS,
        )

    return {
        "id": activity_id,
        "date_local": date_local,
        "start_time_local": time_local,
        "type": typ,
        "distance_mi": round(distance_mi, DISTANCE_MI_DECIMALS) if distance_mi > 0 else "",
        "moving_time_min": (round(moving_min, MOVING_MIN_DECIMALS) if moving_min > 0 else ""),
        "elapsed_time_min": (round(elapsed_min, ELAPSED_MIN_DECIMALS) if elapsed_min > 0 else ""),
        "total_elev_gain_ft": round(elev_ft, ELEV_FT_DECIMALS) if elev_ft > 0 else "",
        "avg_speed_mph": (round(avg_speed_mph, SPEED_MPH_DECIMALS) if avg_speed_mph > 0 else ""),
        "pace_mmss": pace_str,
        "pace_min_per_mi": pace_min_per_mi,
        "name": (a.get("name") or "").strip(),
    }


def main() -> None:
    if not ACTIVITIES_DIR.exists():
        raise SystemExit(f"Archive dir not found: {ACTIVITIES_DIR}")

    ACTIVITIES_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    total_files = count_json_files(ACTIVITIES_DIR)
    rows: List[Dict[str, Any]] = []

    for a in iter_activity_dicts(ACTIVITIES_DIR):
        row = activity_to_row(a)
        if row.get("id"):
            rows.append(row)

    rows.sort(
        key=lambda r: (
            str(r.get("date_local") or ""),
            str(r.get("start_time_local") or ""),
            str(r.get("id") or ""),
        ),
        reverse=True,
    )

    ACTIVITIES_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ACTIVITIES_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} activities to {ACTIVITIES_CSV_PATH}")
    skipped = total_files - len({r["id"] for r in rows if r.get("id")})
    if skipped > 0:
        print(f"Note: {skipped} file(s) were unreadable/non-dict/duplicate-id and were skipped.")


if __name__ == "__main__":
    main()
