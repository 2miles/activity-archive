"""
Export Strava activities to a JSON archive (one file per activity).

Design goals:
- JSON-first archival: one file per activity id
- --limit means "write N new JSON files" (NOT "list N summaries")
- Modes:
  --new   : download activities AFTER newest archived (incremental sync)
  --older : download activities BEFORE oldest archived (backfill)
- Always uses client.get_activity(id) for downloads (DetailedActivity)
- Skips existing files unless --force
- Atomic writes to avoid partial JSON files
- Avoid burning API calls on "checking" (checks are filesystem-only)

Usage:
  # backfill older history: write 100 more (older than your oldest archived)
  python3 src/export_activities_json.py --older --limit 100 --sleep 0.6

  # incremental sync: write up to 25 new activities since last sync
  python3 src/export_activities_json.py --new --limit 25 --sleep 0.2

  # first run (no archive yet): just pull the most recent N
  python3 src/export_activities_json.py --limit 50 --sleep 0.6

  # overwrite existing files
  python3 src/export_activities_json.py --older --limit 50 --force
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Tuple

from client import get_client


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "archive" / "activities"


def parse_iso(dt_str: str) -> Optional[datetime]:
    """Parse ISO datetime string to datetime. Returns None if invalid."""
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None


def get_archive_bounds() -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Return (oldest_start_date_utc, newest_start_date_utc) from archived JSON.
    Uses 'start_date' (UTC) field written in your archive.
    """
    oldest: Optional[datetime] = None
    newest: Optional[datetime] = None

    for p in OUT_DIR.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue

        d = data.get("start_date")
        if not isinstance(d, str):
            continue

        dt = parse_iso(d)
        if dt is None:
            continue

        if oldest is None or dt < oldest:
            oldest = dt
        if newest is None or dt > newest:
            newest = dt

    return oldest, newest


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


def atomic_write_json(path: Path, data: dict) -> None:
    """
    Write JSON to path atomically: write to .tmp then rename.
    Prevents partial files on Ctrl-C / crashes.
    """
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp_path.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Strava DetailedActivity JSON files.")

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Number of NEW activity JSON files to write (default: no limit)",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing JSON files")
    parser.add_argument(
        "--sleep", type=float, default=0.0, help="Seconds to sleep after each successful write"
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--new", action="store_true", help="Incremental sync: fetch after newest archived"
    )
    mode.add_argument("--older", action="store_true", help="Backfill: fetch before oldest archived")

    args = parser.parse_args()

    client = get_client()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    oldest, newest = get_archive_bounds()

    # Choose listing window
    #
    # IMPORTANT: we do NOT pass limit=... to get_activities(), because that limits LISTING,
    # not WRITES. We'll enforce args.limit based on n_written.
    list_kwargs: dict[str, Any] = {}

    if args.older:
        if oldest is None:
            print("Archive is empty; --older has nothing to anchor to. Fetching newest first.")
        else:
            list_kwargs["before"] = oldest
            print("Mode: older/backfill")
            print("Listing activities before oldest archived:", oldest.isoformat())
    elif args.new:
        if newest is None:
            print("Archive is empty; --new has nothing to anchor to. Fetching newest first.")
        else:
            list_kwargs["after"] = newest
            print("Mode: new/incremental")
            print("Listing activities after newest archived:", newest.isoformat())
    else:
        # Default behavior:
        # - If archive exists, act like --new (most common "sync" expectation).
        # - If archive empty, fetch newest first.
        if newest is None:
            print("Archive is empty; fetching newest first.")
        else:
            list_kwargs["after"] = newest
            print("Mode: default (sync like --new)")
            print("Listing activities after newest archived:", newest.isoformat())

    activities_iter = client.get_activities(**list_kwargs)

    n_listed = 0
    n_written = 0
    n_skipped = 0

    first = True
    try:
        for act in activities_iter:
            # Stop condition is WRITES, not listing/processing
            if args.limit is not None and n_written >= args.limit:
                break

            n_listed += 1
            activity_id = act.id
            out_path = OUT_DIR / f"{activity_id}.json"

            if first:
                print("First listed activity id:", activity_id)
                first = False

            # Zero-API check: purely filesystem
            if out_path.exists() and not args.force:
                n_skipped += 1
                continue

            # Expensive call: only happens when we actually intend to write
            detailed = client.get_activity(activity_id)
            data = activity_to_dict(detailed)

            atomic_write_json(out_path, data)
            n_written += 1

            if args.sleep > 0:
                time.sleep(args.sleep)

            if n_written % 25 == 0:
                print(f"Listed {n_listed} | wrote {n_written} | skipped {n_skipped}")

    except KeyboardInterrupt:
        print("\nInterrupted (Ctrl-C). Already-written files are safe.")
    finally:
        print(f"Done. Listed {n_listed} | wrote {n_written} | skipped {n_skipped}")
        print(f"Output: {OUT_DIR}")


if __name__ == "__main__":
    main()
