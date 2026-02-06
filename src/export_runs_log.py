"""
Generate a human-readable runs-only activity log from out/activities.csv.

Output:
  out/runs_log.txt

Newest -> oldest.
Runs include distance, pace, and total time.
Grouped by month with monthly aggregates.
"""

import csv
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import date


CSV_PATH = os.path.join("out", "activities.csv")
OUT_PATH = os.path.join("out", "runs_log.txt")

DELIM = " -- "
SEP = "-" * 46
BIG_SEP = "=" * 46


def pad_left(s: str, width: int) -> str:
    return s.rjust(width)


def pad_right(s: str, width: int) -> str:
    return s.ljust(width)


def hhmm_from_minutes(minutes_float) -> str:
    total_seconds = int(round(float(minutes_float) * 60))
    mm = total_seconds // 60
    ss = total_seconds % 60
    return f"{mm}:{ss:02d}"


def format_miles(mi_str: str, width: int = 5) -> str:
    mi = float(mi_str)
    return f"{mi:>{width}.2f}"


def is_run(type_str: str) -> bool:
    return type_str in {"Run", "TrailRun", "VirtualRun"}


def fmt_total_mmss(total_seconds: int) -> str:
    mm = total_seconds // 60
    ss = total_seconds % 60
    return f"{mm}:{ss:02d}"


def fmt_hhmmss(total_seconds: int) -> str:
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def safe_float(x: str) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


@dataclass(frozen=True)
class RunRow:
    date_str: str
    dist_mi: float
    pace_mmss: str
    moving_time_min: float


def load_runs_by_month(csv_path: str) -> dict[tuple[int, int], list[RunRow]]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        csv_rows = list(csv.DictReader(f))

    by_month: dict[tuple[int, int], list[RunRow]] = defaultdict(list)

    for csv_row in csv_rows:
        if not is_run(csv_row.get("type", "")):
            continue

        date_local = csv_row.get("date_local", "")
        try:
            d = date.fromisoformat(date_local)
        except ValueError:
            continue

        by_month[(d.year, d.month)].append(
            RunRow(
                date_str=d.strftime("%Y-%m-%d"),
                dist_mi=safe_float(csv_row.get("distance_mi", "")),
                pace_mmss=(csv_row.get("pace_mmss") or "").strip(),
                moving_time_min=safe_float(csv_row.get("moving_time_min", "")),
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
        pace_col = pad_left(rr.pace_mmss, 5) + "/mi"
        time_mmss = hhmm_from_minutes(rr.moving_time_min)
        time_col = pad_left(time_mmss, 6) + "min"

        lines.append(f"{rr.date_str}{DELIM}{dist_col}{DELIM}{pace_col}{DELIM}{time_col}")

        total_miles += rr.dist_mi
        total_seconds += int(round(rr.moving_time_min * 60))

    lines.append(SEP)
    run_count = len(month_runs)
    lines.append(f"Runs: {run_count}")
    lines.append(f"Miles: {total_miles:.2f}")
    lines.append(f"Time: {fmt_hhmmss(total_seconds)}")

    if total_miles > 0 and total_seconds > 0:
        avg_pace_sec_per_mi = int(round(total_seconds / total_miles))
        lines.append(f"Pace: {fmt_total_mmss(avg_pace_sec_per_mi)}/mi")
    else:
        lines.append("Pace: N/A")

    lines.append("\n")  # blank line between months
    return lines


def main() -> None:
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Missing {CSV_PATH}. Run export_csv.py first.")

    lines: list[str] = []
    runs_by_month = load_runs_by_month(CSV_PATH)

    # Month order: newest -> oldest
    month_keys = sorted(runs_by_month.keys(), reverse=True)

    for year, month in month_keys:
        lines.extend(render_month_block(year, month, runs_by_month[(year, month)]))

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")

    print(f"Wrote {len(month_keys)} month blocks to {OUT_PATH}")


if __name__ == "__main__":
    main()
