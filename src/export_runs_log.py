"""
Generate a human-readable runs-only activity log from out/activities.csv.

Output:
  out/runs_log.txt

Newest -> oldest.
Runs include distance, pace, and total time.
"""

import csv
import os
from datetime import date


CSV_PATH = os.path.join("out", "activities.csv")
OUT_PATH = os.path.join("out", "runs_log.txt")

DELIM = " -- "


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


def main() -> None:
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Missing {CSV_PATH}. Run export_csv.py first.")

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    lines = []

    for r in rows:
        typ = r["type"]
        if not is_run(typ):
            continue

        date_local = r["date_local"]  # YYYY-MM-DD
        try:
            d = date.fromisoformat(date_local)
            date_str = d.strftime("%Y-%m-%d")
        except ValueError:
            date_str = date_local

        dist = r["distance_mi"]
        pace = r.get("pace_mmss", "")
        time_min = r.get("moving_time_min", "")

        type_col = pad_right("Run", 4)
        dist_col = format_miles(dist)
        pace_col = pad_left(pace, 5) + "/mi"
        time_col = pad_left(hhmm_from_minutes(time_min), 6) + "min"

        line = (
            f"{date_str}"
            f"{DELIM}{type_col}"
            f"{DELIM}{dist_col}"
            f"{DELIM}{pace_col}"
            f"{DELIM}{time_col}"
        )

        lines.append(line)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Wrote {len(lines)} runs to {OUT_PATH}")


if __name__ == "__main__":
    main()
