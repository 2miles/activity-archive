#!/usr/bin/env python3
"""
Export Strava activities to a JSON archive (one file per activity).

- Uses project's get_client() (token.json + auto refresh)
- Fetches SummaryActivity list via client.get_activities()
- Fetches DetailedActivity per id via client.get_activity(id)
- Writes: archive/activities/<activity_id>.json
- Skips existing files unless --force

Usage:
  python3 src/export_activities_json.py
  python3 src/export_activities_json.py --limit 50
  python3 src/export_activities_json.py --force
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from client import get_client


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "archive" / "activities"


def jsonable(v: Any) -> Any:
    """Make values JSON-serializable with minimal distortion."""
    # datetime/date -> isoformat
    try:
        if hasattr(v, "isoformat"):
            return v.isoformat()
    except Exception:
        pass

    # Pint Quantity (distance, elevation, etc.) -> string like "10645.6 meter"
    try:
        if hasattr(v, "magnitude") and hasattr(v, "units"):
            return str(v)
    except Exception:
        pass

    # Dict/list recurse
    if isinstance(v, dict):
        return {str(k): jsonable(val) for k, val in v.items()}
    if isinstance(v, (list, tuple)):
        return [jsonable(val) for val in v]

    # Basic JSON types
    try:
        json.dumps(v)
        return v
    except TypeError:
        return str(v)


def activity_to_dict(a: Any) -> dict:
    """
    Convert stravalib DetailedActivity to a JSON-friendly dict.
    Uses __dict__ (what stravalib populated) and removes client reference.
    """
    data = dict(getattr(a, "__dict__", {}))
    data.pop("bound_client", None)
    return {k: jsonable(v) for k, v in data.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Strava DetailedActivity JSON files.")
    parser.add_argument(
        "--limit", type=int, default=None, help="Max activities to export (default: all)"
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing JSON files")
    parser.add_argument(
        "--sleep", type=float, default=0.0, help="Seconds to sleep between per-activity calls"
    )
    args = parser.parse_args()

    client = get_client()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    n_total = 0
    n_written = 0
    n_skipped = 0

    # This returns SummaryActivity iterator (lightweight)
    activities_iter = client.get_activities(limit=args.limit)

    first = True
    for act in activities_iter:
        if first:
            print("First activity id:", act.id)
            first = False
        n_total += 1
        activity_id = act.id
        out_path = OUT_DIR / f"{activity_id}.json"

        if out_path.exists() and not args.force:
            n_skipped += 1
            continue

        detailed = client.get_activity(activity_id)
        data = activity_to_dict(detailed)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        n_written += 1

        if args.sleep > 0:
            time.sleep(args.sleep)

        if n_total % 25 == 0:
            print(f"Processed {n_total} | wrote {n_written} | skipped {n_skipped}")

    print(f"Done. Processed {n_total} | wrote {n_written} | skipped {n_skipped}")
    print(f"Output: {OUT_DIR}")


if __name__ == "__main__":
    main()
