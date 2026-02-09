#!/usr/bin/env python3
"""
Generate a human-readable activity log from archived JSON.

Input:
  archive/activities/*.json

Output:
  reports/activity_log.txt

Newest -> oldest.
Runs include pace and total time.
Walks / hikes / rides include distance only.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVITIES_DIR = PROJECT_ROOT / "archive" / "activities"
OUT_PATH = PROJECT_ROOT / "reports" / "activity_log.txt"

DELIM = " -- "

RUN_TYPES = {"Run", "TrailRun", "VirtualRun"}


# ---------- helpers ----------


def pad_left(s: str, width: int) -> str:
    return s.rjust(width)


def pad_right(s: str, width: int) -> str:
    return s.ljust(width)


def safe_float(x: Any) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def safe_int(x: Any) -> int:
    try:
        return int(x)
    except (TypeError, ValueError):
        return 0


def meters_to_miles(meters: float) -> float:
    return meters / 1609.344 if meters else 0.0


def seconds_to_mmss(seconds: int) -> str:
    mm = seconds // 60
    ss = seconds % 60
    return f"{mm}:{ss:02d}"


def parse_iso_datetime(s: Any) -> Optional[datetime]:
    if not isinstance(s, str) or not s.strip():
        return None
    try:
        s2 = s.replace("Z", "+00:00").replace(" ", "T")
        return datetime.fromisoformat(s2)
    except Exception:
        return None


def extract_type_str(activity: dict) -> str:
    raw = activity.get("type") or activity.get("sport_type") or ""
    if not isinstance(raw, str):
        raw = str(raw)

    if "root=" in raw:
        q1 = raw.find("'")
        q2 = raw.find("'", q1 + 1)
        if q1 != -1 and q2 != -1:
            return raw[q1 + 1 : q2]

    return raw.strip()


def is_run(activity: dict) -> bool:
    return extract_type_str(activity) in RUN_TYPES


# ---------- main ----------


def main() -> None:
    if not ACTIVITIES_DIR.exists():
        raise FileNotFoundError(f"Missing archive directory: {ACTIVITIES_DIR}")

    activities = []

    for p in ACTIVITIES_DIR.glob("*.json"):
        try:
            a = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue

        if not isinstance(a, dict):
            continue

        dt = parse_iso_datetime(a.get("start_date_local")) or parse_iso_datetime(
            a.get("start_date")
        )
        if dt is None:
            continue

        activities.append((dt, a))

    # Newest -> oldest
    activities.sort(key=lambda x: x[0], reverse=True)

    lines: list[str] = []

    for dt, a in activities:
        date_str = dt.date().isoformat()

        type_str = extract_type_str(a)
        type_col = pad_right(type_str, 4)

        meters = safe_float(a.get("distance"))
        dist_mi = meters_to_miles(meters)
        dist_col = f"{dist_mi:>5.2f}"

        if is_run(a):
            moving_seconds = safe_int(a.get("moving_time"))
            pace_mmss = (
                seconds_to_mmss(int(round(moving_seconds / dist_mi)))
                if dist_mi > 0 and moving_seconds > 0
                else ""
            )
            time_mmss = seconds_to_mmss(moving_seconds)

            pace_col = pad_left(pace_mmss, 5) + "/mi"
            time_col = pad_left(time_mmss, 6) + "min"

            line = (
                f"{date_str}"
                f"{DELIM}{type_col}"
                f"{DELIM}{dist_col}"
                f"{DELIM}{pace_col}"
                f"{DELIM}{time_col}"
            )
        else:
            line = f"{date_str}" f"{DELIM}{type_col}" f"{DELIM}{dist_col}"

        lines.append(line)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {len(lines)} lines to {OUT_PATH}")


if __name__ == "__main__":
    main()
