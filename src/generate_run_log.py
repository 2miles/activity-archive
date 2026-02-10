#!/usr/bin/env python3
"""
Generate a human-readable runs-only activity log from archived JSON.

Input:
  archive/activities/*.json

Output:
  reports/runs_log.txt

Newest -> oldest.
Runs include distance, pace, and total time.
Grouped by month with monthly aggregates.

Design:
- JSON-first: no Strava API calls, no CSV dependency.
- Uses archived "distance" (meters), "moving_time" (seconds), and "type"/"sport_type".
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from activity_archive.activity import is_run, parse_isoish_datetime
from activity_archive.archive import iter_activity_dicts
from activity_archive.units import (
    meters_to_miles,
    pace_mmss,
    safe_float,
    safe_int,
    seconds_to_hhmmss,
    seconds_to_mmss,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVITIES_DIR = PROJECT_ROOT / "archive" / "activities"
OUT_PATH = PROJECT_ROOT / "reports" / "runs_log.txt"

DELIM = " -- "
SEP = "-" * 46
BIG_SEP = "=" * 46


def pad_left(s: str, width: int) -> str:
    return s.rjust(width)


@dataclass(frozen=True)
class RunRow:
    date_str: str
    dist_mi: float
    pace_mmss: str
    moving_seconds: int


def load_runs_by_month(activities_dir: Path) -> dict[tuple[int, int], list[RunRow]]:
    if not activities_dir.exists():
        raise FileNotFoundError(f"Missing activities archive dir: {activities_dir}")

    by_month: dict[tuple[int, int], list[RunRow]] = defaultdict(list)

    for activity in iter_activity_dicts(activities_dir):
        if not is_run(activity):
            continue

        dt_local = parse_isoish_datetime(activity.get("start_date_local")) or parse_isoish_datetime(
            activity.get("start_date")
        )
        if dt_local is None:
            continue

        d = dt_local.date()

        meters = safe_float(activity.get("distance"))
        dist_mi = meters_to_miles(meters)

        moving_seconds = safe_int(activity.get("moving_time"))
        pace = pace_mmss(dist_mi, moving_seconds)

        by_month[(d.year, d.month)].append(
            RunRow(
                date_str=d.strftime("%Y-%m-%d"),
                dist_mi=dist_mi,
                pace_mmss=pace,
                moving_seconds=moving_seconds,
            )
        )

    return by_month


def render_month_block(year: int, month: int, runs: list[RunRow]) -> list[str]:
    month_name = date(year, month, 1).strftime("%B %Y")
    lines: list[str] = [BIG_SEP, month_name, SEP]

    month_runs = sorted(runs, key=lambda rr: rr.date_str, reverse=True)

    total_miles = 0.0
    total_seconds = 0

    for rr in month_runs:
        dist_col = f"{rr.dist_mi:>5.2f}mi"
        pace_col = pad_left(rr.pace_mmss, 5) + "/mi" if rr.pace_mmss else pad_left("", 5)
        time_col = pad_left(seconds_to_mmss(rr.moving_seconds), 6) + "min"

        lines.append(f"{rr.date_str}{DELIM}{dist_col}{DELIM}{pace_col}{DELIM}{time_col}")

        total_miles += rr.dist_mi
        total_seconds += rr.moving_seconds

    lines.append(SEP)
    run_count = len(month_runs)
    lines.append(f"Runs: {run_count}")
    lines.append(f"Miles: {total_miles:.2f}")
    lines.append(f"Time: {seconds_to_hhmmss(total_seconds)}")

    if total_miles > 0 and total_seconds > 0:
        avg_pace_sec_per_mi = int(round(total_seconds / total_miles))
        lines.append(f"Pace: {seconds_to_mmss(avg_pace_sec_per_mi)}/mi")
    else:
        lines.append("Pace: N/A")

    lines.append("\n")
    return lines


def main() -> None:
    runs_by_month = load_runs_by_month(ACTIVITIES_DIR)
    month_keys = sorted(runs_by_month.keys(), reverse=True)

    lines: list[str] = []
    for year, month in month_keys:
        lines.extend(render_month_block(year, month, runs_by_month[(year, month)]))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    print(f"Wrote {len(month_keys)} month blocks to {OUT_PATH}")


if __name__ == "__main__":
    main()
