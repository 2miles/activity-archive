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
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVITIES_DIR = PROJECT_ROOT / "archive" / "activities"
OUT_PATH = PROJECT_ROOT / "reports" / "runs_log.txt"

DELIM = " -- "
SEP = "-" * 46
BIG_SEP = "=" * 46

# If your archive stores type/sport_type as strings like "root='Run'",
# this will still work. If you later normalize to plain "Run", it also works.
RUN_TYPES = {"Run", "TrailRun", "VirtualRun"}


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


def seconds_to_hhmmss(total_seconds: int) -> str:
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def seconds_to_mmss(total_seconds: int) -> str:
    mm = total_seconds // 60
    ss = total_seconds % 60
    return f"{mm}:{ss:02d}"


def pad_left(s: str, width: int) -> str:
    return s.rjust(width)


def parse_iso_datetime(s: Any) -> Optional[datetime]:
    if not isinstance(s, str) or not s.strip():
        return None
    try:
        # Handles "2026-01-18 21:50:17+00:00" or "2026-01-18T21:50:17+00:00"
        s2 = s.replace("Z", "+00:00").replace(" ", "T")
        return datetime.fromisoformat(s2)
    except Exception:
        return None


def extract_type_str(activity: dict) -> str:
    """
    Your archive currently stores 'type' / 'sport_type' like "root='Walk'".
    Normalize to "Walk" / "Run" etc. when possible.
    """
    raw = activity.get("type") or activity.get("sport_type") or ""
    if not isinstance(raw, str):
        raw = str(raw)

    # Try to pull from "root='Run'"
    if "root=" in raw:
        # crude but effective
        # e.g. "root='Run'" -> Run
        q1 = raw.find("'")
        q2 = raw.find("'", q1 + 1) if q1 != -1 else -1
        if q1 != -1 and q2 != -1 and q2 > q1:
            return raw[q1 + 1 : q2]

    return raw.strip()


def is_run(activity: dict) -> bool:
    t = extract_type_str(activity)
    return t in RUN_TYPES


@dataclass(frozen=True)
class RunRow:
    date_str: str
    dist_mi: float
    pace_mmss: str
    moving_seconds: int


def compute_pace_mmss(dist_mi: float, moving_seconds: int) -> str:
    if dist_mi <= 0 or moving_seconds <= 0:
        return ""
    pace_sec_per_mi = int(round(moving_seconds / dist_mi))
    return seconds_to_mmss(pace_sec_per_mi)


def load_runs_by_month(activities_dir: Path) -> dict[tuple[int, int], list[RunRow]]:
    if not activities_dir.exists():
        raise FileNotFoundError(f"Missing activities archive dir: {activities_dir}")

    by_month: dict[tuple[int, int], list[RunRow]] = defaultdict(list)

    for p in sorted(activities_dir.glob("*.json")):
        try:
            activity = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue

        if not isinstance(activity, dict):
            continue
        if not is_run(activity):
            continue

        # Prefer local timestamp for month grouping
        dt_local = parse_iso_datetime(activity.get("start_date_local"))
        if dt_local is None:
            # fallback: UTC start_date, then treat as date in UTC
            dt_local = parse_iso_datetime(activity.get("start_date"))
        if dt_local is None:
            continue

        d = dt_local.date()

        meters = safe_float(activity.get("distance"))
        dist_mi = meters_to_miles(meters)

        moving_seconds = safe_int(activity.get("moving_time"))
        pace_mmss = compute_pace_mmss(dist_mi, moving_seconds)

        by_month[(d.year, d.month)].append(
            RunRow(
                date_str=d.strftime("%Y-%m-%d"),
                dist_mi=dist_mi,
                pace_mmss=pace_mmss,
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

    # Month order: newest -> oldest
    month_keys = sorted(runs_by_month.keys(), reverse=True)

    lines: list[str] = []
    for year, month in month_keys:
        lines.extend(render_month_block(year, month, runs_by_month[(year, month)]))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    print(f"Wrote {len(month_keys)} month blocks to {OUT_PATH}")


if __name__ == "__main__":
    main()
