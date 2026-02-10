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

from datetime import datetime
from pathlib import Path

from activity_archive.archive import iter_activity_dicts
from activity_archive.activity import (
    activity_start_local,
    activity_type,
    is_run,
)
from activity_archive.units import (
    safe_float,
    safe_int,
    meters_to_miles,
    seconds_to_mmss,
    pace_mmss,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVITIES_DIR = PROJECT_ROOT / "archive" / "activities"
OUT_PATH = PROJECT_ROOT / "reports" / "activity_log.txt"

DELIM = " -- "


def pad_left(s: str, width: int) -> str:
    return s.rjust(width)


def pad_right(s: str, width: int) -> str:
    return s.ljust(width)


def main() -> None:
    if not ACTIVITIES_DIR.exists():
        raise FileNotFoundError(f"Missing archive directory: {ACTIVITIES_DIR}")

    activities: list[tuple[datetime, dict]] = []

    for a in iter_activity_dicts(ACTIVITIES_DIR):
        dt = activity_start_local(a)
        if dt is None:
            continue
        activities.append((dt, a))

    # Newest -> oldest
    activities.sort(key=lambda x: x[0], reverse=True)

    lines: list[str] = []

    for dt, a in activities:
        date_str = dt.date().isoformat()

        type_str = activity_type(a)
        type_col = pad_right(type_str, 4)

        meters = safe_float(a.get("distance"))
        dist_mi = meters_to_miles(meters)
        dist_col = f"{dist_mi:>5.2f}"

        if is_run(a):
            moving_seconds = safe_int(a.get("moving_time"))

            pace = pace_mmss(dist_mi, moving_seconds)
            time_mmss = seconds_to_mmss(moving_seconds)

            pace_col = pad_left(pace, 5) + "/mi"
            time_col = pad_left(time_mmss, 6) + "min"

            line = (
                f"{date_str}"
                f"{DELIM}{type_col}"
                f"{DELIM}{dist_col}"
                f"{DELIM}{pace_col}"
                f"{DELIM}{time_col}"
            )
        else:
            line = f"{date_str}{DELIM}{type_col}{DELIM}{dist_col}"

        lines.append(line)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {len(lines)} lines to {OUT_PATH}")


if __name__ == "__main__":
    main()
