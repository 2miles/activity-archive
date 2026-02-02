"""
Export Strava activities to a stable, analysis-friendly CSV.

Outputs:
  out/activities.csv

Default behavior:
- Incremental fetch: if out/activities.csv exists, fetch only activities after the
  latest (date_local + start_time_local) in the file.
- Full rewrite: merge by id, then rewrite the whole CSV deterministically.
"""

import argparse
import csv
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from stravalib import unit_helper

from client import get_client


OUT_DIR = "out"
OUT_PATH = os.path.join(OUT_DIR, "activities.csv")

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


def clean_activity_type(activity_type: Any) -> str:
    root = getattr(activity_type, "root", None)
    return root if isinstance(root, str) and root else str(activity_type)


def miles(distance) -> float:
    if not distance:
        return 0.0
    return float(unit_helper.miles(distance).magnitude)


def seconds_to_mmss(seconds: Optional[float]) -> str:
    if not seconds or seconds <= 0:
        return ""
    total = int(round(seconds))
    mm = total // 60
    ss = total % 60
    return f"{mm}:{ss:02d}"


def pace_seconds_per_mile(distance_mi: float, moving_time_sec: float) -> Optional[float]:
    if distance_mi <= 0 or moving_time_sec <= 0:
        return None
    return moving_time_sec / distance_mi


def mph(speed_mps) -> float:
    if not speed_mps:
        return 0.0
    # speed_mps is usually a pint Quantity; unit_helper.miles_per_hour handles it
    return float(unit_helper.miles_per_hour(speed_mps).magnitude)


def feet(elevation) -> float:
    if not elevation:
        return 0.0
    return float(unit_helper.feet(elevation).magnitude)


def is_run_type(type_str: str) -> bool:
    return type_str in {"Run", "TrailRun", "VirtualRun"}


def hhmmss_local(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    return dt.strftime("%H:%M:%S")


def parse_row_datetime(row: Dict[str, str]) -> Optional[datetime]:
    """
    Parse (date_local + start_time_local) into a naive datetime for comparisons.
    """
    date_s = (row.get("date_local") or "").strip()
    time_s = (row.get("start_time_local") or "").strip()
    if not date_s or not time_s:
        return None
    try:
        return datetime.fromisoformat(f"{date_s}T{time_s}")
    except ValueError:
        return None


def load_existing_rows(path: str) -> Tuple[List[Dict[str, str]], Optional[datetime]]:
    if not os.path.exists(path):
        return [], None

    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    dts = [parse_row_datetime(r) for r in rows]
    dts = [dt for dt in dts if dt is not None]
    latest_dt = max(dts) if dts else None

    return rows, latest_dt


def activity_to_row(a) -> Dict[str, Any]:
    type_str = clean_activity_type(a.type)

    distance_mi = miles(a.distance)
    elev_ft = feet(getattr(a, "total_elevation_gain", None))
    moving_time_sec = float(a.moving_time) if a.moving_time else 0.0
    moving_time_min = moving_time_sec / 60.0 if moving_time_sec else 0.0
    elapsed_time_sec = float(a.elapsed_time) if a.elapsed_time else 0.0
    elapsed_time_min = elapsed_time_sec / 60.0 if elapsed_time_sec else 0.0
    avg_speed_mph = round(mph(getattr(a, "average_speed", None)), SPEED_MPH_DECIMALS)

    pace_sec_mi = (
        pace_seconds_per_mile(distance_mi, moving_time_sec) if is_run_type(type_str) else None
    )

    start_local = getattr(a, "start_date_local", None)

    return {
        "id": str(a.id),
        "date_local": start_local.date().isoformat() if start_local else "",
        "start_time_local": hhmmss_local(start_local),
        "type": type_str,
        "distance_mi": round(distance_mi, DISTANCE_MI_DECIMALS),
        "moving_time_min": round(moving_time_min, MOVING_MIN_DECIMALS),
        "elapsed_time_min": round(elapsed_time_min, ELAPSED_MIN_DECIMALS),
        "total_elev_gain_ft": round(elev_ft, ELEV_FT_DECIMALS) if elev_ft > 0 else "",
        "avg_speed_mph": avg_speed_mph if avg_speed_mph > 0 else "",
        "pace_mmss": seconds_to_mmss(pace_sec_mi),
        "pace_min_per_mi": round((pace_sec_mi / 60.0), PACE_DECIMALS) if pace_sec_mi else "",
        "name": a.name or "",
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Export Strava activities to a deterministic CSV.")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Fetch all activities and rebuild CSV from scratch",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)

    if args.full:
        existing_rows = []
        latest_dt = None
    else:
        existing_rows, latest_dt = load_existing_rows(OUT_PATH)

    client = get_client()

    # Full rebuild fetches all activities; default mode fetches only new ones
    activities_iter = (
        client.get_activities()
        if args.full or not latest_dt
        else client.get_activities(after=latest_dt)
    )

    new_rows: List[Dict[str, Any]] = [activity_to_row(a) for a in activities_iter]

    # Merge (existing + new) by id, with new rows overwriting existing.
    merged_by_id: Dict[str, Dict[str, Any]] = {
        str(r["id"]): r for r in existing_rows if r.get("id")
    }
    for r in new_rows:
        merged_by_id[str(r["id"])] = r

    rows: List[Dict[str, Any]] = list(merged_by_id.values())

    # Deterministic ordering: newest -> oldest by (date, time), then id
    rows.sort(
        key=lambda r: (
            str(r.get("date_local") or ""),
            str(r.get("start_time_local") or ""),
            str(r.get("id") or ""),
        ),
        reverse=True,
    )

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    if args.full:
        print("Full export: fetching all activities")
    elif latest_dt:
        print(f"Incremental export: fetching activities after {latest_dt.isoformat()}")
    else:
        print("Initial export: fetching all activities")

    print(f"Wrote {len(rows)} total activities to {OUT_PATH}")


if __name__ == "__main__":
    main()
