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

import argparse
import csv
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DIR = PROJECT_ROOT / "archive" / "activities"
OUT_DIR = PROJECT_ROOT / "derived"
OUT_PATH = OUT_DIR / "activities.csv"

DISTANCE_MI_DECIMALS = 2
MOVING_MIN_DECIMALS = 2
PACE_DECIMALS = 2
SPEED_MPH_DECIMALS = 2
ELAPSED_MIN_DECIMALS = 2
ELEV_FT_DECIMALS = 0

M_PER_MI = 1609.344
FT_PER_M = 3.280839895
MPS_TO_MPH = 2.2369362920544

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


ROOT_RE = re.compile(r"root='([^']+)'")

RUN_TYPES = {"Run", "TrailRun", "VirtualRun"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate activities CSV from archived JSON.")
    p.add_argument(
        "--archive-dir",
        default=str(ARCHIVE_DIR),
        help="Directory containing activity JSON files (default: archive/activities)",
    )
    p.add_argument(
        "--out",
        default=str(OUT_PATH),
        help="Output CSV path (default: derived/activities.csv)",
    )
    return p.parse_args()


def extract_root_string(v: Any) -> str:
    """
    Normalize activity type strings.

    Examples:
      "root='Walk'" -> "Walk"
      "Run"         -> "Run"
      None          -> ""
    """
    if v is None:
        return ""
    s = str(v)
    m = ROOT_RE.search(s)
    return m.group(1) if m else s


def parse_dt_maybe(dt_str: Optional[str]) -> Optional[datetime]:
    """
    Parse ISO-ish datetime strings.
    Supports:
      - 2026-01-18T13:50:17
      - 2026-01-18 13:50:17
      - 2026-01-18T21:50:17+00:00
      - ...Z
    """
    if not dt_str:
        return None
    s = dt_str.strip()
    s = s.replace("Z", "+00:00")
    # tolerate space separator
    if "T" not in s and " " in s:
        s = s.replace(" ", "T", 1)
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def hhmmss(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    return dt.strftime("%H:%M:%S")


def meters_to_miles(m: Optional[float]) -> float:
    if not m:
        return 0.0
    return float(m) / M_PER_MI


def meters_to_feet(m: Optional[float]) -> float:
    if not m:
        return 0.0
    return float(m) * FT_PER_M


def mps_to_mph(v: Optional[float]) -> float:
    if not v:
        return 0.0
    return float(v) * MPS_TO_MPH


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


def safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v)):
        return float(v)
    try:
        return float(v)
    except Exception:
        return None


def load_activity_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def activity_to_row(a: dict) -> Dict[str, Any]:
    activity_id = str(a.get("id") or "")

    type_str = extract_root_string(a.get("type"))
    sport_type_str = extract_root_string(a.get("sport_type"))
    # prefer "type", fall back to sport_type if needed
    activity_type = type_str or sport_type_str

    start_local = parse_dt_maybe(a.get("start_date_local"))
    date_local = start_local.date().isoformat() if start_local else ""
    time_local = hhmmss(start_local)

    distance_m = safe_float(a.get("distance")) or 0.0
    distance_mi = meters_to_miles(distance_m)

    moving_time_sec = safe_float(a.get("moving_time")) or 0.0
    elapsed_time_sec = safe_float(a.get("elapsed_time")) or 0.0

    moving_time_min = (moving_time_sec / 60.0) if moving_time_sec else 0.0
    elapsed_time_min = (elapsed_time_sec / 60.0) if elapsed_time_sec else 0.0

    elev_gain_m = safe_float(a.get("total_elevation_gain"))
    elev_ft = meters_to_feet(elev_gain_m) if elev_gain_m else 0.0

    avg_speed_mps = safe_float(a.get("average_speed"))
    avg_speed_mph = round(mps_to_mph(avg_speed_mps), SPEED_MPH_DECIMALS) if avg_speed_mps else 0.0

    pace_sec_mi = (
        pace_seconds_per_mile(distance_mi, moving_time_sec) if activity_type in RUN_TYPES else None
    )

    return {
        "id": activity_id,
        "date_local": date_local,
        "start_time_local": time_local,
        "type": activity_type,
        "distance_mi": round(distance_mi, DISTANCE_MI_DECIMALS) if distance_mi > 0 else "",
        "moving_time_min": (
            round(moving_time_min, MOVING_MIN_DECIMALS) if moving_time_min > 0 else ""
        ),
        "elapsed_time_min": (
            round(elapsed_time_min, ELAPSED_MIN_DECIMALS) if elapsed_time_min > 0 else ""
        ),
        "total_elev_gain_ft": round(elev_ft, ELEV_FT_DECIMALS) if elev_ft > 0 else "",
        "avg_speed_mph": avg_speed_mph if avg_speed_mph > 0 else "",
        "pace_mmss": seconds_to_mmss(pace_sec_mi),
        "pace_min_per_mi": round((pace_sec_mi / 60.0), PACE_DECIMALS) if pace_sec_mi else "",
        "name": (a.get("name") or "").strip(),
    }


def parse_row_datetime(row: Dict[str, str]) -> Optional[datetime]:
    date_s = (row.get("date_local") or "").strip()
    time_s = (row.get("start_time_local") or "").strip()
    if not date_s or not time_s:
        return None
    try:
        return datetime.fromisoformat(f"{date_s}T{time_s}")
    except ValueError:
        return None


def main() -> None:
    args = parse_args()
    archive_dir = Path(args.archive_dir)
    out_path = Path(args.out)

    if not archive_dir.exists():
        raise SystemExit(f"Archive dir not found: {archive_dir}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    n_bad = 0

    for p in sorted(archive_dir.glob("*.json")):
        data = load_activity_json(p)
        if not isinstance(data, dict):
            n_bad += 1
            continue
        rows.append(activity_to_row(data))

    # Drop empty ids (shouldn't happen, but keep CSV clean)
    rows = [r for r in rows if r.get("id")]

    # Deterministic ordering: newest -> oldest by (date, time), then id
    rows.sort(
        key=lambda r: (
            str(r.get("date_local") or ""),
            str(r.get("start_time_local") or ""),
            str(r.get("id") or ""),
        ),
        reverse=True,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} activities to {out_path}")
    if n_bad:
        print(f"Warning: skipped {n_bad} unreadable JSON files")


if __name__ == "__main__":
    main()
