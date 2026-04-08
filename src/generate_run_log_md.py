#!/usr/bin/env python3
"""
Generate a mobile-friendly Markdown runs log from archived activity JSON.

Input:
  archive/activities/*.json

Output:
  derived/reports/runs_log.md

Newest -> oldest.
Runs are grouped by month with a short monthly summary followed by compact
per-run bullets designed to read well on narrow screens.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
import os
from pathlib import Path

from activity_archive.activity import is_run, parse_iso_datetime
from activity_archive.archive import iter_activity_dicts
from activity_archive.units import (
    meters_to_miles,
    pace_mmss,
    safe_float,
    safe_int,
    seconds_to_hhmmss,
    seconds_to_mmss,
)
from activity_archive.paths import ACTIVITIES_DIR, RUNS_LOG_MD_PATH


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

        dt_local = parse_iso_datetime(activity.get("start_date_local")) or parse_iso_datetime(
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
    month_runs = sorted(runs, key=lambda rr: rr.date_str, reverse=True)

    total_miles = sum(rr.dist_mi for rr in month_runs)
    total_seconds = sum(rr.moving_seconds for rr in month_runs)

    lines = [f"## {month_name}", ""]
    lines.append(f"- Runs: **{len(month_runs)}**")
    lines.append(f"- Miles: **{total_miles:.2f}**")
    lines.append(f"- Time: **{seconds_to_hhmmss(total_seconds)}**")

    if total_miles > 0 and total_seconds > 0:
        avg_pace_sec_per_mi = int(round(total_seconds / total_miles))
        lines.append(f"- Avg pace: **{seconds_to_mmss(avg_pace_sec_per_mi)}/mi**")
    else:
        lines.append("- Avg pace: **N/A**")

    lines.append("")

    lines.append("day | miles | min/mi | time")
    lines.append("--- | ---: | ---: | ---:")

    for rr in month_runs:
        time_str = seconds_to_hhmmss(rr.moving_seconds)
        pace_str = rr.pace_mmss if rr.pace_mmss else "N/A"
        day_str = rr.date_str[5:].replace("-", " - ")
        lines.append(f"{day_str} | {rr.dist_mi:.2f} | {pace_str} | {time_str}")

    lines.append("")
    return lines


def get_optional_notes_runs_log_md_path() -> Path | None:
    notes_dir = os.getenv("ACTIVITY_ARCHIVE_NOTES_DIR", "").strip()
    if not notes_dir:
        return None
    return Path(notes_dir).expanduser() / "runs_log.md"


def main() -> None:
    runs_by_month = load_runs_by_month(ACTIVITIES_DIR)
    month_keys = sorted(runs_by_month.keys(), reverse=True)

    total_runs = sum(len(runs) for runs in runs_by_month.values())
    total_miles = sum(rr.dist_mi for runs in runs_by_month.values() for rr in runs)
    total_seconds = sum(rr.moving_seconds for runs in runs_by_month.values() for rr in runs)

    lines = ["# Run Log", ""]
    lines.append(f"- Months: **{len(month_keys)}**")
    lines.append(f"- Runs: **{total_runs}**")
    lines.append(f"- Miles: **{total_miles:.2f}**")
    lines.append(f"- Time: **{seconds_to_hhmmss(total_seconds)}**")

    if total_miles > 0 and total_seconds > 0:
        avg_pace_sec_per_mi = int(round(total_seconds / total_miles))
        lines.append(f"- Avg pace: **{seconds_to_mmss(avg_pace_sec_per_mi)}/mi**")
    else:
        lines.append("- Avg pace: **N/A**")

    lines.append("")

    for year, month in month_keys:
        lines.extend(render_month_block(year, month, runs_by_month[(year, month)]))

    content = "\n".join(lines).rstrip() + "\n"

    RUNS_LOG_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUNS_LOG_MD_PATH.write_text(content, encoding="utf-8")

    print(f"Wrote {len(month_keys)} month blocks to {RUNS_LOG_MD_PATH}")

    notes_path = get_optional_notes_runs_log_md_path()
    if notes_path is not None:
        notes_path.parent.mkdir(parents=True, exist_ok=True)
        notes_path.write_text(content, encoding="utf-8")
        print(f"Mirrored Markdown run log to {notes_path}")


if __name__ == "__main__":
    main()
