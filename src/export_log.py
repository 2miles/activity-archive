"""
Generate a human-readable activity log from out/activities.csv.

Output:
  out/activity_log.txt

Newest -> oldest.
Runs include pace and total time.
Walks / hikes / rides include distance only.
"""

import csv
import os
from datetime import date


CSV_PATH = os.path.join("out", "activities.csv")
OUT_PATH = os.path.join("out", "activity_log.txt")

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

    # CSV is already newest -> oldest; keep that order
    lines = []

    for r in rows:
        date_local = r["date_local"]  # YYYY-MM-DD

        try:
            d = date.fromisoformat(date_local)
            date_str = d.strftime("%Y-%m-%d")
        except ValueError:
            date_str = date_local

        typ = r["type"]
        dist = r["distance_mi"]
        type_col = pad_right(typ, 4)
        # dist_col = pad_left(f"{dist}", 5) + "mi"
        dist_col = format_miles(dist)

        if is_run(typ):
            pace = r.get("pace_mmss", "")
            time_min = r.get("moving_time_min", "")
            time_hhmm = hhmm_from_minutes(time_min) if time_min else ""
            pace_col = pad_left(f"{pace}", 5) + "/mi"
            time_col = pad_left(f"{time_hhmm}", 6) + "min"

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

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Wrote {len(lines)} lines to {OUT_PATH}")


if __name__ == "__main__":
    main()
