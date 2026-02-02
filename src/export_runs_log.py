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


def main() -> None:
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Missing {CSV_PATH}. Run export_csv.py first.")

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Group runs by (year, month)
    by_month: dict[tuple[int, int], list[RunRow]] = defaultdict(list)

    for r in rows:
        typ = r.get("type", "")
        if not is_run(typ):
            continue

        date_local = r.get("date_local", "")
        try:
            d = date.fromisoformat(date_local)
        except ValueError:
            # If date is malformed, skip (or you could bucket it separately)
            continue

        by_month[(d.year, d.month)].append(
            RunRow(
                date_str=d.strftime("%Y-%m-%d"),
                dist_mi=safe_float(r.get("distance_mi", "")),
                pace_mmss=(r.get("pace_mmss") or "").strip(),
                moving_time_min=safe_float(r.get("moving_time_min", "")),
            )
        )

    # Month order: newest -> oldest
    month_keys = sorted(by_month.keys(), reverse=True)

    lines: list[str] = []

    for year, month in month_keys:
        month_name = date(year, month, 1).strftime("%B %Y")
        lines.append(f"{month_name}\n")

        # Runs already newest->oldest in the CSV, but grouping can disrupt that.
        # Sort newest->oldest by date string (YYYY-MM-DD) descending.
        month_runs = sorted(by_month[(year, month)], key=lambda rr: rr.date_str, reverse=True)

        total_miles = 0.0
        total_seconds = 0

        for rr in month_runs:
            dist_col = f"{rr.dist_mi:>5.2f}mi"
            pace_col = pad_left(rr.pace_mmss, 5) + "/mi"
            time_mmss = hhmm_from_minutes(rr.moving_time_min)
            time_col = pad_left(time_mmss, 6) + "min"

            line = f"{rr.date_str}{DELIM}{dist_col}{DELIM}{pace_col}{DELIM}{time_col}"
            lines.append(line)

            total_miles += rr.dist_mi
            total_seconds += int(round(rr.moving_time_min * 60))

        lines.append(SEP)
        lines.append(f"Total miles: {total_miles:.2f}")
        lines.append(f"Total time: {fmt_total_mmss(total_seconds)}")

        if total_miles > 0 and total_seconds > 0:
            avg_pace_sec_per_mi = int(round(total_seconds / total_miles))
            lines.append(f"Average pace: {fmt_total_mmss(avg_pace_sec_per_mi)}/mi")
        else:
            lines.append("Average pace: ")

        lines.append("\n")  # blank line between months

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")

    print(f"Wrote {len(month_keys)} month blocks to {OUT_PATH}")


if __name__ == "__main__":
    main()
